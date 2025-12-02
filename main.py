"""
🤖 BOT NEXTCLOUD UO - ERIC SERRANO
Versión: Python 3.13 + python-telegram-bot 21.7
Modo: Stealth (cliente oficial)
Solo para: @Eliel_21
"""

import os
import sys
import logging
import requests
import tempfile
import time
import random
import hashlib
from datetime import datetime
from pathlib import Path
import asyncio

# ================================
# CONFIGURACIÓN PRINCIPAL
# ================================
TELEGRAM_TOKEN = '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU'
ALLOWED_USERNAME = 'eliel_21'  # en minúsculas

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
# IMPORTAR TELEGRAM BOT VERSIÓN 21.x
# ================================
print("🚀 Cargando Telegram Bot (versión 21.x)...")
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    print("✅ Telegram Bot cargado correctamente")
except ImportError as e:
    print(f"❌ Error cargando Telegram Bot: {e}")
    print("\n⚠️  Instala la versión correcta:")
    print("pip install python-telegram-bot==21.7")
    sys.exit(1)

# ================================
# CLIENTE STEALTH PARA NEXTCLOUD UO
# ================================
class NextcloudStealthClient:
    """Cliente que simula ser cliente oficial de Nextcloud"""
    
    # User-Agents de clientes oficiales
    USER_AGENTS = [
        'Mozilla/5.0 (Linux) mirall/3.7.4',
        'Nextcloud-android/3.20.1',
        'ios/15.0 (iPhone) Nextcloud-iOS/4.3.0',
        'Mozilla/5.0 (X11; Linux x86_64) mirall/3.6.1',
        'nextcloud-cmd/1.0',
        'Mozilla/5.0 (compatible; Nextcloud-Client)',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Nextcloud-DesktopClient/3.7.4',
    ]
    
    def __init__(self):
        self.base_url = NEXTCLOUD_URL.rstrip('/')
        self.username = NEXTCLOUD_USER
        self.password = NEXTCLOUD_PASSWORD
        self.session = requests.Session()
        
        # Configurar sesión para evitar bloqueos
        self.session.verify = False
        self._rotate_user_agent()
        
        # Headers que simulan cliente oficial
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es, en-US;q=0.9, en;q=0.8',
            'Connection': 'keep-alive',
            'DNT': '1',
        }
        self.session.headers.update(self.headers)
    
    def _rotate_user_agent(self):
        """Cambia el User-Agent aleatoriamente"""
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS)
        })
    
    def test_connection(self):
        """Prueba conexión simulando cliente oficial"""
        try:
            self._rotate_user_agent()
            
            # Probar con endpoint de estado
            url = f"{self.base_url}/status.php"
            response = self.session.get(
                url,
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "✅ Conectado a Nextcloud UO (modo stealth)"
            else:
                return False, f"❌ Error {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Error de conexión: {str(e)}"
    
    def create_folder(self, folder_path):
        """Crea carpeta usando WebDAV con headers de cliente oficial"""
        try:
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path
            
            self._rotate_user_agent()
            
            webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}{folder_path}"
            
            # Headers específicos para WebDAV de Nextcloud
            dav_headers = {
                **self.headers,
                'Depth': '1',
            }
            
            response = self.session.request(
                'MKCOL',
                webdav_url,
                auth=(self.username, self.password),
                headers=dav_headers,
                timeout=10
            )
            
            if response.status_code in [201, 405]:  # 201=Creado, 405=Ya existe
                logger.info(f"📁 Carpeta creada: {folder_path}")
                return True
            else:
                logger.warning(f"No se pudo crear {folder_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error creando carpeta: {e}")
            return False
    
    def upload_file(self, file_path, remote_filename):
        """Sube archivo usando múltiples métodos stealth"""
        methods = [
            self._upload_via_webdav_stealth,
            self._upload_via_put_direct,
            self._upload_via_basic_auth,
        ]
        
        for method in methods:
            try:
                self._rotate_user_agent()
                logger.info(f"🔧 Probando método: {method.__name__}")
                success, message = method(file_path, remote_filename)
                if success:
                    return success, message
                time.sleep(0.5)  # Pequeña pausa
            except Exception as e:
                logger.warning(f"⚠️ Método {method.__name__} falló: {e}")
        
        return False, "❌ Todos los métodos de subida fallaron"
    
    def _upload_via_webdav_stealth(self, file_path, remote_filename):
        """WebDAV con headers de cliente oficial"""
        try:
            webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
            
            # Headers que usan los clientes oficiales
            upload_headers = {
                **self.headers,
                'Content-Type': 'application/octet-stream',
                'OC-Checksum': self._calculate_md5(file_path),
            }
            
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    webdav_url,
                    auth=(self.username, self.password),
                    data=f,
                    headers=upload_headers,
                    timeout=30
                )
            
            if response.status_code in [201, 204]:
                return True, f"✅ Subido (WebDAV stealth): {remote_filename}"
            else:
                return False, f"❌ WebDAV {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Error WebDAV: {str(e)}"
    
    def _upload_via_put_direct(self, file_path, remote_filename):
        """PUT directo con autenticación básica"""
        try:
            url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
            
            with open(file_path, 'rb') as f:
                # Usar requests directamente para más control
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
                return True, f"✅ Subido (PUT directo): {remote_filename}"
            else:
                return False, f"❌ PUT {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Error PUT: {str(e)}"
    
    def _upload_via_basic_auth(self, file_path, remote_filename):
        """Método más básico posible"""
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
            
            if response.status_code in [201, 204]:
                return True, f"✅ Subido (básico): {remote_filename}"
            else:
                return False, f"❌ Básico {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"❌ Error básico: {str(e)}"
    
    def _calculate_md5(self, file_path):
        """Calcula MD5 para header OC-Checksum"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return f"MD5:{hasher.hexdigest()}"
    
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
# INICIALIZACIÓN DEL CLIENTE
# ================================
print("=" * 60)
print("🤖 BOT NEXTCLOUD UO - MODO STEALTH")
print("=" * 60)
print(f"🔗 Servidor: {NEXTCLOUD_URL}")
print(f"👤 Usuario: {NEXTCLOUD_USER}")
print(f"📱 Telegram: Solo para @{ALLOWED_USERNAME}")
print("=" * 60)

nc_client = NextcloudStealthClient()

# Probar conexión inicial
print("\n🔍 Probando conexión como cliente oficial...")
success, msg = nc_client.test_connection()
print(f"📡 {msg}")

if success:
    # Crear estructura de carpetas
    print("\n📁 Creando estructura de carpetas...")
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
            print(f"✅ {folder} lista")
else:
    print("⚠️ Continuando con conexión limitada")

# ================================
# SEGURIDAD - SOLO USUARIO AUTORIZADO
# ================================
def is_user_allowed(user):
    """Verifica si el usuario está autorizado"""
    if not user or not user.username:
        return False
    return user.username.lower() == ALLOWED_USERNAME

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware para verificar autenticación"""
    user = update.effective_user
    if not is_user_allowed(user):
        username = user.username if user and user.username else 'Desconocido'
        logger.warning(f"❌ Acceso denegado a: {username}")
        
        if update.message:
            await update.message.reply_text(
                "🚫 *ACCESO DENEGADO*\n\nEste bot es solo para @Eliel_21.",
                parse_mode='Markdown'
            )
        return False
    return True

