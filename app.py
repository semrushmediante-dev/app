import os
import sys
import json
import asyncio
import re
import requests as req
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# 1. CONFIGURACIÓN DE RUTAS ABSOLUTAS (Para evitar el error "Not Found")
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder=basedir, static_url_path='')
CORS(app)

DB_FILE = os.path.join(basedir, 'data.json')
COOKIES_FILE = os.path.join(basedir, 'instagram_cookies.json')
browser_instance = None
context_instance = None

# ==========================================
# RUTAS DE NAVEGACIÓN (Páginas HTML)
# ==========================================

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/hosting')
def hosting_page():
    return app.send_static_file('indexHosting.html')

@app.route('/instagram')
def instagram_page():
    return app.send_static_file('indexInstagram.html')

# ==========================================
# FUNCIONES DE APOYO (Datos y Cookies)
# ==========================================

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

# ==========================================
# NUEVA LÓGICA: MONITOREO DE HOSTING
# ==========================================

@app.route('/api/monitor-hosting', methods=['POST'])
def monitor_hosting():
    try:
        body = request.get_json()
        # Recibimos las URLs (vengan de un textarea o procesadas por el botón CSV del front)
        urls_raw = body.get('urls', [])
        
        if isinstance(urls_raw, str):
            urls_raw = urls_raw.split('\n')

        # --- LÓGICA DE FILTRADO Y LIMPIEZA ---
        # Definimos palabras que suelen ser encabezados para ignorarlas
        blacklist = [
            'url', 'urls', 'link', 'links', 'sitio', 'sitios', 
            'enlace', 'enlaces', 'web', 'webs', 'hosting', 'estado'
        ]
        
        urls_validas = []
        for line in urls_raw:
            clean_line = line.strip().replace('"', '').replace("'", "")
            # Si la línea tiene comas (formato CSV crudo), pillamos solo la primera columna
            if ',' in clean_line:
                clean_line = clean_line.split(',')[0].strip()
            
            # Solo añadimos si no está vacío y no es un encabezado de la lista negra
            if clean_line and clean_line.lower() not in blacklist:
                urls_validas.append(clean_line)

        # --- PROCESO DE MONITOREO ---
        resultados = []
        cabeceras = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }

        for url in urls_validas:
            # Asegurar que la URL tenga protocolo para que requests no falle
            url_destino = url
            if not url_destino.startswith(('http://', 'https://')):
                url_destino = 'https://' + url_destino
            
            estado = ""
            status_code = None
            
            try:
                # Realizamos la petición con un timeout de 10 segundos
                response = req.get(url_destino, headers=cabeceras, timeout=10, verify=False)
                status_code = response.status_code
                
                if status_code == 200:
                    estado = "EN LÍNEA"
                else:
                    estado = f"ERROR {status_code}"
            
            except req.exceptions.Timeout:
                estado = "TIMEOUT (Lento)"
            except req.exceptions.ConnectionError:
                estado = "CAÍDA / ERROR CONEXIÓN"
            except Exception as e:
                estado = "ERROR DESCONOCIDO"

            resultados.append({
                'url': url_destino,
                'estado': estado,
                'status_code': status_code,
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M')
            })

        return jsonify({
            'success': True, 
            'total': len(resultados),
            'results': resultados
        })

    except Exception as e:
        print(f"Error en monitoreo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==========================================
# RUTAS DE INSTAGRAM (Scraper y API)
# ==========================================

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    return jsonify(load_data())

@app.route('/api/accounts', methods=['POST'])
def add_account():
    try:
        new_acc = request.get_json()
        data = load_data()
        
        # Evitar duplicados
        if any(a['usuario'].lower() == new_acc['usuario'].lower() for a in data['accounts']):
            return jsonify({'success': False, 'error': 'La cuenta ya existe'}), 400
            
        new_acc.update({
            'seguidores': None, 'following': None, 'posts_week': 0,
            'avg_likes': 0, 'avg_comments': 0, 'engagementRate': 0,
            'lastUpdate': None
        })
        data['accounts'].append(new_acc)
        save_data(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-all', methods=['DELETE'])
def clear_all():
    try:
        save_data({"accounts": [], "history": []})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    try:
        data = load_data()
        csv_content = 'Usuario,Encargada,URL,Estado,Última Actualización\n'
        for a in data['accounts']:
            csv_content += f"{a['usuario']},{a['encargada']},{a['url']},{a.get('seguidores','N/A')},{a['lastUpdate']}\n"
        
        filename = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        path = os.path.join(basedir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==========================================
# INICIO DEL SERVIDOR
# ==========================================

if __name__ == '__main__':
    # Asegúrate de que el puerto coincida con el de tu archivo .bat (7860)
    print(f"Iniciando App en: http://localhost:7860")
    app.run(debug=False, host='0.0.0.0', port=7860)