import io
import base64

import pyotp
import qrcode

from auth.security import encrypt, decrypt


def generate_totp_secret() -> str:
    """Génère un secret TOTP aléatoire (non chiffré)."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="BankAssistant")


def generate_qr_code_base64(totp_uri: str) -> str:
    """Retourne le QR code en base64 PNG pour l'affichage dans l'IHM."""
    img = qrcode.make(totp_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp_code(encrypted_secret: str, code: str, valid_window: int = 1) -> bool:
    """Vérifie un code TOTP. Le secret en base est stocké chiffré."""
    secret = decrypt(encrypted_secret)
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)
