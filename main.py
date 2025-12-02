"""
🤖 BOT NEXTCLOUD UO - ERIC SERRANO
Corregido para Python 3.13 (sin imghdr)
"""

import os
import logging
import requests
import tempfile
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ================================
# CONFIGURACIÓN PRINCIPAL
# ================================
TELEGRAM_TOKEN = '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU'  # Tu token
ALLOWED_USERNAME = 'eliel_21'  # Tu username en minúsculas

NEXTCLOUD_URL = 'https://nube.uo.edu.cu'
NEXTCLOUD_USER = 'eric.serrano'
NEXTCLOUD_PASSWORD = 'Rulebreaker2316'

# ================================
# CONFIGURACIÓN DE LOGGING
# ================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Suprimir warnings SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================
# PARCHE PARA IMGHDR EN PYTHON 3.13
# ================================
try:
    import imghdr
except ImportError:
    # Python 3.13 eliminó imghdr, creamos una versión simple
    import struct
    
    def what(file_path):
        """Versión simplificada de imghdr.what para Python 3.13"""
        with open(file_path, 'rb') as f:
            header = f.read(32)
            
        if len(header) < 32:
            return None
            
        # JPEG
        if header.startswith(b'\xff\xd8\xff'):
            return 'jpeg'
        # PNG
        if header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        # GIF
        if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return 'gif'
        # TIFF
        if header.startswith(b'II\x2a\x00') or header.startswith(b'MM\x00\x2a'):
            return 'tiff'
        # BMP
        if header.startswith(b'BM'):
            return 'bmp'
        # WEBP
        if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
            return 'webp'
        
        return None
    
    # Crear módulo imghdr simulado
    import sys
    class FakeImghdr:
        what = staticmethod(what)
    
    sys.modules['imghdr'] = FakeImghdr()

# ================================
# SEGURIDAD - SOLO USUARIO AUTORIZADO
# ================================
def is_user_allowed(update: Update):
    """Verifica si el usuario está autorizado"""
    user = update.effective_user
    if not user or not user.username:
        return False
    return user.username.lower() == ALLOWED_USERNAME

# ================================
# CLIENTE NEXTCLOUD SIMPLIFICADO
# ================================
class NextcloudUOClient:
    """Cliente para nube.uo.edu.cu"""
    
    def __init__(self):
        self.base_url = NEXTCLOUD_URL.rstrip('/')
        self.username = NEXTCLOUD_USER
        self.password = NEXTCLOUD_PASSWORD
    
    def test_connection(self):
        """Prueba conexión al servidor"""
        try:
            url = f"{self.base_url}/status.php"
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=10,
                verify=False
            )
            return response.status_code == 200
        except:
            return False
    
    def create_folder(self, folder_path):
        """Crea carpeta en Nextcloud"""
        try:
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path
            
            webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}{folder_path}"
            
            response = requests.request(
                'MKCOL',
                webdav_url,
                auth=(self.username, self.password),
                timeout=10,
                verify=False
            )
            
            return response.status_code in [201, 405]
        except:
            return False
    
    def upload_file(self, file_path, remote_filename):
        """Sube archivo a Nextcloud"""
        try:
            url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
            
            with open(file_path, 'rb') as f:
                response = requests.put(
                    url,
                    auth=(self.username, self.password),
                    data=f,
                    timeout=30,
                    verify=False
                )
            
            return response.status_code in [201, 204]
        except Exception as e:
            logger.error(f"Error subiendo: {e}")
            return False
    
    def get_remote_path(self, filename):
        """Determina ruta remota basado en extensión"""
        ext = Path(filename).suffix.lower()
        
        # Definir carpetas
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            folder = '/Telegram_Bot/Imagenes'
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md']:
            folder = '/Telegram_Bot/Documentos'
        elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']:
            folder = '/Telegram_Bot/Audio'
        elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
            folder = '/Telegram_Bot/Video'
        else:
            folder = '/Telegram_Bot/Otros'
        
        # Nombre único con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_no_ext = Path(filename).stem
        final_name = f"{timestamp}_{name_no_ext}{ext}"
        
        return f"{folder}/{final_name}"

# ================================
# INICIALIZACIÓN
# ================================
nc_client = NextcloudUOClient()

# Probar conexión y crear carpetas al iniciar
print("🔍 Probando conexión a Nextcloud UO...")
if nc_client.test_connection():
    print("✅ Conectado a Nextcloud UO")
    folders = [
        '/Telegram_Bot',
        '/Telegram_Bot/Documentos',
        '/Telegram_Bot/Imagenes',
        '/Telegram_Bot/Audio',
        '/Telegram_Bot/Video',
        '/Telegram_Bot/Otros'
    ]
    for folder in folders:
        if nc_client.create_folder(folder):
            print(f"📁 Carpeta {folder} lista")
else:
    print("⚠️ Problemas de conexión con Nextcloud")

# ================================
# MANEJADORES DE TELEGRAM
# ================================
def start(update: Update, context: CallbackContext):
    """Comando /start"""
    if not is_user_allowed(update):
        update.message.reply_text("🚫 Acceso denegado. Este bot es solo para @Eliel_21.")
        return
    
    user = update.effective_user
    
    mensaje = f"""
🤖 *BOT NEXTCLOUD UO - Eric Serrano*

¡Hola {user.first_name}! 👋

*Usuario:* ✅ @{user.username}

*Servidor:* `{NEXTCLOUD_URL}`
*Cuenta:* `{NEXTCLOUD_USER}`

*Instrucciones:*
Envía cualquier archivo y lo subiré a tu Nextcloud UO.

*Comandos:*
/start - Este mensaje
/status - Verificar conexión
/test - Probar subida
    """
    
    update.message.reply_text(mensaje, parse_mode='Markdown')

def status(update: Update, context: CallbackContext):
    """Comando /status"""
    if not is_user_allowed(update):
        return
    
    conexion_ok = nc_client.test_connection()
    
    status_text = f"""
*Estado del Sistema*

{'✅ Conectado a Nextcloud UO' if conexion_ok else '❌ Error de conexión'}

*Detalles:*
• Servidor: `{NEXTCLOUD_URL}`
• Usuario Nextcloud: `{NEXTCLOUD_USER}`
• Usuario Telegram: @{update.effective_user.username}
• Bot: ✅ Activo
    """
    
    update.message.reply_text(status_text, parse_mode='Markdown')

def test(update: Update, context: CallbackContext):
    """Comando /test"""
    if not is_user_allowed(update):
        return
    
    update.message.reply_text("🧪 Creando archivo de prueba...")
    
    # Crear archivo de prueba
    test_content = f"""Archivo de prueba - Bot Nextcloud UO
Fecha: {datetime.now()}
Usuario: {NEXTCLOUD_USER}
Telegram: @{update.effective_user.username}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
        tmp.write(test_content)
        temp_path = tmp.name
    
    try:
        filename = f"prueba_bot_{datetime.now().strftime('%H%M%S')}.txt"
        remote_path = nc_client.get_remote_path(filename)
        
        update.message.reply_text("📤 Subiendo archivo de prueba...")
        
        success = nc_client.upload_file(temp_path, remote_path)
        
        if success:
            update.message.reply_text(
                f"✅ *Prueba exitosa!*\n\n"
                f"Archivo subido: `{remote_path}`\n\n"
                f"Accede en: {NEXTCLOUD_URL}",
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text("❌ *Prueba fallida*\n\nNo se pudo subir el archivo.", parse_mode='Markdown')
    
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)[:200]}")
    
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def handle_document(update: Update, context: CallbackContext):
    """Maneja documentos"""
    if not is_user_allowed(update):
        return
    
    _handle_file(update, context, update.message.document, "📄 Documento")

def handle_photo(update: Update, context: CallbackContext):
    """Maneja fotos"""
    if not is_user_allowed(update):
        return
    
    # Tomar la foto de mayor calidad (última en la lista)
    _handle_file(update, context, update.message.photo[-1], "🖼️ Imagen")

def handle_audio(update: Update, context: CallbackContext):
    """Maneja audio"""
    if not is_user_allowed(update):
        return
    
    _handle_file(update, context, update.message.audio, "🎵 Audio")

def handle_video(update: Update, context: CallbackContext):
    """Maneja video"""
    if not is_user_allowed(update):
        return
    
    _handle_file(update, context, update.message.video, "🎬 Video")

def _handle_file(update: Update, context: CallbackContext, file_obj, file_type):
    """Maneja cualquier tipo de archivo"""
    try:
        # Obtener información del archivo
        if hasattr(file_obj, 'file_name') and file_obj.file_name:
            original_name = file_obj.file_name
        else:
            original_name = f"{file_type.replace(' ', '_').lower()}_{file_obj.file_id}"
        
        file_size = file_obj.file_size or 0
        file_size_mb = file_size / (1024 * 1024)
        
        # Mensaje inicial
        msg = update.message.reply_text(
            f"{file_type}: *{original_name}*\n"
            f"📏 Tamaño: {file_size_mb:.2f} MB\n"
            f"⏳ Descargando...",
            parse_mode='Markdown'
        )
        
        # Descargar archivo
        file = file_obj.get_file()
        
        # Crear nombre temporal único
        temp_dir = tempfile.gettempdir()
        temp_filename = f"telegram_{file_obj.file_id}{Path(original_name).suffix or '.bin'}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        file.download(custom_path=temp_path)
        
        # Actualizar mensaje
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"{file_type}: *{original_name}*\n✅ Descargado\n📤 Subiendo a Nextcloud UO...",
            parse_mode='Markdown'
        )
        
        # Obtener ruta remota
        remote_path = nc_client.get_remote_path(original_name)
        
        # Subir archivo
        success = nc_client.upload_file(temp_path, remote_path)
        
        # Limpiar archivo temporal
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # Resultado final
        if success:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                text=f"✅ *Subida exitosa!*\n\nArchivo: `{remote_path}`\n\nAccede en: {NEXTCLOUD_URL}",
                parse_mode='Markdown'
            )
        else:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                text=f"❌ *Error en la subida*\n\nArchivo: {original_name}\n\nIntenta nuevamente o usa /test",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        update.message.reply_text(f"❌ Error: {str(e)[:200]}")

def unknown(update: Update, context: CallbackContext):
    """Maneja mensajes desconocidos"""
    if not is_user_allowed(update):
        return
    
    update.message.reply_text(
        "🤔 No entiendo ese comando.\n\n"
        "Envía un archivo o usa:\n"
        "/start - Inicio\n"
        "/status - Estado\n"
        "/test - Probar"
    )

# ================================
# FUNCIÓN PRINCIPAL
# ================================
def main():
    """Función principal"""
    print("=" * 60)
    print("🤖 BOT NEXTCLOUD UO - ERIC SERRANO")
    print("=" * 60)
    print(f"🔗 Servidor: {NEXTCLOUD_URL}")
    print(f"👤 Usuario: {NEXTCLOUD_USER}")
    print(f"📱 Telegram: Solo para @{ALLOWED_USERNAME}")
    print(f"🐍 Python: 3.13 (con parche imghdr)")
    print("=" * 60)
    
    # Verificar token
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: Token de Telegram no configurado")
        return
    
    try:
        # Crear updater (versión 13.x es compatible con Python 3.13)
        updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Comandos
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("status", status))
        dispatcher.add_handler(CommandHandler("test", test))
        
        # Handlers de archivos
        dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
        dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))
        dispatcher.add_handler(MessageHandler(Filters.audio, handle_audio))
        dispatcher.add_handler(MessageHandler(Filters.video, handle_video))
        
        # Handler por defecto
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, unknown))
        
        print("✅ Bot configurado correctamente")
        print("📱 Busca tu bot en Telegram y envía /start")
        print("\n" + "=" * 60)
        
        # Iniciar bot
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"\n❌ Error al iniciar bot: {e}")
        print("\nPosibles soluciones:")
        print("1. Verifica que el token sea correcto")
        print("2. Usa python-telegram-bot==13.15 en requirements.txt")
        print("3. Render está usando Python 3.13, este código ya tiene el parche")

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
