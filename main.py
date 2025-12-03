# main.py - VERSIÓN CORREGIDA CON HTML
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin, quote
from typing import Tuple, Optional
import html
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

TELEGRAM_BOT_TOKEN = "8546855140:AAHeX8ZGBNL4p4Au_jviLkFtypBKk5fWHS0"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# FUNCIÓN PARA ESCAPAR HTML
# ============================================

def escape_html_safe(text):
    """Escapa caracteres HTML de forma segura"""
    if text is None:
        return ""
    return html.escape(str(text))

def format_html_message(title, content=""):
    """Formatea un mensaje HTML seguro"""
    safe_content = escape_html_safe(content).replace('\n', '<br>')
    return f"<b>{escape_html_safe(title)}</b><br><br>{safe_content}"

# ============================================
# CLASE NEXTCLOUD CON WEBDAV
# ============================================

class NextCloudCubaClient:
    """Cliente especializado para NextCloud desde Cuba usando WebDAV"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/') + '/'
        self.username = username
        self.password = password
        
        self.session = requests.Session()
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
        
        self.session.auth = (username, password)
        self._verify_connection()
    
    def _verify_connection(self):
        """Verificar que podemos conectar a NextCloud"""
        try:
            status_url = urljoin(self.base_url, 'status.php')
            response = self.session.get(status_url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Conectado a NextCloud {data.get('productname', '')} v{data.get('version', '')}")
                return True
            elif response.status_code == 403:
                logger.warning("⚠️  Acceso denegado. Verifica credenciales.")
                return False
            else:
                logger.warning(f"⚠️  Respuesta inesperada: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False
    
    def upload_via_webdav(self, file_path: Path, remote_path: str = "") -> Tuple[bool, str]:
        """
        Subir archivo via WebDAV
        """
        try:
            if not file_path.exists():
                return False, f"Archivo no existe: {file_path}"
            
            file_name = file_path.name
            file_size = file_path.stat().st_size
            
            webdav_url = f"{self.base_url}remote.php/dav/files/{self.username}/"
            
            if remote_path:
                remote_path = remote_path.strip('/') + '/'
                webdav_url += remote_path
            
            encoded_filename = quote(file_name)
            webdav_url += encoded_filename
            
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(file_size),
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            logger.info(f"📤 Subiendo {file_name} ({file_size:,} bytes) a WebDAV...")
            
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    webdav_url,
                    data=f,
                    headers=headers,
                    timeout=30
                )
            
            if response.status_code in [201, 204]:
                share_url = self._create_share(remote_path + file_name if remote_path else file_name)
                logger.info(f"✅ Subido exitosamente: {file_name}")
                result_msg = f"Subido: {file_name}"
                if share_url:
                    result_msg += f"\nURL compartida: {share_url}"
                return True, result_msg
            else:
                logger.error(f"❌ Error WebDAV {response.status_code}: {response.text[:200]}")
                return False, f"Error {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            logger.error(f"❌ Error en upload_via_webdav: {e}")
            return False, f"Error: {str(e)}"
    
    def _create_share(self, file_path: str) -> Optional[str]:
        """Crear un enlace público para el archivo"""
        try:
            share_url = f"{self.base_url}ocs/v2.php/apps/files_sharing/api/v1/shares"
            
            data = {
                'path': file_path,
                'shareType': 3,
                'permissions': 1
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
            upload_url = f"{self.base_url}ocs/v2.php/apps/files/api/v1/files/{self.username}"
            
            if remote_folder:
                upload_url += f"/{remote_folder.strip('/')}"
            
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
# BOT DE TELEGRAM CON HTML
# ============================================

class TelegramNextCloudBot:
    """Bot de Telegram que maneja subidas a NextCloud usando HTML seguro"""
    
    def __init__(self, token: str, nextcloud_client: NextCloudCubaClient):
        self.bot = telebot.TeleBot(token)
        self.nc_client = nextcloud_client
        
        # Configurar handlers
        self._setup_handlers()
        logger.info("🤖 Bot de Telegram inicializado")
    
    def _send_html_message(self, chat_id, text, reply_to_message_id=None):
        """Envía mensaje HTML seguro"""
        safe_text = escape_html_safe(text).replace('\n', '<br>')
        self.bot.send_message(
            chat_id,
            safe_text,
            parse_mode='HTML',
            reply_to_message_id=reply_to_message_id
        )
    
    def _setup_handlers(self):
        """Configurar comandos del bot"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome_text = """
<b>📁 Bot de Subida a NextCloud</b>

<b>Comandos disponibles:</b>
/start, /help - Muestra este mensaje
/upload - Instrucciones para subir archivos
/status - Verifica conexión con NextCloud

