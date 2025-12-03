# main.py - SIMULADOR DE NAVEGADOR REAL
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin, quote, urlparse
from typing import Tuple, Optional, Dict
import time
import random
import json
from fake_useragent import UserAgent

# ============================================
# CONFIGURACIÓN
# ============================================

NEXTCLOUD_CONFIG = {
    "base_url": "https://minube.uh.cu/",
    "username": "Claudia.btabares@estudiantes.instec.uh.cu",
    "password": "cbt260706*TM",
    "upload_base": "TelegramBot/"
}

TELEGRAM_BOT_TOKEN = "8598403831:AAF_W2ob_i-FVTrW9KC0pmyMX30oeH5WGfo"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# SIMULADOR DE NAVEGADOR REAL
# ============================================

class RealBrowserSimulator:
    """Simula un navegador Chrome real con todos los headers"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self._setup_headers()
        self.logged_in = False
        
    def _setup_headers(self):
        """Configurar headers exactos de Chrome"""
        chrome_version = f"{random.randint(120, 125)}.0.{random.randint(6000, 7000)}.{random.randint(100, 200)}"
        
        self.session.headers = {
            # Headers principales
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            
            # Headers de conexión
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            
            # Headers de seguridad
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            
            # Headers adicionales
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Priority': 'u=0, i',
        }
        
        # Cookies básicas
        self.session.cookies.set('cookie_test', 'test', domain='.uh.cu')
        
    def _add_referer(self, url):
        """Añade Referer header"""
        self.session.headers['Referer'] = url
    
    def _add_origin(self, url):
        """Añade Origin header"""
        parsed = urlparse(url)
        self.session.headers['Origin'] = f"{parsed.scheme}://{parsed.netloc}"
    
    def _random_delay(self):
        """Retraso aleatorio como humano"""
        time.sleep(random.uniform(0.5, 2.0))
    
    def discover_nextcloud_url(self):
        """Descubre la URL real de NextCloud"""
        test_urls = [
            "https://minube.uh.cu/",
            "https://minube.uh.cu/cloud/",
            "https://minube.uh.cu/nextcloud/",
            "https://minube.uh.cu/nc/",
            "https://cloud.uh.cu/",
            "https://nextcloud.uh.cu/",
        ]
        
        for url in test_urls:
            try:
                self._random_delay()
                response = self.session.get(url, timeout=10, allow_redirects=True)
                
                logger.info(f"Probando {url} → {response.status_code}")
                
                # Buscar indicadores de NextCloud
                html_lower = response.text.lower()
                indicators = ['nextcloud', 'owncloud', 'log in to', 'password', 'username']
                
                if any(indicator in html_lower for indicator in indicators):
                    logger.info(f"✓ Posible NextCloud en: {url}")
                    return url
                    
            except Exception as e:
                logger.error(f"Error probando {url}: {e}")
        
        return None
    
    def extract_csrf_token(self, html):
        """Extrae token CSRF del HTML"""
        import re
        
        # Buscar en input hidden
        patterns = [
            r'name="requesttoken"\s+value="([^"]+)"',
            r'name="csrf_token"\s+value="([^"]+)"',
            r'name="token"\s+value="([^"]+)"',
            r'data-requesttoken="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def login(self, base_url, username, password):
        """Login como navegador real"""
        try:
            # 1. Obtener página principal
            self._random_delay()
            response = self.session.get(base_url, timeout=15)
            
            # 2. Seguir redirecciones si las hay
            final_url = response.url
            logger.info(f"URL final después de redirecciones: {final_url}")
            
            # 3. Extraer token CSRF
            csrf_token = self.extract_csrf_token(response.text)
            logger.info(f"Token CSRF encontrado: {csrf_token is not None}")
            
            # 4. Preparar datos de login
            login_data = {
                'user': username,
                'password': password,
                'timezone_offset': '0',
            }
            
            if csrf_token:
                login_data['requesttoken'] = csrf_token
            
            # 5. Determinar URL de login
            login_urls = [
                urljoin(final_url, "index.php/login"),
                urljoin(final_url, "login"),
                urljoin(final_url, ""),  # La misma página
            ]
            
            # 6. Intentar login
            for login_url in login_urls:
                try:
                    self._add_referer(final_url)
                    self._add_origin(final_url)
                    
                    self._random_delay()
                    login_response = self.session.post(
                        login_url,
                        data=login_data,
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    logger.info(f"Login en {login_url} → {login_response.status_code}")
                    
                    # Verificar si login fue exitoso
                    if login_response.status_code == 200:
                        # Buscar indicadores de éxito
                        if "dashboard" in login_response.text.lower() or "files" in login_response.text.lower():
                            self.logged_in = True
                            logger.info("✓ Login exitoso")
                            return True
                        else:
                            # Intentar con cookies de sesión
                            self._try_session_cookie(login_response)
                            return True
                    
                except Exception as e:
                    logger.error(f"Error en login {login_url}: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error en proceso de login: {e}")
            return False
    
    def _try_session_cookie(self, response):
        """Intentar usar cookies de sesión existentes"""
        if 'Set-Cookie' in response.headers:
            cookies = response.headers['Set-Cookie']
            if 'nc_session_id' in cookies or 'oc_sessionPassphrase' in cookies:
                self.logged_in = True
                logger.info("✓ Sesión establecida via cookies")
                return True
        return False
    
    def upload_file(self, file_path: Path, remote_folder: str = "") -> Tuple[bool, str]:
        """Subir archivo simulando navegador"""
        if not self.logged_in:
            return False, "No hay sesión activa"
        
        try:
            file_name = file_path.name
            file_size = file_path.stat().st_size
            
            # 1. Obtener página de files para tener token actual
            self._random_delay()
            files_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "apps/files/")
            files_response = self.session.get(files_url, timeout=15)
            
            # Extraer token actual
            current_token = self.extract_csrf_token(files_response.text)
            
            # 2. Preparar upload via WebDAV (más compatible)
            # Primero crear carpeta si no existe
            if remote_folder:
                self._create_folder(remote_folder, current_token)
            
            # 3. Subir archivo
            upload_methods = [
                self._upload_webdav,
                self._upload_api,
                self._upload_form,
            ]
            
            for method in upload_methods:
                logger.info(f"Intentando método: {method.__name__}")
                success, result = method(file_path, remote_folder, current_token)
                if success:
                    return True, result
            
            return False, "Todos los métodos fallaron"
            
        except Exception as e:
            logger.error(f"Error en upload: {e}")
            return False, f"Error: {str(e)}"
    
    def _create_folder(self, folder_path: str, csrf_token: str):
        """Crear carpeta via API"""
        try:
            create_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "apps/files/api/v1/files")
            
            data = {
                'dirname': folder_path,
                'requesttoken': csrf_token if csrf_token else ''
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'OCS-APIRequest': 'true',
            }
            
            response = self.session.post(create_url, data=data, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"✓ Carpeta {folder_path} creada")
                return True
            else:
                logger.warning(f"No se pudo crear carpeta: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error creando carpeta: {e}")
            return False
    
    def _upload_webdav(self, file_path: Path, remote_folder: str, csrf_token: str) -> Tuple[bool, str]:
        """Método WebDAV"""
        try:
            file_name = file_path.name
            remote_path = f"{remote_folder}/{file_name}" if remote_folder else file_name
            
            webdav_url = urljoin(NEXTCLOUD_CONFIG["base_url"], f"remote.php/dav/files/{NEXTCLOUD_CONFIG['username']}/{quote(remote_path)}")
            
            # Headers para WebDAV
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(file_path.stat().st_size),
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            if csrf_token:
                headers['requesttoken'] = csrf_token
            
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    webdav_url,
                    data=f,
                    headers=headers,
                    timeout=60
                )
            
            if response.status_code in [201, 204]:
                return True, f"WebDAV: {file_name}"
            else:
                return False, f"WebDAV Error {response.status_code}"
                
        except Exception as e:
            return False, f"WebDAV: {str(e)}"
    
    def _upload_api(self, file_path: Path, remote_folder: str, csrf_token: str) -> Tuple[bool, str]:
        """Método API directa"""
        try:
            file_name = file_path.name
            upload_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "ocs/v2.php/apps/files/api/v1/files")
            
            # Añadir path si existe
            if remote_folder:
                upload_url += f"/{remote_folder}"
            
            headers = {
                'OCS-APIRequest': 'true',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            if csrf_token:
                headers['requesttoken'] = csrf_token
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f)}
                response = self.session.post(
                    f"{upload_url}/{file_name}",
                    files=files,
                    headers=headers,
                    timeout=60
                )
            
            if response.status_code == 200:
                return True, f"API: {file_name}"
            else:
                return False, f"API Error {response.status_code}"
                
        except Exception as e:
            return False, f"API: {str(e)}"
    
    def _upload_form(self, file_path: Path, remote_folder: str, csrf_token: str) -> Tuple[bool, str]:
        """Método formulario HTML (como navegador)"""
        try:
            file_name = file_path.name
            form_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "index.php/apps/files/")
            
            with open(file_path, 'rb') as f:
                files = {
                    'files[]': (file_name, f, 'application/octet-stream'),
                    'requesttoken': (None, csrf_token if csrf_token else ''),
                    'dir': (None, remote_folder if remote_folder else '/'),
                }
                
                response = self.session.post(
                    form_url,
                    files=files,
                    timeout=60
                )
            
            if response.status_code == 200:
                # Verificar en respuesta JSON
                try:
                    data = response.json()
                    if data.get('status') == 'success':
                        return True, f"Form: {file_name}"
                except:
                    if 'success' in response.text.lower():
                        return True, f"Form: {file_name}"
                
            return False, f"Form Error {response.status_code}"
            
        except Exception as e:
            return False, f"Form: {str(e)}"

# ============================================
# BOT DE TELEGRAM
# ============================================

class TelegramNextCloudBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.browser = RealBrowserSimulator()
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome = """🤖 <b>NextCloud Bot - Simulador de Navegador</b>

