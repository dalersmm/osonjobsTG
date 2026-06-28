import json
import urllib.request
import xml.etree.ElementTree as ET

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

def get_channel_rss(channel):
    try:
        username = channel.replace('@', '')
        url = f"https://tgstat.ru/channel/@{username}/rss"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=5)
        content = response.read()
        root = ET.fromstring(content)
        jobs = []
        for item in root.findall('.//item')[:5]:
            title = item.findtext('title') or ''
            link = item.findtext('link') or ''
            description = item.findtext('description') or ''
            text = title if title else description[:150]
            if text:
                jobs.append({
                    'text': text[:200],
                    'link': link,
                    'channel': f"@{username}"
                })
        return jobs
    except Exception as e:
        print(f"Xato {channel}: {e}")
        return []

def application(environ, start_response):
    region = environ.get('QUERY_STRING', '')
    region = region.replace('region=', '').strip().lower()

    channels = REGION_CHANNELS.get(region, [])
    all_jobs = []

    for channel in channels[:3]:  # Tezlik uchun 3 ta kanal
        jobs = get_channel_rss(channel)
        all_jobs.extend(jobs)

    result = json.dumps({'ok': True, 'jobs': all_jobs[:20]}, ensure_ascii=False)

    start_response('200 OK', [
        ('Content-Type', 'application/json'),
        ('Access-Control-Allow-Origin', '*'),
    ])
    return [result.encode()]
