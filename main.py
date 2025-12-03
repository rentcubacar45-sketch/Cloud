# main.py - VERSIÓN SIN FAKE-USERAGENT
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin, quote, urlparse
from typing import Tuple, Optional
import time
import random
import re

# ============================================
# CONFIGURACIÓN
# ============================================

NEXTCLOUD_CONFIG = {
    "base_url": "https://minube.uh.cu/",
    "username": "Claudia.btabares@estudiantes.instec.uh.cu",
    "password": "cbt260706*TM",
    "upload_base": "TelegramBot/"
}

TELEGRAM_BOT_TOKEN = "8557318531:AAEGDyrBiYyL06_H5y4WiMj6jzL7jMLdKq0"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# SIMULADOR DE NAVEGADOR SIN FAKE-USERAGENT
# ============================================

class RealBrowserSimulator:
    """Simula un navegador Chrome real sin dependencias externas"""
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers()
        self.logged_in = False
        
    def _get_random_user_agent(self):
        """Genera User-Agent aleatorio sin fake-useragent"""
        chrome_versions = [
            "120.0.6099.217", "121.0.6167.86", "122.0.6261.112",
            "123.0.6312.59", "124.0.6367.91", "125.0.6422.78"
        ]
        
        os_agents = [
            "(Windows NT 10.0; Win64; x64)",
            "(Windows NT 11.0; Win64; x64)",
            "(X11; Linux x86_64)",
            "(Macintosh; Intel Mac OS X 10_15_7)"
        ]
        
        chrome_ver = random.choice(chrome_versions)
        os_agent = random.choice(os_agents)
        
        return f"Mozilla/5.0 {os_agent} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
    
    def _setup_headers(self):
        """Configurar headers exactos de Chrome"""
        
        self.session.headers = {
            # Headers principales
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            
            # Headers de conexión
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            
            # Headers de seguridad
            'Sec-Ch-Ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
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
        
    def _add_referer(self, url):
        """Añade Referer header"""
        self.session.headers['Referer'] = url
    
    def _add_origin(self, url):
        """Añade Origin header"""
        parsed = urlparse(url)
        self.session.headers['Origin'] = f"{parsed.scheme}://{parsed.netloc}"
    
    def _random_delay(self):
        """Retraso aleatorio como humano"""
        time.sleep(random.uniform(0.3, 1.5))
    
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
                
                if response.status_code == 200:
                    # Buscar indicadores de NextCloud
                    html_lower = response.text.lower()
                    indicators = ['nextcloud', 'owncloud', 'log in', 'password', 'username', 'requesttoken']
                    
                    if any(indicator in html_lower for indicator in indicators):
                        logger.info(f"✓ Posible NextCloud en: {url}")
                        return url
                    
                    # También considerar si hay formulario de login
                    if '<form' in html_lower and ('password' in html_lower or 'user' in html_lower):
                        logger.info(f"✓ Formulario de login en: {url}")
                        return url
                    
            except Exception as e:
                logger.error(f"Error probando {url}: {e}")
        
        return None
    
    def extract_csrf_token(self, html):
        """Extrae token CSRF del HTML"""
        patterns = [
            r'name="requesttoken"\s+value="([^"]+)"',
            r'name="csrf_token"\s+value="([^"]+)"',
            r'name="token"\s+value="([^"]+)"',
            r'data-requesttoken="([^"]+)"',
            r'"requesttoken":"([^"]+)"',
            r'<input[^>]*requesttoken[^>]*value="([^"]+)"',
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
            
            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code} al obtener página")
                return False
            
            # 2. URL final después de redirecciones
            final_url = response.url
            logger.info(f"URL final: {final_url}")
            
            # 3. Extraer token CSRF
            csrf_token = self.extract_csrf_token(response.text)
            logger.info(f"Token CSRF: {'Sí' if csrf_token else 'No'}")
            
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
                urljoin(final_url, "index.php/login?clear=1"),
                final_url,  # Intentar en la misma página
            ]
            
            # 6. Intentar login
            for login_url in login_urls:
                try:
                    self._add_referer(final_url)
                    self._add_origin(final_url)
                    
                    # Cambiar headers para POST
                    post_headers = self.session.headers.copy()
                    post_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                    
                    self._random_delay()
                    login_response = self.session.post(
                        login_url,
                        data=login_data,
                        headers=post_headers,
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    logger.info(f"Login {login_url} → {login_response.status_code}")
                    
                    # Verificar login exitoso
                    if login_response.status_code == 200:
                        # Buscar indicadores de éxito
                        success_indicators = [
                            'dashboard', 'files', 'app-menu', 'app-navigation',
                            'logout', 'nextcloud', 'welcome'
                        ]
                        
                        response_lower = login_response.text.lower()
                        if any(indicator in response_lower for indicator in success_indicators):
                            self.logged_in = True
                            logger.info("✓ Login exitoso")
                            return True
                        
                        # Verificar por redirección o cookies
                        if len(login_response.history) > 0:
                            self.logged_in = True
                            logger.info("✓ Login exitoso (redirección)")
                            return True
                        
                        # Verificar cookies de sesión
                        if 'Set-Cookie' in login_response.headers:
                            cookies = login_response.headers['Set-Cookie']
                            if any(x in cookies for x in ['nc_session', 'oc_session', 'nextcloud']):
                                self.logged_in = True
                                logger.info("✓ Login exitoso (cookies)")
                                return True
                    
                except Exception as e:
                    logger.error(f"Error en login {login_url}: {e}")
            
            logger.error("✗ Todos los intentos de login fallaron")
            return False
            
        except Exception as e:
            logger.error(f"Error en proceso de login: {e}")
            return False
    
    def upload_file(self, file_path: Path, remote_folder: str = "") -> Tuple[bool, str]:
        """Subir archivo simulando navegador"""
        if not self.logged_in:
            return False, "❌ No hay sesión activa. Usa /login primero"
        
        try:
            if not file_path.exists():
                return False, "❌ Archivo no existe"
            
            file_name = file_path.name
            file_size = file_path.stat().st_size
            
            logger.info(f"📤 Subiendo {file_name} ({file_size} bytes)")
            
            # Intentar diferentes métodos de upload
            methods = [
                self._upload_direct,
                self._upload_webdav,
                self._upload_form,
            ]
            
            for method in methods:
                logger.info(f"Probando método: {method.__name__}")
                success, result = method(file_path, remote_folder)
                if success:
                    return True, f"✅ {result}"
                
                self._random_delay()
            
            return False, "❌ Todos los métodos fallaron"
            
        except Exception as e:
            logger.error(f"Error en upload: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def _upload_direct(self, file_path: Path, remote_folder: str) -> Tuple[bool, str]:
        """Método directo a files API"""
        try:
            file_name = file_path.name
            
            # URL para subida directa
            upload_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "index.php/apps/files/ajax/upload.php")
            
            # Añadir directorio si se especifica
            params = {}
            if remote_folder:
                params['dir'] = f'/{remote_folder.strip("/")}'
            
            with open(file_path, 'rb') as f:
                files = {'files[]': (file_name, f)}
                response = self.session.post(
                    upload_url,
                    files=files,
                    params=params,
                    timeout=60
                )
            
            logger.info(f"Direct upload → {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('status') == 'success':
                        return True, f"Subido: {file_name}"
                except:
                    if 'success' in response.text.lower():
                        return True, f"Subido: {file_name}"
            
            return False, f"Direct Error {response.status_code}"
            
        except Exception as e:
            return False, f"Direct: {str(e)}"
    
    def _upload_webdav(self, file_path: Path, remote_folder: str) -> Tuple[bool, str]:
        """Método WebDAV"""
        try:
            file_name = file_path.name
            
            # Construir ruta remota
            remote_path = ""
            if remote_folder:
                remote_path = f"{remote_folder.strip('/')}/"
            
            webdav_url = urljoin(
                NEXTCLOUD_CONFIG["base_url"], 
                f"remote.php/dav/files/{NEXTCLOUD_CONFIG['username']}/{remote_path}{quote(file_name)}"
            )
            
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    webdav_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=60
                )
            
            logger.info(f"WebDAV upload → {response.status_code}")
            
            if response.status_code in [201, 204]:
                return True, f"WebDAV: {file_name}"
            else:
                return False, f"WebDAV Error {response.status_code}"
                
        except Exception as e:
            return False, f"WebDAV: {str(e)}"
    
    def _upload_form(self, file_path: Path, remote_folder: str) -> Tuple[bool, str]:
        """Método formulario tradicional"""
        try:
            file_name = file_path.name
            
            # Obtener página de files para tener token
            files_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "apps/files/")
            self._random_delay()
            files_response = self.session.get(files_url, timeout=15)
            
            # Extraer token
            csrf_token = self.extract_csrf_token(files_response.text)
            
            # URL de upload
            upload_url = urljoin(NEXTCLOUD_CONFIG["base_url"], "index.php/core/ajax/upload.php")
            
            # Preparar datos
            data = {
                'requesttoken': csrf_token if csrf_token else '',
            }
            
            if remote_folder:
                data['dir'] = f'/{remote_folder.strip("/")}'
            
            with open(file_path, 'rb') as f:
                files = {'files[]': (file_name, f)}
                response = self.session.post(
                    upload_url,
                    data=data,
                    files=files,
                    timeout=60
                )
            
            logger.info(f"Form upload → {response.status_code}")
            
            if response.status_code == 200:
                return True, f"Form: {file_name}"
            else:
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
        logger.info("🤖 Bot inicializado")
    
    def _setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome = """🤖 <b>NextCloud Bot - Navegador Simulado</b>

<b>Comandos:</b>
/login - Conectar a NextCloud
/status - Ver estado
/test - Probar subida

<b>Envía cualquier archivo</b> para subirlo a NextCloud"""
            
            try:
                self.bot.reply_to(message, welcome, parse_mode='HTML')
            except:
                self.bot.reply_to(message, "🤖 Bot NextCloud. Usa /login primero")
        
        @self.bot.message_handler(commands=['login'])
        def login_command(message):
            msg = self.bot.reply_to(message, "🔍 Buscando NextCloud...")
            
            # Descubrir URL
            url = self.browser.discover_nextcloud_url()
            if not url:
                self.bot.edit_message_text("❌ No se encontró NextCloud", 
                                         chat_id=message.chat.id, 
                                         message_id=msg.message_id)
                return
            
            self.bot.edit_message_text(f"📍 URL: {url}\n🔐 Conectando...", 
                                     chat_id=message.chat.id, 
                                     message_id=msg.message_id)
            
            # Login
            success = self.browser.login(
                url,
                NEXTCLOUD_CONFIG["username"],
                NEXTCLOUD_CONFIG["password"]
            )
            
            if success:
                self.bot.edit_message_text("✅ Conectado a NextCloud", 
                                         chat_id=message.chat.id, 
                                         message_id=msg.message_id)
            else:
                self.bot.edit_message_text("❌ Error en login. Verifica credenciales.", 
                                         chat_id=message.chat.id, 
                                         message_id=msg.message_id)
        
        @self.bot.message_handler(commands=['status'])
        def status_command(message):
            if self.browser.logged_in:
                self.bot.reply_to(message, "✅ Sesión activa")
            else:
                self.bot.reply_to(message, "❌ No hay sesión. Usa /login")
        
        @self.bot.message_handler(commands=['test'])
        def test_command(message):
            self.bot.reply_to(message, "🧪 Creando archivo de prueba...")
            
            # Crear archivo de prueba
            test_file = Path("test_bot.txt")
            test_file.write_text(f"Prueba del bot - {time.ctime()}\nUsuario: {NEXTCLOUD_CONFIG['username']}")
            
            self.bot.reply_to(message, "📤 Subiendo prueba...")
            
            success, result = self.browser.upload_file(
                test_file,
                NEXTCLOUD_CONFIG["upload_base"]
            )
            
            # Limpiar
            test_file.unlink(missing_ok=True)
            
            if success:
                self.bot.reply_to(message, f"✅ {result}")
            else:
                self.bot.reply_to(message, f"❌ {result}")
        
        @self.bot.message_handler(content_types=['document', 'photo'])
        def handle_file(message):
            try:
                # Obtener información del archivo
                file_info = None
                file_name = ""
                
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_name = message.document.file_name or f"document_{message.message_id}.bin"
                elif message.photo:
                    file_info = self.bot.get_file(message.photo[-1].file_id)
                    file_name = f"photo_{message.message_id}.jpg"
                else:
                    self.bot.reply_to(message, "❌ Tipo no soportado")
                    return
                
                # Descargar
                self.bot.reply_to(message, f"📥 Descargando {file_name}...")
                downloaded = self.bot.download_file(file_info.file_path)
                
                # Guardar temporal
                temp_file = Path(f"temp_{file_name}")
                temp_file.write_bytes(downloaded)
                
                # Subir
                self.bot.reply_to(message, f"📤 Subiendo a NextCloud...")
                
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
                logger.error(f"Error manejando archivo: {e}")
                self.bot.reply_to(message, f"❌ Error: {str(e)[:100]}")
        
        @self.bot.message_handler(func=lambda message: True)
        def default_handler(message):
            self.bot.reply_to(message, "📁 Envía un archivo o usa /login")
    
    def run(self):
        """Iniciar bot"""
        logger.info("🚀 Iniciando bot...")
        self.bot.remove_webhook()
        time.sleep(1)
        self.bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    print("""
    🤖 NEXTCLOUD BOT - SIMULADOR DE NAVEGADOR
    ========================================
    
    Características:
    • User-Agent real de Chrome
    • Headers completos de navegador
    • Retrasos aleatorios como humano
    • 3 métodos diferentes de upload
    
    Instrucciones en Telegram:
    1. /login - Conectar a NextCloud
    2. /status - Verificar conexión
    3. Envía archivos - Se suben automáticamente
    """)
    
    try:
        bot = TelegramNextCloudBot(TELEGRAM_BOT_TOKEN)
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido")
    except Exception as e:
        logger.error(f"💥 Error fatal: {e}")
        raise

# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    main()
