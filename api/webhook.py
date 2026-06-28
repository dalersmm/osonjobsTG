import json
import sqlite3
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# ========== CONFIG ==========
BOT_TOKEN = '8817825461:AAHlcXwNMDWYKWIWWWB7iGVlWP2MpT4ByAM'
DB_PATH = '/tmp/osonjobs.db'
MINI_APP_URL = 'https://osonjobs.vercel.app'
BOT_USERNAME = 'osonjobs_bot'

REGION_NAMES = {
    'toshkent':     '🏙 Toshkent',
    'samarqand':    '🕌 Samarqand',
    'andijon':      '🌿 Andijon',
    'namangan':     '🌸 Namangan',
    'fargona':      '🏔 Farg\'ona',
    'buxoro':       '🏺 Buxoro',
    'xorazm':       '🌊 Xorazm',
    'qashqadaryo':  '⛰ Qashqadaryo',
    'surxondaryo':  '🌄 Surxondaryo',
    'jizzax':       '🌾 Jizzax',
    'navoiy':       '💎 Navoiy',
    'sirdaryo':     '🌊 Sirdaryo',
}

REGION_KEYWORDS = {
    'toshkent':    ['toshkent', 'toshkentda', 'тошкент'],
    'samarqand':   ['samarqand', 'самарқанд'],
    'andijon':     ['andijon', 'андижон'],
    'namangan':    ['namangan', 'наманган'],
    'fargona':     ['fargona', 'fergana', 'фарғона'],
    'buxoro':      ['buxoro', 'bukhara', 'бухоро'],
    'xorazm':      ['xorazm', 'хоразм'],
    'qashqadaryo': ['qashqadaryo', 'қашқадарё'],
    'surxondaryo': ['surxondaryo', 'сурхондарё'],
    'jizzax':      ['jizzax', 'жиззах'],
    'navoiy':      ['navoiy', 'навоий'],
    'sirdaryo':    ['sirdaryo', 'сирдарё'],
}

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        ref_by TEXT,
        joined_date TEXT,
        region TEXT DEFAULT 'toshkent'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id TEXT,
        invited_id TEXT,
        date TEXT
    )''')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, ref_by=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT user_id FROM users WHERE user_id=?', (str(user_id),))
        exists = c.fetchone()
        if not exists:
            from datetime import datetime
            c.execute(
                'INSERT INTO users (user_id, username, first_name, ref_by, joined_date) VALUES (?,?,?,?,?)',
                (str(user_id), username or '', first_name or '', str(ref_by) if ref_by else None, datetime.now().isoformat())
            )
            conn.commit()
            if ref_by:
                c.execute('SELECT user_id FROM users WHERE user_id=?', (str(ref_by),))
                if c.fetchone():
                    c.execute(
                        'INSERT INTO referrals (inviter_id, invited_id, date) VALUES (?,?,?)',
                        (str(ref_by), str(user_id), datetime.now().isoformat())
                    )
                    conn.commit()
                    count = get_referral_count(ref_by, conn)
                    conn.close()
                    send_milestone(ref_by, count)
                    return
        conn.close()
    except Exception as e:
        print(f"add_user xato: {e}")

def get_referral_count(user_id, conn=None):
    close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close = True
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id=?', (str(user_id),))
    count = c.fetchone()[0]
    if close:
        conn.close()
    return count

def save_user_region(user_id, region):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET region=? WHERE user_id=?', (region, str(user_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"save_region xato: {e}")

def get_user_region(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT region FROM users WHERE user_id=?', (str(user_id),))
        row = c.fetchone()
        conn.close()
        return row[0] if row and row[0] else 'toshkent'
    except:
        return 'toshkent'

def get_referral_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id=?', (str(user_id),))
        friends = c.fetchone()[0]
        c.execute('SELECT region FROM users WHERE user_id=?', (str(user_id),))
        row = c.fetchone()
        region = row[0] if row and row[0] else 'toshkent'
        conn.close()
        earnings = 0
        if friends >= 500: earnings = 100
        elif friends >= 100: earnings = 15
        elif friends >= 50: earnings = 5
        elif friends >= 10: earnings = 1
        return {'friends': friends, 'earnings': earnings, 'region': region}
    except:
        return {'friends': 0, 'earnings': 0, 'region': 'toshkent'}

# ========== TELEGRAM API ==========
def send_message(chat_id, text, reply_markup=None):
    try:
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data=body,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"send_message xato: {e}")

def get_mini_app_keyboard():
    return {
        'inline_keyboard': [[{
            'text': '🚀 OsonJobs ni ochish',
            'web_app': {'url': MINI_APP_URL}
        }]]
    }

def get_region_keyboard():
    regions = list(REGION_NAMES.items())
    keyboard = []
    for i in range(0, len(regions), 2):
        row = [{'text': regions[i][1], 'callback_data': f'region_{regions[i][0]}'}]
        if i + 1 < len(regions):
            row.append({'text': regions[i+1][1], 'callback_data': f'region_{regions[i+1][0]}'})
        keyboard.append(row)
    return {'inline_keyboard': keyboard}

def send_milestone(user_id, count):
    milestones = {
        3:   ('🔓', "3 do'st chaqirdingiz! Endi yangi qidiruvdan foydalana olasiz!"),
        10:  ('💵', "10 do'st! $1 mukofot qo'shildi!"),
        50:  ('💰', "50 do'st! $5 mukofot qo'shildi!"),
        100: ('🏆', "100 do'st! $15 mukofot qo'shildi!"),
        500: ('🚀', "500 do'st! $100 mukofot qo'shildi! Siz champion!"),
    }
    if count in milestones:
        icon, text = milestones[count]
        send_message(user_id, f"{icon} Tabriklaymiz!\n\n{text}")

# ========== UPDATE HANDLER ==========
def handle_update(update):
    try:
        # Callback query (region tanlash)
        if 'callback_query' in update:
            cq = update['callback_query']
            chat_id = cq['message']['chat']['id']
            data = cq.get('data', '')

            if data.startswith('region_'):
                region = data.replace('region_', '')
                save_user_region(chat_id, region)
                region_name = REGION_NAMES.get(region, region)
                send_message(
                    chat_id,
                    f"✅ Viloyat saqlandi: <b>{region_name}</b>\n\nEndi OsonJobs ni oching va ishlarni ko'ring! 👇",
                    get_mini_app_keyboard()
                )
            return

        # Message
        if 'message' not in update:
            return

        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '')
        user = msg.get('from', {})

        # /start
        if text.startswith('/start'):
            parts = text.split()
            ref_by = None
            if len(parts) > 1 and parts[1].startswith('ref_'):
                try:
                    ref_by = int(parts[1].replace('ref_', ''))
                    if ref_by == chat_id:
                        ref_by = None
                except:
                    ref_by = None

            add_user(chat_id, user.get('username'), user.get('first_name'), ref_by)

            send_message(
                chat_id,
                f"👋 Salom, <b>{user.get('first_name', 'Do\'st')}</b>!\n\n"
                f"🏙 Avval viloyatingizni tanlang:",
                get_region_keyboard()
            )
            return

        # Region detect from text
        text_lower = text.lower()
        for region, keywords in REGION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                save_user_region(chat_id, region)
                region_name = REGION_NAMES.get(region, region)
                send_message(
                    chat_id,
                    f"✅ Viloyat aniqlandi: <b>{region_name}</b>\n\nOsonJobs ni oching! 👇",
                    get_mini_app_keyboard()
                )
                return

        # Default
        send_message(
            chat_id,
            "👇 OsonJobs ni oching:",
            get_mini_app_keyboard()
        )

    except Exception as e:
        print(f"handle_update xato: {e}")

# ========== HANDLER ==========
class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            update = json.loads(body)
            init_db()
            handle_update(update)
            self._respond({'ok': True})
        except Exception as e:
            print(f"POST xato: {e}")
            self._respond({'ok': False})

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        user_id = query.get('user_id', ['guest'])[0]
        init_db()
        stats = get_referral_stats(user_id)
        self._respond(stats)

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
