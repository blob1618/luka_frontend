import base64
import binascii
import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from urllib.parse import urlsplit

import httpx
from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.responses import Response
from supabase import ClientOptions, create_client
from supabase_auth import SyncSupportedStorage


ONBOARDING_COOKIE = "luka_onboarding"
PENDING_AUTH_COOKIE = "luka_pending_google"
SUPABASE_PKCE_COOKIE = "luka_sb_pkce"
SUPABASE_SESSION_COOKIE = "luka_sb_session"

ONBOARDING_CONTEXT_MAX_AGE = 30 * 60
PENDING_AUTH_MAX_AGE = 15 * 60
PKCE_MAX_AGE = 10 * 60
SUPABASE_SESSION_MAX_AGE = 15 * 60

_ONBOARDING_SALT = "luka-onboarding-context-v1"
_PENDING_AUTH_SALT = "luka-pending-google-auth-v1"
_COOKIE_CHUNK_SIZE = 3000
_MAX_COOKIE_CHUNKS = 8
_DEV_SECRET = "super-secret-dev-key-change-in-prod"
_PLACEHOLDER_SECRET = "change-me-to-a-random-secret-in-production"


class AuthConfigurationError(RuntimeError):
    """Raised for invalid auth configuration without exposing its contents."""


@dataclass(frozen=True)
class SupabaseAuthSettings:
    app_env: str
    app_base_url: str
    supabase_url: str
    publishable_key: str
    cookie_secure: bool

    @property
    def callback_url(self) -> str:
        return f"{self.app_base_url}/auth/callback"


@dataclass(frozen=True)
class OnboardingContext:
    invitation_id: str
    agreement_version_id: str
    raw_cookie: str


@dataclass(frozen=True)
class PendingGoogleIdentity:
    auth_user_id: str
    provider: str
    email: str
    authenticated_at: str


def _parse_bool(name: str, default: str) -> bool:
    value = os.getenv(name, default).strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise AuthConfigurationError(f"Invalid boolean setting: {name}")


def _validated_origin(name: str, value: str, *, https_required: bool) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise AuthConfigurationError(f"Invalid URL setting: {name}") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or (https_required and parsed.scheme != "https")
    ):
        raise AuthConfigurationError(f"Invalid URL setting: {name}")
    return value.rstrip("/")


def cookie_secure_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "production"}:
        raise AuthConfigurationError("Invalid APP_ENV")
    secure = _parse_bool("AUTH_COOKIE_SECURE", "false")
    if app_env == "production" and not secure:
        raise AuthConfigurationError("Secure auth cookies are required")
    return secure


def get_auth_settings() -> SupabaseAuthSettings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "production"}:
        raise AuthConfigurationError("Invalid APP_ENV")

    https_required = app_env == "production"
    app_base_url = _validated_origin(
        "APP_BASE_URL",
        os.getenv("APP_BASE_URL", ""),
        https_required=https_required,
    )
    supabase_url = _validated_origin(
        "SUPABASE_URL",
        os.getenv("SUPABASE_URL", ""),
        https_required=https_required,
    )
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not publishable_key.startswith("sb_publishable_") or len(publishable_key) < 20:
        raise AuthConfigurationError("Invalid Supabase publishable key")

    return SupabaseAuthSettings(
        app_env=app_env,
        app_base_url=app_base_url,
        supabase_url=supabase_url,
        publishable_key=publishable_key,
        cookie_secure=cookie_secure_enabled(),
    )


def _secret_key() -> str:
    secret = os.getenv("SECRET_KEY", _DEV_SECRET)
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if not secret or (
        app_env == "production"
        and (secret in {_DEV_SECRET, _PLACEHOLDER_SECRET} or len(secret) < 32)
    ):
        raise AuthConfigurationError("A production SECRET_KEY is required")
    return secret


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret_key())


def create_onboarding_context(
    invitation_id: Any,
    agreement_version_id: Any,
    invitation_expires_at: datetime,
) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_at = invitation_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    remaining = int((expires_at.astimezone(timezone.utc) - now).total_seconds())
    if remaining <= 0:
        raise ValueError("Invitation has expired")
    max_age = min(ONBOARDING_CONTEXT_MAX_AGE, remaining)
    value = _serializer().dumps(
        {"i": str(invitation_id), "a": str(agreement_version_id)},
        salt=_ONBOARDING_SALT,
    )
    return value, max_age


