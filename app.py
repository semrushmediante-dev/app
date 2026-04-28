import os
import json
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
import asyncio
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración explícita para evitar el error "Not Found" en Render
app = Flask(__name__, static_folder=os.getcwd(), static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'

# ═════════════════════════════════════════════════════════════
# ALMACENAMIENTO
# ═════════════════════════════════════════════════════════════

def load_data():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {"accounts": [], "history": []}

def save_data(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def get_data():
    return load_data()

# ═════════════════════════════════════════════════════════════
# LÓGICA DE SCRAPING (MEJORADA)
# ═════════════════════════════════════════════════════════════

def get_last_week_range():
    today = datetime.now().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    start_ts = int(datetime.combine(last_monday, datetime.min.time()).timestamp())
    end_ts = int(datetime.combine(last_sunday, datetime.max.time()).timestamp())
    label = f"{last_monday.strftime('%d/%m')} - {last_sunday.strftime('%d/%m/%Y')}"
    return start_ts, end_ts, label

async def scrape_profile(page, username, csrf=''):
    try:
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        headers = {
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
            'Referer': f'https://www.instagram.com/{username}/',
        }

        resp = await page.request.get(url, headers=headers)
        if not resp.ok:
            return {'success': False, 'error': f'IG Error {resp.status}'}

        data = await resp.json()
        user = data.get('data', {}).get('user')
        if not user:
            return {'success': False, 'error': 'Perfil privado o no encontrado'}

        followers = user.get('edge_followed_by', {}).get('count', 0)
        following = user.get('edge_follow', {}).get('count', 0)
        total_posts = user.get('edge_owner_to_timeline_media', {}).get('count', 0)
        
        start_ts, end_ts, week_label = get_last_week_range()
        edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
        
        reels_data = []
        for edge in edges:
            node = edge.get('node', {})
            ts = node.get('taken_at_timestamp', 0)
            if start_ts <= ts <= end_ts:
                reels_data.append({
                    'likes': node.get('edge_liked_by', {}).get('count', 0),
                    'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                    'views': node.get('video_view_count', 0) or 0
                })

        posts_week = len(reels_data)
        t_views = sum(r['views'] for r in reels_data)
        t_likes = sum(r['likes'] for r in reels_data)
        t_comments = sum(r['comments'] for r in reels_data)
        
        eng_rate = round(((t_likes + t_comments) / followers * 100), 2) if followers > 0 and posts_week > 0 else 0

        return {
            'success': True,
            'seguidores': followers,
            'following': following,
            'posts': total_posts,
            'posts_week': posts_week,
            'total_views_week': t_views,
            'avg_likes': round(t_likes / posts_week, 1) if posts_week > 0 else 0,
            'avg_comments': round(t_comments / posts_week, 1) if posts_week > 0 else 0,
            'avg_views': round(t_views / posts_week, 1) if posts_week > 0 else 0,
            'engagementRate': eng_rate,
            'week_label': week_label,
            'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ═════════════════════════════════════════════════════════════
# RUTAS DE NAVEGACIÓN
# ═════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/instagram')
def instagram_page():
    return send_from_directory(app.static_folder, 'indexInstagram.html')

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    usuario = request.json.get('usuario')
    if not usuario: return jsonify({"error": "No user"}), 400

    async def run_scrape():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context()
            if os.path.exists(COOKIES_FILE):
                with open(COOKIES_FILE, 'r') as f:
                    await context.add_cookies(json.load(f))
            page = await context.new_page()
            await page.goto('https://www.instagram.com/', wait_until='networkidle')
            cookies = await context.cookies()
            csrf = next((c['value'] for c in cookies if c['name'] == 'csrftoken'), '')
            res = await scrape_profile(page, usuario, csrf)
            await browser.close()
            return res

    result = asyncio.run(run_scrape())
    if result.get('success'):
        data = get_data()
        for acc in data['accounts']:
            if acc['usuario'] == usuario:
                acc.update(result)
                acc['status'] = 'completed'
                break
        save_data(data)
    return jsonify(result)

# ... (Mantener las demás rutas de la API del archivo original)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)