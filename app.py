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

app = Flask(__name__, static_folder='.', static_url_path='')
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
    if not os.path.exists(DB_FILE):
        d = {"accounts": [], "history": []}
        save_data(d)
        return d
    return load_data()

# ═════════════════════════════════════════════════════════════
# COOKIES Y PLAYWRIGHT
# ═════════════════════════════════════════════════════════════

SAMESITE_MAP = {
    'strict': 'Strict', 'lax': 'Lax', 'none': 'None',
    'no_restriction': 'None', 'unspecified': 'None', '': 'None',
}

def normalize_cookies(cookies):
    result = []
    for cookie in cookies:
        c = dict(cookie)
        ss = str(c.get('sameSite', '')).lower()
        c['sameSite'] = SAMESITE_MAP.get(ss, 'None')
        if c.get('expires') == -1:
            c.pop('expires', None)
        result.append(c)
    return result

def get_browser_args():
    return [
        '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
        '--disable-blink-features=AutomationControlled',
        '--disable-setuid-sandbox', '--single-process',
    ]

def get_last_week_range():
    """Retorna (start_ts, end_ts, label) para lunes-domingo de la semana pasada"""
    today = datetime.now().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    start_ts = int(datetime(last_monday.year, last_monday.month, last_monday.day, 0, 0, 0).timestamp())
    end_ts   = int(datetime(last_sunday.year,  last_sunday.month,  last_sunday.day,  23, 59, 59).timestamp())
    label = f"{last_monday.strftime('%d/%m')} - {last_sunday.strftime('%d/%m/%Y')}"
    return start_ts, end_ts, label

async def establish_session(page, context):
    """
    Navega a instagram.com para activar la sesión con las cookies cargadas
    y devuelve el csrftoken actualizado (necesario para API calls).
    """
    await page.goto('https://www.instagram.com/', wait_until='domcontentloaded', timeout=30000)
    await page.wait_for_timeout(2000)
    cookies = await context.cookies()
    csrf = next((c['value'] for c in cookies if c['name'] == 'csrftoken'), '')
    logger.info(f"Sesión establecida. csrf={'ok' if csrf else 'MISSING'}")
    return csrf

async def scrape_profile(page, username, csrf=''):
    """
    Llama a la API interna de Instagram y devuelve todos los campos necesarios.
    Filtra reels de la semana pasada (lunes a domingo).
    """
    try:
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        resp = await page.request.get(url, headers={
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
            'Referer': 'https://www.instagram.com/',
            'X-CSRFToken': csrf,
        })

        if not resp.ok:
            logger.warning(f"{username}: API status {resp.status}")
            return {'success': False, 'error': f'HTTP {resp.status}'}

        body = await resp.json()
        user = body.get('data', {}).get('user', {})
        if not user:
            return {'success': False, 'error': 'Usuario no encontrado o privado'}

        followers = user.get('edge_followed_by', {}).get('count', 0)
        following = user.get('edge_follow', {}).get('count', 0)
        total_posts = user.get('edge_owner_to_timeline_media', {}).get('count', 0)
        bio = user.get('biography', '')

        # --- Reels de la semana pasada ---
        start_ts, end_ts, week_label = get_last_week_range()
        edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])

        reels = []
        for edge in edges:
            node = edge.get('node', {})
            ts = node.get('taken_at_timestamp', 0)
            if start_ts <= ts <= end_ts and node.get('is_video', False):
                reels.append({
                    'likes':    node.get('edge_liked_by', {}).get('count', 0),
                    'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                    'views':    node.get('video_view_count') or 0,
                })

        posts_week        = len(reels)
        total_likes_week  = sum(r['likes']    for r in reels)
        total_comments_week = sum(r['comments'] for r in reels)
        total_views_week  = sum(r['views']    for r in reels)
        avg_likes         = round(total_likes_week    / posts_week, 1) if posts_week else 0
        avg_comments      = round(total_comments_week / posts_week, 1) if posts_week else 0
        avg_views         = round(total_views_week    / posts_week, 1) if posts_week else 0

        # Engagement = (likes + comentarios) de la semana / seguidores * 100
        engagement = round((total_likes_week + total_comments_week) / followers * 100, 2) \
                     if followers > 0 and posts_week > 0 else 0

        logger.info(f"{username}: {followers} seg | {posts_week} reels semana {week_label}")
        return {
            'success': True,
            'seguidores':           followers,
            'following':            following,
            'posts':                total_posts,
            'bio':                  bio,
            'posts_week':           posts_week,
            'total_likes_week':     total_likes_week,
            'total_comments_week':  total_comments_week,
            'total_views_week':     total_views_week,
            'avg_likes':            avg_likes,
            'avg_comments':         avg_comments,
            'avg_views':            avg_views,
            'engagementRate':       engagement,
            'week_label':           week_label,
        }

    except Exception as e:
        logger.warning(f"scrape_profile error {username}: {e}")
        return {'success': False, 'error': str(e)}

def apply_result_to_account(account, r):
    """Copia todos los campos del resultado al diccionario de la cuenta"""
    account['seguidores']           = r['seguidores']
    account['following']            = r['following']
    account['posts']                = r['posts']
    account['bio']                  = r.get('bio', account.get('bio', ''))
    account['posts_week']           = r['posts_week']
    account['total_likes_week']     = r['total_likes_week']
    account['total_comments_week']  = r['total_comments_week']
    account['total_views_week']     = r['total_views_week']
    account['avg_likes']            = r['avg_likes']
    account['avg_comments']         = r['avg_comments']
    account['avg_views']            = r['avg_views']
    account['engagementRate']       = r['engagementRate']
    account['lastUpdate']           = datetime.now().strftime('%Y-%m-%d')
    account['status']               = 'completed'

async def _open_context(p):
    browser = await p.chromium.launch(headless=True, args=get_browser_args())
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        extra_http_headers={'Accept-Language': 'es-ES,es;q=0.9'},
    )
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            raw = json.load(f)
        await context.add_cookies(normalize_cookies(raw))
    return browser, context

async def fetch_account_data(username):
    """Abre un browser propio, establece sesión y raspa una cuenta"""
    try:
        async with async_playwright() as p:
            browser, context = await _open_context(p)
            page = await context.new_page()
            csrf = await establish_session(page, context)
            result = await scrape_profile(page, username, csrf)
            await browser.close()
            return result
    except Exception as e:
        logger.error(f"fetch_account_data error {username}: {e}")
        return {'success': False, 'error': str(e)}

async def fetch_all_batch(usernames):
    """Raspa todas las cuentas con un único browser — una sola sesión"""
    results = {}
    try:
        async with async_playwright() as p:
            browser, context = await _open_context(p)
            page = await context.new_page()
            # Navegar una sola vez para activar sesión y obtener csrf
            csrf = await establish_session(page, context)
            for username in usernames:
                results[username] = await scrape_profile(page, username, csrf)
                await page.wait_for_timeout(1500)
            await browser.close()
    except Exception as e:
        logger.error(f"fetch_all_batch error: {e}")
        for u in usernames:
            if u not in results:
                results[u] = {'success': False, 'error': str(e)}
    return results

# ═════════════════════════════════════════════════════════════
# RUTAS ESTÁTICAS
# ═════════════════════════════════════════════════════════════

@app.route('/')
def index():
    try:
        return send_from_directory('.', 'index.html')
    except:
        return jsonify({"error": "index.html not found"}), 404

@app.route('/instagram')
def instagram_page():
    try:
        return send_from_directory('.', 'indexInstagram.html')
    except:
        return jsonify({"error": "indexInstagram.html not found"}), 404

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

