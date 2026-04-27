import os
from flask import Flask, request, jsonify, redirect, url_for, render_template_string
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__, static_folder='.', static_url_path='')

# --- CONFIGURACIÓN DE SEGURIDAD ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-12345')

csp = {
    'default-src': "'self'",
    'script-src': ["'self'", 'https://cdnjs.cloudflare.com', "'unsafe-inline'"],
    'style-src': ["'self'", 'https://fonts.googleapis.com', "'unsafe-inline'"],
    'font-src': ["'self'", 'https://fonts.gstatic.com']
}
Talisman(app, content_security_policy=csp, force_https=False)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

# --- LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

users = {"admin": {"password": generate_password_hash("empresa2024")}}
accounts_db = [] # Base de datos temporal

class User(UserMixin):
    def __init__(self, id): self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users: return User(user_id)
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        if u in users and check_password_hash(users[u]['password'], p):
            login_user(User(u))
            return redirect(url_for('index'))
    return render_template_string(LOGIN_HTML)

@app.route('/')
@login_required
def index(): return app.send_static_file('index.html')

@app.route('/instagram')
@login_required
def instagram_page(): return app.send_static_file('indexInstagram.html')

@app.route('/hosting')
@login_required
def hosting_page(): return app.send_static_file('indexHosting.html')

# --- RUTAS DE API (ESTO ES LO QUE SOLUCIONA EL ERROR) ---

@app.route('/api/accounts')
@login_required
def get_accounts():
    return jsonify({"success": True, "accounts": accounts_db})

@app.route('/api/history')
@login_required
def get_history():
    return jsonify({"success": True, "history": []})

@app.route('/api/monitor-hosting', methods=['POST'])
@login_required
def monitor_hosting():
    return jsonify({"success": True, "results": []})

@app.route('/api/import-csv', methods=['POST'])
@login_required
def import_csv():
    return jsonify({"success": True, "message": "Recibido"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)