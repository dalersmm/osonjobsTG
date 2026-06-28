import os
import json
import sqlite3
import urllib.request
import urllib.parse

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
MINI_APP_URL = os.environ.get('MINI_APP_URL', '')
DB_PATH = '/tmp/osonjobs.db'

# 12 viloyat kanallari
REGION_CHANNELS = {
    'toshkent': ['@tashkent_jobs', '@ish_toshkent'],
    'samarqand': ['@ish_samarqand', '@samarqand_jobs'],
    'andijon': ['@ish_andijon', '@andijon_jobs'],
    'namangan': ['@ish_namangan', '@namangan_jobs'],
    'fargona': ['@ish_fargona', '@fargona_jobs'],
    'buxoro': ['@ish_buxoro', '@buxoro_jobs'],
    'xorazm': ['@ish_xorazm', '@xorazm_jobs'],
    'qashqadaryo': ['@ish_qashqa', '@qashqa_jobs'],
    'surxondaryo': ['@ish_surxon', '@surxon_jobs'],
    'jizzax': ['@ish_jizzax', '@jizzax_jobs'],
    'navoiy': ['@ish_navoiy', '@navoiy_jobs'],
    'sirdaryo': ['@ish_sirdaryo', '@sirdaryo_jobs'],
}

# Viloyat nomlari (qidirish uchun)
REGION_NAMES = {
    'toshkent': '🏙️ Toshkent',
    'samarqand': '🏛️ Samarqand',
    'andijon': '🌿 Andijon',
    'namangan': '🏔️ Namangan',
    'fargona': '🌸 Farg\'ona',
    'buxoro': '📚 Buxoro',
    'xorazm': '💧 Xorazm',
    'qashqadaryo': '⛰️ Qashqadaryo',
    'surxondaryo': '🌄 Surxondaryo',
    'jizzax': '🌾 Jizzax',
    'navoiy': '⚗️ Navoiy',
    'sirdaryo': '🌊 Sirdaryo',
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id INTEGER PRIMARY KEY, channel TEXT, message_id INTEGER,
                  text TEXT, date TEXT, link TEXT, category TEXT, region TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY, username TEXT, first_name TEXT,
                  ref_by TEXT, joined_date TEXT, region TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (id INTEGER PRIMARY KEY, inviter_id TEXT, invited_id TEXT, date TEXT)''')
    conn.commit()
    conn.close()

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

def save_user_region(user_id, region):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET region=? WHERE user_id=?', (region, str(user_id)))
        conn.commit()
        conn.close()
    except:
        pass

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

def add_user(user_id, username, first_name, ref_by=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        from datetime import datetime
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, ref_by, joined_date)
                     VALUES (?, ?, ?, ?, ?)''',
                  (str(user_id), username, first_name, ref_by,
                   datetime.now().isoformat()))
        if ref_by:
            c.execute('''INSERT OR IGNORE INTO referrals (inviter_id, invited_id, date)
                         VALUES (?, ?, ?)''',
                      (ref_by, str(user_id), datetime.now().isoformat()))
            c.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id=?', (ref_by,))
            count = c.fetchone()[0]
            milestones = {3: '🎉 3 do\'st! Qidiruv ochildi!',
                         10: '💰 10 do\'st! $1 daromad!',
                         50: '💰 50 do\'st! $5 daromad!',
                         100: '💰 100 do\'st! $15 daromad!',
                         500: '💰 500 do\'st! $100 daromad!'}
            if count in milestones:
                send_message(ref_by, milestones[count])
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"add_user error: {e}")

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
        return {'ok': True, 'friends': friends, 'earnings': earnings,
                'searches_unlocked': friends >= 3}
    except:
        return {'ok': False, 'friends': 0, 'earnings': 0, 'searches_unlocked': False}

def send_message(chat_id, text, keyboard=None):
    try:
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        req = urllib.request.Request(url,
              data=json.dumps(data).encode(),
              headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"send_message error: {e}")

def get_mini_app_keyboard():
    return {
        'inline_keyboard': [[{
            'text': '🔍 Ish qidirish',
            'web_app': {'url': MINI_APP_URL}
        }]]
    }

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

def handle_update(update):
    try:
        init_db()

        # Callback query (viloyat tanlash)
        if 'callback_query' in update:
            cb = update['callback_query']
            user_id = cb['from']['id']
            data = cb.get('data', '')

            if data.startswith('region_'):
                region = data.replace('region_', '')
                save_user_region(user_id, region)
                region_name = REGION_NAMES.get(region, region)
                send_message(user_id,
                    f'✅ <b>{region_name}</b> viloyati saqlandi!\n\n'
                    f'Endi siz uchun {region_name} bo\'yicha ishlar ko\'rsatiladi. 👇',
                    get_mini_app_keyboard())
            return

        # Oddiy xabar
        if 'message' not in update:
            return

        msg = update['message']
        user_id = msg['from']['id']
        username = msg['from'].get('username', '')
        first_name = msg['from'].get('first_name', '')
        text = msg.get('text', '')

        # /start komandasi
        if text.startswith('/start'):
            parts = text.split()
            ref_by = parts[1].replace('ref_', '') if len(parts) > 1 else None
            add_user(user_id, username, first_name, ref_by)

            send_message(user_id,
                f'Salom, <b>{first_name}</b>! 👋\n\n'
                f'🏙️ Qaysi viloyatdasiz? Tanlang:',
                get_region_keyboard())
            return

        # Viloyat nomini yozsa
        region = detect_region(text)
        if region:
            save_user_region(user_id, region)
            region_name = REGION_NAMES.get(region, region)
            send_message(user_id,
                f'✅ <b>{region_name}</b> viloyati saqlandi!\n\n'
                f'Endi siz uchun {region_name} bo\'yicha ishlar ko\'rsatiladi. 👇',
                get_mini_app_keyboard())
            return

        # Boshqa xabar
        user_region = get_user_region(user_id)
        if user_region:
            region_name = REGION_NAMES.get(user_region, '')
            send_message(user_id,
                f'🔍 {region_name} bo\'yicha ishlarni ko\'rish uchun tugmani bosing 👇',
                get_mini_app_keyboard())
        else:
            send_message(user_id,
                '🏙️ Avval viloyatingizni tanlang:',
                get_region_keyboard())

    except Exception as e:
        print(f"handle_update error: {e}")

class handler:
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response

    def __iter__(self):
        try:
            if self.environ['REQUEST_METHOD'] == 'POST':
                length = int(self.environ.get('CONTENT_LENGTH', 0))
                body = self.environ['wsgi.input'].read(length)
                update = json.loads(body)
                handle_update(update)
                self.start_response('200 OK', [('Content-Type', 'application/json')])
                yield json.dumps({'ok': True}).encode()
            else:
                self.start_response('200 OK', [('Content-Type', 'application/json')])
                yield json.dumps({'ok': True, 'status': 'OsonJobs bot ishlayapti!'}).encode()
        except Exception as e:
            self.start_response('200 OK', [('Content-Type', 'application/json')])
            yield json.dumps({'ok': False, 'error': str(e)}).encode()