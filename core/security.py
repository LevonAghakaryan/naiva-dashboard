"""Encryption for secrets stored in the DB (Instagram access tokens)."""
from cryptography.fernet import Fernet

from core.config import settings


def _fernet() -> Fernet:
    if not settings.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY is not set in .env")
    return Fernet(settings.encryption_key.encode())


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
