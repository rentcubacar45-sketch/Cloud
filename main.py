# main.py - VERSIÓN CON DIAGNÓSTICO
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin, quote
from typing import Tuple, Optional
import time

# ============================================
# CONFIGURACIÓN
# ============================================

NEXTCLOUD_CONFIG = {
    "base_url": "https://minube.uh.cu/",
    "username": "Claudia.btabares@estudiantes.instec.uh.cu",
    "password": "cbt260706*TM",
    "upload_base": "TelegramBot/"
}

TELEGRAM_BOT_TOKEN = "8461093571:AAG2gKIKd1hanVqsDIc5PNcpl2JAeSSCgmU"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# DIAGNÓSTICO DE CONEXIÓN NEXTCLOUD
# ============================================

def test_nextcloud_connection():
    """Prueba diferentes métodos de conexión a NextCloud"""
    base_url = NEXTCLOUD_CONFIG["base_url"]
    username = NEXTCLOUD_CONFIG["username"]
    password = NEXTCLOUD_CONFIG["password"]
    
    print("\n" + "="*50)
    print("DIAGNÓSTICO NEXTCLOUD")
    print("="*50)
    
    session = requests.Session()
    session.auth = (username, password)
    
    # Probar diferentes endpoints
    endpoints = [
        "status.php",
        "index.php",
        "apps/files/",
        "remote.php/dav/",
        "ocs/v1.php/cloud/capabilities"
    ]
    
    for endpoint in endpoints:
        url = urljoin(base_url, endpoint)
        try:
            response = session.get(url, timeout=10)
            print(f"{endpoint:30} → Status: {response.status_code} | Size: {len(response.text)} chars")
            if response.status_code == 200:
                print(f"   Contenido: {response.text[:100]}...")
        except Exception as e:
            print(f"{endpoint:30} → Error: {e}")
    
    print("\n" + "="*50)
    print("PRUEBAS DE AUTENTICACIÓN")
    print("="*50)
    
    # Probar métodos de autenticación
    methods = [
        ("Basic Auth", session),
        ("Sin Auth", requests.Session()),
        ("Con User-Agent", requests.Session()),
    ]
    
    for method_name, test_session in methods:
        if method_name == "Con User-Agent":
            test_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            test_session.auth = (username, password)
        
        url = urljoin(base_url, "status.php")
        try:
            response = test_session.get(url, timeout=10)
            print(f"{method_name:20} → Status: {response.status_code}")
        except Exception as e:
            print(f"{method_name:20} → Error: {e}")
    
    # Probar URL de login
    print("\n" + "="*50)
    print("PRUEBA DE LOGIN WEB")
    print("="*50)
    
    login_url = urljoin(base_url, "index.php/login")
    try:
        response = session.get(login_url, timeout=10)
        print(f"Login page: {response.status_code}")
        if "nextcloud" in response.text.lower():
            print("✓ Página de NextCloud detectada")
        else:
            print("✗ No parece ser NextCloud")
            print(f"Título: {response.text[:200]}...")
    except Exception as e:
        print(f"Error login: {e}")

# ============================================
# CLASE NEXTCLOUD MEJORADA
# ============================================

