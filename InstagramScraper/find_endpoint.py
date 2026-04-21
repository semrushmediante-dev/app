import requests

headers = {
    'x-rapidapi-key': '44402f3fdamsh8f809a3de0bd410p1308a7jsn31b643963a88',
    'x-rapidapi-host': 'instagram-api-fast-reliable-data-scraper.p.rapidapi.com',
    'Content-Type': 'application/json'
}

endpoints = ['user', 'users', 'profile', 'account', 'user_info', 'users/info', 'get_user', 'username']

for endpoint in endpoints:
    r = requests.get(
        f'https://instagram-api-fast-reliable-data-scraper.p.rapidapi.com/{endpoint}',
        headers=headers,
        params={'username': 'lascuatroesquinas'}
    )
    print(f'{endpoint}: {r.status_code} - {r.text[:100]}')