# ================================
# MANEJADORES DE TELEGRAM (ASYNC)
# ================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    if not await check_auth(update, context):
        return
    
    user = update.effective_user
    
    # Probar conexión actual
    success, msg = nc_client.test_connection()
    
    welcome_text = f"""
🤖 *BOT NEXTCLOUD UO - Eric Serrano*

¡Hola {user.first_name}! 👋

*Usuario:* ✅ @{user.username}
*Estado:* {msg}

*Servidor:* `{NEXTCLOUD_URL}`
*Cuenta:* `{NEXTCLOUD_USER}`
*Modo:* Stealth (cliente oficial simulado)

*¿Cómo funciona?*
1. Envíame cualquier archivo
2. Lo subiré automáticamente a tu Nextcloud UO
3. Se organizará en carpetas según el tipo

*Comandos:*
/start - Este mensaje
/status - Verificar conexión
/test - Probar subida

*📁 Carpetas:*
• Documentos (PDF, Word, etc.)
• Imagenes (JPG, PNG, etc.)
• Audio (MP3, WAV, etc.)
• Video (MP4, AVI, etc.)
• Otros (cualquier formato)
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    if not await check_auth(update, context):
        return
    
    success, msg = nc_client.test_connection()
    
    status_text = f"""
*Estado del Sistema*