def load_onboarding_context(request: Request) -> Optional[OnboardingContext]:
    raw = request.cookies.get(ONBOARDING_COOKIE)
    if not raw:
        return None
    try:
        payload = _serializer().loads(
            raw,
            salt=_ONBOARDING_SALT,
            max_age=ONBOARDING_CONTEXT_MAX_AGE,
        )
        invitation_id = payload["i"]
        agreement_version_id = payload["a"]
        if not isinstance(invitation_id, str) or not isinstance(
            agreement_version_id, str
        ):
            return None
        return OnboardingContext(invitation_id, agreement_version_id, raw)
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        return None


def create_pending_auth_context(
    identity: PendingGoogleIdentity,
    onboarding_cookie: str,
) -> str:
    payload = {
        "auth_user_id": identity.auth_user_id,
        "provider": identity.provider,
        "email": identity.email,
        "authenticated_at": identity.authenticated_at,
        "onboarding_context_hash": hashlib.sha256(
            onboarding_cookie.encode("utf-8")
        ).hexdigest(),
    }
    return _serializer().dumps(payload, salt=_PENDING_AUTH_SALT)


def load_pending_auth_context(
    request: Request,
    onboarding_cookie: str,
) -> Optional[PendingGoogleIdentity]:
    raw = request.cookies.get(PENDING_AUTH_COOKIE)
    if not raw:
        return None
    try:
        payload = _serializer().loads(
            raw,
            salt=_PENDING_AUTH_SALT,
            max_age=PENDING_AUTH_MAX_AGE,
        )
        expected_hash = hashlib.sha256(onboarding_cookie.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(payload["onboarding_context_hash"], expected_hash):
            return None
        identity = PendingGoogleIdentity(
            auth_user_id=payload["auth_user_id"],
            provider=payload["provider"],
            email=payload["email"],
            authenticated_at=payload["authenticated_at"],
        )
        if identity.provider != "google" or not identity.auth_user_id or not identity.email:
            return None
        return identity
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        return None


def set_private_cookie(
    response: Response,
    key: str,
    value: str,
    *,
    max_age: int,
    secure: bool,
) -> None:
    response.set_cookie(
        key,
        value,
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )


def delete_auth_cookie(response: Response, key: str, *, secure: bool) -> None:
    response.delete_cookie(
        key,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )


def clear_temporary_auth_context(response: Response, *, secure: bool) -> None:
    for key in (ONBOARDING_COOKIE, PENDING_AUTH_COOKIE):
        delete_auth_cookie(response, key, secure=secure)
    CookieAuthStorage.clear_known_cookies(response, secure=secure)


class CookieAuthStorage(SyncSupportedStorage):
    """Request-local Supabase storage persisted only through secure cookies."""

    def __init__(self, cookies: Mapping[str, str], *, secure: bool):
        self._cookies = dict(cookies)
        self._secure = secure
        self._pending: dict[str, Optional[str]] = {}
        self._max_ages: dict[str, int] = {}

    @staticmethod
    def _base_name(key: str) -> str:
        if key.endswith("-code-verifier"):
            return SUPABASE_PKCE_COOKIE
        return SUPABASE_SESSION_COOKIE

    def _read(self, name: str) -> Optional[str]:
        if name in self._pending:
            return self._pending[name]
        return self._cookies.get(name)

    def get_item(self, key: str) -> Optional[str]:
        base_name = self._base_name(key)
        manifest = self._read(base_name)
        if not manifest or not manifest.startswith("v1:"):
            return None
        try:
            count = int(manifest.removeprefix("v1:"))
            if count < 1 or count > _MAX_COOKIE_CHUNKS:
                return None
            encoded = "".join(
                self._read(f"{base_name}.{index}") or "" for index in range(count)
            )
            if not encoded:
                return None
            return base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeError):
            return None

    def set_item(self, key: str, value: str) -> None:
        base_name = self._base_name(key)
        encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
        chunks = [
            encoded[index : index + _COOKIE_CHUNK_SIZE]
            for index in range(0, len(encoded), _COOKIE_CHUNK_SIZE)
        ]
        if not chunks or len(chunks) > _MAX_COOKIE_CHUNKS:
            raise ValueError("Supabase auth state exceeds cookie storage limit")

        max_age = (
            PKCE_MAX_AGE
            if base_name == SUPABASE_PKCE_COOKIE
            else SUPABASE_SESSION_MAX_AGE
        )
        self._pending[base_name] = f"v1:{len(chunks)}"
        self._max_ages[base_name] = max_age
        for index, chunk in enumerate(chunks):
            name = f"{base_name}.{index}"
            self._pending[name] = chunk
            self._max_ages[name] = max_age
        for index in range(len(chunks), _MAX_COOKIE_CHUNKS):
            self._pending[f"{base_name}.{index}"] = None

    def remove_item(self, key: str) -> None:
        base_name = self._base_name(key)
        self._pending[base_name] = None
        for index in range(_MAX_COOKIE_CHUNKS):
            self._pending[f"{base_name}.{index}"] = None

    def apply(self, response: Response) -> None:
        for name, value in self._pending.items():
            if value is None:
                delete_auth_cookie(response, name, secure=self._secure)
            else:
                set_private_cookie(
                    response,
                    name,
                    value,
                    max_age=self._max_ages[name],
                    secure=self._secure,
                )

    @staticmethod
    def clear_known_cookies(response: Response, *, secure: bool) -> None:
        for base_name in (SUPABASE_PKCE_COOKIE, SUPABASE_SESSION_COOKIE):
            delete_auth_cookie(response, base_name, secure=secure)
            for index in range(_MAX_COOKIE_CHUNKS):
                delete_auth_cookie(response, f"{base_name}.{index}", secure=secure)


