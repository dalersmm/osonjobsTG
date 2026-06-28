import os
import json
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8817825461:AAHlcXwNMDWYKWIWWWB7iGVlWP2MpT4ByAM')
MINI_APP_URL = os.environ.get('MINI_APP_URL', 'https://osonjobs.vercel.app')
DB_PATH = '/tmp/osonjobs.db'

REGION_CHANNELS = {
    'toshkent': [
        '@ishtopuz_rasmiy',
        '@vakansiya_ishchikerak_toshkent',
        '@ishtoparuz_kanal',
        '@ish_qidiring',
        '@manavakansiya_uz',
        '@vacancy_argos',
        '@ish_keremi',
        '@toshkent_ishlar_bormi',
        '@vakansyuz',
        '@Toshkent_Ishbor1',
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

REGION_NAMES = {
    'toshkent': '🏙️ Toshkent',
    'samarqand': '🏛️ Samarqand',
    'andijon': '🌿 Andijon',
    'namangan': '🏔️ Namangan',
    'fargona': '🌸 Fargona',
    'buxoro': '📚 Buxoro',
    'xorazm': '💧 Xorazm',
    'qashqadaryo': '⛰️ Qashqadaryo',
    'surxondaryo': '🌄 Surxondaryo',
    'jizzax': '🌾 Jizzax',
    'navoiy': '⚗️ Navoiy',
    'sirdaryo': '🌊 Sirdaryo',
}

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY, username TEXT, first_name TEXT,
                  ref_by TEXT, joined_date TEXT, region TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (id INTEGER PRIMARY KEY, inviter_id TEXT, invited_id TEXT, date TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, ref_by=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, ref_by, joined_date)
                     VALUES (?, ?, ?, ?, ?)''',
                  (str(user_id), username, first_name, ref_by, datetime.now().isoformat()))
        if ref_by:
            c.execute('''INSERT OR IGNORE INTO referrals (inviter_id, invited_id, date)
                         VALUES (?, ?, ?)''',
                      (ref_by, str(user_id), datetime.now().isoformat()))
            c.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id=?', (ref_by,))
            count = c.fetchone()[0]
            milestones = {
                3: "🎉 3 do'st! Qidiruv ochildi!",
                10: "💰 10 do'st! $1 daromad!",
                50: "💰 50 do'st! $5 daromad!",
                100: "💰 100 do'st! $15 daromad!",
                500: "💰 500 do'st! $100 daromad!"
            }
            if count in milestones:
                send_message(ref_by, milestones[count])
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"add_user error: {e}")

def save_user_region(user_id, region):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET region=? WHERE user_id=?', (region, str(user_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"save_user_region error: {e}")

def get_user_region(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT region FROM users WHERE user_id=?', (str(user_id),))
        row = c.fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    except:
        return None

def get_referral_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id=?', (str(user_id),))
        count = c.fetchone()[0]
        conn.close()
        earnings = 0
        if count >= 500: earnings = 100
        elif count >= 100: earnings = 15
        elif count >= 50: earnings = 5
        elif count >= 10: earnings = 1
        return {'friends': count, 'earnings': earnings}
    except:
        return {'friends': 0, 'earnings': 0}

# ========== HELPERS ==========
def detect_region(text):
    text = text.lower().strip()
    region_keywords = {
        'toshkent': ['toshkent', 'ташкент'],
        'samarqand': ['samarqand', 'самарканд'],
        'andijon': ['andijon', 'андижан'],
        'namangan': ['namangan', 'наманган'],
        'fargona': ['fargona', "farg'ona", 'фергана'],
        'buxoro': ['buxoro', 'бухара'],
        'xorazm': ['xorazm', 'хорезм'],
        'qashqadaryo': ['qashqa', 'qashqadaryo', 'кашкадарья'],
        'surxondaryo': ['surxon', 'surxondaryo', 'сурхандарья'],
        'jizzax': ['jizzax', 'джизак'],
        'navoiy': ['navoiy', 'навои'],
        'sirdaryo': ['sirdaryo', 'сырдарья'],
    }
    for region, keywords in region_keywords.items():
        for kw in keywords:
            if kw in text:
                return region
    return None

# ========== KEYBOARDS ==========
def get_region_keyboard():
    keyboard = []
    row = []
    for key, name in REGION_NAMES.items():
        row.append({'text': name, 'callback_data': f'region_{key}'})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return {'inline_keyboard': keyboard}

def get_mini_app_keyboard(region_name=''):
    text = f"🔍 {region_name} ishlarini ko'rish" if region_name else "🔍 Ish qidirish"
    return {
        'inline_keyboard': [[{
            'text': text,
            'web_app': {'url': MINI_APP_URL}
        }]]
    }

# ========== TELEGRAM API ==========
def send_message(chat_id, text, keyboard=None):
    try:
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"send_message error: {e}")

def answer_callback(callback_id):
    try:
        data = {'callback_query_id': callback_id}
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery'
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"answer_callback error: {e}")

# ========== MAIN HANDLER ==========
def handle_update(update):
    try:
        init_db()

        # Callback (viloyat tanlash)
        if 'callback_query' in update:
            cb = update['callback_query']
            user_id = cb['from']['id']
            data = cb.get('data', '')
            answer_callback(cb['id'])

            if data.startswith('region_'):
                region = data.replace('region_', '')
                save_user_region(user_id, region)
                region_name = REGION_NAMES.get(region, region)
                send_message(
                    user_id,
                    f'✅ <b>{region_name}</b> tanlandi!\n\n'
                    f'Endi {region_name} bo\'yicha ishlarni ko\'rishingiz mumkin 👇',
                    get_mini_app_keyboard(region_name)
                )
            return

        if 'message' not in update:
            return

        msg = update['message']
        user_id = msg['from']['id']
        username = msg['from'].get('username', '')
        first_name = msg['from'].get('first_name', 'Foydalanuvchi')
        text = msg.get('text', '')

        # /start
        if text.startswith('/start'):
            parts = text.split()
            ref_by = None
            if len(parts) > 1 and parts[1].startswith('ref_'):
                ref_by = parts[1].replace('ref_', '')
                if ref_by == str(user_id):
                    ref_by = None

            add_user(user_id, username, first_name, ref_by)

            send_message(
                user_id,
                f'Salom, <b>{first_name}</b>! 👋\n\n'
                f'OsonJobs - ish topish endi oson!\n\n'
                f'🏙️ Qaysi viloyatdasiz? Tanlang:',
                get_region_keyboard()
            )
            return

        # Matndan region aniqlash
        region = detect_region(text)
        if region:
            save_user_region(user_id, region)
            region_name = REGION_NAMES.get(region, region)
            send_message(
                user_id,
                f'✅ <b>{region_name}</b> saqlandi!\n\n'
                f'Ishlarni ko\'rish uchun tugmani bosing 👇',
                get_mini_app_keyboard(region_name)
            )
            return

        # Boshqa xabarlar
        user_region = get_user_region(user_id)
        if user_region:
            region_name = REGION_NAMES.get(user_region, '')
            send_message(
                user_id,
                f'👋 <b>{first_name}</b>!\n\n'
                f'📍 Hozirgi viloyat: <b>{region_name}</b>\n\n'
                f'Ishlarni ko\'rish yoki viloyatni o\'zgartirish:',
                {
                    'inline_keyboard': [
                        [{'text': f"🔍 {region_name} ishlarini ko'rish", 'web_app': {'url': MINI_APP_URL}}],
                        [{'text': '🏙️ Viloyatni o\'zgartirish', 'callback_data': 'change_region'}]
                    ]
                }
            )
        else:
            send_message(
                user_id,
                '🏙️ Avval viloyatingizni tanlang:',
                get_region_keyboard()
            )

    except Exception as e:
        print(f"handle_update error: {e}")

# ========== VERCEL HANDLER ==========
class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        # Referral stats API
        if '/api/referral' in self.path:
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                user_id = query.get('user_id', ['guest'])[0]
                stats = get_referral_stats(user_id)
                self._respond(200, stats)
            except Exception as e:
                self._respond(200, {'friends': 0, 'earnings': 0})
        else:
            self._respond(200, {'ok': True, 'status': 'OsonJobs bot ishlayapti!'})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            update = json.loads(body)
            handle_update(update)
        except Exception as e:
            print(f"POST error: {e}")
        finally:
            self._respond(200, {'ok': True})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass
