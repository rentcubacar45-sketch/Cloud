"""
BOT TELEGRAM + NEXTCLOUD UO - Universidad de Oriente
Autor: Eric Serrano
Servidor: https://nube.uo.edu.cu
Modo: Stealth (simula cliente oficial)
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
from urllib.parse import urljoin
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================================
# CONFIGURACIÓN PRINCIPAL
# ================================
TELEGRAM_TOKEN = '8221776242:AAG_FzrirAxdM4EXfM5ctiQuazyFMyWKmsU'  # ⬅️ REEMPLAZA CON TU TOKEN
NEXTCLOUD_URL = 'https://nube.uo.edu.cu'
NEXTCLOUD_USER = 'eric.serrano'
NEXTCLOUD_PASSWORD = 'Rulebreaker2316'

# Carpetas en Nextcloud (se crearán si es posible)
CARPETAS = [
    '/Telegram_Bot',
    '/Telegram_Bot/Documentos',
    '/Telegram_Bot/Imagenes', 
    '/Telegram_Bot/Audio',
    '/Telegram_Bot/Video',
    '/Telegram_Bot/Otros'
]

# ================================
# CONFIGURACIÓN DE LOGGING
# ================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_nextcloud_uo.log')
    ]
)
logger = logging.getLogger(__name__)

# ================================
# CLIENTE STEALTH - SIMULA CLIENTE OFICIAL
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
        
        # Sesión persistente
        self.session = requests.Session()
        self.session.verify = False  # Solo si hay problemas SSL
        
        # Headers que imitan cliente oficial
        self.update_headers()
        
        # Estado
        self.csrf_token = None
        self.logged_in = False
        self.last_request = 0
        self.request_delay = 1.0  # Delay entre requests
    
    def update_headers(self):
        """Actualiza headers con User-Agent aleatorio"""
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es, en-US;q=0.9, en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(headers)
    
    def _rate_limit(self):
        """Respeta rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request = time.time()
    
    def login(self):
        """Intenta iniciar sesión de diferentes formas"""
        login_methods = [
            self._login_via_web,
            self._login_via_ajax,
            self._login_via_api,
        ]
        
        for method in login_methods:
            try:
                logger.info(f"🔐 Probando login: {method.__name__}")
                if method():
                    self.logged_in = True
                    logger.info("✅ Login exitoso")
                    return True
            except Exception as e:
                logger.warning(f"⚠️ {method.__name__} falló: {e}")
        
        logger.error("❌ Todos los métodos de login fallaron")
        return False
    
    def _login_via_web(self):
        """Login vía formulario web"""
        self._rate_limit()
        
        # 1. Obtener página de login
        login_url = f"{self.base_url}/login"
        response = self.session.get(login_url, timeout=10)
        
        if response.status_code != 200:
            return False
        
        # 2. Extraer token CSRF si existe
        if 'data-requesttoken' in response.text:
            import re
            match = re.search(r'data-requesttoken="([^"]+)"', response.text)
            if match:
                self.csrf_token = match.group(1)
                self.session.headers['requesttoken'] = self.csrf_token
        
        # 3. Enviar credenciales
        login_data = {
            'user': self.username,
            'password': self.password,
            'timezone': 'America/Havana',
        }
        
        self._rate_limit()
        response = self.session.post(
            f"{self.base_url}/login",
            data=login_data,
            timeout=15,
            allow_redirects=True
        )
        
        return response.status_code == 200 and self.username in response.text
    
    def _login_via_ajax(self):
        """Login vía API AJAX"""
        self._rate_limit()
        
        ajax_url = f"{self.base_url}/index.php/login"
        ajax_data = {
            'user': self.username,
            'password': self.password,
            'remember_login': '1'
        }
        
        response = self.session.post(
            ajax_url,
            data=ajax_data,
            timeout=10,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        return response.status_code == 200
    
    def _login_via_api(self):
        """Login vía OCS API"""
        self._rate_limit()
        
        api_url = f"{self.base_url}/ocs/v2.php/cloud/user"
        response = self.session.get(
            api_url,
            auth=(self.username, self.password),
            headers={'OCS-APIRequest': 'true'},
            timeout=10
        )
        
        return response.status_code == 200
    
    def create_folder(self, folder_path):
        """Crea carpeta si no existe"""
        try:
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path
            
            webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}{folder_path}"
            
            self._rate_limit()
            response = self.session.request(
                'MKCOL',
                webdav_url,
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code in [201, 405, 409]:
                logger.info(f"📁 Carpeta {folder_path} lista")
                return True
            else:
                logger.warning(f"⚠️ No se pudo crear {folder_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creando carpeta: {e}")
            return False
    
    def upload_file(self, file_path, remote_filename):
        """Sube archivo usando múltiples métodos"""
        upload_methods = [
            self._upload_via_webdav,
            self._upload_via_webui,
            self._upload_via_ocs,
            self._upload_via_direct,
        ]
        
        for method in upload_methods:
            try:
                logger.info(f"⬆️ Probando método: {method.__name__}")
                success, message = method(file_path, remote_filename)
                if success:
                    return True, message
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"⚠️ {method.__name__} error: {e}")
        
        return False, "❌ Todos los métodos de subida fallaron"
    
    def _upload_via_webdav(self, file_path, remote_filename):
        """WebDAV estándar"""
        webdav_url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
        
        # Headers específicos de WebDAV
        headers = {
            'Content-Type': 'application/octet-stream',
            'OC-Checksum': self._calculate_checksum(file_path),
        }
        
        with open(file_path, 'rb') as f:
            self._rate_limit()
            response = self.session.put(
                webdav_url,
                data=f,
                headers=headers,
                auth=(self.username, self.password),
                timeout=30
            )
        
        if response.status_code in [201, 204]:
            return True, f"✅ WebDAV: {remote_filename}"
        return False, f"❌ WebDAV {response.status_code}"
    
    def _upload_via_webui(self, file_path, remote_filename):
        """Simula subida vía interfaz web"""
        upload_url = f"{self.base_url}/apps/files/ajax/upload.php"
        
        with open(file_path, 'rb') as f:
            files = {'files[]': (remote_filename, f, 'application/octet-stream')}
            
            params = {
                'dir': '/',
                'requesttoken': self.csrf_token or ''
            }
            
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': self.csrf_token or '',
            }
            
            self._rate_limit()
            response = self.session.post(
                upload_url,
                files=files,
                data=params,
                headers=headers,
                timeout=30
            )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'success':
                    return True, f"✅ WebUI: {remote_filename}"
            except:
                if 'success' in response.text.lower():
                    return True, f"✅ WebUI: {remote_filename}"
        
        return False, f"❌ WebUI {response.status_code}"
    
    def _upload_via_ocs(self, file_path, remote_filename):
        """Usa OCS API"""
        ocs_url = f"{self.base_url}/ocs/v2.php/apps/files/api/v1/upload"
        
        with open(file_path, 'rb') as f:
            files = {'file': (remote_filename, f)}
            
            headers = {
                'OCS-APIRequest': 'true',
                'Content-Type': 'multipart/form-data',
            }
            
            params = {
                'path': '/',
                'override': 'true'
            }
            
            self._rate_limit()
            response = self.session.post(
                ocs_url,
                files=files,
                params=params,
                headers=headers,
                auth=(self.username, self.password),
                timeout=30
            )
        
        if response.status_code == 200:
            return True, f"✅ OCS API: {remote_filename}"
        return False, f"❌ OCS {response.status_code}"
    
    def _upload_via_direct(self, file_path, remote_filename):
        """PUT directo con headers mínimos"""
        direct_url = f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_filename}"
        
        with open(file_path, 'rb') as f:
            self._rate_limit()
            response = requests.put(
                direct_url,
                data=f,
                auth=(self.username, self.password),
                timeout=30,
                headers={'User-Agent': 'nextcloud-cmd/1.0'}
            )
        
        if response.status_code in [201, 204]:
            return True, f"✅ Direct PUT: {remote_filename}"
        return False, f"❌ Direct {response.status_code}"
    
    def _calculate_checksum(self, file_path):
        """Calcula checksum MD5 para OC-Checksum"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return f"MD5:{hasher.hexdigest()}"
    
    def get_remote_path(self, filename, file_type='document'):
        """Determina ruta remota basado en tipo de archivo"""
        ext = Path(filename).suffix.lower()
        
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
        
        # Añadir timestamp para evitar duplicados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_no_ext = Path(filename).stem
        ext = Path(filename).suffix
        final_name = f"{timestamp}_{name_no_ext}{ext}"
        
        return f"{folder}/{final_name}"
    
    def test_connection(self):
        """Prueba conexión al servidor"""
        test_endpoints = [
            f"{self.base_url}/status.php",
            f"{self.base_url}/index.php",
            f"{self.base_url}/ocs/v1.php/cloud/capabilities",
        ]
        
        for endpoint in test_endpoints:
            try:
                self._rate_limit()
                response = self.session.get(
                    endpoint,
                    timeout=10,
                    auth=(self.username, self.password) if 'ocs' in endpoint else None
                )
                
                logger.info(f"📍 {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    return True, f"✅ Conectado a Nextcloud UO"
                    
            except Exception as e:
                logger.warning(f"⚠️ {endpoint}: {e}")
        
        return False, "❌ No se pudo conectar al servidor"

# ================================
# MANEJADORES DE TELEGRAM
# ================================
class TelegramBotHandler:
    """Maneja la interacción con Telegram"""
    
    def __init__(self):
        self.nc_client = NextcloudStealthClient()
        self.user_states = {}
        
        # Inicializar cliente Nextcloud
        self._initialize_nextcloud()
    
    def _initialize_nextcloud(self):
        """Inicializa conexión con Nextcloud"""
        logger.info("🚀 Inicializando Bot Nextcloud UO...")
        logger.info(f"🔗 Servidor: {NEXTCLOUD_URL}")
        logger.info(f"👤 Usuario: {NEXTCLOUD_USER}")
        
        # Probar conexión
        success, msg = self.nc_client.test_connection()
        logger.info(f"📡 {msg}")
        
        if success:
            # Intentar login
            if self.nc_client.login():
                # Crear estructura de carpetas
                self._create_folder_structure()
            else:
                logger.warning("⚠️ Login no requerido o falló, continuando...")
        else:
            logger.warning("⚠️ Conexión limitada, intentando métodos alternativos")
    
    def _create_folder_structure(self):
        """Crea estructura de carpetas en Nextcloud"""
        logger.info("📁 Creando estructura de carpetas...")
        for folder in CARPETAS:
            self.nc_client.create_folder(folder)
        logger.info("✅ Estructura de carpetas lista")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user = update.effective_user
        
        welcome_text = f"""
🤖 *Bot Nextcloud UO - Universidad de Oriente*

¡Hola {user.first_name}! 👋

*Servidor:* `{NEXTCLOUD_URL}`
*Usuario:* `{NEXTCLOUD_USER}`

*¿Cómo funciona?*
1. Envíame cualquier archivo (documento, imagen, audio, video)
2. Lo subiré automáticamente a tu Nextcloud UO
3. Se organizará en carpetas según el tipo

*Comandos disponibles:*
/start - Muestra este mensaje
/status - Verifica conexión
/help - Ayuda y soporte
/test - Prueba de subida
/carpetas - Muestra estructura

*📁 Carpetas creadas:*
• Documentos (PDF, Word, etc.)
• Imagenes (JPG, PNG, etc.)
• Audio (MP3, WAV, etc.)
• Video (MP4, AVI, etc.)
• Otros (cualquier formato)

⚠️ *Nota:* Este bot simula ser cliente oficial para evitar bloqueos.
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
        # Probar conexión en segundo plano
        success, msg = self.nc_client.test_connection()
        if not success:
            await update.message.reply_text(f"⚠️ {msg}")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        await update.message.reply_text("🔍 Verificando estado...")
        
        # Probar conexión
        success, msg = self.nc_client.test_connection()
        
        status_text = f"""
*Estado del Sistema*

{msg}

*Detalles:*
• Servidor: `{NEXTCLOUD_URL}`
• Usuario: `{NEXTCLOUD_USER}`
• Conectado: {'✅ Sí' if success else '❌ No'}
• Login: {'✅ Activo' if self.nc_client.logged_in else '⚠️ Limitado'}
• Método: Modo Stealth (cliente simulado)
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def handle_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /test - Prueba de subida"""
        await update.message.reply_text("🧪 Creando archivo de prueba...")
        
        # Crear archivo de prueba
        test_content = f"""Archivo de prueba - Bot Nextcloud UO
Fecha: {datetime.now()}
Usuario: {NEXTCLOUD_USER}
Servidor: {NEXTCLOUD_URL}

Este archivo fue generado automáticamente por el bot de Telegram.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
            tmp.write(test_content)
            temp_path = tmp.name
        
        try:
            # Subir archivo
            remote_name = f"prueba_bot_{datetime.now().strftime('%H%M%S')}.txt"
            remote_path = self.nc_client.get_remote_path(remote_name)
            
            await update.message.reply_text("📤 Subiendo archivo de prueba...")
            
            success, message = self.nc_client.upload_file(temp_path, remote_path)
            
            if success:
                result_text = f"""
✅ *Prueba exitosa!*

{message}

*Puedes verificar en:*
`{NEXTCLOUD_URL}/apps/files/?dir=/Telegram_Bot/Documentos`

*Siguientes pasos:*
1. Envía un archivo real para probar
2. Verifica que aparezca en tu Nextcloud
3. Usa /help si tienes problemas
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
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        help_text = """
*🆘 Ayuda y Soporte*

*Problemas comunes:*

1. *Error 403 - Acceso denegado*
   El servidor UO bloquea acceso automático.
   *Solución:* El bot usa modo "stealth" para evitarlo.

2. *Archivo no aparece en Nextcloud*
   • Verifica tu conexión a internet
   • Revisa la carpeta correcta en Nextcloud
   • Espera unos segundos (puede haber delay)

3. *Bot no responde*
   • Usa /status para verificar conexión
   • Reinicia el bot si es necesario
   • Contacta al desarrollador

*Formatos soportados:*
• Documentos: PDF, DOC, DOCX, TXT, XLS, PPT, etc.
• Imágenes: JPG, PNG, GIF, BMP, WEBP, SVG
• Audio: MP3, WAV, OGG, FLAC, M4A
• Video: MP4, AVI, MKV, MOV, WMV
• Otros: Cualquier tipo de archivo

*Soporte técnico:*
Para problemas específicos de la UO, contacta al departamento de TI.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_carpetas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /carpetas"""
        carpetas_text = """
*📁 Estructura de carpetas*

El bot organiza los archivos en:

*`/Telegram_Bot/`*
├── 📄 *Documentos/*
│   └── PDF, Word, Excel, PowerPoint, texto
├── 🖼️ *Imagenes/*
│   └── JPG, PNG, GIF, BMP, WEBP
├── 🎵 *Audio/*
│   └── MP3, WAV, OGG, FLAC
├── 🎬 *Video/*
│   └── MP4, AVI, MKV, MOV
└── 📦 *Otros/*
    └── Cualquier otro formato

*Los archivos se renombran automáticamente:*
`AAAAMMDD_HHMMSS_nombre_original.ext`

Esto evita duplicados y organiza por fecha.
        """
        
        await update.message.reply_text(carpetas_text, parse_mode='Markdown')
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja documentos"""
        await self._handle_any_file(update, update.message.document, "📄 Documento")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja fotos"""
        await self._handle_any_file(update, update.message.photo[-1], "🖼️ Imagen")
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja audio"""
        await self._handle_any_file(update, update.message.audio, "🎵 Audio")
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja video"""
        await self._handle_any_file(update, update.message.video, "🎬 Video")
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de voz"""
        await self._handle_any_file(update, update.message.voice, "🎤 Audio de voz")
    
    async def _handle_any_file(self, update: Update, file_obj, file_type):
        """Maneja cualquier tipo de archivo"""
        try:
            # Obtener información del archivo
            if hasattr(file_obj, 'file_name') and file_obj.file_name:
                original_name = file_obj.file_name
            else:
                original_name = f"{file_type.lower().replace(' ', '_')}_{file_obj.file_id}"
            
            file_size = file_obj.file_size or 0
            file_size_mb = file_size / (1024 * 1024)
            
            # Enviar mensaje inicial
            status_msg = await update.message.reply_text(
                f"{file_type}\n"
                f"📝 *{original_name}*\n"
                f"📏 Tamaño: {file_size_mb:.2f} MB\n"
                f"⏳ Descargando...",
                parse_mode='Markdown'
            )
            
            # Descargar archivo
            telegram_file = await file_obj.get_file()
            
            # Crear archivo temporal con extensión correcta
            file_ext = Path(original_name).suffix or self._get_extension_by_type(file_type)
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                temp_path = tmp.name
                await telegram_file.download_to_drive(temp_path)
            
            # Actualizar mensaje
            await status_msg.edit_text(
                f"{file_type}\n"
                f"📝 *{original_name}*\n"
                f"✅ Descargado\n"
                f"📤 Subiendo a Nextcloud UO...",
                parse_mode='Markdown'
            )
            
            # Determinar ruta remota
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

*Puedes acceder en:*
`{NEXTCLOUD_URL}/apps/files/?dir={Path(remote_path).parent}`

*Detalles:*
• Tipo: {file_type}
• Original: `{original_name}`
• Servidor: Nextcloud UO
                """
                await status_msg.edit_text(result_text, parse_mode='Markdown')
            else:
                error_text = f"""
❌ *Error en la subida*

*Archivo:* {original_name}
*Error:* {message}

*Posibles soluciones:*
1. Verifica tu conexión a internet
2. Intenta con otro archivo
3. Usa /status para verificar el servidor
4. Contacta soporte si persiste
                """
                await status_msg.edit_text(error_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error procesando archivo: {e}")
            error_msg = f"❌ *Error crítico*\n\n{str(e)[:200]}"
            if update.message:
                await update.message.reply_text(error_msg, parse_mode='Markdown')
    
    def _get_extension_by_type(self, file_type):
        """Obtiene extensión por tipo de archivo"""
        extensions = {
            "📄 Documento": ".bin",
            "🖼️ Imagen": ".jpg",
            "🎵 Audio": ".mp3",
            "🎬 Video": ".mp4",
            "🎤 Audio de voz": ".ogg",
        }
        return extensions.get(file_type, ".bin")
    
    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes desconocidos"""
        await update.message.reply_text(
            "🤔 No entiendo ese comando.\n\n"
            "Envía un archivo o usa:\n"
            "/start - Inicio\n"
            "/help - Ayuda\n"
            "/status - Verificar conexión"
        )

# ================================
# APLICACIÓN PRINCIPAL
# ================================
class NextcloudUOBot:
    """Aplicación principal del bot"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.handler = TelegramBotHandler()
        
    async def run(self):
        """Ejecuta el bot"""
        # Verificar token
        if self.token == 'TU_TOKEN_AQUI':
            print("\n" + "="*60)
            print("❌ ERROR: Token de Telegram no configurado")
            print("="*60)
            print("\nPasos para configurar:")
            print("1. Busca @BotFather en Telegram")
            print("2. Crea un nuevo bot con /newbot")
            print("3. Copia el token que te dé")
            print("4. Reemplaza 'TU_TOKEN_AQUI' en el código")
            print("\nEjemplo: TELEGRAM_TOKEN = '123456:ABCdefGHIjklMnOpQRsTUVwxyz'")
            print("="*60)
            return
        
        # Crear aplicación de Telegram
        application = Application.builder().token(self.token).build()
        
        # Registrar handlers
        application.add_handler(CommandHandler("start", self.handler.handle_start))
        application.add_handler(CommandHandler("status", self.handler.handle_status))
        application.add_handler(CommandHandler("test", self.handler.handle_test))
        application.add_handler(CommandHandler("help", self.handler.handle_help))
        application.add_handler(CommandHandler("carpetas", self.handler.handle_carpetas))
        
        # Handlers de archivos
        application.add_handler(MessageHandler(filters.Document.ALL, self.handler.handle_document))
        application.add_handler(MessageHandler(filters.PHOTO, self.handler.handle_photo))
        application.add_handler(MessageHandler(filters.AUDIO, self.handler.handle_audio))
        application.add_handler(MessageHandler(filters.VIDEO, self.handler.handle_video))
        application.add_handler(MessageHandler(filters.VOICE, self.handler.handle_voice))
        
        # Handler por defecto
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handler.handle_unknown))
        
        # Error handler
        application.add_error_handler(self._error_handler)
        
        # Banner de inicio
        self._print_banner()
        
        # Iniciar bot
        print("✅ Bot configurado correctamente")
        print("📱 Envía /start a tu bot en Telegram para comenzar")
        print("\n" + "="*60)
        
        await application.run_polling()
    
    def _print_banner(self):
        """Imprime banner de inicio"""
        print("\n" + "="*60)
        print("🤖 BOT NEXTCLOUD UO - UNIVERSIDAD DE ORIENTE")
        print("="*60)
        print(f"🔗 Servidor: {NEXTCLOUD_URL}")
        print(f"👤 Usuario: {NEXTCLOUD_USER}")
        print(f"🤫 Modo: Stealth (cliente oficial simulado)")
        print("="*60)
        
        # Probar conexión inicial
        print("\n🔍 Probando conexión al servidor...")
        success, msg = self.handler.nc_client.test_connection()
        print(f"📡 {msg}")
        
        if success and self.handler.nc_client.login():
            print("✅ Login simulado exitoso")
        else:
            print("⚠️ Login limitado, usando métodos alternativos")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja errores globales"""
        logger.error(f"Error: {context.error}")
        
        try:
            if update and update.message:
                await update.message.reply_text(
                    "❌ Ocurrió un error inesperado.\n\n"
                    "Por favor, intenta nuevamente o usa /help para soporte."
                )
        except:
            pass

# ================================
# FUNCIÓN DE PRUEBA DIRECTA
# ================================
def prueba_directa_nextcloud():
    """Prueba directa sin Telegram"""
    print("\n" + "="*60)
    print("🧪 PRUEBA DIRECTA - NEXTCLOUD UO")
    print("="*60)
    
    client = NextcloudStealthClient()
    
    # 1. Probar conexión
    print("\n1. 🔍 Probando conexión...")
    success, msg = client.test_connection()
    print(f"   {msg}")
    
    if not success:
        print("\n❌ No se pudo conectar al servidor")
        print("   Posibles causas:")
        print("   • Credenciales incorrectas")
        print("   • Servidor bloquea acceso automático")
        print("   • Problemas de red")
        return
    
    # 2. Probar login
    print("\n2. 🔐 Probando login...")
    if client.login():
        print("   ✅ Login simulado exitoso")
    else:
        print("   ⚠️ Login falló, continuando con acceso básico")
    
    # 3. Crear archivo de prueba
    print("\n3. 📝 Creando archivo de prueba...")
    test_content = f"""Prueba Bot Nextcloud UO
