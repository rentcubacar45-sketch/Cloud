import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path
from urllib.parse import urljoin, quote
import mimetypes
from datetime import datetime
import tempfile

# ================================
# CONFIGURACIÓN DIRECTA
# ================================

# Credenciales Nextcloud Universidad de Oriente
NEXTCLOUD_URL = 'https://nube.uo.edu.cu'
NEXTCLOUD_USER = 'eric.serrano'
NEXTCLOUD_PASSWORD = 'Rulebreaker2316'

# Token de tu bot de Telegram (debes obtenerlo de @BotFather)
TELEGRAM_TOKEN = '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU'  # ¡REEMPLAZA ESTO!

# Configuración de carpetas
CARPETA_BASE = '/Telegram_Bot'
CARPETA_DOCUMENTOS = '/Telegram_Bot/Documentos'
CARPETA_IMAGENES = '/Telegram_Bot/Imagenes'
CARPETA_AUDIO = '/Telegram_Bot/Audio'
CARPETA_VIDEO = '/Telegram_Bot/Video'

# ================================
# CONFIGURACIÓN DE LOGGING
# ================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_nextcloud.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================================
# CLIENTE NEXTCLOUD PARA UO
# ================================

class NextCloudUOClient:
    """Cliente especializado para nube.uo.edu.cu"""
    
    def __init__(self):
        self.base_url = NEXTCLOUD_URL.rstrip('/')
        self.username = NEXTCLOUD_USER
        self.password = NEXTCLOUD_PASSWORD
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}"
        
        # Crear estructura de carpetas al iniciar
        self._crear_estructura_carpetas()
    
    def _crear_estructura_carpetas(self):
        """Crea la estructura de carpetas en Nextcloud"""
        carpetas = [CARPETA_BASE, CARPETA_DOCUMENTOS, CARPETA_IMAGENES, 
                   CARPETA_AUDIO, CARPETA_VIDEO]
        
        for carpeta in carpetas:
            self.crear_carpeta(carpeta)
    
    def verificar_conexion(self):
        """Verifica que podemos conectar a nube.uo.edu.cu"""
        try:
            # Endpoint de estado de Nextcloud
            status_url = f"{self.base_url}/status.php"
            response = requests.get(status_url, auth=self.auth, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Conectado a Nextcloud UO v{data.get('version', 'N/A')}")
                return True, f"Conectado a nube.uo.edu.cu"
            else:
                logger.error(f"❌ Error HTTP {response.status_code}")
                return False, f"Error del servidor: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ No se puede conectar a nube.uo.edu.cu")
            return False, "No se puede conectar al servidor"
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def crear_carpeta(self, ruta_carpeta):
        """Crea una carpeta en Nextcloud (MKCOL en WebDAV)"""
        try:
            # Asegurar que la ruta empiece con /
            if not ruta_carpeta.startswith('/'):
                ruta_carpeta = '/' + ruta_carpeta
            
            url = f"{self.webdav_url}{ruta_carpeta}"
            
            response = requests.request(
                'MKCOL',
                url,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code in [201, 405]:  # 201=Creada, 405=Ya existe
                logger.info(f"✅ Carpeta '{ruta_carpeta}' lista")
                return True
            else:
                logger.warning(f"⚠️ No se pudo crear carpeta {ruta_carpeta}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creando carpeta: {str(e)}")
            return False
    
    def subir_archivo(self, archivo_local, ruta_remota):
        """
        Sube un archivo a nube.uo.edu.cu
        
        Args:
            archivo_local: Ruta completa al archivo local
            ruta_remota: Ruta donde guardar en Nextcloud (ej: '/Telegram_Bot/Documentos/archivo.pdf')
        """
        try:
            # Verificar que el archivo local existe
            if not os.path.exists(archivo_local):
                return False, "❌ Archivo local no existe"
            
            # Asegurar ruta remota
            if not ruta_remota.startswith('/'):
                ruta_remota = '/' + ruta_remota
            
            # URL completa para WebDAV
            url = f"{self.webdav_url}{ruta_remota}"
            
            # Determinar tipo MIME
            tipo_mime, _ = mimetypes.guess_type(archivo_local)
            if not tipo_mime:
                tipo_mime = 'application/octet-stream'
            
            headers = {
                'Content-Type': tipo_mime
            }
            
            # Leer y subir el archivo
            with open(archivo_local, 'rb') as archivo:
                file_size = os.path.getsize(archivo_local)
                logger.info(f"📤 Subiendo {file_size/1024:.2f} KB a {ruta_remota}")
                
                response = requests.put(
                    url,
                    auth=self.auth,
                    data=archivo,
                    headers=headers,
                    timeout=30  # Timeout de 30 segundos
                )
            
            # Verificar respuesta
            if response.status_code in [201, 204]:
                # Crear URL de acceso directo
                url_acceso = f"{self.base_url}/apps/files/?dir={quote(ruta_remota)}"
                logger.info(f"✅ Subido exitosamente: {ruta_remota}")
                return True, f"✅ Subido a: {url_acceso}"
            else:
                error_msg = f"❌ Error {response.status_code}: {response.text[:100]}"
                logger.error(error_msg)
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "⏱️ Timeout - El servidor tardó demasiado"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ Error inesperado: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def determinar_carpeta_por_tipo(self, tipo_archivo, nombre_archivo):
        """Determina la carpeta destino basado en el tipo de archivo"""
        extension = Path(nombre_archivo).suffix.lower()
        
        # Imágenes
        if tipo_archivo == 'photo' or extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return CARPETA_IMAGENES
        
        # Documentos
        elif extension in ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.xls', '.ppt', '.pptx', '.odt']:
            return CARPETA_DOCUMENTOS
        
        # Audio
        elif extension in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']:
            return CARPETA_AUDIO
        
        # Video
        elif extension in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
            return CARPETA_VIDEO
        
        # Otros
        else:
            return CARPETA_BASE

# ================================
# MANEJADORES DE TELEGRAM
# ================================

# Inicializar cliente
nc_client = NextCloudUOClient()

async def comando_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    mensaje = f"""
    🤖 **Bot de Nextcloud UO**
    
    Universidad de Oriente - nube.uo.edu.cu
    
    *Comandos disponibles:*
    /start - Muestra este mensaje
    /status - Verifica conexión con nube.uo.edu.cu
    /info - Información del usuario
    /carpeta [nombre] - Cambiar carpeta destino
    
    *Modo de uso:*
    Simplemente envíame cualquier archivo y lo subiré automáticamente a tu Nextcloud.
    
    *Estructura de carpetas:*
    • Documentos: PDF, Word, Excel, etc.
    • Imagenes: JPG, PNG, GIF, etc.
    • Audio: MP3, WAV, etc.
    • Video: MP4, AVI, etc.
    
    Usuario: {NEXTCLOUD_USER}
    Servidor: {NEXTCLOUD_URL}
    """
    
    # Verificar conexión inicial
    conexion_ok, mensaje_conexion = nc_client.verificar_conexion()
    if conexion_ok:
        mensaje += f"\n\n✅ *Estado:* {mensaje_conexion}"
    else:
        mensaje += f"\n\n⚠️ *Estado:* {mensaje_conexion}"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def comando_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica el estado de la conexión"""
    await update.message.reply_text("🔍 Verificando conexión con nube.uo.edu.cu...")
    
    conexion_ok, mensaje = nc_client.verificar_conexion()
    
    if conexion_ok:
        await update.message.reply_text(f"✅ {mensaje}")
    else:
        await update.message.reply_text(f"❌ {mensaje}")

async def comando_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra información del usuario"""
    info_text = f"""
    📋 *Información de cuenta:*
    
    *Usuario:* `{NEXTCLOUD_USER}`
    *Servidor:* `{NEXTCLOUD_URL}`
    *Carpeta base:* `{CARPETA_BASE}`
    
    *Carpetas disponibles:*
    • `{CARPETA_DOCUMENTOS}`
    • `{CARPETA_IMAGENES}`
    • `{CARPETA_AUDIO}`
    • `{CARPETA_VIDEO}`
    """
    
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def comando_carpeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cambia la carpeta destino"""
    if context.args:
        nueva_carpeta = ' '.join(context.args)
        if not nueva_carpeta.startswith('/'):
            nueva_carpeta = '/' + nueva_carpeta
        
        # Crear la carpeta si no existe
        nc_client.crear_carpeta(nueva_carpeta)
        
        # Guardar en contexto del usuario
        context.user_data['carpeta_personalizada'] = nueva_carpeta
        
        await update.message.reply_text(f"📂 Carpeta destino cambiada a:\n`{nueva_carpeta}`", 
                                      parse_mode='Markdown')
    else:
        carpeta_actual = context.user_data.get('carpeta_personalizada', 'Automática (por tipo)')
        await update.message.reply_text(f"📂 Carpeta actual: {carpeta_arpeta_actual}")

async def manejar_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la subida de documentos"""
    try:
        documento = update.message.document
        nombre_archivo = documento.file_name or f"documento_{documento.file_id}"
        tamano_mb = documento.file_size / (1024 * 1024) if documento.file_size else 0
        
        await update.message.reply_text(
            f"📄 *Procesando documento:*\n"
            f"`{nombre_archivo}`\n"
            f"📏 Tamaño: {tamano_mb:.2f} MB\n"
            f"⏳ Descargando...",
            parse_mode='Markdown'
        )
        
        # Descargar archivo temporal
        archivo_tg = await documento.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(nombre_archivo).suffix) as tmp:
            ruta_temporal = tmp.name
            await archivo_tg.download_to_drive(ruta_temporal)
        
        # Determinar carpeta destino
        if 'carpeta_personalizada' in context.user_data:
            carpeta_destino = context.user_data['carpeta_personalizada']
        else:
            carpeta_destino = nc_client.determinar_carpeta_por_tipo('document', nombre_archivo)
        
        # Crear nombre con timestamp para evitar duplicados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_final = f"{timestamp}_{nombre_archivo}"
        ruta_remota = f"{carpeta_destino}/{nombre_final}"
        
        await update.message.reply_text(f"📤 Subiendo a nube.uo.edu.cu...")
        
        # Subir a Nextcloud
        exito, mensaje = nc_client.subir_archivo(ruta_temporal, ruta_remota)
        
        # Limpiar archivo temporal
        os.unlink(ruta_temporal)
        
        if exito:
            await update.message.reply_text(
                f"✅ *Documento subido exitosamente*\n\n"
                f"📁 *Ubicación:* `{ruta_remota}`\n"
                f"🔗 *Acceso:* {mensaje.split(' ')[-1] if '://' in mensaje else 'En Nextcloud'}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ *Error al subir:*\n{str(mensaje)}", 
                                          parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error en documento: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")

async def manejar_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la subida de imágenes"""
    try:
        # Obtener la imagen de mayor calidad
        foto = update.message.photo[-1]
        
        await update.message.reply_text("🖼️ Procesando imagen...")
        
        # Descargar imagen
        archivo_tg = await foto.get_file()
        
        # Crear nombre único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"imagen_{timestamp}.jpg"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            ruta_temporal = tmp.name
            await archivo_tg.download_to_drive(ruta_temporal)
        
        # Determinar carpeta
        if 'carpeta_personalizada' in context.user_data:
            carpeta_destino = context.user_data['carpeta_personalizada']
        else:
            carpeta_destino = CARPETA_IMAGENES
        
        ruta_remota = f"{carpeta_destino}/{nombre_archivo}"
        
        await update.message.reply_text("📤 Subiendo imagen...")
        
        # Subir
        exito, mensaje = nc_client.subir_archivo(ruta_temporal, ruta_remota)
        
        # Limpiar
        os.unlink(ruta_temporal)
        
        if exito:
            await update.message.reply_text(f"✅ Imagen subida a:\n`{ruta_remota}`", 
                                          parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Error: {mensaje}")
            
    except Exception as e:
        logger.error(f"Error en imagen: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")

async def manejar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la subida de audio"""
    try:
        audio = update.message.audio or update.message.voice
        if audio:
            nombre = audio.file_name or f"audio_{audio.file_id}.ogg"
            
            await update.message.reply_text("🎵 Procesando audio...")
            
            archivo_tg = await audio.get_file()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
                ruta_temp = tmp.name
                await archivo_tg.download_to_drive(ruta_temp)
            
            # Carpeta destino
            carpeta = context.user_data.get('carpeta_personalizada', CARPETA_AUDIO)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_remota = f"{carpeta}/{timestamp}_{nombre}"
            
            exito, msg = nc_client.subir_archivo(ruta_temp, ruta_remota)
            os.unlink(ruta_temp)
            
            if exito:
                await update.message.reply_text(f"✅ Audio subido: `{ruta_remota}`", 
                                              parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Error: {msg}")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Error audio: {str(e)[:200]}")

async def manejar_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores"""
    logger.error(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Ocurrió un error. Intenta nuevamente.")

# ================================
# FUNCIÓN PRINCIPAL
# ================================

def main():
    """Inicia el bot"""
    print(f"""
    ====================================
    🤖 BOT NEXTCLOUD UO - Universidad de Oriente
    ====================================
    Servidor: {NEXTCLOUD_URL}
    Usuario: {NEXTCLOUD_USER}
    Carpeta base: {CARPETA_BASE}
    ====================================
    """)
    
    # Verificar conexión inicial
    print("🔍 Verificando conexión con nube.uo.edu.cu...")
    conexion_ok, mensaje = nc_client.verificar_conexion()
    if conexion_ok:
        print(f"✅ {mensaje}")
    else:
        print(f"⚠️ {mensaje}")
        print("⚠️ El bot iniciará pero puede tener problemas de conexión")
    
    # Crear aplicación de Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", comando_inicio))
    application.add_handler(CommandHandler("status", comando_status))
    application.add_handler(CommandHandler("info", comando_info))
    application.add_handler(CommandHandler("carpeta", comando_carpeta))
    
    # Manejadores de archivos
    application.add_handler(MessageHandler(filters.Document.ALL, manejar_documento))
    application.add_handler(MessageHandler(filters.PHOTO, manejar_imagen))
    application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, manejar_audio))
    
    # Manejar otros archivos (genérico)
    application.add_handler(MessageHandler(
        filters.ATTACHMENT | filters.VIDEO | filters.VIDEO_NOTE, 
        manejar_documento
    ))
    
    # Manejar errores
    application.add_error_handler(manejar_error)
    
    # Iniciar bot
    print("\n🤖 Bot iniciado. Presiona Ctrl+C para detener.")
    print("📱 Envía /start a tu bot en Telegram para comenzar")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ================================
# EJECUCIÓN
# ================================

if __name__ == '__main__':
    # Verificar que el token esté configurado
    if TELEGRAM_TOKEN == 'TU_TOKEN_AQUI':
        print("""
        ❌ ERROR: Debes configurar tu token de Telegram.
        
        Pasos:
        1. Busca @BotFather en Telegram
        2. Crea un bot con /newbot
        3. Copia el token que te dé
        4. Reemplaza 'TU_TOKEN_AQUI' en el código
        """)
    else:
        try:
            main()
        except KeyboardInterrupt:
            print("\n👋 Bot detenido")
        except Exception as e:
            logger.error(f"Error fatal: {str(e)}")
            print(f"❌ Error fatal: {str(e)}")
