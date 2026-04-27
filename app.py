import os
from flask import Flask, request, jsonify, redirect, url_for, render_template_string
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__, static_folder='.', static_url_path='')

# --- CONFIGURACIÓN DE SEGURIDAD ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-muy-larga-12345')

# Cabeceras de seguridad (CSP)
csp = {
    'default-src': '\'self\'',
    'script-src': ['\'self\'', 'https://cdnjs.cloudflare.com', '\'unsafe-inline\''],
    'style-src': ['\'self\'', 'https://fonts.googleapis.com', '\'unsafe-inline\''],
    'font-src': ['\'self\'', 'https://fonts.gstatic.com']
}
Talisman(app, content_security_policy=csp, force_https=False)

# Limitar intentos de login para evitar hackeos por fuerza bruta
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

# --- SISTEMA DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Base de datos de usuarios (Simulada con hash de seguridad)
users = {
    "admin": {
        "password": generate_password_hash("empresa2024")
    }
}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users: return User(user_id)
    return None

# HTML del Formulario de Login (Incrustado para facilitar el despliegue)
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Acceso Privado</title>
    <style>
        body { background: #0a0a0f; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #13131a; padding: 40px; border-radius: 20px; border: 1px solid #1e1e2e; width: 300px; text-align: center; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #1e1e2e; color: white; border-radius: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #a855f7; border: none; color: white; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        .error { color: #ef4444; font-size: 14px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🔒 Panel de Control</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
'''

# --- RUTAS ---

@app.route('/api/accounts')
@login_required
def get_accounts():
    # Aquí deberías retornar tu lista de cuentas real
    return jsonify({"accounts": [], "success": True})

@app.route('/api/history')
@login_required
def get_history():
    return jsonify({"history": [], "success": True})

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users.get(username)
        
        if user and check_password_hash(user['password'], password):
            login_user(User(username))
            return redirect(url_for('index'))
        else:
            error = "Credenciales incorrectas"
    
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return app.send_static_file('index.html')

@app.route('/hosting')
@login_required
def hosting_page():
    return app.send_static_file('indexHosting.html')

@app.route('/instagram')
@login_required
def instagram_page():
    return app.send_static_file('indexInstagram.html')

# Asegura que las APIs también necesiten login
@app.route('/api/monitor-hosting', methods=['POST'])
@login_required
def monitor_hosting():
    # Aquí va tu código de monitoreo...
    return jsonify({"success": True, "results": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)