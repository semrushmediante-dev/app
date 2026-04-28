import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import json
import requests as req
from datetime import datetime, timedelta
import re
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'
browser_instance = None
context_instance = None

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check para Render"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

def load_data():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando data.json: {str(e)}")
    return {"accounts": [], "history": []}

def save_data(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando data.json: {str(e)}")

async def save_cookies_async():
    """Abre navegador visible para que el usuario haga login y guarda cookies"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            logger.info("🌐 Abriendo Instagram en el navegador...")
            await page.goto('https://www.instagram.com/accounts/login/')
            await page.wait_for_timeout(2000)
            
            logger.info("⏳ Esperando que hagas login... (tienes 60 segundos)")
            
            try:
                await page.wait_for_url('https://www.instagram.com/', timeout=60000)
            except:
                try:
                    await page.wait_for_selector('svg[aria-label="Home"]', timeout=60000)
                except:
                    pass
            
            await page.wait_for_timeout(2000)
            
            # Guardar cookies
            cookies = await context.cookies()
            with open(COOKIES_FILE, 'w') as f:
                json.dump(cookies, f)
            
            logger.info(f"✅ Cookies guardadas en {COOKIES_FILE}")
            await browser.close()
            return True
    except Exception as e:
        logger.error(f"❌ Error en save_cookies_async: {str(e)}")
        return False

async def get_instagram_data(username):
    """Obtener datos de Instagram usando Playwright + API interna"""
    try:
        logger.info(f"🔍 Obteniendo datos de @{username}...")
        username = username.strip().lower()

        if not os.path.exists(COOKIES_FILE):
            logger.warning("No hay sesión iniciada. Sube las cookies primero.")
            return {'success': False, 'error': 'No hay sesión iniciada. Sube las cookies primero.'}

        # Calcular semana anterior
        today = datetime.now()
        dias_desde_lunes = today.weekday()
        lunes_esta_semana = (today - timedelta(days=dias_desde_lunes)).replace(hour=0, minute=0, second=0, microsecond=0)
        lunes_anterior = lunes_esta_semana - timedelta(days=7)
        domingo_anterior = lunes_anterior + timedelta(days=6, hours=23, minutes=59, seconds=59)
        logger.info(f"📅 Buscando posts: {lunes_anterior.strftime('%d/%m')} - {domingo_anterior.strftime('%d/%m')}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            try:
                with open(COOKIES_FILE, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info(f"✅ {len(cookies)} cookies cargadas")
            except Exception as e:
                logger.error(f"Error cargando cookies: {str(e)}")
                await browser.close()
                return {'success': False, 'error': f'Error cargando cookies: {str(e)}'}

            page = await context.new_page()

            # Paso 1: Cargar perfil para obtener user_id y seguidores
            api_data = {}

            async def handle_response(response):
                try:
                    if 'graphql' in response.url and response.status == 200:
                        body = await response.json()
                        data_field = body.get('data', {})
                        user = data_field.get('user', {})
                        if user and user.get('follower_count'):
                            api_data['user'] = user
                except Exception as e:
                    logger.debug(f"Error en handle_response: {str(e)}")
                    pass

            page.on('response', handle_response)

            logger.info(f"🌐 Cargando perfil...")
            try:
                await page.goto(f"https://www.instagram.com/{username}/", wait_until='domcontentloaded', timeout=20000)
            except Exception as e:
                logger.error(f"Error cargando perfil: {str(e)}")
                await browser.close()
                return {'success': False, 'error': f'Error cargando perfil: {str(e)}'}

            await page.wait_for_timeout(3000)

            followers = 0
            following = 0
            posts = 0
            bio = ""
            user_id = None

            if api_data.get('user'):
                user = api_data['user']
                followers = user.get('follower_count', 0)
                following = user.get('following_count', 0)
                posts = user.get('media_count', 0)
                bio = (user.get('biography') or '')[:100]
                user_id = user.get('pk') or user.get('id')
                logger.info(f"✅ {followers} seguidores | user_id: {user_id}")
            else:
                logger.warning(f"No se encontraron datos del usuario")
                await browser.close()
                return {'success': False, 'error': 'No se pudieron obtener datos del perfil. Verifica que el usuario existe.'}

            if not user_id:
                logger.error("No se obtuvo user_id")
                await browser.close()
                return {'success': False, 'error': 'No se obtuvo user_id'}

            # Paso 2: Paginar posts usando fetch() desde dentro del navegador
            all_posts = []
            max_id = None

            for pagina in range(10):
                url_api = f"https://www.instagram.com/api/v1/feed/user/{user_id}/?count=50"
                if max_id:
                    url_api += f"&max_id={max_id}"

                try:
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
                        logger.warning(f"Error en página {pagina+1}: {result}")
                        break

                    items = result.get('items', [])
                    if not items:
                        logger.info(f"No hay más posts")
                        break

                    all_posts.extend(items)

                    fechas = [datetime.fromtimestamp(int(item['taken_at'])) for item in items if item.get('taken_at')]
                    if fechas:
                        mas_antigua = min(fechas)
                        mas_nueva = max(fechas)
                        logger.info(f"Pág {pagina+1}: {len(items)} posts | {mas_nueva.strftime('%d/%m/%Y')} → {mas_antigua.strftime('%d/%m/%Y')} | total: {len(all_posts)}")

                    max_id = result.get('next_max_id')
                    if not max_id:
                        logger.info(f"No hay más páginas")
                        break

                    await page.wait_for_timeout(500)
                except Exception as e:
                    logger.error(f"Error obteniendo posts página {pagina+1}: {str(e)}")
                    break

            await browser.close()

            # Paso 3: Filtrar y procesar posts de la semana anterior
            logger.info(f"📊 Procesando {len(all_posts)} posts totales...")

            posts_week = 0
            likes_week = []
            comments_week = []
            views_week = []

            for item in all_posts:
                if not item.get('taken_at'):
                    continue
                taken_at = datetime.fromtimestamp(int(item['taken_at']))
                if lunes_anterior <= taken_at <= domingo_anterior:
                    posts_week += 1
                    likes_week.append(item.get('like_count', 0))
                    comments_week.append(item.get('comment_count', 0))
                    if item.get('view_count'):
                        views_week.append(item.get('view_count', 0))

            avg_likes = sum(likes_week) / len(likes_week) if likes_week else 0
            avg_comments = sum(comments_week) / len(comments_week) if comments_week else 0
            avg_views = sum(views_week) / len(views_week) if views_week else 0
            total_likes_week = sum(likes_week)
            total_comments_week = sum(comments_week)
            total_views_week = sum(views_week)

            if followers > 0:
                engagement = ((total_likes_week + total_comments_week) / followers / posts_week * 100) if posts_week > 0 else 0
            else:
                engagement = 0

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            result = {
                'success': True,
                'followers': followers,
                'following': following,
                'posts': posts,
                'bio': bio,
                'posts_week': posts_week,
                'avg_likes': round(avg_likes, 2),
                'avg_comments': round(avg_comments, 2),
                'avg_views': round(avg_views, 2),
                'total_likes_week': total_likes_week,
                'total_comments_week': total_comments_week,
                'total_views_week': total_views_week,
                'engagement': round(engagement, 2),
                'timestamp': timestamp
            }

            logger.info(f"✅ Datos obtenidos: {followers} seguidores, {posts_week} posts esta semana")
            return result

    except Exception as e:
        logger.error(f"❌ Error en get_instagram_data: {str(e)}", exc_info=True)
        return {'success': False, 'error': f'Error: {str(e)}'}

# ============ LOGIN ============

@app.route('/api/login', methods=['POST'])
def login():
    """Iniciar sesión en Instagram"""
    try:
        logger.info("Iniciando proceso de login...")
        result = asyncio.run(save_cookies_async())
        if result:
            return jsonify({'success': True, 'message': 'Login exitoso'})
        else:
            return jsonify({'success': False, 'error': 'Error durante el login'}), 500
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-cookies', methods=['POST'])
def upload_cookies():
    """Cargar cookies desde archivo"""
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        cookies = json.load(file)
        
        # Convertir a formato Playwright
        playwright_cookies = []
        for c in cookies:
            pc = {
                'name': c.get('name', ''),
                'value': c.get('value', ''),
                'domain': c.get('domain', '.instagram.com'),
                'path': c.get('path', '/'),
                'secure': c.get('secure', True),
                'httpOnly': c.get('httpOnly', False),
                'sameSite': 'Lax'
            }
            if c.get('expires') and c['expires'] > 0:
                pc['expires'] = float(c['expires'])
            playwright_cookies.append(pc)

        with open(COOKIES_FILE, 'w') as f:
            json.dump(playwright_cookies, f)

        session_cookie = next((c for c in cookies if c['name'] == 'sessionid'), None)
        if not session_cookie:
            return jsonify({'success': False, 'error': 'No se encontró sessionid en las cookies'}), 400

        logger.info(f"✅ {len(playwright_cookies)} cookies guardadas")
        return jsonify({'success': True, 'message': f'{len(playwright_cookies)} cookies cargadas'})

    except Exception as e:
        logger.error(f"Error en upload_cookies: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-login', methods=['GET'])
def check_login():
    """Verificar si hay sesión guardada"""
    has_session = os.path.exists(COOKIES_FILE)
    return jsonify({'success': True, 'logged_in': has_session})

# ============ IMPORT CSV ============

@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    try:
        csv_data = request.json.get('csvData', '')
        lines = csv_data.strip().split('\n')
        data = load_data()
        new_accounts = []

        for i, line in enumerate(lines[1:], 1):
            parts = [p.strip().strip('"') for p in line.split(',')]
            if len(parts) < 3:
                continue
            usuario, encargada, url = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not usuario or not encargada or not url:
                continue
            if not any(a['usuario'] == usuario for a in data['accounts']):
                new_accounts.append({
                    'id': int(datetime.now().timestamp() * 1000) + i,
                    'usuario': usuario,
                    'encargada': encargada,
                    'url': url,
                    'seguidores': None,
                    'following': None,
                    'posts': None,
                    'bio': None,
                    'posts_week': None,
                    'avg_likes': None,
                    'avg_comments': None,
                    'total_likes_week': None,
                    'total_comments_week': None,
                    'engagementRate': None,
                    'lastUpdate': None,
                    'status': 'pending'
                })

        data['accounts'].extend(new_accounts)
        save_data(data)
        logger.info(f"✅ {len(new_accounts)} cuentas importadas")
        return jsonify({'success': True, 'message': f'{len(new_accounts)} cuentas importadas'})

    except Exception as e:
        logger.error(f"Error en import_csv: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ FETCH FOLLOWERS ============

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    try:
        usuario = request.json.get('usuario')
        logger.info(f"Obteniendo datos para: {usuario}")
        
        data = load_data()
        account = next((a for a in data['accounts'] if a['usuario'] == usuario), None)
        if not account:
            logger.warning(f"Cuenta no encontrada: {usuario}")
            return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404

        result = asyncio.run(get_instagram_data(usuario))
        
        if result['success']:
            account.update({
                'seguidores': result['followers'],
                'following': result['following'],
                'posts': result['posts'],
                'bio': result['bio'],
                'posts_week': result['posts_week'],
                'avg_likes': result['avg_likes'],
                'avg_comments': result['avg_comments'],
                'avg_views': result.get('avg_views', 0),
                'total_likes_week': result['total_likes_week'],
                'total_comments_week': result['total_comments_week'],
                'total_views_week': result.get('total_views_week', 0),
                'engagementRate': result['engagement'],
                'lastUpdate': result['timestamp'],
                'status': 'completed'
            })
            data['history'].append({
                'usuario': usuario,
                'seguidores': result['followers'],
                'following': result['following'],
                'posts': result['posts'],
                'posts_week': result['posts_week'],
                'avg_likes': result['avg_likes'],
                'avg_comments': result['avg_comments'],
                'engagement': result['engagement'],
                'fecha': result['timestamp']
            })
            save_data(data)
            logger.info(f"✅ Datos obtenidos exitosamente para {usuario}")
            return jsonify({'success': True, 'data': result})
        else:
            account['status'] = 'failed'
            save_data(data)
            logger.error(f"Error obteniendo datos: {result['error']}")
            return jsonify({'success': False, 'error': result['error']}), 500

    except Exception as e:
        logger.error(f"Error en fetch_followers: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ OTROS ENDPOINTS ============

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    data = load_data()
    return jsonify({'success': True, 'accounts': data['accounts']})

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify({'success': True, 'history': data['history']})

@app.route('/api/update-followers', methods=['POST'])
def update_followers():
    try:
        req_data = request.json
        usuario = req_data.get('usuario')
        seguidores = int(req_data.get('seguidores', 0))
        engagement = float(req_data.get('engagementRate', 0))
        data = load_data()
        account = next((a for a in data['accounts'] if a['usuario'] == usuario), None)
        if not account:
            return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404
        today = datetime.now().strftime('%Y-%m-%d')
        account['seguidores'] = seguidores
        account['engagementRate'] = engagement
        account['lastUpdate'] = today
        account['status'] = 'completed'
        data['history'].append({'usuario': usuario, 'seguidores': seguidores, 'engagementRate': engagement, 'fecha': today})
        save_data(data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error en update_followers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/account/<usuario>', methods=['DELETE'])
def delete_account(usuario):
    try:
        data = load_data()
        data['accounts'] = [a for a in data['accounts'] if a['usuario'] != usuario]
        data['history'] = [h for h in data['history'] if h['usuario'] != usuario]
        save_data(data)
        logger.info(f"✅ Cuenta eliminada: {usuario}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error en delete_account: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    try:
        data = load_data()
        csv = 'Usuario,Encargada,URL,Seguidores,Posts Semana,Visualizaciones,Avg Likes,Avg Comments,Engagement Rate (%),Última Actualización\n'
        for a in data['accounts']:
            csv += f"{a['usuario']},{a['encargada']},{a['url']},"
            csv += f"{a['seguidores'] or 'N/A'},"
            csv += f"{a.get('posts_week') or 'N/A'},"
            csv += f"{a.get('total_views_week') or 'N/A'},"
            csv += f"{a.get('avg_likes') or 'N/A'},{a.get('avg_comments') or 'N/A'},"
            csv += f"{a.get('engagementRate') or 'N/A'},{a['lastUpdate'] or 'N/A'}\n"
        filename = f"instagram_{datetime.now().strftime('%Y-%m-%d')}.csv"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(csv)
        return send_file(filename, as_attachment=True, mimetype='text/csv')
    except Exception as e:
        logger.error(f"Error en export_csv: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-all', methods=['DELETE'])
def clear_all():
    try:
        save_data({'accounts': [], 'history': []})
        logger.info("✅ Todos los datos eliminados")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error en clear_all: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("\n🚀 Servidor Flask con Playwright + Cookies")
    logger.info("📊 Abre http://localhost:7860 en tu navegador")
    logger.info("🔐 Primero haz Login desde la app\n")
    port = int(os.environ.get('PORT', 7860))
    app.run(debug=False, host='0.0.0.0', port=port)