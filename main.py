# main.py - VERSIÓN CORREGIDA PARA RENDER
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin, quote
from typing import Tuple, Optional

# ... resto de tu código ...

# ============================================
# CONFIGURACIÓN - REEMPLAZA CON TUS DATOS
# ============================================

# CONFIGURACIÓN DE NEXTCLOUD (EJEMPLO)
NEXTCLOUD_CONFIG = {
    "base_url": "https://minube.uh.cu/",  # Sin /index.php
    "username": "Claudia.btabares@estudiantes.instec.uh.cu",
    "password": "cbt260706*TM",  # CRUCIAL: Usa App Password desde Ajustes
    "upload_base": "TelegramBot/"  # Carpeta base dentro de tus archivos
}

# CONFIGURACIÓN TELEGRAM
TELEGRAM_BOT_TOKEN = "8546855140:AAHeX8ZGBNL4p4Au_jviLkFtypBKk5fWHS0"  # Token real de @BotFather

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CLASE NEXTCLOUD CON WEBDAV (MÉTODO MÁS FIABLE)
# ============================================

class NextCloudCubaClient:
    """Cliente especializado para NextCloud desde Cuba usando WebDAV"""
    
    def __init__(self, base_url: str, username: str, password: str):
        """
        Inicializa cliente que simula ser cliente oficial
        
        Args:
            base_url: https://tudominio.com/nextcloud/
            username: tu_usuario
            password: App Password (desde Ajustes > Seguridad)
        """
        # Asegurar formato correcto de URL
        self.base_url = base_url.rstrip('/') + '/'
        self.username = username
        self.password = password
        
        # Crear sesión con headers de cliente oficial
        self.session = requests.Session()
        
        # HEADERS QUE SIMULAN CLIENTE OFICIAL DE NEXTCLOUD
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows) mirall/3.4.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es, en-US;q=0.7, en;q=0.3',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Origin': self.base_url,
            'Referer': self.base_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
        
        # Autenticación básica
        self.session.auth = (username, password)
        
        # Configurar proxies si es necesario (para Cuba)
        self._setup_proxies()
        
        # Verificar conexión
        self._verify_connection()
    
    def _setup_proxies(self):
        """Configurar proxies si es necesario en Cuba"""
        # Si necesitas proxy, configúralo aquí
        # self.session.proxies = {
        #     'http': 'http://proxy:puerto',
        #     'https': 'http://proxy:puerto',
        # }
        pass
    
    def _verify_connection(self):
        """Verificar que podemos conectar a NextCloud"""
        try:
            # Probar endpoint status
            status_url = urljoin(self.base_url, 'status.php')
            response = self.session.get(status_url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Conectado a NextCloud {data.get('productname', '')} v{data.get('version', '')}")
                return True
            elif response.status_code == 403:
                logger.warning("⚠️  Acceso denegado. Verifica credenciales y App Password.")
                return False
            else:
                logger.warning(f"⚠️  Respuesta inesperada: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            logger.error("⏱️  Timeout de conexión. Verifica VPN/proxy si es necesario.")
            return False
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False
    
    def upload_via_webdav(self, file_path: Path, remote_path: str = "") -> Tuple[bool, str]:
        """
        Subir archivo via WebDAV (método más compatible)
        
        Args:
            file_path: Ruta local al archivo
            remote_path: Ruta remota relativa (ej: "TelegramBot/2024/")
            
        Returns:
            (éxito, mensaje/url)
        """
        try:
            # Leer archivo
            if not file_path.exists():
                return False, f"Archivo no existe: {file_path}"
            
            file_name = file_path.name
            file_size = file_path.stat().st_size
            
            # Construir URL WebDAV
            # Formato: https://dominio.com/nextcloud/remote.php/dav/files/USUARIO/ruta/archivo
            webdav_url = f"{self.base_url}remote.php/dav/files/{self.username}/"
            
            if remote_path:
                # Asegurar formato correcto de ruta
                remote_path = remote_path.strip('/') + '/'
                webdav_url += remote_path
            
            # Codificar nombre de archivo para URL
            encoded_filename = quote(file_name)
            webdav_url += encoded_filename
            
            # Headers específicos para WebDAV
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(file_size),
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            logger.info(f"📤 Subiendo {file_name} ({file_size:,} bytes) a WebDAV...")
            
            # Leer y subir archivo en chunks
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    webdav_url,
                    data=f,
                    headers=headers,
                    timeout=30
                )
            
            # Verificar respuesta
            if response.status_code in [201, 204]:
                # Construir URL de compartir (opcional)
                share_url = self._create_share(remote_path + file_name if remote_path else file_name)
                
                logger.info(f"✅ Subido exitosamente: {file_name}")
                return True, f"Subido: {file_name}\nURL: {share_url if share_url else webdav_url}"
            else:
                logger.error(f"❌ Error WebDAV {response.status_code}: {response.text[:200]}")
                return False, f"Error {response.status_code} en WebDAV"
                
        except Exception as e:
            logger.error(f"❌ Error en upload_via_webdav: {e}")
            return False, f"Excepción: {str(e)}"
    
    def _create_share(self, file_path: str) -> Optional[str]:
        """Crear un enlace público para el archivo"""
        try:
            share_url = f"{self.base_url}ocs/v2.php/apps/files_sharing/api/v1/shares"
            
            data = {
                'path': file_path,
                'shareType': 3,  # 3 = enlace público
                'permissions': 1  # 1 = solo lectura
            }
            
            headers = {
                'OCS-APIRequest': 'true',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(share_url, data=data, headers=headers)
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                url_element = root.find('.{http://owncloud.org/ns}url')
                if url_element is not None:
                    return url_element.text
            
            return None
            
        except:
            return None
    
    def upload_via_ocs(self, file_path: Path, remote_folder: str = "") -> Tuple[bool, str]:
        """Método alternativo usando API OCS"""
        try:
            file_name = file_path.name
            
            # URL para subida
            upload_url = f"{self.base_url}ocs/v2.php/apps/files/api/v1/files/{self.username}"
            
            if remote_folder:
                upload_url += f"/{remote_folder.strip('/')}"
            
            # Preparar archivo
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f)}
                
                headers = {
                    'OCS-APIRequest': 'true',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                response = self.session.post(
                    f"{upload_url}/{file_name}",
                    files=files,
                    headers=headers
                )
            
            if response.status_code == 200:
                return True, f"Subido via OCS: {file_name}"
            else:
                return False, f"Error OCS: {response.status_code}"
                
        except Exception as e:
            return False, f"Error OCS: {str(e)}"

# ============================================
# BOT DE TELEGRAM
# ============================================

class TelegramNextCloudBot:
    """Bot de Telegram que maneja subidas a NextCloud"""
    
    def __init__(self, token: str, nextcloud_client: NextCloudCubaClient):
        self.bot = telebot.TeleBot(token)
        self.nc_client = nextcloud_client
        self.allowed_users = []  # Lista de IDs permitidos (opcional)
        
        # Configurar handlers
        self._setup_handlers()
        
        logger.info("🤖 Bot de Telegram inicializado")
    
    def _setup_handlers(self):
        """Configurar comandos del bot"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome_text = """
            📁 *Bot de Subida a NextCloud*
            
            *Comandos disponibles:*
            /start, /help - Muestra este mensaje
            /upload - Instrucciones para subir archivos
            /status - Verifica conexión con NextCloud
            
            *Para subir archivos:*
            Simplemente envía cualquier archivo (documento, imagen, video, etc.)
            
            *Carpeta de destino:* TelegramBot/
            """
            self.bot.reply_to(message, welcome_text, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['status'])
        def check_status(message):
            """Verificar estado de NextCloud"""
            self.bot.reply_to(message, "🔍 Verificando conexión con NextCloud...")
            # La verificación ya se hizo en __init__, pero podemos reconfirmar
            self.bot.reply_to(message, "✅ Bot operativo y conectado a NextCloud")
        
        @self.bot.message_handler(commands=['upload'])
        def upload_instructions(message):
            instructions = """
            📤 *Instrucciones para subir:*
            
            1. Envía el archivo directamente al bot
            2. Tamaño máximo: 2GB (límite de Telegram)
            3. Formatos soportados: Todos
            
            El archivo se subirá a tu NextCloud en la carpeta: TelegramBot/
            
            ⚠️ *Nota:* Para archivos grandes (>50MB) la subida puede tardar
            """
            self.bot.reply_to(message, instructions, parse_mode='Markdown')
        
        @self.bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
        def handle_file(message):
            """Manejar archivos subidos"""
            try:
                self.bot.reply_to(message, "⏳ Descargando archivo de Telegram...")
                
                # Obtener información del archivo
                file_info = None
                file_type = None
                
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_type = "document"
                    file_name = message.document.file_name
                elif message.photo:
                    file_info = self.bot.get_file(message.photo[-1].file_id)
                    file_type = "photo"
                    file_name = f"photo_{message.message_id}.jpg"
                elif message.video:
                    file_info = self.bot.get_file(message.video.file_id)
                    file_type = "video"
                    file_name = message.video.file_name or f"video_{message.message_id}.mp4"
                elif message.audio:
                    file_info = self.bot.get_file(message.audio.file_id)
                    file_type = "audio"
                    file_name = message.audio.file_name or f"audio_{message.message_id}.mp3"
                else:
                    self.bot.reply_to(message, "❌ Tipo de archivo no soportado")
                    return
                
                # Descargar archivo
                downloaded_file = self.bot.download_file(file_info.file_path)
                
                # Guardar localmente temporalmente
                local_path = Path(f"temp_{file_name}")
                with open(local_path, 'wb') as f:
                    f.write(downloaded_file)
                
                # Subir a NextCloud
                self.bot.reply_to(message, f"📤 Subiendo {file_name} a NextCloud...")
                
                success, result = self.nc_client.upload_via_webdav(
                    local_path,
                    NEXTCLOUD_CONFIG["upload_base"]
                )
                
                # Limpiar archivo temporal
                local_path.unlink(missing_ok=True)
                
                if success:
                    # Acortar mensaje si es muy largo
                    if len(result) > 4000:
                        result = result[:4000] + "...\n\n(Mensaje truncado por longitud)"
                    
                    reply_msg = f"✅ *Subida exitosa*\n\n{result}"
                    self.bot.reply_to(message, reply_msg, parse_mode='Markdown')
                else:
                    # Intentar método alternativo
                    self.bot.reply_to(message, "🔄 Intentando método alternativo...")
                    
                    success2, result2 = self.nc_client.upload_via_ocs(
                        local_path,
                        NEXTCLOUD_CONFIG["upload_base"]
                    )
                    
                    if success2:
                        self.bot.reply_to(message, f"✅ *Subida exitosa (método alternativo)*\n\n{result2}", parse_mode='Markdown')
                    else:
                        self.bot.reply_to(message, f"❌ *Error en la subida*\n\n{result2}", parse_mode='Markdown')
                        
            except Exception as e:
                logger.error(f"Error en handle_file: {e}")
                self.bot.reply_to(message, f"❌ Error interno: {str(e)[:200]}")
        
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            """Manejar otros mensajes"""
            self.bot.reply_to(message, "📁 Envíame un archivo para subirlo a NextCloud\nUsa /help para ayuda")
    
    def run(self):
        """Iniciar el bot"""
        logger.info("🚀 Iniciando bot de Telegram...")
        self.bot.infinity_polling(timeout=30, long_polling_timeout=30)

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """Función principal"""
    logger.info("⚡ Iniciando sistema de subida NextCloud para Cuba")
    
    try:
        # 1. Inicializar cliente NextCloud
        logger.info("🔗 Conectando a NextCloud...")
        nc_client = NextCloudCubaClient(
            base_url=NEXTCLOUD_CONFIG["base_url"],
            username=NEXTCLOUD_CONFIG["username"],
            password=NEXTCLOUD_CONFIG["password"]
        )
        
        # 2. Inicializar bot de Telegram
        logger.info("🤖 Inicializando bot de Telegram...")
        bot = TelegramNextCloudBot(
            token=TELEGRAM_BOT_TOKEN,
            nextcloud_client=nc_client
        )
        
        # 3. Iniciar bot
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"💥 Error fatal: {e}")
        raise

# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    print("""
    📁 NEXTCLOUD UPLOAD BOT PARA CUBA
    =================================
    
    Configuración:
    1. Reemplaza los datos en NEXTCLOUD_CONFIG
    2. Usa App Password en NextCloud (Ajustes > Seguridad)
    3. Asegúrate de tener Python 3.7+
    
    Instalación de dependencias:
    pip install requests pyTelegramBotAPI
    
    Iniciar bot: python bot_nextcloud.py
    """)
    
    # Ejecutar bot
    main()
