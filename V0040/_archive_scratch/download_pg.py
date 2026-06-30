import urllib.request
import zipfile
import os

req = urllib.request.Request('https://get.enterprisedb.com/postgresql/postgresql-14.15-1-windows-x64-binaries.zip', headers={'User-Agent': 'Mozilla/5.0'})
print('Downloading...')
with urllib.request.urlopen(req) as response, open('pgsql.zip', 'wb') as out_file:
    out_file.write(response.read())

print('Extracting...')
os.makedirs('ut_server/bin', exist_ok=True)
with zipfile.ZipFile('pgsql.zip', 'r') as zip_ref:
    zip_ref.extractall('ut_server/bin')

os.remove('pgsql.zip')
print('Done!')
☺