import asyncio
from playwright.async_api import async_playwright
import json
import os

COOKIES_FILE = 'instagram_cookies.json'

async def test():
    username = 'clinica_javier_miranda'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        api_data = {}
        
        async def handle_response(response):
            try:
                if 'graphql' in response.url and response.status == 200:
                    body = await response.json()
                    data_field = body.get('data', {})
                    user = data_field.get('user', {})
                    if user and user.get('follower_count'):
                        api_data['user'] = user
                        print(f"✅ ENCONTRADO: {user.get('follower_count')} seguidores")
            except:
                pass
        
        page.on('response', handle_response)
        
        print(f"Cargando perfil de @{username}...")
        try:
            await page.goto(f"https://www.instagram.com/{username}/", wait_until='domcontentloaded', timeout=20000)
        except:
            pass
        
        await page.wait_for_timeout(4000)
        
        if api_data.get('user'):
            u = api_data['user']
            print(f"\n✅ RESULTADO:")
            print(f"   Seguidores: {u.get('follower_count')}")
            print(f"   Following:  {u.get('following_count')}")
            print(f"   Posts:      {u.get('media_count')}")
            print(f"   Bio:        {u.get('biography', '')[:50]}")
        else:
            print("\n❌ No se encontraron datos")
            print("Guardando debug...")
            html = await page.content()
            with open('debug2.html', 'w', encoding='utf-8') as f:
                f.write(html)
        
        await browser.close()

asyncio.run(test())
