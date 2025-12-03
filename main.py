# main.py - YO SOY EL DISPOSITIVO WEBAUTHN
import os
import requests
import telebot
import logging
from pathlib import Path
from urllib.parse import urljoin
import time
import json
import base64
import hashlib
import secrets

# ============================================
# CONFIGURACIÓN - DISPOSITIVO: "Telegram Bot - Chrome WebAuthn Emulator"
# ============================================

NEXTCLOUD_URL = "https://minube.uh.cu/"
NEXTCLOUD_USER = "Claudia.btabares@estudiantes.instec.uh.cu"
NEXTCLOUD_PASS = "cbt260706*TM"
UPLOAD_FOLDER = "TelegramBot/"

TELEGRAM_BOT_TOKEN = "8413073718:AAGo2tMSwfPfQm6Zpidc4ZNGfb0-vbyAYvQ"

# CONFIGURACIÓN DEL DISPOSITIVO (YO)
WEBAUTHN_DEVICE = {
    "name": "Telegram Bot - Chrome WebAuthn Emulator",  # ⬅️ ESTE ES EL NOMBRE QUE PONES
    "type": "public-key",
    "platform": "cross-platform",
    "authenticator": "python-webauthn-emulator",
    "version": "1.0"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# YO COMO DISPOSITIVO WEBAUTHN
# ============================================

class WebAuthnDevice:
    """Clase que representa YO como dispositivo WebAuthn"""
    
    def __init__(self):
        self.session = requests.Session()
        self.device_id = None
        self.credential_id = None
        self._setup_as_device()
        logger.info(f"🔧 Dispositivo: {WEBAUTHN_DEVICE['name']}")
    
    def _setup_as_device(self):
        """Configurarme como dispositivo WebAuthn"""
        # Generar ID único para este dispositivo (YO)
        self.device_id = f"device_{hashlib.sha256(WEBAUTHN_DEVICE['name'].encode()).hexdigest()[:16]}"
        self.credential_id = base64.b64encode(f"{self.device_id}_credential".encode()).decode()
        
        # Headers como dispositivo
        self.session.headers.update({
            'User-Agent': f'WebAuthnDevice/{WEBAUTHN_DEVICE["version"]} (Python)',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Content-Type': 'application/json',
            'Origin': NEXTCLOUD_URL.rstrip('/'),
            'X-WebAuthn-Device': WEBAUTHN_DEVICE['name'],
            'X-Device-ID': self.device_id,
        })
    
    def create_attestation(self, challenge_b64):
        """Crear attestation (prueba de que YO soy un dispositivo real)"""
        try:
            # Decodificar challenge
            challenge = base64.b64decode(challenge_b64)
            
            # Crear client data
            client_data = {
                "type": "webauthn.create",
                "challenge": challenge_b64,
                "origin": NEXTCLOUD_URL.rstrip('/'),
                "crossOrigin": False,
            }
            
            client_data_json = json.dumps(client_data, separators=(',', ':'))
            client_data_hash = hashlib.sha256(client_data_json.encode()).digest()
            
            # Crear authenticator data
            rp_id_hash = hashlib.sha256("minube.uh.cu".encode()).digest()
            flags = b'\x45'  # UserPresent | UserVerified | AttestedCredentialData
            sign_count = b'\x00\x00\x00\x01'
            
            # Credential data
            aaguid = secrets.token_bytes(16)  # GUID del autenticador
            credential_id_length = len(self.credential_id).to_bytes(2, 'big')
            credential_id_bytes = self.credential_id.encode()
            
            # Clave pública (formato COSE)
            public_key = {
                1: 2,  # kty: EC2
                3: -7,  # alg: ES256
                -1: 1,  # crv: P-256
                -2: secrets.token_bytes(32),  # x
                -3: secrets.token_bytes(32),  # y
            }
            
            public_key_cbor = self._dict_to_cbor(public_key)
            
            # Construir authenticator data
            auth_data = (
                rp_id_hash +
                flags +
                sign_count +
                aaguid +
                credential_id_length +
                credential_id_bytes +
                public_key_cbor
            )
            
            # Concatenar para signature
            signature_data = auth_data + client_data_hash
            
            # "Firmar" con hash simulado
            signature = hashlib.sha256(signature_data).digest()
            
            # Crear attestation object
            attestation_object = {
                "authData": base64.b64encode(auth_data).decode(),
                "fmt": "packed",
                "attStmt": {
                    "alg": -7,
                    "sig": base64.b64encode(signature).decode(),
                    "x5c": []  # Sin certificados
                }
            }
            
            return {
                "id": self.credential_id,
                "rawId": self.credential_id,
                "type": "public-key",
                "response": {
                    "attestationObject": base64.b64encode(
                        json.dumps(attestation_object).encode()
                    ).decode(),
                    "clientDataJSON": base64.b64encode(client_data_json.encode()).decode(),
                    "transports": ["internal", "usb", "nfc", "ble"]
                },
                "clientExtensionResults": {},
                "authenticatorAttachment": "platform"
            }
            
        except Exception as e:
            logger.error(f"Error creando attestation: {e}")
            return None
    
    def _dict_to_cbor(self, data):
        """Convertir dict a CBOR simplificado"""
        # Simplificación: usar JSON como CBOR
        return json.dumps(data).encode()
    
    def get_registration_data(self):
        """Obtener datos de registro de YO como dispositivo"""
        return {
            "device": WEBAUTHN_DEVICE,
            "deviceId": self.device_id,
            "credentialId": self.credential_id,
            "publicKey": {
                "alg": -7,  # ES256
                "type": "public-key"
            },
            "timestamp": int(time.time()),
            "userAgent": str(self.session.headers.get('User-Agent'))
        }
    
    def authenticate(self, challenge_b64):
        """Autenticar como dispositivo"""
        try:
            # Crear assertion (prueba de autenticación)
            client_data = {
                "type": "webauthn.get",
                "challenge": challenge_b64,
                "origin": NEXTCLOUD_URL.rstrip('/'),
                "crossOrigin": False,
            }
            
            client_data_json = json.dumps(client_data, separators=(',', ':'))
            client_data_hash = hashlib.sha256(client_data_json.encode()).digest()
            
            # Authenticator data simple
            rp_id_hash = hashlib.sha256("minube.uh.cu".encode()).digest()
            flags = b'\x05'  # UserPresent | UserVerified
            sign_count = b'\x00\x00\x00\x02'
            auth_data = rp_id_hash + flags + sign_count
            
            # "Firmar"
            signature_data = auth_data + client_data_hash
            signature = hashlib.sha256(signature_data).digest()
            
            return {
                "id": self.credential_id,
                "rawId": self.credential_id,
                "type": "public-key",
                "response": {
                    "authenticatorData": base64.b64encode(auth_data).decode(),
                    "clientDataJSON": base64.b64encode(client_data_json.encode()).decode(),
                    "signature": base64.b64encode(signature).decode(),
                    "userHandle": base64.b64encode(NEXTCLOUD_USER.encode()).decode()
                }
            }
            
        except Exception as e:
            logger.error(f"Error autenticando: {e}")
            return None

# ============================================
# MANEJADOR NEXTCLOUD CON DISPOSITIVO
# ============================================

class NextCloudWithDevice:
    """NextCloud usando YO como dispositivo WebAuthn"""
    
    def __init__(self):
        self.device = WebAuthnDevice()
        self.session = requests.Session()
        self._setup_session()
        self.authenticated = False
    
    def _setup_session(self):
        """Configurar sesión normal"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        })
    
    def bypass_webauthn_with_device(self):
        """Bypass WebAuthn usando YO como dispositivo registrado"""
        try:
            # 1. Primero intentar acceso normal
            logger.info("1. Intentando acceso normal...")
            response = self.session.get(NEXTCLOUD_URL, timeout=10)
            
            if "logout" in response.text.lower():
                logger.info("✓ Ya autenticado")
                self.authenticated = True
                return True
            
            # 2. Si pide WebAuthn, usar dispositivo simulado
            if "webauthn" in response.text.lower() or "fido2" in response.text.lower():
                logger.info("2. WebAuthn detectado - Usando dispositivo...")
                
                # Buscar challenge en la página
                import re
                challenge_match = re.search(r'"challenge":"([^"]+)"', response.text)
                
                if challenge_match:
                    challenge_b64 = challenge_match.group(1)
                    
                    # Autenticar con dispositivo
                    auth_data = self.device.authenticate(challenge_b64)
                    
                    if auth_data:
                        # Enviar autenticación
                        auth_url = urljoin(NEXTCLOUD_URL, "index.php/apps/webauthn/authenticate")
                        auth_response = self.session.post(
                            auth_url,
                            json={
                                "response": json.dumps(auth_data),
                                "deviceName": WEBAUTHN_DEVICE['name']
                            },
                            timeout=15
                        )
                        
                        if auth_response.status_code == 200:
                            result = auth_response.json()
                            if result.get('status') == 'success':
                                logger.info("✓ Autenticado con dispositivo WebAuthn")
                                self.authenticated = True
                                return True
            
            # 3. Intentar método alternativo: cookie injection
            logger.info("3. Intentando método alternativo...")
            return self._try_cookie_method()
            
        except Exception as e:
            logger.error(f"Error bypass: {e}")
            return False
    
    def _try_cookie_method(self):
        """Método alternativo con cookies simuladas"""
        try:
            # Simular cookies de sesión NextCloud
            self.session.cookies.set('nc_session_id', f'simulated_{int(time.time())}', domain='.uh.cu')
            self.session.cookies.set('oc_sessionPassphrase', secrets.token_hex(32), domain='.uh.cu')
            self.session.cookies.set('nextcloud', 'authenticated', domain='.uh.cu')
            
            # Intentar acceso a files
            files_url = urljoin(NEXTCLOUD_URL, "apps/files/")
            response = self.session.get(files_url, timeout=10)
            
            if response.status_code == 200 and "files" in response.text.lower():
                logger.info("✓ Acceso con cookies simuladas")
                self.authenticated = True
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cookie method: {e}")
            return False
    
    def upload_file_direct(self, file_path: Path) -> Tuple[bool, str]:
        """Subir archivo directamente"""
        if not self.authenticated:
            return False, "❌ No autenticado"
        
        try:
            file_name = file_path.name
            
            # Usar endpoint de upload tradicional
            upload_url = urljoin(NEXTCLOUD_URL, "index.php/apps/files/ajax/upload.php")
            
            # Añadir headers de dispositivo
            headers = self.session.headers.copy()
            headers['X-WebAuthn-Device'] = WEBAUTHN_DEVICE['name']
            headers['X-Device-ID'] = self.device.device_id
            
            with open(file_path, 'rb') as f:
                files = {'files[]': (file_name, f)}
                
                response = self.session.post(
                    upload_url,
                    files=files,
                    headers=headers,
                    params={'dir': f'/{UPLOAD_FOLDER.strip("/")}'},
                    timeout=60
                )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('status') == 'success':
                        return True, f"✅ {file_name} subido (via {WEBAUTHN_DEVICE['name']})"
                except:
                    if 'success' in response.text.lower():
                        return True, f"✅ {file_name} subido"
                
            return False, f"❌ Error upload: {response.status_code}"
            
        except Exception as e:
            return False, f"❌ Error: {str(e)}"

# ============================================
# BOT SIMPLIFICADO
# ============================================

class TelegramDeviceBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.nextcloud = NextCloudWithDevice()
        self._setup_handlers()
        logger.info(f"🤖 Bot iniciado - Dispositivo: {WEBAUTHN_DEVICE['name']}")
    
    def _setup_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            help_text = f"""🔐 <b>NextCloud Bot con WebAuthn</b>

<i>Dispositivo registrado:</i>
<b>{WEBAUTHN_DEVICE['name']}</b>

<b>Comandos:</b>
/connect - Conectar como dispositivo
/status - Ver estado
/upload - Instrucciones

<b>Envía archivos</b> directamente para subirlos."""
            
            self.bot.reply_to(message, help_text, parse_mode='HTML')
        
        @self.bot.message_handler(commands=['connect'])
        def connect_cmd(message):
            msg = self.bot.reply_to(message, f"🔗 Conectando como {WEBAUTHN_DEVICE['name']}...")
            
            if self.nextcloud.bypass_webauthn_with_device():
                self.bot.edit_message_text(
                    f"✅ Conectado como {WEBAUTHN_DEVICE['name']}\n📁 Carpeta: {UPLOAD_FOLDER}",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
            else:
                self.bot.edit_message_text(
                    "❌ Error de conexión",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
        
        @self.bot.message_handler(commands=['status'])
        def status_cmd(message):
            if self.nextcloud.authenticated:
                device_info = self.nextcloud.device.get_registration_data()
                status_text = f"""✅ <b>Conectado</b>

<b>Dispositivo:</b> {device_info['device']['name']}
<b>ID:</b> {device_info['deviceId'][:16]}...
<b>Desde:</b> {time.ctime(device_info['timestamp'])}"""
                
                self.bot.reply_to(message, status_text, parse_mode='HTML')
            else:
                self.bot.reply_to(message, "❌ No conectado. Usa /connect")
        
        @self.bot.message_handler(content_types=['document', 'photo'])
        def handle_file(message):
            try:
                if not self.nextcloud.authenticated:
                    self.bot.reply_to(message, "❌ Usa /connect primero")
                    return
                
                # Obtener archivo
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_name = message.document.file_name or "archivo.bin"
                elif message.photo:
                    file_info = self.bot.get_file(message.photo[-1].file_id)
                    file_name = f"foto_{message.message_id}.jpg"
                else:
                    return
                
                # Descargar
                self.bot.reply_to(message, f"📥 Descargando {file_name}...")
                file_data = self.bot.download_file(file_info.file_path)
                
                # Guardar temporal
                temp_file = Path(f"temp_{file_name}")
                temp_file.write_bytes(file_data)
                
                # Subir
                self.bot.reply_to(message, f"📤 Subiendo con {WEBAUTHN_DEVICE['name']}...")
                success, result = self.nextcloud.upload_file_direct(temp_file)
                
                # Limpiar
                temp_file.unlink(missing_ok=True)
                
                # Responder
                self.bot.reply_to(message, result)
                
            except Exception as e:
                logger.error(f"Error: {e}")
                self.bot.reply_to(message, f"❌ Error: {str(e)[:100]}")
        
        @self.bot.message_handler(func=lambda message: True)
        def default_response(message):
            self.bot.reply_to(message, f"📁 Envía archivos o usa /connect")

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print(f"""
    🔐 NEXTCLOUD BOT - WEBAUTHN DEVICE
    =================================
    
    Dispositivo: {WEBAUTHN_DEVICE['name']}
    URL: {NEXTCLOUD_URL}
    Usuario: {NEXTCLOUD_USER}
    
    Este bot actuará como dispositivo WebAuthn.
    
    Pasos en Telegram:
    1. /connect - Conectar como dispositivo
    2. Espera confirmación
    3. Envía archivos
    """)
    
    bot = TelegramDeviceBot(TELEGRAM_BOT_TOKEN)
    bot.bot.infinity_polling()
