from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime, timedelta
import re

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'facebook_cookies.json'

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

async def get_facebook_data(page_name, url=None):
    """Obtener datos de página de Facebook con Playwright"""
    try:
        print(f"🔍 Obteniendo datos de {page_name}...")
        page_name = page_name.strip()

        if not os.path.exists(COOKIES_FILE):
            return {'success': False, 'error': 'No hay sesión. Sube las cookies de Facebook primero.'}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )

            with open(COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print(f"   🍪 {len(cookies)} cookies cargadas")

            page = await context.new_page()

            # Usar la URL directamente si se proporciona, si no construir desde el nombre
            if url and url.startswith('http'):
                target_url = url
            else:
                target_url = f"https://www.facebook.com/{page_name}"
            print(f"   🌐 Cargando {target_url}...")

            try:
                await page.goto(target_url, wait_until='domcontentloaded', timeout=20000)
            except:
                pass

            await page.wait_for_timeout(3000)

            html = await page.content()

            followers = 0
            likes = 0
            name = page_name
            bio = ""
            posts_week = 0
            avg_likes = 0
            avg_comments = 0
            total_likes = 0
            total_comments = 0

            # Extraer datos del HTML de Facebook
            try:
                # Nombre de la página
                name_match = re.search(r'"name"\s*:\s*"([^"]+)".*?"category"', html)
                if name_match:
                    name = name_match.group(1)

                # Seguidores - Facebook usa varios formatos
                follower_patterns = [
                    r'([\d,.]+)\s*(?:personas siguen|people follow|followers)',
                    r'"follower_count"\s*:\s*(\d+)',
                    r'([\d,.]+)\s*seguidores',
                ]
                for pattern in follower_patterns:
                    m = re.search(pattern, html, re.IGNORECASE)
                    if m:
                        val = m.group(1).replace(',', '').replace('.', '')
                        try:
                            followers = int(val)
                            if followers > 0:
                                break
                        except:
                            pass

                # Likes de la página
                likes_patterns = [
                    r'([\d,.]+)\s*(?:personas les gusta|people like|likes)',
                    r'"like_count"\s*:\s*(\d+)',
                    r'([\d,.]+)\s*Me gusta',
                ]
                for pattern in likes_patterns:
                    m = re.search(pattern, html, re.IGNORECASE)
                    if m:
                        val = m.group(1).replace(',', '').replace('.', '')
                        try:
                            likes = int(val)
                            if likes > 0:
                                break
                        except:
                            pass

                # Bio
                bio_match = re.search(r'"description"\s*:\s*"([^"]{10,200})"', html)
                if bio_match:
                    bio = bio_match.group(1)[:100]

            except Exception as e:
                print(f"   ⚠️ Error extrayendo datos básicos: {e}")

            # Si no encontró con regex, buscar en JavaScript
            if followers == 0 and likes == 0:
                try:
                    result = await page.evaluate("""
                        () => {
                            try {
                                // Buscar en __initialData o __bbox
                                const scripts = document.querySelectorAll('script[type="application/json"]');
                                for (const s of scripts) {
                                    const text = s.textContent;
                                    if (text.includes('follower_count') || text.includes('fan_count')) {
                                        const data = JSON.parse(text);
                                        const str = JSON.stringify(data);
                                        const fMatch = str.match(/"follower_count":(\d+)/);
                                        const lMatch = str.match(/"fan_count":(\d+)/);
                                        if (fMatch || lMatch) {
                                            return {
                                                followers: fMatch ? parseInt(fMatch[1]) : 0,
                                                likes: lMatch ? parseInt(lMatch[1]) : 0
                                            };
                                        }
                                    }
                                }
                                return null;
                            } catch(e) { return null; }
                        }
                    """)
                    if result:
                        followers = result.get('followers', 0)
                        likes = result.get('likes', 0)
                        print(f"   ✅ Datos de JavaScript")
                except:
                    pass

            # Obtener posts de la última semana
            try:
                print(f"   📊 Analizando posts de la última semana...")
                one_week_ago = datetime.now() - timedelta(days=7)

                # Buscar timestamps de posts en el HTML
                timestamps = re.findall(r'"creation_time"\s*:\s*(\d+)', html)
                reactions = re.findall(r'"reaction_count"\s*:\s*\{"count"\s*:\s*(\d+)', html)
                comments = re.findall(r'"comment_count"\s*:\s*(\d+)', html)

                likes_week = []
                comments_week = []

                for i, ts in enumerate(timestamps[:20]):
                    try:
                        post_date = datetime.fromtimestamp(int(ts))
                        if post_date >= one_week_ago:
                            posts_week += 1
                            if i < len(reactions):
                                likes_week.append(int(reactions[i]))
                            if i < len(comments):
                                comments_week.append(int(comments[i]))
                    except:
                        pass

                avg_likes = round(sum(likes_week) / len(likes_week), 1) if likes_week else 0
                avg_comments = round(sum(comments_week) / len(comments_week), 1) if comments_week else 0
                total_likes = sum(likes_week)
                total_comments = sum(comments_week)

                print(f"   📊 {posts_week} posts esta semana")
            except Exception as e:
                print(f"   ⚠️ Error posts: {e}")

            await browser.close()

            # Engagement
            if followers > 0 and posts_week > 0:
                engagement = round(((total_likes + total_comments) / (followers * posts_week)) * 100, 2)
            elif likes > 0 and posts_week > 0:
                engagement = round(((total_likes + total_comments) / (likes * posts_week)) * 100, 2)
            else:
                engagement = 0

            print(f"✅ {page_name}: {followers} seguidores | {likes} likes | {posts_week} posts/semana")

            return {
                'success': True,
                'name': name,
                'followers': followers,
                'likes': likes,
                'bio': bio,
                'posts_week': posts_week,
                'avg_likes': avg_likes,
                'avg_comments': avg_comments,
                'total_likes_week': total_likes,
                'total_comments_week': total_comments,
                'engagement': engagement,
                'timestamp': datetime.now().strftime('%Y-%m-%d')
            }

    except Exception as e:
        print(f"❌ Error en {page_name}: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/api/login-cookie', methods=['POST'])
def login_cookie():
    try:
        body = request.get_json(force=True, silent=True)
        if not body:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400

        cookies = body.get('cookies', [])
        if not cookies:
            return jsonify({'success': False, 'error': 'No se recibieron cookies'}), 400

        print(f"🔐 Guardando {len(cookies)} cookies de Facebook...")

        playwright_cookies = []
        for c in cookies:
            pc = {
                'name': c.get('name', ''),
                'value': c.get('value', ''),
                'domain': c.get('domain', '.facebook.com'),
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

        print(f"✅ {len(playwright_cookies)} cookies guardadas")
        return jsonify({'success': True, 'message': f'{len(playwright_cookies)} cookies cargadas'})

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            pagina, encargada, url = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not pagina or not encargada or not url:
                continue
            if not any(a['pagina'] == pagina for a in data['accounts']):
                new_accounts.append({
                    'id': int(datetime.now().timestamp() * 1000) + i,
                    'pagina': pagina,
                    'encargada': encargada,
                    'url': url,
                    'name': None,
                    'seguidores': None,
                    'likes': None,
                    'bio': None,
                    'posts_week': None,
                    'avg_likes': None,
                    'avg_comments': None,
                    'engagementRate': None,
                    'lastUpdate': None,
                    'status': 'pending'
                })

        data['accounts'].extend(new_accounts)
        save_data(data)
        return jsonify({'success': True, 'message': f'{len(new_accounts)} páginas importadas'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    try:
        pagina = request.json.get('pagina')
        data = load_data()
        account = next((a for a in data['accounts'] if a['pagina'] == pagina), None)
        if not account:
            return jsonify({'success': False, 'error': 'Página no encontrada'}), 404

        # Obtener URL de la cuenta si existe
        fb_url = account.get('url', '')
        result = asyncio.run(get_facebook_data(pagina, url=fb_url))

        if result['success']:
            account.update({
                'name': result['name'],
                'seguidores': result['followers'],
                'likes': result['likes'],
                'bio': result['bio'],
                'posts_week': result['posts_week'],
                'avg_likes': result['avg_likes'],
                'avg_comments': result['avg_comments'],
                'engagementRate': result['engagement'],
                'lastUpdate': result['timestamp'],
                'status': 'completed'
            })
            data['history'].append({
                'pagina': pagina,
                'seguidores': result['followers'],
                'likes': result['likes'],
                'posts_week': result['posts_week'],
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

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    data = load_data()
    return jsonify({'success': True, 'accounts': data['accounts']})

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify({'success': True, 'history': data['history']})

@app.route('/api/account/<pagina>', methods=['DELETE'])
def delete_account(pagina):
    try:
        data = load_data()
        data['accounts'] = [a for a in data['accounts'] if a['pagina'] != pagina]
        data['history'] = [h for h in data['history'] if h['pagina'] != pagina]
        save_data(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    try:
        data = load_data()
        csv = 'Página,Encargada,URL,Nombre,Seguidores,Likes,Posts Semana,Avg Likes,Avg Comments,Engagement (%),Última Actualización\n'
        for a in data['accounts']:
            csv += f"{a['pagina']},{a['encargada']},{a['url']},"
            csv += f"{a.get('name') or 'N/A'},{a['seguidores'] or 'N/A'},"
            csv += f"{a.get('likes') or 'N/A'},{a.get('posts_week') or 'N/A'},"
            csv += f"{a.get('avg_likes') or 'N/A'},{a.get('avg_comments') or 'N/A'},"
            csv += f"{a.get('engagementRate') or 'N/A'},{a['lastUpdate'] or 'N/A'}\n"
        filename = f"facebook_{datetime.now().strftime('%Y-%m-%d')}.csv"
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
    print("\n🚀 Servidor Facebook Scraper")
    print("📊 Abre http://localhost:5001 en tu navegador\n")
    app.run(debug=False, host='localhost', port=5001)