Fecha: {datetime.now()}
Usuario: {NEXTCLOUD_USER}
Servidor: {NEXTCLOUD_URL}
    
Este es un archivo de prueba generado automáticamente.
"""
    
    test_file = "prueba_directa.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print(f"   ✅ Archivo creado: {test_file}")
    
    # 4. Subir archivo
    print("\n4. ⬆️ Subiendo archivo...")
    remote_path = client.get_remote_path(test_file)
    print(f"   📍 Ruta remota: {remote_path}")
    
    success, message = client.upload_file(test_file, remote_path)
    print(f"   📊 Resultado: {message}")
    
    # 5. Limpiar
    if os.path.exists(test_file):
        os.unlink(test_file)
    
    # 6. Resultado final
    print("\n" + "="*60)
    if success:
        print("🎉 ¡PRUEBA EXITOSA!")
        print(f"📁 Archivo subido a: {remote_path}")
        print(f"🔗 Accede en: {NEXTCLOUD_URL}")
    else:
        print("❌ PRUEBA FALLIDA")
        print("\nPosibles soluciones:")
        print("1. Verifica que las credenciales sean correctas")
        print("2. El servidor UO podría bloquear acceso automático")
        print("3. Contacta al departamento de TI de la UO")
        print("4. Usa el cliente desktop de Nextcloud como alternativa")
    print("="*60)

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == '__main__':
    import sys
    
    # Verificar si es prueba directa
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        prueba_directa_nextcloud()
    else:
        # Ejecutar bot normal
        bot = NextcloudUOBot()
        
        try:
            # Para Python 3.7+
            if hasattr(asyncio, 'run'):
                asyncio.run(bot.run())
            else:
                # Para versiones anteriores
                loop = asyncio.get_event_loop()
                loop.run_until_complete(bot.run())
                
        except KeyboardInterrupt:
            print("\n\n👋 Bot detenido por el usuario")
        except Exception as e:
            logger.error(f"Error fatal: {e}")
            print(f"\n❌ Error fatal: {e}")
            print("Revisa el archivo bot_nextcloud_uo.log para más detalles")
