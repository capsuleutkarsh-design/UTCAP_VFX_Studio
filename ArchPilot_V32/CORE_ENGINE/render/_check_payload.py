import json
content = open('output/utcap_v32_db_sync.html', encoding='utf-8').read()
if '__JSON_PAYLOAD__' in content:
    print('ERROR: __JSON_PAYLOAD__ was not replaced!')
else:
    marker = 'application/json" id="gd">'
    js_start = content.find(marker)
    js_end = content.find('</script>', js_start)
    raw = content[js_start+len(marker):js_end]
    try:
        data = json.loads(raw)
        print(f'main_nodes: {len(data["main_nodes"])}')
        print(f'main_edges: {len(data["main_edges"])}')
        print(f'total_files: {data.get("total_files","MISSING")}')
        print('First node:', data["main_nodes"][0]["label"] if data["main_nodes"] else 'NONE')
    except Exception as e:
        print(f'JSON parse error: {e}')
        print('Raw snippet:', raw[:200])
