"""Fernet encryption for secrets at rest (API keys).

The Fernet key is derived deterministically from the app's SECRET_KEY, so no
extra key-management step is needed for the local/demo deployment. Rotating
SECRET_KEY invalidates previously encrypted values (they decrypt to "").
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt *plaintext* for storage. Empty input stays empty."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    """Decrypt a stored value. Returns "" when the token is empty or invalid
    (e.g. SECRET_KEY changed since encryption)."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""
