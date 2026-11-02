"""Password hashing, opaque tokens, CSRF binding and secret encryption (ADR 008)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

_hasher = PasswordHasher()  # Argon2id with library defaults (RFC 9106 low-memory profile)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        # constant-ish work to reduce user enumeration through timing
        _hasher.hash(password)
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token(nbytes: int = 32) -> str:
    """Opaque URL-safe token. Only its hash is stored."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_for_session(secret_key: str, session_token: str) -> str:
    """CSRF token bound to the session (signed double submit)."""
    return hmac.new(secret_key.encode(), b"csrf:" + session_token.encode(), "sha256").hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


class SecretBox:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str | None:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            return None


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str, issuer: str = "Handball AI") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)
