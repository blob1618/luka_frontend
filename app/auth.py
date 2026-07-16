"""
auth.py — Mock token authentication for LUKA Frontend.

In production, the LUKA bot generates a signed JWT link:
  https://luka-web.onrender.com/login?token=<jwt>

For local development, any call to /dev-login will generate a
valid session so you don't need the bot running.
"""

import os
from typing import Optional

from fastapi import HTTPException, Request, status
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

load_dotenv()

# --- Configuration -----------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-dev-key-change-in-prod")
MOCK_WHATSAPP_ID = os.getenv("MOCK_WHATSAPP_ID", "5491100000000")  # stub user
SESSION_COOKIE = "luka_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

serializer = URLSafeTimedSerializer(SECRET_KEY)


def mock_auth_enabled() -> bool:
    """Keep development shortcuts unavailable outside explicit mock mode."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    enabled = os.getenv("ENABLE_MOCK_AUTH", "true").strip().lower() == "true"
    return app_env == "development" and enabled


# --- Session helpers ----------------------------------------------------------


def create_session_token(whatsapp_id: str) -> str:
    """Sign a whatsapp_id into a tamper-proof session cookie value."""
    return serializer.dumps(whatsapp_id, salt="session")


def decode_session_token(token: str) -> Optional[str]:
    """Return the whatsapp_id or None if invalid/expired."""
    try:
        return serializer.loads(token, salt="session", max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


# --- Mock JWT (stub for the bot link) ----------------------------------------


def decode_magic_link_token(token: str) -> Optional[str]:
    """
    Stub: accepts the magic token sent by the WhatsApp bot.
    For now, any non-empty token returns the MOCK_WHATSAPP_ID.
    Replace this with real JWT verification once the bot generates them.
    """
    if mock_auth_enabled() and token and len(token) > 4:
        return MOCK_WHATSAPP_ID
    return None


# --- FastAPI dependency -------------------------------------------------------


def get_current_user(request: Request) -> str:
    """
    Dependency: read the session cookie and return the whatsapp_id.
    Raises 401 if missing or invalid — caller should redirect to /login.
    """
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    whatsapp_id = decode_session_token(raw)
    if not whatsapp_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )
    return whatsapp_id
