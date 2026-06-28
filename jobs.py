import json
import sqlite3
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

DB_PATH = '/tmp/osonjobs.db'

def get_jobs_from_db(category=None, limit=20):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if category and category != 'all':
            c.execute('SELECT text, link, channel, date, category FROM jobs WHERE category=? ORDER BY date DESC LIMIT ?',
                (category, limit))
        else:
            c.execute('SELECT text, link, channel, date, category FROM jobs ORDER BY date DESC LIMIT ?',
                (limit,))
        rows = c.fetchall()
        conn.close()
        jobs = []
        for row in rows:
            text = row[0] or ''
            lines = text.strip().split('\n')
            title = lines[0][:60] if lines else 'Vakansiya'
            jobs.append({
                'title': title,
                'text': text[:200],
                'link': row[1],
                'channel': row[2],
                'date': row[3],
                'category': row[4]
            })
        return jobs
    except Exception as e:
        print(f'DB error: {e}')
        return []

def get_hh_jobs(keyword='dasturchi', limit=20):
    try:
        params = urllib.parse.urlencode({
            'text': keyword,
            'area': 97,
            'per_page': limit,
            'order_by': 'relevance'
        })
        url = f'https://api.hh.ru/vacancies?{params}'
        req = urllib.request.Request(url, headers={'User-Agent': 'OsonJobs/1.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())
            jobs = []
            for item in data.get('items', []):
                salary = ''
                if item.get('salary'):
                    s = item['salary']
                    salary = f"{s.get('from', '')} - {s.get('to', '')} {s.get('currency', '')}".strip()
                jobs.append({
                    'title': item.get('name', ''),
                    'company': item.get('employer', {}).get('name', ''),
                    'location': item.get('area', {}).get('name', ''),
                    'salary': salary,
                    'link': item.get('alternate_url', ''),
                    'category': 'hh'
                })
            return jobs
    except Exception as e:
        print(f'HH error: {e}')
        return []

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            category = params.get('category', ['all'])[0]
            limit = int(params.get('limit', [20])[0])
            source = params.get('source', ['db'])[0]

            if source == 'hh':
                keyword = params.get('keyword', ['ish'])[0]
                jobs = get_hh_jobs(keyword, limit)
            else:
                jobs = get_jobs_from_db(category, limit)
                if not jobs:
                    jobs = get_hh_jobs('dasturchi' if category == 'it' else 'ish', limit)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'jobs': jobs}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode())

    def log_message(self, format, *args):
        pass