<i>Conectando como navegador real...</i>

<b>Comandos:</b>
/login - Conectar a NextCloud
/status - Ver estado
/test - Probar conexión
/upload - Instrucciones

<b>Envía cualquier archivo</b> para subirlo."""
            
            self.bot.reply_to(message, welcome, parse_mode='HTML')
        
        @self.bot.message_handler(commands=['login'])
        def login_command(message):
            self.bot.reply_to(message, "🔐 Conectando a NextCloud...")
            
            # Descubrir URL
            url = self.browser.discover_nextcloud_url()
            if not url:
                self.bot.reply_to(message, "❌ No se pudo encontrar NextCloud")
                return
            
            self.bot.reply_to(message, f"📍 URL encontrada: {url}")
            
            # Login
            success = self.browser.login(
                url,
                NEXTCLOUD_CONFIG["username"],
                NEXTCLOUD_CONFIG["password"]
            )
            
            if success:
                self.bot.reply_to(message, "✅ Conectado a NextCloud")
            else:
                self.bot.reply_to(message, "❌ Error en login")
        
        @self.bot.message_handler(commands=['status'])
        def status_command(message):
            if self.browser.logged_in:
                self.bot.reply_to(message, "✅ Sesión activa")
            else:
                self.bot.reply_to(message, "❌ No hay sesión. Usa /login")
        
        @self.bot.message_handler(commands=['test'])
        def test_command(message):
            self.bot.reply_to(message, "🧪 Probando...")
            
            # Crear archivo de prueba
            test_file = Path("test.txt")
            test_file.write_text(f"Prueba {time.ctime()}")
            
            success, result = self.browser.upload_file(
                test_file,
                NEXTCLOUD_CONFIG["upload_base"]
            )
            
            test_file.unlink(missing_ok=True)
            
            if success:
                self.bot.reply_to(message, f"✅ {result}")
            else:
                self.bot.reply_to(message, f"❌ {result}")
        
        @self.bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
        def handle_file(message):
            try:
                self.bot.reply_to(message, "📥 Descargando...")
                
                # Obtener archivo
                file_info = None
                file_name = ""
                
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_name = message.document.file_name or f"doc_{message.message_id}"
                elif message.photo:
                    file_info = self.bot.get_file(message.photo[-1].file_id)
                    file_name = f"photo_{message.message_id}.jpg"
                elif message.video:
                    file_info = self.bot.get_file(message.video.file_id)
                    file_name = message.video.file_name or f"video_{message.message_id}.mp4"
                elif message.audio:
                    file_info = self.bot.get_file(message.audio.file_id)
                    file_name = message.audio.file_name or f"audio_{message.message_id}.mp3"
                else:
                    self.bot.reply_to(message, "❌ Tipo no soportado")
                    return
                
                # Descargar
                downloaded = self.bot.download_file(file_info.file_path)
                
                # Guardar temporal
                temp_file = Path(f"temp_{file_name}")
                temp_file.write_bytes(downloaded)
                
                # Subir
                self.bot.reply_to(message, f"📤 Subiendo {file_name}...")
                
                success, result = self.browser.upload_file(
                    temp_file,
                    NEXTCLOUD_CONFIG["upload_base"]
                )
                
                # Limpiar
                temp_file.unlink(missing_ok=True)
                
                if success:
                    self.bot.reply_to(message, f"✅ {result}")
                else:
                    self.bot.reply_to(message, f"❌ {result}")
                    
            except Exception as e:
                logger.error(f"Error: {e}")
                self.bot.reply_to(message, f"❌ Error: {str(e)[:100]}")
        
        @self.bot.message_handler(func=lambda message: True)
        def default_handler(message):
            self.bot.reply_to(message, "Usa /login primero, luego envía archivos")
    
    def run(self):
        logger.info("🚀 Iniciando bot simulador...")
        self.bot.remove_webhook()
        time.sleep(1)
        self.bot.infinity_polling(timeout=30, skip_pending=True)

# ============================================
# MAIN
# ============================================

def main():
    print("""
    🤖 NEXTCLOUD BOT - SIMULADOR DE NAVEGADOR
    ========================================
    
    Características:
    1. User-Agent real de Chrome
    2. Headers completos de navegador
    3. Manejo de cookies y sesiones
    4. Retrasos aleatorios como humano
    5. Múltiples métodos de upload
    
    Pasos:
    1. Usa /login en Telegram
    2. Espera conexión
    3. Envía archivos
    """)
    
    bot = TelegramNextCloudBot(TELEGRAM_BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()
