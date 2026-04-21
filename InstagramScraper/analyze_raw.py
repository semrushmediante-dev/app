import json

with open('debug_api.json', 'r') as f:
    responses = json.load(f)

key = 'xdt_api__v1__feed__user_timeline_graphql_connection'

for i, resp in enumerate(responses):
    data = resp.get('data', {})
    if key in data:
        edges = data[key].get('edges', [])
        print(f"Respuesta {i+1} - {len(edges)} posts\n")
        
        for j, edge in enumerate(edges[:3]):
            node = edge.get('node', {})
            print(f"--- POST {j+1} ---")
            print(json.dumps(node, indent=2, ensure_ascii=False)[:2000])
            print()
        break