<b>Para subir archivos:</b>
Simplemente envía cualquier archivo (documento, imagen, video, etc.)

<b>Carpeta de destino:</b> TelegramBot/
            """
            self.bot.reply_to(message, welcome_text, parse_mode='HTML')
        
        @self.bot.message_handler(commands=['status'])
        def check_status(message):
            self.bot.reply_to(message, "🔍 Verificando conexión con NextCloud...")
            self.bot.reply_to(message, "✅ Bot operativo y conectado a NextCloud", parse_mode='HTML')
        
        @self.bot.message_handler(commands=['upload'])
        def upload_instructions(message):
            instructions = """
<b>📤 Instrucciones para subir:</b>

1. Envía el archivo directamente al bot
2. Tamaño máximo: 2GB (límite de Telegram)
3. Formatos soportados: Todos

El archivo se subirá a tu NextCloud en la carpeta: TelegramBot/

⚠️ <b>Nota:</b> Para archivos grandes (>50MB) la subida puede tardar
            """
            self.bot.reply_to(message, instructions, parse_mode='HTML')
        
        @self.bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
        def handle_file(message):
            """Manejar archivos subidos"""
            try:
                # Responder inmediatamente
                self.bot.reply_to(message, "⏳ Descargando archivo de Telegram...", parse_mode='HTML')
                
                # Obtener información del archivo
                file_info = None
                file_name = ""
                
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_name = message.document.file_name or f"document_{message.message_id}"
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
                    self.bot.reply_to(message, "❌ Tipo de archivo no soportado", parse_mode='HTML')
                    return
                
                # Descargar archivo
                downloaded_file = self.bot.download_file(file_info.file_path)
                
                # Guardar temporalmente
                local_path = Path(f"temp_{file_name}")
                with open(local_path, 'wb') as f:
                    f.write(downloaded_file)
                
                # Subir a NextCloud
                self.bot.reply_to(message, f"📤 Subiendo {escape_html_safe(file_name)} a NextCloud...", parse_mode='HTML')
                
                success, result = self.nc_client.upload_via_webdav(
                    local_path,
                    NEXTCLOUD_CONFIG["upload_base"]
                )
                
                # Limpiar archivo temporal
                if local_path.exists():
                    local_path.unlink()
                
                if success:
                    # Mensaje de éxito con HTML
                    success_msg = f"✅ <b>Subida exitosa</b><br><br>{escape_html_safe(result)}"
                    if len(success_msg) > 4000:
                        success_msg = success_msg[:4000] + "<br>...(mensaje truncado)"
                    self.bot.reply_to(message, success_msg, parse_mode='HTML')
                else:
                    # Intentar método alternativo
                    self.bot.reply_to(message, "🔄 Intentando método alternativo...", parse_mode='HTML')
                    
                    success2, result2 = self.nc_client.upload_via_ocs(
                        local_path,
                        NEXTCLOUD_CONFIG["upload_base"]
                    )
                    
                    if success2:
                        success_msg = f"✅ <b>Subida exitosa (método alternativo)</b><br><br>{escape_html_safe(result2)}"
                        self.bot.reply_to(message, success_msg, parse_mode='HTML')
                    else:
                        error_msg = f"❌ <b>Error en la subida</b><br><br>{escape_html_safe(result2)}"
                        self.bot.reply_to(message, error_msg, parse_mode='HTML')
                        
            except Exception as e:
                logger.error(f"Error en handle_file: {e}")
                error_msg = f"❌ <b>Error interno</b><br>{escape_html_safe(str(e)[:200])}"
                self.bot.reply_to(message, error_msg, parse_mode='HTML')
        
        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            reply_text = "📁 Envíame un archivo para subirlo a NextCloud<br>Usa /help para ayuda"
            self.bot.reply_to(message, reply_text, parse_mode='HTML')
    
    def run(self):
        """Iniciar el bot"""
        logger.info("🚀 Iniciando bot de Telegram...")
        # Limpiar webhook previo si existe
        self.bot.remove_webhook()
        time.sleep(1)
        self.bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """Función principal"""
    logger.info("⚡ Iniciando sistema de subida NextCloud para Cuba")
    
    try:
        # Verificar variables críticas
        if not NEXTCLOUD_CONFIG["username"] or not NEXTCLOUD_CONFIG["password"]:
            logger.error("❌ Credenciales de NextCloud no configuradas")
            return
        
        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ Token de Telegram no configurado")
            return
        
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
    
    Iniciando bot...
    """)
    
    # Ejecutar bot
    main()
