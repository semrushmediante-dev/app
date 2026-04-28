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

# INICIALIZACIÓN DE FLASK (Gunicorn busca esta variable 'app')
app = Flask(__name__, static_folder='.', static_url_path='')
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

# --- Lógica de Playwright y Scraping ---
def get_last_week_range():
    today = datetime.now().date()
    # Lunes de la semana pasada
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    start_ts = int(datetime.combine(last_monday, datetime.min.time()).timestamp())
    end_ts = int(datetime.combine(last_sunday, datetime.max.time()).timestamp())
    label = f"{last_monday.strftime('%d/%m')} - {last_sunday.strftime('%d/%m/%Y')}"
    return start_ts, end_ts, label

async def scrape_profile(page, username, csrf=''):
    """Extrae y calcula todos los campos para la tabla de Instagram"""
    try:
        # Usamos el endpoint oficial de la web para mayor estabilidad
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        headers = {
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
            'Referer': f'https://www.instagram.com/{username}/'
        }
        
        response = await page.request.get(url, headers=headers)
        if response.status != 200:
            return {'success': False, 'error': f'Status {response.status}'}
            
        data = await response.json()
        user = data.get('data', {}).get('user')
        if not user:
            return {'success': False, 'error': 'Perfil no accesible'}

        # Datos básicos
        followers = user.get('edge_followed_by', {}).get('count', 0)
        following = user.get('edge_follow', {}).get('count', 0)
        posts_count = user.get('edge_owner_to_timeline_media', {}).get('count', 0)
        
        # Procesar posts de la última semana
        start_ts, end_ts, week_label = get_last_week_range()
        edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
        
        week_reels = []
        for edge in edges:
            node = edge.get('node', {})
            ts = node.get('taken_at_timestamp', 0)
            if start_ts <= ts <= end_ts:
                week_reels.append({
                    'likes': node.get('edge_liked_by', {}).get('count', 0),
                    'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                    'views': node.get('video_view_count', 0) or 0
                })

        # Cálculos
        n_posts = len(week_reels)
        t_views = sum(r['views'] for r in week_reels)
        t_likes = sum(r['likes'] for r in week_reels)
        t_comments = sum(r['comments'] for r in week_reels)
        
        engagement = 0
        if followers > 0 and n_posts > 0:
            engagement = round(((t_likes + t_comments) / followers) * 100, 2)

        return {
            'success': True,
            'seguidores': followers,
            'following': following,
            'posts': posts_count,
            'posts_week': n_posts,
            'total_views_week': t_views,
            'avg_likes': round(t_likes / n_posts, 1) if n_posts > 0 else 0,
            'avg_comments': round(t_comments / n_posts, 1) if n_posts > 0 else 0,
            'avg_views': round(t_views / n_posts, 1) if n_posts > 0 else 0,
            'engagementRate': engagement,
            'week_label': week_label,
            'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        logger.error(f"Error scraping {username}: {e}")
        return {'success': False, 'error': str(e)}

# --- Rutas API (Ejemplo de una ruta corregida) ---
@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    usuario = request.json.get('usuario')
    if not usuario:
        return jsonify({"success": False, "error": "Falta usuario"}), 400

    async def run():
        async with async_playwright() as p:
            # Configuración para que funcione en Docker/Render
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context()
            
            # Cargar cookies si existen
            if os.path.exists(COOKIES_FILE):
                with open(COOKIES_FILE, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
            
            page = await context.new_page()
            # Activar sesión
            await page.goto('https://www.instagram.com/', wait_until='networkidle')
            all_cookies = await context.cookies()
            csrf = next((c['value'] for c in all_cookies if c['name'] == 'csrftoken'), '')
            
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

# Importante: Mantener esto al final para ejecución local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)