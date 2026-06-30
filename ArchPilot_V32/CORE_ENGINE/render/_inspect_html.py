content = open('output/utcap_v32_db_sync.html', encoding='utf-8').read()
# Find the main script block (not the JSON one)
idx = content.rfind('<script>')
print('Script starts at:', idx)
snippet = content[idx:idx+800]
# Replace emoji to avoid encode errors
safe = snippet.encode('ascii', errors='replace').decode('ascii')
print(safe[:800])
