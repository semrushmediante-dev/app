import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import json
import requests as req
from datetime import datetime, timedelta
import re



app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'
browser_instance = None
context_instance = None

@app.route('/')
def index():
    return app.send_static_file('index.html')

def load_data():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"accounts": [], "history": []}

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def save_cookies_async():
    """Abre navegador visible para que el usuario haga login y guarda cookies"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        print("🌐 Abriendo Instagram en el navegador...")
        await page.goto('https://www.instagram.com/accounts/login/')
        await page.wait_for_timeout(2000)
        
        print("⏳ Esperando que hagas login... (tienes 60 segundos)")
        print("   1. Ingresa tu usuario y contraseña en el navegador")
        print("   2. Completa cualquier verificación si Instagram la pide")
        print("   3. Espera a que cargue el feed principal")
        
        # Esperar hasta que llegue al feed (login exitoso)
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
        
        print(f"✅ Cookies guardadas en {COOKIES_FILE}")
        await browser.close()
        return True

async def get_instagram_data(username):
    """Obtener datos de Instagram usando Playwright + API interna"""
    try:
        print(f"🔍 Obteniendo datos de @{username}...")
        username = username.strip().lower()

        if not os.path.exists(COOKIES_FILE):
            return {'success': False, 'error': 'No hay sesión iniciada. Sube las cookies primero.'}

        # Calcular semana anterior
        today = datetime.now()
        dias_desde_lunes = today.weekday()
        lunes_esta_semana = (today - timedelta(days=dias_desde_lunes)).replace(hour=0, minute=0, second=0, microsecond=0)
        lunes_anterior = lunes_esta_semana - timedelta(days=7)
        domingo_anterior = lunes_anterior + timedelta(days=6, hours=23, minutes=59, seconds=59)
        print(f"   📅 Buscando posts: {lunes_anterior.strftime('%d/%m')} - {domingo_anterior.strftime('%d/%m')}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            with open(COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)

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
                except:
                    pass

            page.on('response', handle_response)

            print(f"   🌐 Cargando perfil...")
            try:
                await page.goto(f"https://www.instagram.com/{username}/", wait_until='domcontentloaded', timeout=20000)
            except:
                pass
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
                print(f"   ✅ {followers} seguidores | user_id: {user_id}")
            else:
                print(f"   ❌ No se encontraron datos del usuario")
                await browser.close()
                return {'success': False, 'error': 'No se pudieron obtener datos del perfil'}

            if not user_id:
                await browser.close()
                return {'success': False, 'error': 'No se obtuvo user_id'}

            # Paso 2: Paginar posts usando fetch() desde dentro del navegador
            all_posts = []
            max_id = None

            for pagina in range(10):
                url_api = f"https://www.instagram.com/api/v1/feed/user/{user_id}/?count=50"
                if max_id:
                    url_api += f"&max_id={max_id}"

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
                    print(f"   ⚠️ Error en página {pagina+1}: {result}")
                    break

                items = result.get('items', [])
                if not items:
                    print(f"   ℹ️ No hay más posts")
                    break

                all_posts.extend(items)

                fechas = [datetime.fromtimestamp(int(item['taken_at'])) for item in items if item.get('taken_at')]
                if fechas:
                    mas_antigua = min(fechas)
                    mas_nueva = max(fechas)
                    print(f"   Pág {pagina+1}: {len(items)} posts | {mas_nueva.strftime('%d/%m/%Y')} → {mas_antigua.strftime('%d/%m/%Y')} | total: {len(all_posts)}")

                max_id = result.get('next_max_id')
                if not max_id:
                    print(f"   ℹ️ No hay más páginas")
                    break

                await page.wait_for_timeout(500)

            await browser.close()

            # Paso 3: Filtrar y procesar posts de la semana anterior
            print(f"   📊 Procesando {len(all_posts)} posts totales...")

            posts_week = 0
            likes_week = []
            comments_week = []
            views_week = []

            for item in all_posts:
                taken_at = item.get('taken_at')
                if not taken_at:
                    continue

                post_date = datetime.fromtimestamp(int(taken_at))

                if lunes_anterior <= post_date <= domingo_anterior:
                    media_type = item.get('media_type', 1)
                    
                    # Solo contar videos/reels (media_type == 2)
                    if media_type != 2:
                        continue
                    
                    posts_week += 1
                    likes = item.get('like_count', 0)
                    comments = item.get('comment_count', 0)
                    views = (
                        item.get('view_count') or
                        item.get('play_count') or
                        item.get('video_view_count') or
                        0
                    )

                    likes_week.append(likes)
                    comments_week.append(comments)
                    views_week.append(views)

                    print(f"      📹 Reel ({post_date.strftime('%d/%m')}): {likes}L {comments}C {views}V")

            avg_likes = round(sum(likes_week) / len(likes_week), 1) if likes_week else 0
            avg_comments = round(sum(comments_week) / len(comments_week), 1) if comments_week else 0
            total_views = sum(views_week)
            views_con_datos = [v for v in views_week if v > 0]
            avg_views = round(total_views / len(views_con_datos), 1) if views_con_datos else 0
            total_likes = sum(likes_week)
            total_comments = sum(comments_week)

            print(f"   ✅ {posts_week} posts semana anterior | {total_views} visualizaciones")

            if followers > 0 and posts_week > 0:
                engagement = round(((total_likes + total_comments) / (followers * posts_week)) * 100, 2)
            else:
                engagement = 0

            print(f"✅ {username}: {followers} seg | {posts_week} posts/semana | {total_views} visualizaciones")

            return {
                'success': True,
                'followers': followers,
                'following': following,
                'posts': posts,
                'bio': bio,
                'posts_week': posts_week,
                'avg_likes': avg_likes,
                'avg_comments': avg_comments,
                'avg_views': avg_views,
                'total_likes_week': total_likes,
                'total_comments_week': total_comments,
                'total_views_week': total_views,
                'engagement': engagement,
                'timestamp': datetime.now().strftime('%Y-%m-%d')
            }

    except Exception as e:
        print(f"❌ Error en @{username}: {str(e)}")
        return {'success': False, 'error': str(e)}


@app.route('/api/login-browser', methods=['POST'])
def login_browser():
    """Abrir navegador para login manual"""
    try:
        print("🔐 Abriendo navegador para login...")
        asyncio.run(save_cookies_async())
        return jsonify({'success': True, 'message': 'Login exitoso. Cookies guardadas.'})
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/login-cookie', methods=['POST'])
def login_cookie():
    try:
        body = request.get_json(force=True, silent=True)
        if not body:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400

        cookies = body.get('cookies', [])
        if not cookies:
            return jsonify({'success': False, 'error': 'No se recibieron cookies'}), 400

        print(f"🔐 Guardando {len(cookies)} cookies de Instagram...")

        # Convertir al formato que Playwright espera
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

        print(f"✅ {len(playwright_cookies)} cookies guardadas")
        return jsonify({'success': True, 'message': f'{len(playwright_cookies)} cookies cargadas'})

    except Exception as e:
        print(f"❌ Error: {str(e)}")
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
        return jsonify({'success': True, 'message': f'{len(new_accounts)} cuentas importadas'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ FETCH FOLLOWERS ============

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    try:
        usuario = request.json.get('usuario')
        data = load_data()
        account = next((a for a in data['accounts'] if a['usuario'] == usuario), None)
        if not account:
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
            return jsonify({'success': True, 'data': result})
        else:
            account['status'] = 'failed'
            save_data(data)
            return jsonify({'success': False, 'error': result['error']}), 500

    except Exception as e:
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
        req = request.json
        usuario = req.get('usuario')
        seguidores = int(req.get('seguidores', 0))
        engagement = float(req.get('engagementRate', 0))
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/account/<usuario>', methods=['DELETE'])
def delete_account(usuario):
    try:
        data = load_data()
        data['accounts'] = [a for a in data['accounts'] if a['usuario'] != usuario]
        data['history'] = [h for h in data['history'] if h['usuario'] != usuario]
        save_data(data)
        return jsonify({'success': True})
    except Exception as e:
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-all', methods=['DELETE'])
def clear_all():
    save_data({'accounts': [], 'history': []})
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n🚀 Servidor Flask con Playwright + Cookies")
    print("📊 Abre http://localhost:5000 en tu navegador")
    print("🔐 Primero haz Login desde la app\n")
    app.run(debug=False, host='0.0.0.0', port=7860)