# ═════════════════════════════════════════════════════════════
# API - CUENTAS
# ═════════════════════════════════════════════════════════════

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    try:
        data = get_data()
        accounts = data.get('accounts', [])
        for a in accounts:
            a.setdefault('seguidores', 0)
            a.setdefault('posts_week', 0)
            a.setdefault('total_views_week', 0)
            a.setdefault('engagementRate', 0.0)
            a.setdefault('lastUpdate', 'N/A')
            a.setdefault('status', 'Pending')
        return jsonify({"success": True, "accounts": accounts, "total": len(accounts)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    try:
        req_data = request.get_json()
        csv_data = req_data.get('csvData', '')
        if not csv_data:
            return jsonify({"success": False, "error": "No hay datos CSV"}), 400

        data = get_data()
        lineas = csv_data.strip().split('\n')
        if lineas and ('usuario' in lineas[0].lower()):
            lineas = lineas[1:]

        importados = 0
        for linea in lineas:
            if not linea.strip():
                continue
            partes = [p.strip() for p in linea.split(',')]
            usuario   = partes[0].strip('"\'') if len(partes) > 0 else ''
            encargada = partes[1].strip('"\'') if len(partes) > 1 else 'N/A'
            url       = partes[2].strip('"\'') if len(partes) > 2 else ''
            if not usuario:
                continue

            new_acc = {
                "usuario": usuario, "encargada": encargada, "url": url,
                "seguidores": 0, "following": 0, "posts": 0, "bio": "",
                "posts_week": 0, "avg_likes": 0, "avg_comments": 0,
                "total_likes_week": 0, "total_comments_week": 0,
                "total_views_week": 0, "avg_views": 0, "engagementRate": 0.0,
                "lastUpdate": datetime.now().strftime('%Y-%m-%d'), "status": "Pending"
            }
            existe = False
            for acc in data['accounts']:
                if acc.get('usuario') == usuario:
                    # Solo actualiza encargada y url, no borra datos existentes
                    acc['encargada'] = encargada
                    acc['url'] = url
                    existe = True
                    break
            if not existe:
                data['accounts'].append(new_acc)
            importados += 1

        save_data(data)
        return jsonify({
            "success": True,
            "message": f"✅ {importados} cuenta(s) importadas",
            "importados": importados,
            "accounts": data['accounts']
        })
    except Exception as e:
        logger.error(f"import_csv error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/login-cookie', methods=['POST'])
def login_cookie():
    try:
        req_data = request.get_json()
        cookies = req_data.get('cookies', [])
        if not cookies:
            return jsonify({"success": False, "error": "No se proporcionaron cookies"}), 400
        normalized = normalize_cookies(cookies)
        with open(COOKIES_FILE, 'w') as f:
            json.dump(normalized, f, indent=2)
        logger.info(f"Cookies guardadas: {len(normalized)}")
        return jsonify({"success": True, "message": f"✅ {len(normalized)} cookies guardadas correctamente"})
    except Exception as e:
        logger.error(f"login_cookie error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    """Actualizar una sola cuenta"""
    try:
        req_data = request.get_json()
        usuario = req_data.get('usuario', '')
        if not usuario:
            return jsonify({"success": False, "error": "Usuario no especificado"}), 400

        if not os.path.exists(COOKIES_FILE):
            return jsonify({"success": False, "error": "No hay cookies. Sube el archivo primero."}), 400

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        r = loop.run_until_complete(fetch_account_data(usuario))
        loop.close()

        if not r.get('success'):
            return jsonify({"success": False, "error": r.get('error', 'Error desconocido')}), 400

        data = get_data()
        for account in data['accounts']:
            if account.get('usuario') == usuario:
                apply_result_to_account(account, r)
                break

        # Añadir al historial
        _, _, week_label = get_last_week_range()
        data['history'].append({
            "usuario":    usuario,
            "seguidores": r['seguidores'],
            "following":  r['following'],
            "posts":      r['posts'],
            "posts_week": r['posts_week'],
            "avg_likes":  r['avg_likes'],
            "avg_comments": r['avg_comments'],
            "engagement": r['engagementRate'],
            "semana":     week_label,
            "fecha":      datetime.now().strftime('%Y-%m-%d'),
        })
        save_data(data)

        return jsonify({
            "success": True,
            "message": f"✅ @{usuario}: {r['seguidores']:,} seg | {r['posts_week']} reels semana",
            "accounts": data['accounts'],
        })
    except Exception as e:
        logger.error(f"fetch_followers error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/fetch-all-batch', methods=['POST'])
def fetch_all_batch_endpoint():
    """Actualizar todas las cuentas con un único browser"""
    try:
        if not os.path.exists(COOKIES_FILE):
            return jsonify({"success": False, "error": "No hay cookies. Sube el archivo primero."}), 400

        data = get_data()
        accounts = data.get('accounts', [])
        if not accounts:
            return jsonify({"success": False, "error": "No hay cuentas"}), 400

        usernames = [a['usuario'] for a in accounts]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(fetch_all_batch(usernames))
        loop.close()

        _, _, week_label = get_last_week_range()
        updated, failed = 0, 0

        for account in data['accounts']:
            r = results.get(account['usuario'], {})
            if r.get('success'):
                apply_result_to_account(account, r)
                data['history'].append({
                    "usuario":    account['usuario'],
                    "seguidores": r['seguidores'],
                    "following":  r['following'],
                    "posts":      r['posts'],
                    "posts_week": r['posts_week'],
                    "avg_likes":  r['avg_likes'],
                    "avg_comments": r['avg_comments'],
                    "engagement": r['engagementRate'],
                    "semana":     week_label,
                    "fecha":      datetime.now().strftime('%Y-%m-%d'),
                })
                updated += 1
            else:
                account['status'] = 'failed'
                failed += 1
                logger.warning(f"Failed: {account['usuario']} — {r.get('error')}")

        save_data(data)
        logger.info(f"Batch done: {updated} ok / {failed} failed")
        msg = f"✅ {updated}/{len(accounts)} cuentas actualizadas"
        if failed:
            msg += f" ({failed} fallidas)"
        return jsonify({
            "success": True,
            "message": msg,
            "updated": updated,
            "failed":  failed,
            "week":    week_label,
            "accounts": data['accounts'],
        })
    except Exception as e:
        logger.error(f"fetch_all_batch_endpoint error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/update-followers', methods=['POST'])
def update_followers():
    """Actualización manual de seguidores"""
    try:
        req_data = request.get_json()
        usuario       = req_data.get('usuario', '')
        seguidores    = req_data.get('seguidores', 0)
        engagement_rate = req_data.get('engagementRate', 0)
        if not usuario:
            return jsonify({"success": False, "error": "Usuario no especificado"}), 400

        data = get_data()
        for account in data['accounts']:
            if account.get('usuario') == usuario:
                account['seguidores']    = int(seguidores)
                account['engagementRate'] = float(engagement_rate)
                account['lastUpdate']    = datetime.now().strftime('%Y-%m-%d')
                account['status']        = 'completed'
                break
        else:
            return jsonify({"success": False, "error": "Cuenta no encontrada"}), 404

        save_data(data)
        return jsonify({
            "success": True,
            "message": f"✅ @{usuario} actualizado manualmente",
            "accounts": data['accounts'],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/account/<usuario>', methods=['DELETE'])
def delete_account(usuario):
    try:
        data = get_data()
        before = len(data['accounts'])
        data['accounts'] = [a for a in data['accounts'] if a.get('usuario') != usuario]
        if len(data['accounts']) == before:
            return jsonify({"success": False, "error": "Cuenta no encontrada"}), 404
        save_data(data)
        return jsonify({"success": True, "message": f"✅ @{usuario} eliminada", "accounts": data['accounts']})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        data = get_data()
        return jsonify({"success": True, "history": data.get('history', [])})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    """Descarga el CSV directamente (no JSON)"""
    try:
        data = get_data()
        _, _, week_label = get_last_week_range()
        lines = [
            "Usuario,Encargada,URL,Seguidores,Following,Posts totales,"
            f"Reels semana ({week_label}),Vistas totales,Avg Likes,Avg Comments,"
            "Engagement (%),Última actualización"
        ]
        for a in data['accounts']:
            lines.append(
                f"{a.get('usuario','')},{a.get('encargada','')},{a.get('url','')},"
                f"{a.get('seguidores',0)},{a.get('following',0)},{a.get('posts',0)},"
                f"{a.get('posts_week',0)},{a.get('total_views_week',0)},"
                f"{a.get('avg_likes',0)},{a.get('avg_comments',0)},"
                f"{a.get('engagementRate',0)},{a.get('lastUpdate','N/A')}"
            )
        csv_content = '\n'.join(lines)
        return Response(
            csv_content,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename=cuentas_instagram.csv'}
        )
    except Exception as e:
        logger.error(f"export_csv error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/clear-all', methods=['DELETE', 'POST'])
def clear_all():
    try:
        save_data({"accounts": [], "history": []})
        return jsonify({"success": True, "message": "✅ Datos eliminados", "accounts": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ═════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Server error"}), 500

# ═════════════════════════════════════════════════════════════
# STARTUP
# ═════════════════════════════════════════════════════════════

def repair_cookies_file():
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, 'r') as f:
                raw = json.load(f)
            fixed = normalize_cookies(raw)
            with open(COOKIES_FILE, 'w') as f:
                json.dump(fixed, f, indent=2)
            logger.info(f"Cookies reparadas al arrancar: {len(fixed)}")
        except Exception as e:
            logger.warning(f"No se pudo reparar cookies: {e}")

repair_cookies_file()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
