import json, re

with open('debug_api.json', 'r') as f:
    responses = json.load(f)

print(f"Total respuestas: {len(responses)}\n")

view_fields = ['play_count', 'view_count', 'ig_play_count', 'video_view_count', 
               'clip_play_count', 'reel_play_count', 'fb_play_count']

for i, resp in enumerate(responses):
    url = resp['url']
    data = resp.get('data', {})
    text = json.dumps(data)
    
    found = [f for f in view_fields if f in text]
    if found:
        print(f"=== Respuesta {i+1}: {url[:60]} ===")
        for field in found:
            matches = re.findall(f'"{field}"\\s*:\\s*(\\d+)', text)
            if matches:
                print(f"  {field}: {matches[:5]}")
        print()

    timeline_key = 'xdt_api__v1__feed__user_timeline_graphql_connection'
    if timeline_key in data:
        edges = data[timeline_key].get('edges', [])
        print(f"=== TIMELINE en respuesta {i+1} - {len(edges)} posts ===")
        for j, edge in enumerate(edges[:3]):
            node = edge.get('node', {})
            print(f"  Post {j+1}:")
            for k, v in node.items():
                if not isinstance(v, (dict, list)):
                    print(f"    {k}: {v}")
        print()

print("✅ Análisis completado")