{msg}

*Detalles:*
• Servidor: `{NEXTCLOUD_URL}`
• Usuario Nextcloud: `{NEXTCLOUD_USER}`
• Usuario Telegram: @{update.effective_user.username}
• Modo: Stealth (cliente oficial)
• Bot: ✅ Activo
    """
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /test - Prueba de subida"""
    if not await check_auth(update, context):
        return
    
    await update.message.reply_text("🧪 Creando archivo de prueba...")
    
    # Crear archivo de prueba
    test_content = f"""Archivo de prueba - Bot Nextcloud UO
Fecha: {datetime.now()}
Usuario: {NEXTCLOUD_USER}
Servidor: {NEXTCLOUD_URL}
Modo: Stealth (cliente oficial simulado)
"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
        tmp.write(test_content)
        temp_path = tmp.name
    
    try:
        filename = f"prueba_bot_{datetime.now().strftime('%H%M%S')}.txt"
        remote_path = nc_client.get_remote_path(filename)
        
        await update.message.reply_text("📤 Subiendo archivo de prueba...")
        
        success, message = nc_client.upload_file(temp_path, remote_path)
        
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
        if os.path.exists(temp_path):
            os.unlink(temp_path)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja documentos"""
    if not await check_auth(update, context):
        return
    
    await _handle_file(update, context, update.message.document, "📄 Documento")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja fotos"""
    if not await check_auth(update, context):
        return
    
    # Tomar la foto de mayor calidad (última en la lista)
    await _handle_file(update, context, update.message.photo[-1], "🖼️ Imagen")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja audio"""
    if not await check_auth(update, context):
        return
    
    await _handle_file(update, context, update.message.audio, "🎵 Audio")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja video"""
    if not await check_auth(update, context):
        return
    
    await _handle_file(update, context, update.message.video, "🎬 Video")

async def _handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_obj, file_type):
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
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(original_name).suffix or '.bin') as tmp:
            temp_path = tmp.name
            await telegram_file.download_to_drive(temp_path)
        
        # Verificar que se descargó
        if not os.path.exists(temp_path):
            raise Exception("No se pudo descargar el archivo")
        
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
        
        # Limpiar archivo temporal
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # Resultado final
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
                f"*Archivo:* {original_name}\n"
                f"*Error:* {message}\n\n"
                f"Intenta nuevamente o usa /test",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes desconocidos"""
    if not await check_auth(update, context):
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
    """Maneja errores globales"""
    logger.error(f"Error: {context.error}")
    try:
        if update and update.message:
            await update.message.reply_text(
                "❌ Ocurrió un error inesperado.\n"
                "Por favor, intenta nuevamente.",
                parse_mode='Markdown'
            )
    except:
        pass

# ================================
# FUNCIÓN PRINCIPAL
# ================================
async def main():
    """Función principal async"""
    print("\n🤖 Inicializando bot de Telegram...")
    
    # Verificar token
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI':
        print("❌ ERROR: Token de Telegram no configurado")
        return
    
    try:
        # Crear aplicación (versión 21.x)
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Comandos
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CommandHandler("test", test))
        
        # Handlers de archivos
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
        application.add_handler(MessageHandler(filters.VIDEO, handle_video))
        
        # Handler por defecto
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        print("✅ Bot configurado correctamente")
        print("📱 Busca tu bot en Telegram y envía /start")
        print("\n" + "=" * 60)
        
        # Iniciar bot
        await application.run_polling()
        
    except Exception as e:
        print(f"\n❌ Error al iniciar bot: {e}")
        print("\nPosibles soluciones:")
        print("1. Verifica que el token sea correcto")
        print("2. Asegúrate de usar python-telegram-bot==21.7")
        print("3. El bot ya está ejecutándose en otra instancia")

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == '__main__':
    try:
        # Ejecutar con asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot detenido")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
