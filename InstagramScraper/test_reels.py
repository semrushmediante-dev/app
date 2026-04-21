import os
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = r'D:\playwright-browsers'

import requests
from datetime import datetime, timedelta

RAPIDAPI_KEY = '44402f3fdamsh8f809a3de0bd410p1308a7jsn31b643963a88'
RAPIDAPI_HOST = 'instagram-api-fast-reliable-data-scraper.p.rapidapi.com'
HEADERS = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST,
    'Content-Type': 'application/json'
}

# Calcular semana anterior
today = datetime.now()
days_since_monday = today.weekday()
last_monday = today - timedelta(days=days_since_monday + 7)
last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)

print(f"Hoy: {today.strftime('%d/%m/%Y %A')}")
print(f"Semana anterior: {last_monday.strftime('%d/%m/%Y')} → {last_sunday.strftime('%d/%m/%Y')}")
print()

# Obtener perfil
username = 'lascuatroesquinas'
r = requests.get(f'https://{RAPIDAPI_HOST}/profile', headers=HEADERS, params={'username': username})
profile = r.json()
user_id = profile.get('pk')
print(f"User ID de @{username}: {user_id}")
print()

# Obtener reels
r2 = requests.get(f'https://{RAPIDAPI_HOST}/reels', headers=HEADERS, params={'user_id': str(user_id), 'include_feed_video': 'true'})
data = r2.json()
items = data.get('data', {}).get('items', [])

print(f"Total reels obtenidos: {len(items)}")
print()
print("Fechas de los últimos 10 reels:")
for i, item in enumerate(items[:10]):
    media = item.get('media', {})
    taken_at = media.get('taken_at')
    play_count = media.get('play_count', 0)
    if taken_at:
        post_date = datetime.fromtimestamp(int(taken_at))
        en_semana = "✅ EN SEMANA" if last_monday <= post_date <= last_sunday else "❌ fuera"
        print(f"  Post {i+1}: {post_date.strftime('%d/%m/%Y')} | plays: {play_count} | {en_semana}")
