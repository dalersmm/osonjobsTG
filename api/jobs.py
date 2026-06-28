import json
import urllib.request
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler
import urllib.parse

REGION_CHANNELS = {
    'toshkent': [
        '@ishtopuz_rasmiy',
        '@vakansiya_ishchikerak_toshkent',
        '@ishtoparuz_kanal',
        '@ish_qidiring',
        '@manavakansiya_uz',
    ],
    'samarqand': [],
    'andijon': [],
    'namangan': [],
    'fargona': [],
    'buxoro': [],
    'xorazm': [],
    'qashqadaryo': [],
    'surxondaryo': [],
    'jizzax': [],
    'navoiy': [],
    'sirdaryo': [],
}

def get_rss_jobs(channel):
    try:
        username = channel.replace('@', '')
        url = f"https://tgstat.ru/channel/@{username}/rss"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        response = urllib.request.urlopen(req, timeout=5)
        root = ET.fromstring(response.read())
        jobs = []
        for item in root.findall('.//item')[:5]:
            title = item.findtext('title') or ''
            link  = item.findtext('link')  or ''
            desc  = item.findtext('description') or ''
            text  = title if title else desc[:150]
            text  = text.replace('<![CDATA[', '').replace(']]>', '').strip()
            if text and link:
                jobs.append({
                    'text'   : text[:200],
                    'link'   : link,
                    'channel': f"@{username}"
                })
        return jobs
    except Exception as e:
        print(f"RSS xato {channel}: {e}")
        return []

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        query  = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        region = query.get('region', ['toshkent'])[0].lower()
        channels = REGION_CHANNELS.get(region, REGION_CHANNELS['toshkent'])

        all_jobs = []
        for ch in channels[:3]:
            all_jobs.extend(get_rss_jobs(ch))
            if len(all_jobs) >= 15:
                break

        self._respond({'ok': True, 'jobs': all_jobs[:20]})

    def do_OPTIONS(self):
        self._respond({'ok': True})

    def _respond(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass
