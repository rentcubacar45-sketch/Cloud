"""
🤖 BOT NEXTCLOUD UO - ERIC SERRANO
Solo para: @Eliel_21
Servidor: https://nube.uo.edu.cu
"""

import os
import logging
import requests
import tempfile
import time
import hashlib
import random
import asyncio
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================================
# CONFIGURACIÓN PRINCIPAL (TODO EN CÓDIGO)
# ================================
TELEGRAM_TOKEN = '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU'  # ⬅️ TU TOKEN AQUÍ
ALLOWED_USERNAME = 'Eliel_21'  # Tu username de Telegram (en minúsculas)

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

# Suprimir warnings SSL (para evitar el warning en logs)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================
# SEGURIDAD - SOLO USUARIO AUTORIZADO
# ================================
def is_user_allowed(user):
    """Verifica si el usuario está autorizado"""
    if not user:
        return False
    # Verificar username
    if user.username and user.username.lower() == ALLOWED_USERNAME:
        return True
    # Verificar ID si lo conoces (opcional)
    return False

async def check_auth(update: Update):
    """Middleware para verificar autenticación"""
    user = update.effective_user
    
    if not is_user_allowed(user):
        username = user.username if user and user.username else 'Desconocido'
        logger.warning(f"❌ Acceso denegado a: {username} (ID: {user.id if user else 'N/A'})")
        
        if update.message:
            await update.message.reply_text(
                "🚫 *ACCESO DENEGADO*\n\n"
                "Este bot es de uso exclusivo para @Eliel_21.\n"
                "Usuario detectado: @" + (username if username != 'Desconocido' else 'No tiene username'),
                parse_mode='Markdown'
            )
        return False
    return True

# ================================
# CLIENTE NEXTCLOUD SIMPLIFICADO Y FUNCIONAL
# ================================
class NextcloudUOClient:
    """Cliente optimizado para nube.uo.edu.cu"""
    
    def __init__(self):
        self.base_url = NEXTCLOUD_URL.rstrip('/')
        self.username = NEXTCLOUD_USER
        self.password = NEXTCLOUD_PASSWORD
        self.session = requests.Session()
        
        # Headers para evitar bloqueos
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Nextcloud-Client)',
            'Accept': '*/*',
        })
        
        # Suprimir warnings SSL en esta sesión
        self.session.verify = False
    
    def test_connection(self):
        """Prueba conexión al servidor"""
        try:
            url = f"{self.base_url}/status.php"
            response = self.session.get(
                url,
                auth=(self.username, self.password),
                timeout=10
            )
            if response.status_code == 200:
                return True, "✅ Conectado a Nextcloud UO"
            else:
                return False, f"❌ Error {response.status_code}"
        except Exception as e:
            return False, f"❌ Error de conexión: {str(e)}"
    
    def create_folder(self, folder_path):
        """Crea carpeta en Nextcloud"""
        try:
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path
            
            webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}{folder_path}"
            
            response = self.session.request(
                'MKCOL',
                webdav_url,
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code in [201, 405]:  # 201=Creado, 405=Ya existe
                logger.info(f"📁 Carpeta creada: {folder_path}")
                return True
            else:
                logger.warning(f"No se pudo crear carpeta {folder_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error creando carpeta: {e}")
            return False
    
    def upload_file(self, file_path, remote_filename):
        """Sube archivo a Nextcloud - MÉTODO SIMPLIFICADO"""
        try:
            # Método 1: WebDAV PUT directo
            webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
            
            with open(file_path, 'rb') as f:
                response = requests.put(
                    webdav_url,
                    auth=(self.username, self.password),
                    data=f,
                    timeout=30,
                    verify=False  # Ignorar verificación SSL
                )
            
            if response.status_code in [201, 204]:
                return True, f"✅ Subido: {remote_filename}"
            else:
                # Método alternativo: intentar con requests básico
                return self._upload_alternative(file_path, remote_filename)
                
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def _upload_alternative(self, file_path, remote_filename):
        """Método alternativo de subida"""
        try:
            # URL alternativa
            url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
            
            with open(file_path, 'rb') as f:
                # Usar requests directamente con headers mínimos
                response = requests.put(
                    url,
                    auth=(self.username, self.password),
                    data=f,
                    timeout=30,
                    verify=False,
                    headers={
                        'User-Agent': 'Nextcloud-DesktopClient/3.7.4',
                        'Content-Type': 'application/octet-stream'
                    }
                )
            
            if response.status_code in [201, 204]:
                return True, f"✅ Subido (método alternativo): {remote_filename}"
            else:
                return False, f"❌ Error {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"❌ Error alternativo: {str(e)}"
    
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
# MANEJADORES DE TELEGRAM (CORREGIDOS)
# ================================
class TelegramBotHandler:
    def __init__(self):
        self.nc_client = NextcloudUOClient()
        self._init_nextcloud()
    
    def _init_nextcloud(self):
        """Inicializa conexión con Nextcloud"""
        logger.info("🚀 Inicializando conexión con Nextcloud UO...")
        
        # Probar conexión
        success, msg = self.nc_client.test_connection()
        logger.info(f"📡 {msg}")
        
        if success:
            # Crear carpetas básicas
            folders = [
                '/Telegram_Bot',
                '/Telegram_Bot/Documentos',
                '/Telegram_Bot/Imagenes',
                '/Telegram_Bot/Audio',
                '/Telegram_Bot/Video',
                '/Telegram_Bot/Otros'
            ]
            
            for folder in folders:
                self.nc_client.create_folder(folder)
            logger.info("✅ Estructura de carpetas lista")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - SOLO PARA USUARIO AUTORIZADO"""
        # Verificar autenticación
        if not await check_auth(update):
            return
        
        user = update.effective_user
        
        welcome_text = f"""
🤖 *BOT NEXTCLOUD UO - Eric Serrano*

¡Hola {user.first_name}! 👋

*Usuario autorizado:* ✅ @{user.username}

*Servidor:* `{NEXTCLOUD_URL}`
*Cuenta Nextcloud:* `{NEXTCLOUD_USER}`

*¿Cómo funciona?*
1. Envíame cualquier archivo
2. Lo subiré automáticamente a tu Nextcloud UO
3. Se organizará en carpetas según el tipo

*Comandos disponibles:*
/start - Este mensaje
/status - Verificar conexión
/test - Probar subida

*📁 Carpetas creadas:*
• `/Telegram_Bot/Documentos/` - PDF, Word, etc.
• `/Telegram_Bot/Imagenes/` - JPG, PNG, etc.
• `/Telegram_Bot/Audio/` - MP3, WAV, etc.
• `/Telegram_Bot/Video/` - MP4, AVI, etc.
• `/Telegram_Bot/Otros/` - Otros formatos
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        if not await check_auth(update):
            return
        
        await update.message.reply_text("🔍 Verificando estado del sistema...")
        
        success, msg = self.nc_client.test_connection()
        
        status_text = f"""
*Estado del Sistema*

{msg}

*Detalles:*
• Servidor: `{NEXTCLOUD_URL}`
• Usuario Nextcloud: `{NEXTCLOUD_USER}`
• Usuario Telegram: @{update.effective_user.username}
• Bot: ✅ Activo
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def handle_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /test - Prueba de subida"""
        if not await check_auth(update):
            return
        
        await update.message.reply_text("🧪 Creando archivo de prueba...")
        
        # Crear archivo de prueba
        test_content = f"""Archivo de prueba - Bot Nextcloud UO
Fecha: {datetime.now()}
Usuario: {NEXTCLOUD_USER}
Servidor: {NEXTCLOUD_URL}
Telegram: @{update.effective_user.username}

Este archivo fue generado automáticamente por el bot.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
            tmp.write(test_content)
            temp_path = tmp.name
        
        try:
            # Subir archivo
            filename = f"prueba_bot_{datetime.now().strftime('%H%M%S')}.txt"
            remote_path = self.nc_client.get_remote_path(filename)
            
            await update.message.reply_text("📤 Subiendo archivo de prueba...")
            
            success, message = self.nc_client.upload_file(temp_path, remote_path)
            
            if success:
                result_text = f"""
✅ *Prueba exitosa!*

{message}

*Puedes verificar en:*
`{NEXTCLOUD_URL}/apps/files/?dir=/Telegram_Bot/Documentos`

*Ahora puedes enviar archivos reales.*
                """
                await update.message.reply_text(result_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ *Prueba fallida*\n\n{message}", parse_mode='Markdown')
        
        except Exception as e:
            await update.message.reply_text(f"❌ Error en prueba: {str(e)[:200]}")
        
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja documentos"""
        if not await check_auth(update):
            return
        
        await self._handle_file(update, update.message.document, "📄 Documento")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja fotos"""
        if not await check_auth(update):
            return
        
        await self._handle_file(update, update.message.photo[-1], "🖼️ Imagen")
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja audio"""
        if not await check_auth(update):
            return
        
        await self._handle_file(update, update.message.audio, "🎵 Audio")
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja video"""
        if not await check_auth(update):
            return
        
        await self._handle_file(update, update.message.video, "🎬 Video")
    
    async def _handle_file(self, update: Update, file_obj, file_type):
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
            msg = await update.message.reply_text(
                f"{file_type}: *{original_name}*\n"
                f"📏 Tamaño: {file_size_mb:.2f} MB\n"
                f"⏳ Descargando...",
                parse_mode='Markdown'
            )
            
            # Descargar archivo
            telegram_file = await file_obj.get_file()
            
            # Guardar temporalmente
            file_ext = Path(original_name).suffix or '.bin'
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
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
            remote_path = self.nc_client.get_remote_path(original_name)
            
            # Subir archivo
            success, message = self.nc_client.upload_file(temp_path, remote_path)
            
            # Limpiar archivo temporal
            os.unlink(temp_path)
            
            # Resultado final
            if success:
                result_text = f"""
✅ *Subida exitosa!*

{message}

*Ubicación:* `{remote_path}`

*Accede en:* {NEXTCLOUD_URL}
                """
                await msg.edit_text(result_text, parse_mode='Markdown')
            else:
                error_text = f"""
❌ *Error en la subida*

*Archivo:* {original_name}
*Error:* {message}

*Posibles soluciones:*
• Verifica tu conexión a internet
• Intenta con otro archivo
• Usa /status para verificar
                """
                await msg.edit_text(error_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error procesando archivo: {e}")
            if update.message:
                await update.message.reply_text(f"❌ Error crítico: {str(e)[:200]}")

# ================================
# APLICACIÓN PRINCIPAL (CORREGIDA)
# ================================
def main():
    """Función principal - CORREGIDA para evitar error de Updater"""
    
    # Verificar token
    if TELEGRAM_TOKEN == '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU':
        print("⚠️  Usando token de ejemplo. Asegúrate de usar tu token real.")
    
    print("=" * 60)
    print("🤖 BOT NEXTCLOUD UO - ERIC SERRANO")
    print("=" * 60)
    print(f"🔗 Servidor: {NEXTCLOUD_URL}")
    print(f"👤 Nextcloud: {NEXTCLOUD_USER}")
    print(f"📱 Telegram: Solo para @{ALLOWED_USERNAME}")
    print(f"🔐 Token: {'✅ Configurado' if TELEGRAM_TOKEN else '❌ Faltante'}")
    print("=" * 60)
    
    try:
        # Crear aplicación - FORMA CORRECTA
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Inicializar handler
        handler = TelegramBotHandler()
        
        # Registrar handlers con funciones lambda para evitar problemas
        application.add_handler(CommandHandler("start", handler.handle_start))
        application.add_handler(CommandHandler("status", handler.handle_status))
        application.add_handler(CommandHandler("test", handler.handle_test))
        
        # Handlers de archivos
        application.add_handler(MessageHandler(filters.Document.ALL, handler.handle_document))
        application.add_handler(MessageHandler(filters.PHOTO, handler.handle_photo))
        application.add_handler(MessageHandler(filters.AUDIO, handler.handle_audio))
        application.add_handler(MessageHandler(filters.VIDEO, handler.handle_video))
        
        print("✅ Bot configurado correctamente")
        print("📱 Busca tu bot en Telegram y envía /start")
        print("\n" + "=" * 60)
        
        # Iniciar bot - FORMA CORRECTA
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error fatal al iniciar bot: {e}")
        print(f"❌ Error fatal: {e}")
        print("\nPosibles soluciones:")
        print("1. Verifica que el token de Telegram sea correcto")
        print("2. Asegúrate de usar python-telegram-bot==20.3")
        print("3. Revisa que no haya otro bot ejecutándose con el mismo token")

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == '__main__':
    # NOTA: En Render, asegúrate de que requirements.txt tenga:
    # python-telegram-bot==20.3
    # requests==2.31.0
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
