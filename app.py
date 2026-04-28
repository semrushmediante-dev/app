import os
import json
import asyncio
from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'

# ═══════════════════════════════════════════════════════════
# DATOS
# ═══════════════════════════════════════════════════════════

def load_data():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {"accounts": [], "history": []}

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_async(coro):
    """Ejecutar corutina en un event loop nuevo (compatible con gunicorn)"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ═══════════════════════════════════════════════════════════
# SEMANA ANTERIOR (lunes - domingo)
# ═══════════════════════════════════════════════════════════

def get_last_week():
    today = datetime.now()
    lunes_esta = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    lunes_ant  = lunes_esta - timedelta(days=7)
    domingo_ant = lunes_ant + timedelta(days=6, hours=23, minutes=59, seconds=59)
    label = f"{lunes_ant.strftime('%d/%m')} - {domingo_ant.strftime('%d/%m/%Y')}"
    return lunes_ant, domingo_ant, label

# ═══════════════════════════════════════════════════════════
# PLAYWRIGHT – contexto base
# ═══════════════════════════════════════════════════════════

BROWSER_ARGS = [
    '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
    '--disable-setuid-sandbox',
]
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

async def make_context(p):
    browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
    context = await browser.new_context(user_agent=UA)
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            await context.add_cookies(json.load(f))
    return browser, context

# ═══════════════════════════════════════════════════════════
# SCRAPING DE UNA CUENTA (acepta un context existente)
# ═══════════════════════════════════════════════════════════

async def scrape_account(context, username, lunes_ant, domingo_ant):
    logger.info(f"Scraping @{username}...")
    page = await context.new_page()
    api_data = {}

    async def capture(response):
        try:
            if 'graphql' in response.url and response.status == 200:
                body = await response.json()
                user = body.get('data', {}).get('user', {})
                if user and user.get('follower_count'):
                    api_data['user'] = user
        except Exception:
            pass

    page.on('response', capture)

    try:
        await page.goto(f'https://www.instagram.com/{username}/',
                        wait_until='domcontentloaded', timeout=25000)
    except Exception:
        pass
    await page.wait_for_timeout(2500)

    if not api_data.get('user'):
        await page.close()
        return {'success': False, 'error': 'No se obtuvieron datos del perfil'}

    user      = api_data['user']
    followers = user.get('follower_count', 0)
    following = user.get('following_count', 0)
    posts     = user.get('media_count', 0)
    bio       = (user.get('biography') or '')[:100]
    user_id   = user.get('pk') or user.get('id')

    if not user_id:
        await page.close()
        return {'success': False, 'error': 'No se obtuvo user_id'}

    # ── Paginar feed ──────────────────────────────────────
    all_posts = []
    max_id    = None

    for _ in range(10):
        url_api = f'https://www.instagram.com/api/v1/feed/user/{user_id}/?count=50'
        if max_id:
            url_api += f'&max_id={max_id}'

        result = await page.evaluate(f"""
            async () => {{
                const r = await fetch('{url_api}', {{
                    headers: {{
                        'X-IG-App-ID': '936619743392459',
                        'X-Requested-With': 'XMLHttpRequest'
                    }}
                }});
                if (!r.ok) return {{ error: r.status }};
                return await r.json();
            }}
        """)

        if not result or result.get('error'):
            break

        items = result.get('items', [])
        if not items:
            break

        all_posts.extend(items)

        # Si el post más antiguo de esta página ya está antes del lunes anterior, parar
        oldest = min((i.get('taken_at', 0) for i in items), default=0)
        if oldest and datetime.fromtimestamp(oldest) < lunes_ant:
            break

        max_id = result.get('next_max_id')
        if not max_id:
            break

        await page.wait_for_timeout(400)

    await page.close()

    # ── Filtrar reels de la semana pasada (media_type == 2) ──
    likes_w, comments_w, views_w = [], [], []

    for item in all_posts:
        ts = item.get('taken_at')
        if not ts:
            continue
        post_dt = datetime.fromtimestamp(int(ts))
        if lunes_ant <= post_dt <= domingo_ant and item.get('media_type') == 2:
            likes_w.append(item.get('like_count', 0))
            comments_w.append(item.get('comment_count', 0))
            views_w.append(
                item.get('view_count') or
                item.get('play_count') or
                item.get('video_view_count') or 0
            )

    posts_week       = len(likes_w)
    total_likes      = sum(likes_w)
    total_comments   = sum(comments_w)
    total_views      = sum(views_w)
    avg_likes        = round(total_likes    / posts_week, 1) if posts_week else 0
    avg_comments     = round(total_comments / posts_week, 1) if posts_week else 0
    views_validas    = [v for v in views_w if v > 0]
    avg_views        = round(total_views / len(views_validas), 1) if views_validas else 0
    engagement       = round(((total_likes + total_comments) / (followers * posts_week)) * 100, 2) \
                       if followers > 0 and posts_week > 0 else 0

    logger.info(f"@{username}: {followers} seg | {posts_week} reels | {total_views} vistas")
    return {
        'success':             True,
        'followers':           followers,
        'following':           following,
        'posts':               posts,
        'bio':                 bio,
        'posts_week':          posts_week,
        'avg_likes':           avg_likes,
        'avg_comments':        avg_comments,
        'avg_views':           avg_views,
        'total_likes_week':    total_likes,
        'total_comments_week': total_comments,
        'total_views_week':    total_views,
        'engagement':          engagement,
        'timestamp':           datetime.now().strftime('%Y-%m-%d'),
    }

# ── Una cuenta – browser propio ──────────────────────────
async def get_instagram_data(username):
    lunes_ant, domingo_ant, _ = get_last_week()
    async with async_playwright() as p:
        browser, context = await make_context(p)
        try:
            return await scrape_account(context, username, lunes_ant, domingo_ant)
        finally:
            await browser.close()

# ── Todas las cuentas – UN solo browser ─────────────────
async def get_all_accounts_batch(usernames):
    lunes_ant, domingo_ant, _ = get_last_week()
    results = {}
    async with async_playwright() as p:
        browser, context = await make_context(p)
        try:
            for username in usernames:
                try:
                    results[username] = await scrape_account(context, username, lunes_ant, domingo_ant)
                except Exception as e:
                    logger.error(f"@{username} batch error: {e}")
                    results[username] = {'success': False, 'error': str(e)}
                await asyncio.sleep(0.5)
        finally:
            await browser.close()
    return results

# ═══════════════════════════════════════════════════════════
# RUTAS ESTÁTICAS
# ═══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/instagram')
def instagram():
    return app.send_static_file('indexInstagram.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# ═══════════════════════════════════════════════════════════
# API – LOGIN
# ═══════════════════════════════════════════════════════════

@app.route('/api/login-cookie', methods=['POST'])
def login_cookie():
    try:
        body = request.get_json(force=True, silent=True) or {}
        cookies = body.get('cookies', [])
        if not cookies:
            return jsonify({'success': False, 'error': 'No se recibieron cookies'}), 400

        # Forzar formato Playwright (sameSite siempre válido)
        playwright_cookies = []
        for c in cookies:
            pc = {
                'name':     c.get('name', ''),
                'value':    c.get('value', ''),
                'domain':   c.get('domain', '.instagram.com'),
                'path':     c.get('path', '/'),
                'secure':   c.get('secure', True),
                'httpOnly': c.get('httpOnly', False),
                'sameSite': 'Lax',
            }
            if c.get('expires') and float(c['expires']) > 0:
                pc['expires'] = float(c['expires'])
            playwright_cookies.append(pc)

        if not any(c['name'] == 'sessionid' for c in playwright_cookies):
            return jsonify({'success': False, 'error': 'No se encontró sessionid en las cookies'}), 400

        with open(COOKIES_FILE, 'w') as f:
            json.dump(playwright_cookies, f)

        logger.info(f"Cookies guardadas: {len(playwright_cookies)}")
        return jsonify({'success': True, 'message': f'{len(playwright_cookies)} cookies cargadas correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-login', methods=['GET'])
def check_login():
    return jsonify({'success': True, 'logged_in': os.path.exists(COOKIES_FILE)})

# ═══════════════════════════════════════════════════════════
# API – CUENTAS
# ═══════════════════════════════════════════════════════════

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    data = load_data()
    return jsonify({'success': True, 'accounts': data['accounts']})

@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    try:
        csv_data = request.json.get('csvData', '')
        lines = csv_data.strip().split('\n')
        data = load_data()
        added = 0
        for i, line in enumerate(lines[1:], 1):
            parts = [p.strip().strip('"') for p in line.split(',')]
            if len(parts) < 3:
                continue
            usuario, encargada, url = parts[0], parts[1], parts[2]
            if not usuario or not encargada or not url:
                continue
            if not any(a['usuario'] == usuario for a in data['accounts']):
                data['accounts'].append({
                    'id':                 int(datetime.now().timestamp() * 1000) + i,
                    'usuario':            usuario,
                    'encargada':          encargada,
                    'url':                url,
                    'seguidores':         None,
                    'following':          None,
                    'posts':              None,
                    'bio':                None,
                    'posts_week':         None,
                    'avg_likes':          None,
                    'avg_comments':       None,
                    'total_likes_week':   None,
                    'total_comments_week': None,
                    'total_views_week':   None,
                    'avg_views':          None,
                    'engagementRate':     None,
                    'lastUpdate':         None,
                    'status':             'pending',
                })
                added += 1
        save_data(data)
        return jsonify({'success': True, 'message': f'{added} cuentas importadas', 'accounts': data['accounts']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _apply_result(account, result):
    account.update({
        'seguidores':          result['followers'],
        'following':           result['following'],
        'posts':               result['posts'],
        'bio':                 result['bio'],
        'posts_week':          result['posts_week'],
        'avg_likes':           result['avg_likes'],
        'avg_comments':        result['avg_comments'],
        'avg_views':           result.get('avg_views', 0),
        'total_likes_week':    result['total_likes_week'],
        'total_comments_week': result['total_comments_week'],
        'total_views_week':    result.get('total_views_week', 0),
        'engagementRate':      result['engagement'],
        'lastUpdate':          result['timestamp'],
        'status':              'completed',
    })

def _history_entry(usuario, result):
    return {
        'usuario':      usuario,
        'seguidores':   result['followers'],
        'following':    result['following'],
        'posts':        result['posts'],
        'posts_week':   result['posts_week'],
        'avg_likes':    result['avg_likes'],
        'avg_comments': result['avg_comments'],
        'engagement':   result['engagement'],
        'fecha':        result['timestamp'],
    }

# ── Actualizar UNA cuenta ────────────────────────────────
@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    try:
        usuario = request.json.get('usuario')
        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario requerido'}), 400
        if not os.path.exists(COOKIES_FILE):
            return jsonify({'success': False, 'error': 'Sube las cookies primero'}), 400

        data    = load_data()
        account = next((a for a in data['accounts'] if a['usuario'] == usuario), None)
        if not account:
            return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404

        result = run_async(get_instagram_data(usuario))

        if result['success']:
            _apply_result(account, result)
            data['history'].append(_history_entry(usuario, result))
            save_data(data)
            return jsonify({'success': True, 'data': result, 'accounts': data['accounts']})
        else:
            account['status'] = 'failed'
            save_data(data)
            return jsonify({'success': False, 'error': result['error']}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ── Actualizar TODAS las cuentas – un solo browser ──────
@app.route('/api/fetch-all-batch', methods=['POST'])
def fetch_all_batch():
    try:
        if not os.path.exists(COOKIES_FILE):
            return jsonify({'success': False, 'error': 'Sube las cookies primero'}), 400

        data      = load_data()
        accounts  = data['accounts']
        if not accounts:
            return jsonify({'success': False, 'error': 'No hay cuentas'}), 400

        _, _, week_label = get_last_week()
        usernames = [a['usuario'] for a in accounts]
        results   = run_async(get_all_accounts_batch(usernames))

        updated, failed = 0, 0
        for account in accounts:
            r = results.get(account['usuario'], {})
            if r.get('success'):
                _apply_result(account, r)
                data['history'].append(_history_entry(account['usuario'], r))
                updated += 1
            else:
                account['status'] = 'failed'
                failed += 1
                logger.warning(f"@{account['usuario']} failed: {r.get('error')}")

        save_data(data)
        msg = f"✅ {updated}/{len(accounts)} cuentas actualizadas — semana {week_label}"
        if failed:
            msg += f" ({failed} fallidas)"
        return jsonify({
            'success':  True,
            'message':  msg,
            'updated':  updated,
            'failed':   failed,
            'week':     week_label,
            'accounts': data['accounts'],
        })

    except Exception as e:
        logger.error(f"fetch_all_batch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ── Actualización manual ─────────────────────────────────
@app.route('/api/update-followers', methods=['POST'])
def update_followers():
    try:
        body      = request.json
        usuario   = body.get('usuario')
        seguidores = int(body.get('seguidores', 0))
        engagement = float(body.get('engagementRate', 0))
        data      = load_data()
        account   = next((a for a in data['accounts'] if a['usuario'] == usuario), None)
        if not account:
            return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404
        today = datetime.now().strftime('%Y-%m-%d')
        account['seguidores']    = seguidores
        account['engagementRate'] = engagement
        account['lastUpdate']    = today
        account['status']        = 'completed'
        data['history'].append({'usuario': usuario, 'seguidores': seguidores,
                                 'engagementRate': engagement, 'fecha': today})
        save_data(data)
        return jsonify({'success': True, 'message': f'✅ @{usuario} actualizado', 'accounts': data['accounts']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/account/<usuario>', methods=['DELETE'])
def delete_account(usuario):
    try:
        data = load_data()
        data['accounts'] = [a for a in data['accounts'] if a['usuario'] != usuario]
        data['history']  = [h for h in data['history']  if h['usuario'] != usuario]
        save_data(data)
        return jsonify({'success': True, 'accounts': data['accounts']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify({'success': True, 'history': data['history']})

@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    try:
        data = load_data()
        _, _, week_label = get_last_week()
        lines = [f'Usuario,Encargada,URL,Seguidores,Reels semana ({week_label}),'
                 'Visualizaciones totales,Avg Likes,Avg Comments,Engagement (%),Última actualización']
        for a in data['accounts']:
            lines.append(
                f"{a['usuario']},{a['encargada']},{a['url']},"
                f"{a.get('seguidores') or 'N/A'},"
                f"{a.get('posts_week') or 0},"
                f"{a.get('total_views_week') or 0},"
                f"{a.get('avg_likes') or 0},"
                f"{a.get('avg_comments') or 0},"
                f"{a.get('engagementRate') or 0},"
                f"{a.get('lastUpdate') or 'N/A'}"
            )
        csv_content = '\n'.join(lines)
        return Response(
            csv_content,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition':
                     f'attachment; filename=instagram_{datetime.now().strftime("%Y-%m-%d")}.csv'}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-all', methods=['DELETE', 'POST'])
def clear_all():
    save_data({'accounts': [], 'history': []})
    return jsonify({'success': True, 'accounts': []})

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Servidor en puerto {port}")
    app.run(debug=False, host='0.0.0.0', port=port)