class NextCloudCubaClient:
    """Cliente mejorado con múltiples estrategias"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/') + '/'
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        # Estrategia 1: Headers normales
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es, en-US;q=0.7, en;q=0.3',
        })
        
        # Probar diferentes métodos de autenticación
        self._find_working_auth()
    
    def _find_working_auth(self):
        """Encuentra el método de autenticación que funcione"""
        methods = [
            self._try_basic_auth,
            self._try_session_login,
            self._try_cookie_login,
        ]
        
        for method in methods:
            if method():
                logger.info(f"✓ Autenticación exitosa con {method.__name__}")
                return True
        
        logger.error("✗ No se pudo autenticar con ningún método")
        return False
    
    def _try_basic_auth(self):
        """Intentar autenticación básica"""
        self.session.auth = (self.username, self.password)
        try:
            response = self.session.get(urljoin(self.base_url, "status.php"), timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _try_session_login(self):
        """Intentar login por sesión (simular navegador)"""
        try:
            # Primero obtener la página de login
            login_url = urljoin(self.base_url, "index.php/login")
            response = self.session.get(login_url, timeout=10)
            
            # Extraer token CSRF si existe
            import re
            csrf_match = re.search(r'name="requesttoken" value="([^"]+)"', response.text)
            csrf_token = csrf_match.group(1) if csrf_match else ""
            
            # Enviar credenciales
            login_data = {
                'user': self.username,
                'password': self.password,
                'timezone-offset': '0',
                'requesttoken': csrf_token,
            }
            
            login_response = self.session.post(login_url, data=login_data, timeout=10)
            return "location" in login_response.headers or login_response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error en login por sesión: {e}")
            return False
    
    def _try_cookie_login(self):
        """Intentar con cookies de sesión existente"""
        # Este método requiere que primero inicies sesión manualmente en navegador
        # y extraigas las cookies
        return False
    
    def upload_file(self, file_path: Path, remote_path: str = "") -> Tuple[bool, str]:
        """Subir archivo con múltiples métodos"""
        methods = [
            self._upload_webdav,
            self._upload_ocs,
            self._upload_public,
        ]
        
        for method in methods:
            logger.info(f"Intentando método: {method.__name__}")
            success, result = method(file_path, remote_path)
            if success:
                return True, result
        
        return False, "Todos los métodos de subida fallaron"
    
    def _upload_webdav(self, file_path: Path, remote_path: str = "") -> Tuple[bool, str]:
        """Método WebDAV"""
        try:
            if not file_path.exists():
                return False, "Archivo no existe"
            
            file_name = file_path.name
            webdav_url = f"{self.base_url}remote.php/dav/files/{self.username}/"
            
            if remote_path:
                webdav_url += remote_path.strip('/') + '/'
            
            webdav_url += quote(file_name)
            
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    webdav_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=30
                )
            
            if response.status_code in [201, 204]:
                return True, f"WebDAV: {file_name}"
            else:
                return False, f"WebDAV Error {response.status_code}"
                
        except Exception as e:
            return False, f"WebDAV Exception: {str(e)}"
    
    def _upload_ocs(self, file_path: Path, remote_path: str = "") -> Tuple[bool, str]:
        """Método OCS API"""
        try:
            file_name = file_path.name
            upload_url = f"{self.base_url}ocs/v2.php/apps/files/api/v1/files"
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f)}
                headers = {'OCS-APIRequest': 'true'}
                
                response = self.session.post(
                    upload_url,
                    files=files,
                    headers=headers,
                    timeout=30
                )
            
            if response.status_code == 200:
                return True, f"OCS: {file_name}"
            else:
                return False, f"OCS Error {response.status_code}"
                
        except Exception as e:
            return False, f"OCS Exception: {str(e)}"
    
    def _upload_public(self, file_path: Path, remote_path: str = "") -> Tuple[bool, str]:
        """Método para uploads públicos (si está habilitado)"""
        try:
            # Primero obtener un link de upload público
            share_url = f"{self.base_url}ocs/v2.php/apps/files_sharing/api/v1/shares"
            data = {
                'path': remote_path if remote_path else '/',
                'shareType': 3,
                'permissions': 1,
                'publicUpload': True
            }
            
            response = self.session.post(share_url, data=data, timeout=10)
            if response.status_code != 200:
                return False, "No se pudo crear upload público"
            
            # Parsear respuesta XML para obtener token
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            token_element = root.find('.{http://owncloud.org/ns}token')
            
            if token_element is None:
                return False, "No token en respuesta"
            
            token = token_element.text
            upload_url = f"{self.base_url}public.php/webdav/{token}/"
            
            # Subir archivo
            with open(file_path, 'rb') as f:
                put_response = self.session.put(
                    upload_url + file_path.name,
                    data=f,
                    timeout=30
                )
            
            if put_response.status_code in [201, 204]:
                return True, f"Público: {file_path.name}"
            else:
                return False, f"Público Error {put_response.status_code}"
                
        except Exception as e:
            return False, f"Público Exception: {str(e)}"

# ============================================
# BOT SIMPLIFICADO (Mientras resolvemos NextCloud)
# ============================================

class SimpleTelegramBot:
    """Bot simple mientras resolvemos NextCloud"""
    
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self._setup_handlers()
        logger.info("🤖 Bot simple inicializado")
    
    def _setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            self.bot.reply_to(message, "Bot en diagnóstico. Usa /test para probar NextCloud")
        
        @self.bot.message_handler(commands=['test'])
        def test_connection(message):
            self.bot.reply_to(message, "Ejecutando diagnóstico de NextCloud...")
            # Ejecutar diagnóstico
            import io
            import sys
            
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()
            
            test_nextcloud_connection()
            
            sys.stdout = old_stdout
            result = buffer.getvalue()
            
            # Enviar resultado en chunks
            for i in range(0, len(result), 4000):
                self.bot.reply_to(message, result[i:i+4000])
        
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            self.bot.reply_to(message, "⚠️ NextCloud no configurado. Usa /test para diagnóstico")

# ============================================
# MAIN
# ============================================

def main():
    print("\n" + "="*60)
    print("NEXTCLOUD TELEGRAM BOT - DIAGNÓSTICO")
    print("="*60)
    
    # Ejecutar diagnóstico primero
    test_nextcloud_connection()
    
    # Iniciar bot
    bot = SimpleTelegramBot(TELEGRAM_BOT_TOKEN)
    
    print("\n" + "="*60)
    print("INICIANDO BOT...")
    print("="*60)
    
    try:
        bot.bot.infinity_polling(timeout=30, skip_pending=True)
    except KeyboardInterrupt:
        print("\n👋 Bot detenido")

if __name__ == "__main__":
    main()
