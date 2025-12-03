# main.py - VERSIÓN DIRECTA SIN BÚSQUEDA
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin, quote
from typing import Tuple, Optional
import time
import random
import re

# ============================================
# CONFIGURACIÓN DIRECTA
# ============================================

NEXTCLOUD_URL = "https://minube.uh.cu/"  # URL FIJA
NEXTCLOUD_USER = "Claudia.btabares@estudiantes.instec.uh.cu"
NEXTCLOUD_PASS = "cbt260706*TM"
UPLOAD_FOLDER = "TelegramBot/"

TELEGRAM_BOT_TOKEN = "8557318531:AAEGDyrBiYyL06_H5y4WiMj6jzL7jMLdKq0"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# SIMULADOR DE NAVEGADOR SIMPLIFICADO
# ============================================

class NextCloudBrowser:
    """Navegador simplificado para NextCloud específico"""
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_browser()
        self.logged_in = False
    
    def _setup_browser(self):
        """Configurar como navegador real"""
        # User-Agent de Chrome Windows
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        })
    
    def get_csrf_token(self, html):
        """Extraer token CSRF del HTML"""
        patterns = [
            r'name="requesttoken"\s+value="([^"]+)"',
            r'data-requesttoken="([^"]+)"',
            r'"requesttoken":"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def login_direct(self):
        """Login directo a NextCloud"""
        try:
            logger.info(f"🔐 Intentando login en {NEXTCLOUD_URL}")
            
            # 1. Obtener página principal
            response = self.session.get(NEXTCLOUD_URL, timeout=15)
            logger.info(f"GET {NEXTCLOUD_URL} → {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code}")
                return False
            
            # 2. Verificar si ya estamos logueados
            if "logout" in response.text.lower() or "app-menu" in response.text.lower():
                self.logged_in = True
                logger.info("✓ Ya está logueado")
                return True
            
            # 3. Extraer token CSRF
            csrf_token = self.get_csrf_token(response.text)
            logger.info(f"Token CSRF: {'Sí' if csrf_token else 'No'}")
            
            # 4. Intentar login en diferentes endpoints
            login_endpoints = [
                "index.php/login",
                "login",
                "",  # La misma página
                "index.php/login?redirect_url=/apps/files",
            ]
            
            for endpoint in login_endpoints:
                login_url = urljoin(NEXTCLOUD_URL, endpoint)
                logger.info(f"Intentando login en: {login_url}")
                
                # Preparar datos
                login_data = {
                    'user': NEXTCLOUD_USER,
                    'password': NEXTCLOUD_PASS,
                    'timezone_offset': '0',
                }
                
                if csrf_token:
                    login_data['requesttoken'] = csrf_token
                
                # Hacer login
                login_response = self.session.post(
                    login_url,
                    data=login_data,
                    timeout=15,
                    allow_redirects=True
                )
                
                logger.info(f"POST {login_url} → {login_response.status_code}")
                
                # Verificar éxito
                if login_response.status_code == 200:
                    success_indicators = ['files', 'dashboard', 'welcome', 'app-navigation']
                    response_lower = login_response.text.lower()
                    
                    if any(indicator in response_lower for indicator in success_indicators):
                        self.logged_in = True
                        logger.info("✓ Login exitoso")
                        return True
                    
                    # Verificar redirección
                    if len(login_response.history) > 0:
                        self.logged_in = True
                        logger.info("✓ Login exitoso (redirección)")
                        return True
            
            logger.error("✗ Todos los intentos de login fallaron")
            return False
            
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False
    
    def upload_file_simple(self, file_path: Path) -> Tuple[bool, str]:
        """Subir archivo de forma simple y directa"""
        try:
            if not self.logged_in:
                return False, "❌ No hay sesión activa"
            
            if not file_path.exists():
                return False, "❌ Archivo no existe"
            
            file_name = file_path.name
            file_size = file_path.stat().st_size
            
            logger.info(f"Subiendo {file_name} ({file_size} bytes)")
            
            # MÉTODO 1: Upload directo al endpoint de files
            upload_url = urljoin(NEXTCLOUD_URL, "index.php/apps/files/ajax/upload.php")
            
            # Parámetros
            params = {'dir': f'/{UPLOAD_FOLDER.strip("/")}'} if UPLOAD_FOLDER else {}
            
            with open(file_path, 'rb') as f:
                files = {'files[]': (file_name, f)}
                response = self.session.post(
                    upload_url,
                    files=files,
                    params=params,
                    timeout=60
                )
            
            logger.info(f"Upload → {response.status_code}")
            
            # Verificar respuesta
            if response.status_code == 200:
                try:
                    # Intentar parsear JSON
                    import json
                    result = response.json()
                    if result.get('status') == 'success':
                        return True, f"✅ {file_name} subido"
                    else:
                        error_msg = result.get('data', {}).get('message', 'Error desconocido')
                        return False, f"❌ {error_msg}"
                except:
                    # Si no es JSON, verificar texto
                    if 'success' in response.text.lower():
                        return True, f"✅ {file_name} subido"
                    else:
                        return False, f"❌ Error en respuesta: {response.text[:100]}"
            else:
                return False, f"❌ Error HTTP {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error en upload: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def test_connection(self):
        """Probar conexión simple"""
        try:
            # Intentar acceder a status.php
            status_url = urljoin(NEXTCLOUD_URL, "status.php")
            response = self.session.get(status_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✓ status.php accesible")
                return True
            else:
                logger.info(f"status.php → {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error test: {e}")
            return False

# ============================================
# BOT DE TELEGRAM SIMPLIFICADO
# ============================================

class SimpleNextCloudBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.nc = NextCloudBrowser()
        self._setup_handlers()
        logger.info("🤖 Bot simplificado listo")
    
    def _setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            help_text = """📁 <b>NextCloud Upload Bot</b>

<b>URL:</b> https://minube.uh.cu/
<b>Usuario:</b> Claudia.btabares@estudiantes.instec.uh.cu

<b>Comandos:</b>
/login - Conectar a NextCloud
/status - Ver estado
/test - Probar subida

<b>Envía cualquier archivo</b> para subirlo."""
            
            self.bot.reply_to(message, help_text, parse_mode='HTML')
        
        @self.bot.message_handler(commands=['login'])
        def login_cmd(message):
            msg = self.bot.reply_to(message, "🔐 Conectando a NextCloud...")
            
            if self.nc.login_direct():
                self.bot.edit_message_text(
                    "✅ Conectado a NextCloud\n📁 Carpeta: TelegramBot/",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
            else:
                self.bot.edit_message_text(
                    "❌ Error de conexión\nVerifica usuario/contraseña",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
        
        @self.bot.message_handler(commands=['status'])
        def status_cmd(message):
            if self.nc.logged_in:
                self.bot.reply_to(message, "✅ Conectado a NextCloud")
            else:
                self.bot.reply_to(message, "❌ No conectado. Usa /login")
        
        @self.bot.message_handler(commands=['test'])
        def test_cmd(message):
            self.bot.reply_to(message, "🧪 Probando conexión...")
            
            # Probar conexión
            if self.nc.test_connection():
                self.bot.reply_to(message, "✅ NextCloud accesible")
            else:
                self.bot.reply_to(message, "❌ No se puede acceder a NextCloud")
            
            # Probar subida si está logueado
            if self.nc.logged_in:
                self.bot.reply_to(message, "📤 Probando subida...")
                
                # Crear archivo de prueba
                import datetime
                test_file = Path("test_nextcloud.txt")
                test_content = f"Prueba de subida\nFecha: {datetime.datetime.now()}\nBot: Telegram NextCloud Uploader"
                test_file.write_text(test_content, encoding='utf-8')
                
                success, result = self.nc.upload_file_simple(test_file)
                test_file.unlink()
                
                self.bot.reply_to(message, result)
        
        @self.bot.message_handler(content_types=['document', 'photo'])
        def handle_file(message):
            try:
                # Obtener archivo
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_name = message.document.file_name or "archivo.bin"
                elif message.photo:
                    file_info = self.bot.get_file(message.photo[-1].file_id)
                    file_name = f"foto_{message.message_id}.jpg"
                else:
                    self.bot.reply_to(message, "❌ Tipo no soportado")
                    return
                
                # Verificar login
                if not self.nc.logged_in:
                    self.bot.reply_to(message, "❌ Usa /login primero")
                    return
                
                # Descargar
                self.bot.reply_to(message, f"📥 Descargando {file_name}...")
                file_data = self.bot.download_file(file_info.file_path)
                
                # Guardar temporal
                temp_file = Path(f"temp_{file_name}")
                temp_file.write_bytes(file_data)
                
                # Subir
                self.bot.reply_to(message, f"📤 Subiendo a NextCloud...")
                success, result = self.nc.upload_file_simple(temp_file)
                
                # Limpiar
                temp_file.unlink(missing_ok=True)
                
                # Responder
                self.bot.reply_to(message, result)
                
            except Exception as e:
                logger.error(f"Error: {e}")
                self.bot.reply_to(message, f"❌ Error: {str(e)[:100]}")
        
        @self.bot.message_handler(func=lambda message: True)
        def default_response(message):
            self.bot.reply_to(message, "📁 Envía un archivo o usa /help")
    
    def run(self):
        """Ejecutar bot"""
        logger.info("🚀 Iniciando bot NextCloud...")
        self.bot.remove_webhook()
        time.sleep(1)
        self.bot.infinity_polling(timeout=30, skip_pending=True)

# ============================================
# MAIN
# ============================================

def main():
    print("""
    📁 NEXTCLOUD UPLOAD BOT
    =======================
    
    Configuración:
    • URL: https://minube.uh.cu/
    • Usuario: Claudia.btabares@estudiantes.instec.uh.cu
    • Carpeta: TelegramBot/
    
    Instrucciones:
    1. En Telegram, usa /login
    2. Espera confirmación
    3. Envía archivos
    """)
    
    bot = SimpleNextCloudBot(TELEGRAM_BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()
