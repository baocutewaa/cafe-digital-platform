from __future__ import annotations

import hashlib
import secrets

from app.core.config import settings


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(raw_token: str) -> str:
    salted = f"{settings.SESSION_TOKEN_PEPPER}:{raw_token}".encode()
    return hashlib.sha256(salted).hexdigest()
