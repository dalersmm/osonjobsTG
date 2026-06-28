import json
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler

DB_PATH = '/tmp/osonjobs.db'

def get_referral_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id=?', (str(user_id),))
        friends = c.fetchone()[0]
        conn.close()

        earnings = 0
        if friends >= 500: earnings = 100
        elif friends >= 100: earnings = 15
        elif friends >= 50: earnings = 5
        elif friends >= 10: earnings = 1

        return {
            'ok': True,
            'friends': friends,
            'earnings': earnings,
            'searches_unlocked': friends >= 3,
            'next_milestone': get_next_milestone(friends)
        }
    except Exception as e:
        return {
            'ok': False,
            'friends': 0,
            'earnings': 0,
            'searches_unlocked': False,
            'error': str(e)
        }

def get_next_milestone(friends):
    milestones = [3, 10, 50, 100, 500]
    for m in milestones:
        if friends < m:
            return m
    return 500

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            user_id = params.get('user_id', ['0'])[0]

            stats = get_referral_stats(user_id)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode())

    def log_message(self, format, *args):
        pass