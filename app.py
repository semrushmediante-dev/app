import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from playwright.async_api import async_playwright

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CONFIGURACIÓN CRÍTICA PARA RENDER
# Usamos os.getcwd() para asegurar que la raíz sea el directorio de trabajo
app = Flask(__name__, static_folder=os.getcwd(), static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'

# --- Utilidades de Datos ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando datos: {e}")
    return {"accounts": [], "history": []}

def save_data(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error guardando datos: {e}")
        return False

def get_last_week_range():
    today = datetime.now().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    start_ts = int(datetime.combine(last_monday, datetime.min.time()).timestamp())
    end_ts = int(datetime.combine(last_sunday, datetime.max.time()).timestamp())
    label = f"{last_monday.strftime('%d/%m')} - {last_sunday.strftime('%d/%m/%Y')}"
    return start_ts, end_ts, label

# --- Lógica de Scraping ---
async def scrape_profile(page, username, csrf=''):
    try:
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        headers = {
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
            'Referer': f'https://www.instagram.com/{username}/'
        }
        resp = await page.request.get(url, headers=headers)
        if not resp.ok: return {'success': False, 'error': f'IG Status {resp.status}'}
        
        data = await resp.json()
        user = data.get('data', {}).get('user')
        if not user: return {'success': False, 'error': 'Privado o No existe'}

        followers = user.get('edge_followed_by', {}).get('count', 0)
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

        n_posts = len(reels_data)
        t_views = sum(r['views'] for r in reels_data)
        t_likes = sum(r['likes'] for r in reels_data)
        t_comments = sum(r['comments'] for r in reels_data)
        eng = round(((t_likes + t_comments) / followers * 100), 2) if followers > 0 and n_posts > 0 else 0

        return {
            'success': True,
            'seguidores': followers,
            'posts_week': n_posts,
            'total_views_week': t_views,
            'engagementRate': eng,
            'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'status': 'completed'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# --- RUTAS DE NAVEGACIÓN ---
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/instagram')
def serve_instagram():
    return send_from_directory(app.static_folder, 'indexInstagram.html')

# --- RUTAS API ---
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    return jsonify(load_data())

@app.route('/api/login-cookie', methods=['POST'])
def login_cookie():
    cookies = request.json.get('cookies')
    with open(COOKIES_FILE, 'w') as f:
        json.dump(cookies, f)
    return jsonify({"success": True})

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    usuario = request.json.get('usuario')
    
    async def run():
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

    result = asyncio.run(run())
    if result['success']:
        data = load_data()
        for acc in data['accounts']:
            if acc['usuario'] == usuario:
                acc.update(result)
                break
        save_data(data)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)