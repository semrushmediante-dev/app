import os
import json
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuración de almacenamiento
DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'

# Variables globales
data_cache = {}

# ═════════════════════════════════════════════════════════════
# FUNCIONES DE ALMACENAMIENTO
# ═════════════════════════════════════════════════════════════

def load_data():
    """Cargar datos del archivo JSON"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {"accounts": [], "history": []}

def save_data(data):
    """Guardar datos al archivo JSON"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def get_data():
    """Obtener datos cacheados"""
    global data_cache
    if not data_cache:
        data_cache = load_data()
    return data_cache

def update_data_cache(data):
    """Actualizar caché y guardar"""
    global data_cache
    data_cache = data
    save_data(data)

# ═════════════════════════════════════════════════════════════
# RUTAS PRINCIPALES
# ═════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Servir página principal"""
    try:
        return send_from_directory('.', 'index.html')
    except:
        return jsonify({"error": "index.html not found"}), 404

@app.route('/instagram')
def instagram_page():
    """Servir página de Instagram"""
    try:
        return send_from_directory('.', 'indexInstagram.html')
    except:
        return jsonify({"error": "indexInstagram.html not found"}), 404

@app.route('/health')
def health():
    """Health check para Render"""
    return jsonify({"status": "ok"}), 200

# ═════════════════════════════════════════════════════════════
# API ENDPOINTS - CUENTAS
# ═════════════════════════════════════════════════════════════

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Obtener todas las cuentas"""
    try:
        data = get_data()
        accounts = data.get('accounts', [])
        
        # Asegurar campos completos
        for account in accounts:
            if 'seguidores' not in account:
                account['seguidores'] = 0
            if 'posts_week' not in account:
                account['posts_week'] = 0
            if 'total_views_week' not in account:
                account['total_views_week'] = 0
            if 'engagementRate' not in account:
                account['engagementRate'] = 0.0
            if 'lastUpdate' not in account:
                account['lastUpdate'] = 'N/A'
            if 'status' not in account:
                account['status'] = 'Pending'
        
        return jsonify({
            "success": True,
            "accounts": accounts,
            "total": len(accounts)
        })
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    """Importar cuentas desde CSV"""
    try:
        req_data = request.get_json()
        csv_data = req_data.get('csvData', '')
        
        if not csv_data:
            return jsonify({"success": False, "error": "No hay datos CSV"}), 400
        
        data = get_data()
        lineas = csv_data.strip().split('\n')
        
        # Saltar header si existe
        if len(lineas) > 0 and ('Usuario' in lineas[0] or 'usuario' in lineas[0]):
            lineas = lineas[1:]
        
        importados = 0
        for linea in lineas:
            if linea.strip():
                partes = [p.strip() for p in linea.split(',')]
                
                if len(partes) >= 1:
                    usuario = partes[0].strip('"\'')
                    encargada = partes[1] if len(partes) > 1 else "N/A"
                    url = partes[2] if len(partes) > 2 else ""
                    
                    # Crear cuenta con todos los campos
                    account = {
                        "usuario": usuario,
                        "encargada": encargada,
                        "url": url,
                        "seguidores": 0,
                        "posts_week": 0,
                        "total_views_week": 0,
                        "engagementRate": 0.0,
                        "lastUpdate": datetime.now().strftime('%Y-%m-%d %H:%M'),
                        "status": "Pending"
                    }
                    
                    # Verificar si ya existe
                    existe = False
                    for acc in data['accounts']:
                        if acc.get('usuario') == usuario:
                            acc.update(account)
                            existe = True
                            break
                    
                    if not existe:
                        data['accounts'].append(account)
                    
                    importados += 1
        
        update_data_cache(data)
        return jsonify({
            "success": True,
            "message": f"✅ Se importaron {importados} cuenta(s) correctamente",
            "importados": importados,
            "accounts": data['accounts']
        })
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    """Obtener datos de seguidores"""
    try:
        req_data = request.get_json()
        usuario = req_data.get('usuario', '')
        
        if not usuario:
            return jsonify({"success": False, "error": "Usuario no especificado"}), 400
        
        data = get_data()
        
        # Buscar la cuenta
        for account in data['accounts']:
            if account.get('usuario') == usuario:
                return jsonify({
                    "success": True,
                    "usuario": usuario,
                    "data": {
                        "seguidores": account.get('seguidores', 0),
                        "posts_week": account.get('posts_week', 0),
                        "total_views_week": account.get('total_views_week', 0),
                        "engagementRate": account.get('engagementRate', 0.0)
                    }
                })
        
        return jsonify({"success": False, "error": "Cuenta no encontrada"}), 404
    except Exception as e:
        logger.error(f"Error fetching followers: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/update-followers', methods=['POST'])
def update_followers():
    """Actualizar datos de seguidores"""
    try:
        req_data = request.get_json()
        usuario = req_data.get('usuario', '')
        seguidores = req_data.get('seguidores', 0)
        engagement_rate = req_data.get('engagementRate', 0)
        
        if not usuario:
            return jsonify({"success": False, "error": "Usuario no especificado"}), 400
        
        data = get_data()
        
        # Buscar y actualizar
        actualizado = False
        for account in data['accounts']:
            if account.get('usuario') == usuario:
                account['seguidores'] = int(seguidores)
                account['engagementRate'] = float(engagement_rate)
                account['lastUpdate'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                actualizado = True
                logger.info(f"Updated account {usuario}")
                break
        
        if not actualizado:
            return jsonify({"success": False, "error": "Cuenta no encontrada"}), 404
        
        update_data_cache(data)
        
        return jsonify({
            "success": True,
            "message": f"✅ @{usuario} actualizado correctamente",
            "accounts": data['accounts']
        })
    except Exception as e:
        logger.error(f"Error updating followers: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/account/<usuario>', methods=['DELETE'])
def delete_account(usuario):
    """Eliminar una cuenta"""
    try:
        data = get_data()
        original_length = len(data['accounts'])
        data['accounts'] = [acc for acc in data['accounts'] if acc.get('usuario') != usuario]
        
        if len(data['accounts']) == original_length:
            return jsonify({"success": False, "error": "Cuenta no encontrada"}), 404
        
        logger.info(f"Deleted account: {usuario}")
        update_data_cache(data)
        
        return jsonify({
            "success": True,
            "message": f"✅ Cuenta @{usuario} eliminada",
            "accounts": data['accounts']
        })
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

# ═════════════════════════════════════════════════════════════
# API ENDPOINTS - DATOS ADICIONALES
# ═════════════════════════════════════════════════════════════

@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtener historial"""
    try:
        data = get_data()
        return jsonify({
            "success": True,
            "history": data.get('history', [])
        })
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    """Exportar cuentas como CSV"""
    try:
        data = get_data()
        csv_content = "Usuario,Encargada,URL,Seguidores,Engagement,Última Actualización\n"
        
        for account in data['accounts']:
            csv_content += f"{account.get('usuario')},{account.get('encargada')},{account.get('url')},{account.get('seguidores', 0)},{account.get('engagementRate', 0)},{account.get('lastUpdate', 'N/A')}\n"
        
        return jsonify({
            "success": True,
            "csv": csv_content,
            "filename": "cuentas_instagram.csv"
        })
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/clear-all', methods=['DELETE', 'POST'])
def clear_all():
    """Limpiar todas las cuentas"""
    try:
        data = {"accounts": [], "history": []}
        update_data_cache(data)
        logger.info("All accounts cleared")
        
        return jsonify({
            "success": True,
            "message": "✅ Todas las cuentas han sido eliminadas",
            "accounts": []
        })
    except Exception as e:
        logger.error(f"Error clearing accounts: {e}")
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
# MAIN
# ═════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)