"""Symmetric encryption for secrets at rest (3X-UI panel passwords)."""
from cryptography.fernet import Fernet

from app.core.config import get_settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_settings().encryption_key
        if not key:
            raise RuntimeError("ENCRYPTION_KEY is not set")
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def reset_crypto() -> None:
    """Used by tests when the key changes."""
    global _fernet
    _fernet = None
