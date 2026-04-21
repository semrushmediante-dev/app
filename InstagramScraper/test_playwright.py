import os
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = r'D:\playwright-browsers'
import asyncio
from playwright.async_api import async_playwright
import json
import os
import re

COOKIES_FILE = 'instagram_cookies.json'

async def test():
    username = 'lascuatroesquinas'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # VISIBLE para ver qué pasa
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        
        # Cargar cookies
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print(f"✅ {len(cookies)} cookies cargadas")
        else:
            print("❌ No hay cookies. Ejecuta la app y haz login primero.")
            await browser.close()
            return
        
        page = await context.new_page()
        
        # Interceptar TODAS las respuestas
        print("\n📡 Interceptando respuestas de red...")
        responses_found = []
        
        async def handle_response(response):
            url = response.url
            if 'instagram' in url and response.status == 200:
                if any(x in url for x in ['graphql', 'api/v1', 'api/v2']):
                    try:
                        body = await response.json()
                        responses_found.append({'url': url, 'data': body})
                        print(f"   📦 API response: {url[:80]}")
                    except:
                        pass
        
        page.on('response', handle_response)
        
        url = f"https://www.instagram.com/{username}/"
        print(f"\n🌐 Cargando {url}...")
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        except:
            pass
        
        # Scroll para forzar carga de posts
        print("   📜 Haciendo scroll para cargar posts...")
        for _ in range(5):
            await page.evaluate('window.scrollBy(0, 800)')
            await page.wait_for_timeout(1500)
        
        await page.wait_for_timeout(3000)
        
        # Guardar HTML para análisis
        html = await page.content()
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML guardado en debug_page.html ({len(html)} chars)")
        
        # Buscar datos en el HTML
        print("\n🔍 Buscando datos en HTML...")
        patterns = {
            'followers': [r'"follower_count":(\d+)', r'"edge_followed_by":\{"count":(\d+)'],
            'following': [r'"following_count":(\d+)', r'"edge_follow":\{"count":(\d+)'],
            'posts':     [r'"media_count":(\d+)', r'"edge_owner_to_timeline_media":\{"count":(\d+)'],
        }
        
        for key, pats in patterns.items():
            for pat in pats:
                m = re.search(pat, html)
                if m:
                    print(f"   ✅ {key}: {m.group(1)} (pattern: {pat})")
                    break
            else:
                print(f"   ❌ {key}: NO ENCONTRADO")
        
        # Buscar en APIs interceptadas
        print(f"\n📦 APIs interceptadas: {len(responses_found)}")
        for r in responses_found[:3]:
            print(f"   URL: {r['url'][:80]}")
            print(f"   Keys: {list(r['data'].keys())[:5]}")
        
        # Guardar respuestas
        with open('debug_api.json', 'w') as f:
            json.dump(responses_found, f, indent=2, default=str)
        print(f"\n💾 APIs guardadas en debug_api.json")
        
        # Buscar con JavaScript
        print("\n🔍 Buscando con JavaScript...")
        js_result = await page.evaluate("""
            () => {
                const results = {};
                
                // window._sharedData
                if (window._sharedData) results['_sharedData'] = 'EXISTS';
                
                // window.__additionalData
                if (window.__additionalData) results['__additionalData'] = Object.keys(window.__additionalData);
                
                // Buscar en todos los scripts
                const scripts = document.querySelectorAll('script');
                let found = false;
                for (const s of scripts) {
                    if (s.textContent.includes('follower_count')) {
                        results['script_with_follower'] = s.textContent.substring(0, 200);
                        found = true;
                        break;
                    }
                }
                if (!found) results['script_with_follower'] = 'NOT FOUND';
                
                return results;
            }
        """)
        print(f"   JS result: {json.dumps(js_result, indent=2)[:500]}")
        
        print("\n⏳ Esperando 5 segundos (mira el navegador)...")
        await page.wait_for_timeout(5000)
        
        await browser.close()
        print("\n✅ Test completado")

if __name__ == '__main__':
    asyncio.run(test())
