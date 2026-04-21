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

def get_reels_data(username):
    try:
        # Paso 1: Obtener user_id
        r = requests.get(f'https://{RAPIDAPI_HOST}/profile', headers=HEADERS, params={'username': username}, timeout=10)
        print(f"Profile status: {r.status_code}")
        profile = r.json()
        user_id = profile.get('pk') or profile.get('id')
        print(f"User ID: {user_id}")

        # Paso 2: Obtener reels
        r2 = requests.get(f'https://{RAPIDAPI_HOST}/reels', headers=HEADERS, params={'user_id': str(user_id), 'include_feed_video': 'true'}, timeout=10)
        print(f"Reels status: {r2.status_code}")
        data = r2.json()
        items = data.get('data', {}).get('items', [])
        print(f"Total items: {len(items)}")

        # Semana anterior
        today = datetime.now()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        print(f"Semana: {last_monday.strftime('%d/%m')} - {last_sunday.strftime('%d/%m')}")

        plays_week = []
        posts_with_video = 0
        likes_week = []
        comments_week = []

        for item in items:
            media = item.get('media', {})
            taken_at = media.get('taken_at')
            if taken_at:
                post_date = datetime.fromtimestamp(int(taken_at))
                in_week = last_monday <= post_date <= last_sunday
                print(f"  Post {post_date.strftime('%d/%m')} plays:{media.get('play_count')} en_semana:{in_week}")
                if in_week:
                    posts_with_video += 1
                    plays_week.append(media.get('play_count') or 0)
                    likes_week.append(media.get('like_count') or 0)
                    comments_week.append(media.get('comment_count') or 0)

        total_views = sum(plays_week)
        avg_views = round(total_views / len(plays_week), 1) if plays_week else 0
        avg_likes = round(sum(likes_week) / len(likes_week), 1) if likes_week else 0
        avg_comments = round(sum(comments_week) / len(comments_week), 1) if comments_week else 0

        print(f"\nResultado: {posts_with_video} posts | {total_views} views | {avg_likes} likes")
        return total_views, avg_views, posts_with_video, avg_likes, avg_comments

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 0, 0, 0

get_reels_data('lascuatroesquinas')
