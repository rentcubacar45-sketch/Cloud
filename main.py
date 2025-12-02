"""
🤖 BOT NEXTCLOUD UO - ERIC SERRANO
Versión optimizada para Render + Python 3.13
"""

import os
import sys
import logging
import requests
import tempfile
import random
import hashlib
from datetime import datetime
from pathlib import Path
import signal

# ================================
# CONFIGURACIÓN PRINCIPAL
# ================================
TELEGRAM_TOKEN = '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU'
ALLOWED_USERNAME = 'eliel_21'

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
# CLIENTE NEXTCLOUD SIMPLIFICADO
# ================================
class NextcloudUOClient:
    """Cliente para nube.uo.edu.cu"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Linux) mirall/3.7.4',
        'Nextcloud-android/3.20.1',
        'ios/15.0 (iPhone) Nextcloud-iOS/4.3.0',
    ]
    
    def __init__(self):
        self.base_url = NEXTCLOUD_URL.rstrip('/')
        self.username = NEXTCLOUD_USER
        self.password = NEXTCLOUD_PASSWORD
        self.session = requests.Session()
        self.session.verify = False
    
    def _get_headers(self):
        """Headers para simular cliente oficial"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': '*/*',
        }
    
    def test_connection(self):
        """Prueba conexión al servidor"""
        try:
            url = f"{self.base_url}/status.php"
            headers = self._get_headers()
            
            response = requests.get(
                url,
                auth=(self.username, self.password),
                headers=headers,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                return True, "✅ Conectado a Nextcloud UO"
            else:
                return False, f"❌ Error {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def upload_file(self, file_path, remote_filename):
        """Sube archivo a Nextcloud"""
        try:
            url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
            headers = self._get_headers()
            
            with open(file_path, 'rb') as f:
                response = requests.put(
                    url,
                    auth=(self.username, self.password),
                    data=f,
                    headers=headers,
                    timeout=30,
                    verify=False
                )
            
            if response.status_code in [201, 204]:
                return True, f"✅ Subido: {remote_filename}"
            else:
                return False, f"❌ Error {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error subiendo: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def get_remote_path(self, filename):
        """Determina ruta remota"""
        ext = Path(filename).suffix.lower()
        
        # Definir carpetas
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            folder = '/Telegram_Bot/Imagenes'
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
            folder = '/Telegram_Bot/Documentos'
        elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
            folder = '/Telegram_Bot/Audio'
        elif ext in ['.mp4', '.avi', '.mkv', '.mov']:
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
print("=" * 60)
print("🤖 BOT NEXTCLOUD UO - ERIC SERRANO")
print("=" * 60)
print(f"🔗 Servidor: {NEXTCLOUD_URL}")
print(f"👤 Usuario: {NEXTCLOUD_USER}")
print(f"📱 Telegram: Solo para @{ALLOWED_USERNAME}")
print("=" * 60)

nc_client = NextcloudUOClient()

# Probar conexión
print("\n🔍 Probando conexión a Nextcloud...")
success, msg = nc_client.test_connection()
print(f"📡 {msg}")

# ================================
# MANEJO DE SEÑALES PARA RENDER
# ================================
def signal_handler(signum, frame):
    """Maneja señales de terminación"""
    print(f"\n📡 Señal {signum} recibida. Deteniendo bot...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ================================
# IMPORTAR TELEGRAM BOT
# ================================
print("\n📦 Cargando Telegram Bot...")
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    print("✅ Telegram Bot cargado correctamente")
except ImportError as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# ================================
# SEGURIDAD
# ================================
def is_user_allowed(user):
    """Verifica si el usuario está autorizado"""
    if not user or not user.username:
        return False
    return user.username.lower() == ALLOWED_USERNAME

async def check_auth(update: Update):
    """Verifica autenticación"""
    user = update.effective_user
    if not is_user_allowed(user):
        if update.message:
            await update.message.reply_text(
                "🚫 *ACCESO DENEGADO*\n\nEste bot es solo para @Eliel_21.",
                parse_mode='Markdown'
            )
        return False
    return True

# ================================
# MANEJADORES DE TELEGRAM
# ================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    if not await check_auth(update):
        return
    
    user = update.effective_user
    
    welcome_text = f"""
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
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    if not await check_auth(update):
        return
    
    success, msg = nc_client.test_connection()
    
    status_text = f"""
*Estado del Sistema*

{msg}

*Detalles:*
• Servidor: `{NEXTCLOUD_URL}`
• Usuario: `{NEXTCLOUD_USER}`
• Telegram: @{update.effective_user.username}
    """
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /test"""
    if not await check_auth(update):
        return
    
    await update.message.reply_text("🧪 Creando archivo de prueba...")
    
    # Crear archivo de prueba
    test_content = f"""Archivo de prueba - Bot Nextcloud UO
Fecha: {datetime.now()}
Usuario: {NEXTCLOUD_USER}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
        temp_path = tmp.name
        tmp.write(test_content)
    
    try:
        filename = f"prueba_bot_{datetime.now().strftime('%H%M%S')}.txt"
        remote_path = nc_client.get_remote_path(filename)
        
        await update.message.reply_text("📤 Subiendo archivo de prueba...")
        
        success, message = nc_client.upload_file(temp_path, remote_path)
        
        if success:
            await update.message.reply_text(
                f"✅ *Prueba exitosa!*\n\n{message}\n\n"
                f"Accede en: {NEXTCLOUD_URL}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ *Prueba fallida*\n\n{message}",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
    
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja cualquier archivo"""
    if not await check_auth(update):
        return
    
    try:
        # Determinar tipo de archivo
        if update.message.document:
            file_obj = update.message.document
            file_type = "📄 Documento"
        elif update.message.photo:
            file_obj = update.message.photo[-1]
            file_type = "🖼️ Imagen"
        elif update.message.audio:
            file_obj = update.message.audio
            file_type = "🎵 Audio"
        elif update.message.video:
            file_obj = update.message.video
            file_type = "🎬 Video"
        else:
            await update.message.reply_text("❌ Tipo no soportado")
            return
        
        # Obtener nombre
        if hasattr(file_obj, 'file_name') and file_obj.file_name:
            original_name = file_obj.file_name
        else:
            original_name = f"{file_type.replace(' ', '_').lower()}_{file_obj.file_id}"
        
        file_size = file_obj.file_size or 0
        file_size_mb = file_size / (1024 * 1024)
        
        # Mensaje inicial
        msg = await update.message.reply_text(
            f"{file_type}: *{original_name}*\n"
            f"📏 Tamaño: {file_size_mb:.2f} MB\n"
            f"⏳ Descargando...",
            parse_mode='Markdown'
        )
        
        # Descargar archivo
        telegram_file = await file_obj.get_file()
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(original_name).suffix or '.bin') as tmp:
            temp_path = tmp.name
            await telegram_file.download_to_drive(temp_path)
        
        # Actualizar mensaje
        await msg.edit_text(
            f"{file_type}: *{original_name}*\n"
            f"✅ Descargado\n"
            f"📤 Subiendo a Nextcloud UO...",
            parse_mode='Markdown'
        )
        
        # Obtener ruta remota
        remote_path = nc_client.get_remote_path(original_name)
        
        # Subir archivo
        success, message = nc_client.upload_file(temp_path, remote_path)
        
        # Limpiar
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # Resultado
        if success:
            await msg.edit_text(
                f"✅ *Subida exitosa!*\n\n"
                f"{message}\n\n"
                f"*Accede en:* {NEXTCLOUD_URL}",
                parse_mode='Markdown'
            )
        else:
            await msg.edit_text(
                f"❌ *Error en la subida*\n\n"
                f"Archivo: {original_name}\n"
                f"Error: {message}",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes desconocidos"""
    if not await check_auth(update):
        return
    
    await update.message.reply_text(
        "🤔 No entiendo ese comando.\n\n"
        "Envía un archivo o usa:\n"
        "/start - Inicio\n"
        "/status - Estado\n"
        "/test - Probar",
        parse_mode='Markdown'
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores"""
    logger.error(f"Error: {context.error}")
    try:
        if update and update.message:
            await update.message.reply_text("❌ Ocurrió un error.")
    except:
        pass

# ================================
# FUNCIÓN PRINCIPAL OPTIMIZADA
# ================================
def main():
    """Función principal optimizada para Render"""
    print("\n🤖 Iniciando bot de Telegram...")
    
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: Token no configurado")
        return
    
    try:
        # Crear aplicación
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Comandos
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("test", test))
        
        # Handlers de archivos
        app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
        app.add_handler(MessageHandler(filters.PHOTO, handle_file))
        app.add_handler(MessageHandler(filters.AUDIO, handle_file))
        app.add_handler(MessageHandler(filters.VIDEO, handle_file))
        
        # Handler por defecto
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
        
        # Error handler
        app.add_error_handler(error_handler)
        
        print("✅ Bot listo")
        print("📱 Envía /start a tu bot en Telegram")
        print("\n🔄 Bot en ejecución...")
        
        # Iniciar bot (forma simplificada)
        app.run_polling()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n⚠️  Verifica:")
        print("1. Token correcto")
        print("2. No hay otro bot ejecutándose")
        print("3. Conexión a internet")

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido")
    except SystemExit:
        print("\n🛑 Bot terminado")
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