class RequestSupabaseAuth:
    def __init__(
        self,
        client: Any,
        storage: CookieAuthStorage,
        http_client: httpx.Client,
        settings: SupabaseAuthSettings,
    ):
        self.client = client
        self.storage = storage
        self.http_client = http_client
        self.settings = settings

    def apply_cookies(self, response: Response) -> None:
        self.storage.apply(response)

    def close(self) -> None:
        self.http_client.close()


def create_supabase_auth_client(request: Request) -> RequestSupabaseAuth:
    settings = get_auth_settings()
    storage = CookieAuthStorage(request.cookies, secure=settings.cookie_secure)
    http_client = httpx.Client(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=False,
    )
    try:
        client = create_client(
            settings.supabase_url,
            settings.publishable_key,
            options=ClientOptions(
                flow_type="pkce",
                storage=storage,
                auto_refresh_token=False,
                persist_session=True,
                httpx_client=http_client,
                postgrest_client_timeout=10.0,
                storage_client_timeout=10,
                function_client_timeout=10,
            ),
        )
    except Exception:
        http_client.close()
        raise
    return RequestSupabaseAuth(client, storage, http_client, settings)


def extract_verified_google_identity(user_response: Any) -> PendingGoogleIdentity:
    user = getattr(user_response, "user", None)
    if user is None:
        raise ValueError("Missing authenticated user")

    raw_auth_user_id = getattr(user, "id", None)
    try:
        auth_user_id = str(uuid.UUID(str(raw_auth_user_id)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Authenticated user id is not a UUID") from exc
    email = getattr(user, "email", None)
    email_confirmed_at = getattr(user, "email_confirmed_at", None) or getattr(
        user, "confirmed_at", None
    )
    identities = getattr(user, "identities", None) or []
    identity_providers = {
        getattr(identity, "provider", None)
        if not isinstance(identity, dict)
        else identity.get("provider")
        for identity in identities
    }
    app_metadata = getattr(user, "app_metadata", None) or {}
    metadata_provider = app_metadata.get("provider")
    is_google = metadata_provider == "google" and "google" in identity_providers
    valid_email = (
        isinstance(email, str)
        and email == email.strip()
        and 3 <= len(email) <= 320
        and "@" in email
        and not any(character in email for character in "\r\n\0")
    )
    if not valid_email or not email_confirmed_at or not is_google:
        raise ValueError("Authenticated identity is not a verified Google user")

    return PendingGoogleIdentity(
        auth_user_id=auth_user_id,
        provider="google",
        email=email,
        authenticated_at=datetime.now(timezone.utc).isoformat(),
    )
