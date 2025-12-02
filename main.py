# test_nextcloud.py
import requests
from requests.auth import HTTPBasicAuth

# Configuración UO
NEXTCLOUD_URL = 'https://nube.uo.edu.cu'
USERNAME = 'eric.serrano'
PASSWORD = 'Rulebreaker2316'

print("🔍 Probando conexión a nube.uo.edu.cu...")
print(f"Usuario: {USERNAME}")

# 1. Probar endpoint de estado
try:
    response = requests.get(
        f"{NEXTCLOUD_URL}/status.php",
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=10
    )
    print(f"✅ Status endpoint: {response.status_code}")
    print(f"Respuesta: {response.text[:100]}")
except Exception as e:
    print(f"❌ Error status: {e}")

# 2. Probar WebDAV (crear carpeta)
try:
    webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{USERNAME}/test_folder"
    response = requests.request(
        'MKCOL',
        webdav_url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=10
    )
    print(f"\n📁 WebDAV MKCOL: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    if response.status_code != 201:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error WebDAV: {e}")

# 3. Probar si ya existe una carpeta
try:
    existing_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{USERNAME}/"
    response = requests.request(
        'PROPFIND',
        existing_url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={'Depth': '1'},
        timeout=10
    )
    print(f"\n📂 Listar carpeta raíz: {response.status_code}")
    if response.status_code == 207:
        print("✅ Tienes acceso a WebDAV")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error PROPFIND: {e}")
