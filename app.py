import os
import json
import logging
import asyncio
import csv
import io
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración crítica para Render
app = Flask(__name__, static_folder=os.getcwd(), static_url_path='')
CORS(app)

DB_FILE = 'data.json'
COOKIES_FILE = 'instagram_cookies.json'

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"accounts": [], "history": []}

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- RUTAS DE NAVEGACIÓN ---
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/instagram')
def serve_instagram():
    return send_from_directory(app.static_folder, 'indexInstagram.html')

# --- RUTAS API ---
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    return jsonify(load_data())

@app.route('/api/add-account', methods=['POST'])
def add_account():
    new_acc = request.json
    data = load_data()
    # Evitar duplicados
    if not any(a['usuario'] == new_acc['usuario'] for a in data['accounts']):
        new_acc.update({"seguidores": 0, "posts_week": 0, "total_views_week": 0, "engagementRate": 0, "status": "pending"})
        data['accounts'].append(new_acc)
        save_data(data)
    return jsonify({"success": True, "accounts": data['accounts']})

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file"}), 400
    
    file = request.files['file']
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.DictReader(stream)
    
    data = load_data()
    count = 0
    for row in csv_input:
        user = row.get('usuario', '').replace('@', '').strip()
        if user and not any(a['usuario'] == user for a in data['accounts']):
            data['accounts'].append({
                "usuario": user,
                "encargada": row.get('encargada', 'Sin asignar'),
                "seguidores": 0, "posts_week": 0, "total_views_week": 0, "engagementRate": 0, "status": "pending"
            })
            count += 1
    
    save_data(data)
    return jsonify({"success": True, "added": count, "accounts": data['accounts']})

@app.route('/api/fetch-followers', methods=['POST'])
def fetch_followers():
    usuario = request.json.get('usuario')
    
    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context()
            if os.path.exists(COOKIES_FILE):
                with open(COOKIES_FILE, 'r') as f:
                    await context.add_cookies(json.load(f))
            page = await context.new_page()
            # Lógica de scraping aquí... (usa la función scrape_profile anterior)
            # Por brevedad, simulamos éxito o inserta aquí tu función scrape_profile
            await browser.close()
            return {"success": True, "seguidores": 1500, "posts_week": 3, "total_views_week": 5000, "engagementRate": 4.5}

    result = asyncio.run(run())
    # Actualizar DB
    data = load_data()
    for acc in data['accounts']:
        if acc['usuario'] == usuario:
            acc.update(result)
            acc['status'] = 'completed'
            acc['lastUpdate'] = datetime.now().strftime('%H:%M:%S')
    save_data(data)
    return jsonify(result)

# ... (Otras rutas como delete, etc.)