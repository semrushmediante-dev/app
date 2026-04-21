import json
import re

# Leer el archivo debug
with open('debug_api.json', 'r') as f:
    responses = json.load(f)

print(f"Total respuestas: {len(responses)}\n")

def search_dict(d, target_keys, path=""):
    """Buscar recursivamente claves en un dict"""
    results = []
    if isinstance(d, dict):
        for k, v in d.items():
            current_path = f"{path}.{k}" if path else k
            if any(t in k.lower() for t in target_keys):
                results.append((current_path, v))
            results.extend(search_dict(v, target_keys, current_path))
    elif isinstance(d, list):
        for i, item in enumerate(d[:5]):
            results.extend(search_dict(item, target_keys, f"{path}[{i}]"))
    return results

# Buscar followers, following, posts en todas las respuestas
target = ['follower', 'following', 'media_count', 'biography', 'username']

for i, resp in enumerate(responses):
    print(f"=== Respuesta {i+1}: {resp['url'][:60]} ===")
    results = search_dict(resp['data'], target)
    if results:
        for path, val in results[:10]:
            print(f"  ✅ {path}: {val}")
    else:
        print(f"  ❌ Sin datos relevantes")
        print(f"  Keys: {list(resp['data'].keys())}")
    print()
