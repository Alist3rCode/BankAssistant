from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet = Fernet(settings.encryption_key.encode())


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def encrypt(value: str) -> str:
    """Chiffre une valeur sensible (PIN CA, clé API…) avec Fernet."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Déchiffre une valeur Fernet."""
    return _fernet.decrypt(token.encode()).decode()


def is_account_locked(locked_until: Optional[datetime]) -> bool:
    if locked_until is None:
        return False
    return datetime.now(timezone.utc) < locked_until.replace(tzinfo=timezone.utc)


def compute_lockout_until(attempts: int) -> Optional[datetime]:
    if attempts >= settings.max_login_attempts:
        return datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_duration_minutes)
    return None
