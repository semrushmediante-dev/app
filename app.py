import os
import logging
import datetime
from flask import Flask, request, jsonify, redirect, url_for, render_template_string, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
logger.info("Flask app creada correctamente")

# --- CONFIGURACIÓN DE SEGURIDAD ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-12345')

csp = {
    'default-src': "'self'",
    'script-src': ["'self'", 'https://cdnjs.cloudflare.com', "'unsafe-inline'"],
    'style-src': ["'self'", 'https://fonts.googleapis.com', "'unsafe-inline'"],
    'font-src': ["'self'", 'https://fonts.gstatic.com']
}
Talisman(app, content_security_policy=csp, force_https=False)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://"
)

# --- LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

users = {"admin": {"password": generate_password_hash("empresa2024")}}
accounts_db = []  # Base de datos temporal

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

LOGIN_HTML = '''
<!DOCTYPE html>
<html><head><title>Login</title><style>
body{background:#0a0a0f;color:white;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;}
.card{background:#13131a;padding:30px;border-radius:15px;border:1px solid #1e1e2e;}
input{width:100%;padding:10px;margin:10px 0;background:#000;border:1px solid #333;color:white;}
button{width:100%;padding:10px;background:#a855f7;color:white;border:none;cursor:pointer;}
</style></head><body>
<div class="card"><h2>Acceso Privado</h2><form method="post">
<input name="username" placeholder="Usuario"><input type="password" name="password" placeholder="Clave">
<button type="submit">Entrar</button></form></div></body></html>
'''

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint para Render"""
    return jsonify({"status": "ok"}), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        if u in users and check_password_hash(users[u]['password'], p):
            login_user(User(u))
            return redirect(url_for('index'))
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return send_from_directory('.', 'index.html')

@app.route('/instagram')
@login_required
def instagram_page():
    return send_from_directory('.', 'indexInstagram.html')

@app.route('/hosting')
@login_required
def hosting_page():
    return send_from_directory('.', 'indexHosting.html')

# --- RUTAS DE API ---

@app.route('/api/accounts', methods=['GET'])
@login_required
def get_accounts():
    return jsonify({
        "success": True, 
        "accounts": accounts_db,
        "total": len(accounts_db)
    })

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    return jsonify({"success": True, "history": []})

@app.route('/api/monitor-hosting', methods=['POST'])
@login_required
def monitor_hosting():
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        
        results = []
        for url in urls:
            if not url.strip():
                continue
            
            # Agregar http:// si no tiene protocolo
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            try:
                import requests
                response = requests.head(url, timeout=5, allow_redirects=True)
                results.append({
                    'url': url,
                    'estado': 'EN LÍNEA',
                    'status_code': response.status_code
                })
            except:
                results.append({
                    'url': url,
                    'estado': 'OFFLINE',
                    'status_code': 0
                })
        
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/import-csv', methods=['POST'])
@login_required
def import_csv():
    try:
        data = request.get_json()
        csv_data = data.get('csvData', '')
        
        if not csv_data:
            return jsonify({"success": False, "error": "No hay datos CSV"}), 400
        
        # Procesar las líneas del CSV
        lineas = csv_data.strip().split('\n')
        
        # Saltar header si existe
        if len(lineas) > 0 and ('Usuario' in lineas[0] or 'usuario' in lineas[0]):
            lineas = lineas[1:]
        
        # Procesar cada línea
        importados = 0
        for linea in lineas:
            if linea.strip():
                # Separar por coma
                partes = [p.strip() for p in linea.split(',')]
                
                if len(partes) >= 1:
                    usuario = partes[0].strip('"\'')
                    encargada = partes[1] if len(partes) > 1 else "N/A"
                    url = partes[2] if len(partes) > 2 else ""
                    
                    # Guardar en la lista (en producción sería en BD)
                    accounts_db.append({
                        "usuario": usuario,
                        "encargada": encargada,
                        "url": url,
                        "followers": 0,
                        "fecha_importacion": str(datetime.datetime.now())
                    })
                    importados += 1
        
        return jsonify({
            "success": True, 
            "message": f"✅ Se importaron {importados} cuenta(s) correctamente",
            "importados": importados
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# --- ENDPOINTS DE INSTAGRAM (PLACEHOLDER) ---

@app.route('/api/login-cookie', methods=['POST'])
@login_required
def login_cookie():
    try:
        data = request.get_json()
        return jsonify({"success": True, "message": "Cookies cargadas"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/fetch-followers', methods=['POST'])
@login_required
def fetch_followers():
    try:
        data = request.get_json()
        usuario = data.get('usuario', 'unknown')
        return jsonify({
            "success": True,
            "usuario": usuario,
            "followers": 1000,
            "following": 500,
            "posts": 150,
            "engagement": 5.2
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/update-followers', methods=['POST'])
@login_required
def update_followers():
    try:
        data = request.get_json()
        return jsonify({"success": True, "updated": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/account/<usuario>', methods=['GET'])
@login_required
def get_account(usuario):
    try:
        return jsonify({
            "success": True,
            "usuario": usuario,
            "followers": 1000,
            "following": 500,
            "posts": 150,
            "bio": "Sample bio",
            "website": "https://example.com"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/clear-all', methods=['POST'])
@login_required
def clear_all():
    try:
        global accounts_db
        accounts_db.clear()
        return jsonify({"success": True, "message": "Datos borrados"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/export-csv', methods=['GET'])
@login_required
def export_csv():
    """Exportar cuentas como CSV"""
    try:
        # Crear CSV en memoria
        csv_content = "Usuario,Encargada,URL,Followers,Fecha\n"
        for account in accounts_db:
            csv_content += f"{account.get('usuario')},{account.get('encargada')},{account.get('url')},{account.get('followers', 0)},{account.get('fecha_importacion', 'N/A')}\n"
        
        # Retornar como JSON para que JavaScript lo descargue
        return jsonify({
            "success": True,
            "csv": csv_content,
            "filename": "cuentas_instagram.csv"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)