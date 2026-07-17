import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import itsdangerous.timed
from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from supabase_auth.errors import AuthInvalidJwtError

from app.main import app
from app.models.database import (
    AcuerdoAceptado,
    AcuerdoVersion,
    Base,
    OnboardingInvitacion,
    Usuario,
    get_db,
)
from app.services import supabase_auth


TEST_SECRET = "test-secret-key-for-stk-146"
GOOGLE_URL = "https://example.supabase.co/auth/v1/authorize?provider=google"


class FakeSupabaseAuth:
    def __init__(self, storage, recorder):
        self.storage = storage
        self.recorder = recorder

    def sign_in_with_oauth(self, credentials):
        self.recorder["oauth_credentials"] = credentials
        if self.recorder.get("oauth_error"):
            raise OSError("network detail with secret")
        self.storage.remove_item("sb-project-auth-token")
        self.storage.set_item(
            "sb-project-auth-token-code-verifier",
            "test-pkce-code-verifier",
        )
        return SimpleNamespace(url=GOOGLE_URL)

    def exchange_code_for_session(self, params):
        self.recorder["exchange_params"] = params
        if self.recorder.get("exchange_error"):
            raise ValueError("sensitive Supabase response")
        verifier = self.storage.get_item("sb-project-auth-token-code-verifier")
        if not verifier:
            raise ValueError("missing code verifier")
        self.recorder["pkce_verifier"] = verifier
        self.storage.remove_item("sb-project-auth-token-code-verifier")
        self.storage.set_item(
            "sb-project-auth-token",
            '{"access_token":"access-secret","refresh_token":"refresh-secret"}',
        )
        return SimpleNamespace(
            session=SimpleNamespace(access_token="access-secret")
        )

    def get_user(self, access_token=None):
        self.recorder["get_user_token"] = access_token
        self.recorder["sql_seen_before_get_user"] = self.recorder.get(
            "sql_seen", False
        )
        if self.recorder.get("user_exception") is not None:
            raise self.recorder["user_exception"]
        if self.recorder.get("user_error"):
            raise ValueError("invalid authenticated user")
        user = SimpleNamespace(
            id=self.recorder.get(
                "auth_user_id", "76aecc76-0e88-4bae-a08f-c3c3297ed20a"
            ),
            email=self.recorder.get("email", "persona@example.com"),
            email_confirmed_at=self.recorder.get(
                "email_confirmed_at", "2026-07-16T12:00:00Z"
            ),
            confirmed_at=None,
            identities=self.recorder.get(
                "identities",
                [
                    SimpleNamespace(
                        provider=self.recorder.get("identity_provider", "google")
                    )
                ],
            ),
            app_metadata={
                "provider": self.recorder.get("metadata_provider", "google"),
                "providers": ["google"],
            },
            user_metadata=self.recorder.get(
                "user_metadata", {"provider": "google", "full_name": "Persona Google"}
            ),
        )
        return SimpleNamespace(user=user)


@pytest.fixture(autouse=True)
def auth_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_key")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("ENABLE_MOCK_AUTH", "true")
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)


@pytest.fixture
def auth_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'supabase-auth.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with testing_session() as db:
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def sdk(monkeypatch):
    recorder = {"create_calls": []}

    def fake_create_client(url, key, options):
        recorder["create_calls"].append((url, key, options))
        return SimpleNamespace(auth=FakeSupabaseAuth(options.storage, recorder))

    monkeypatch.setattr(supabase_auth, "create_client", fake_create_client)
    return recorder


@pytest.fixture
def client(auth_db, sdk):
    with TestClient(app, base_url="http://localhost:8000") as test_client:
        yield test_client


def add_invitation(db: Session, token: str, **overrides):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    values = {
        "whatsapp_id": "5491112345678",
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "estado": "pendiente",
        "expira_en": now + timedelta(hours=1),
        "creado_en": now,
        "actualizado_en": now,
    }
    values.update(overrides)
    invitation = OnboardingInvitacion(**values)
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def add_agreement(db: Session):
    agreement = AcuerdoVersion(
        version="2026-07",
        contenido="Términos privados de prueba",
        esta_vigente=True,
        vigente_desde=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
    return agreement


def begin_registration(client, db, token="stk-146-secret-token"):
    invitation = add_invitation(db, token)
    agreement = add_agreement(db)
    response = client.get("/registro", params={"token": token})
    assert response.status_code == 200
    return invitation, agreement, response


def begin_oauth(client, db, token="stk-146-secret-token"):
    invitation, agreement, _ = begin_registration(client, db, token)
    response = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return invitation, agreement, response


def decode_cookie(value, salt, max_age=1800):
    return URLSafeTimedSerializer(TEST_SECRET).loads(
        value,
        salt=salt,
        max_age=max_age,
    )


def test_valid_registration_creates_minimal_signed_context(client, auth_db):
    token = "token-original-no-exponer"
    invitation, agreement, response = begin_registration(client, auth_db, token)

    cookie = client.cookies.get(supabase_auth.ONBOARDING_COOKIE)
    payload = decode_cookie(cookie, "luka-onboarding-context-v1")

    assert payload == {"i": str(invitation.id), "a": str(agreement.id)}
    assert invitation.whatsapp_id not in cookie
    assert token not in cookie
    assert invitation.token_hash not in cookie
    assert token not in response.text
    assert invitation.whatsapp_id not in response.text
    assert invitation.token_hash not in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_oauth_requires_acceptance_and_valid_context(client, auth_db, sdk):
    begin_registration(client, auth_db)

    missing_acceptance = client.post("/auth/google")
    client.cookies.clear()
    missing_context = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
    )

    assert missing_acceptance.status_code == 400
    assert "Debés aceptar" in missing_acceptance.text
    assert missing_context.status_code == 400
    assert "sesión de registro venció" in missing_context.text
    assert sdk["create_calls"] == []


def test_oauth_revalidates_invitation_and_agreement(client, auth_db, sdk):
    invitation, agreement, _ = begin_registration(client, auth_db)
    invitation.estado = "vencida"
    auth_db.commit()

    expired = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
    )
    invitation.estado = "pendiente"
    auth_db.commit()
    client.get("/registro", params={"token": "stk-146-secret-token"})
    agreement.esta_vigente = False
    auth_db.commit()
    inactive_terms = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
    )

    assert "enlace venció" in expired.text
    assert "términos cambiaron" in inactive_terms.text
    assert sdk["create_calls"] == []


def test_oauth_uses_google_pkce_callback_and_sdk_url(client, auth_db, sdk):
    _, _, response = begin_oauth(client, auth_db)

    assert response.headers["location"] == GOOGLE_URL
    credentials = sdk["oauth_credentials"]
    assert credentials == {
        "provider": "google",
        "options": {"redirect_to": "http://localhost:8000/auth/callback"},
    }
    url, key, options = sdk["create_calls"][0]
    assert url == "https://example.supabase.co"
    assert key == "sb_publishable_test_key"
    assert options.flow_type == "pkce"
    assert options.persist_session is True
    assert options.auto_refresh_token is False
    assert isinstance(options.storage, supabase_auth.CookieAuthStorage)
    assert options.httpx_client.timeout.connect == 5.0


def test_callback_exchanges_pkce_validates_user_and_creates_context(
    client,
    auth_db,
    sdk,
):
    begin_oauth(client, auth_db)

    response = client.get(
        "/auth/callback",
        params={"code": "oauth-code-secret"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/registro/continuar"
    assert sdk["exchange_params"] == {"auth_code": "oauth-code-secret"}
    assert sdk["pkce_verifier"] == "test-pkce-code-verifier"
    assert sdk["get_user_token"] == "access-secret"
    pending = client.cookies.get(supabase_auth.PENDING_AUTH_COOKIE)
    payload = decode_cookie(
        pending,
        "luka-pending-google-auth-v1",
        max_age=900,
    )
    assert payload["auth_user_id"] == "76aecc76-0e88-4bae-a08f-c3c3297ed20a"
    assert payload["provider"] == "google"
    assert payload["email"] == "persona@example.com"
    assert payload["authenticated_at"]
    assert payload["onboarding_context_hash"]
    assert response.headers["cache-control"] == "private, no-store"


def test_auth_cookies_are_http_only_lax_and_limited(client, auth_db):
    _, _, registration = begin_registration(client, auth_db)
    oauth = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
        follow_redirects=False,
    )

    headers = registration.headers.get_list("set-cookie") + oauth.headers.get_list(
        "set-cookie"
    )
    relevant = [header for header in headers if "luka_" in header and "Max-Age=0" not in header]
    assert relevant
    assert all("HttpOnly" in header for header in relevant)
    assert all("SameSite=lax" in header for header in relevant)
    assert all("Path=/" in header for header in relevant)
    assert all("Max-Age=" in header for header in relevant)
    assert all("Secure" not in header for header in relevant)


def test_auth_cookies_are_secure_in_production(monkeypatch, auth_db, sdk):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_BASE_URL", "https://luka-frontend-v3yt.onrender.com")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("ENABLE_MOCK_AUTH", "false")
    monkeypatch.setenv("SECRET_KEY", "production-secret-not-default-32-chars")
    with TestClient(
        app,
        base_url="https://luka-frontend-v3yt.onrender.com",
    ) as secure_client:
        _, _, registration = begin_registration(secure_client, auth_db)
        oauth = secure_client.post(
            "/auth/google",
            data={"terms_accepted": "accepted"},
            follow_redirects=False,
        )

    headers = registration.headers.get_list("set-cookie") + oauth.headers.get_list(
        "set-cookie"
    )
    relevant = [header for header in headers if "luka_" in header and "Max-Age=0" not in header]
    assert relevant
    assert all("Secure" in header for header in relevant)
    assert sdk["oauth_credentials"]["options"]["redirect_to"] == (
        "https://luka-frontend-v3yt.onrender.com/auth/callback"
    )


def test_callback_provider_errors_and_missing_code_are_controlled(client, auth_db):
    cancelled = client.get(
        "/auth/callback",
        params={"error": "access_denied", "error_description": "email=secret"},
    )
    missing = client.get("/auth/callback")

    assert cancelled.status_code == 400
    assert "autenticación con Google fue cancelada" in cancelled.text
    assert "email=secret" not in cancelled.text
    assert missing.status_code == 400
    assert "No recibimos una respuesta válida" in missing.text


def test_invalid_code_does_not_create_pending_context(client, auth_db, sdk):
    begin_oauth(client, auth_db)
    sdk["exchange_error"] = True

    response = client.get("/auth/callback", params={"code": "invalid-code"})

    assert response.status_code == 400
    assert "sensitive Supabase response" not in response.text
    assert client.cookies.get(supabase_auth.PENDING_AUTH_COOKIE) is None


def test_unverified_provider_does_not_trust_user_metadata(client, auth_db, sdk):
    begin_oauth(client, auth_db)
    sdk["identity_provider"] = "github"
    sdk["metadata_provider"] = "github"

    response = client.get("/auth/callback", params={"code": "valid-code"})

    assert response.status_code == 400
    assert "No pudimos validar la sesión de Google" in response.text
    assert client.cookies.get(supabase_auth.PENDING_AUTH_COOKIE) is None


def test_configuration_and_network_errors_are_safe(client, auth_db, sdk, monkeypatch):
    begin_registration(client, auth_db)
    monkeypatch.delenv("SUPABASE_URL")
    missing_config = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
    )

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    sdk["oauth_error"] = True
    network_error = client.post(
        "/auth/google",
        data={"terms_accepted": "accepted"},
    )

    assert missing_config.status_code == 503
    assert "no está disponible temporalmente" in missing_config.text
    assert network_error.status_code == 502
    assert "network detail with secret" not in network_error.text


def test_callback_configuration_error_is_controlled(client, auth_db, monkeypatch):
    begin_oauth(client, auth_db)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY")

    response = client.get("/auth/callback", params={"code": "valid-code"})

    assert response.status_code == 503
    assert "no está disponible temporalmente" in response.text
    assert "SUPABASE_PUBLISHABLE_KEY" not in response.text
    assert client.cookies.get(supabase_auth.PENDING_AUTH_COOKIE) is None


def test_expired_pkce_context_does_not_exchange_or_create_session(
    client,
    auth_db,
    sdk,
):
    begin_oauth(client, auth_db)
    for name in list(client.cookies.keys()):
        if name.startswith(supabase_auth.SUPABASE_PKCE_COOKIE):
            client.cookies.delete(name)

    response = client.get("/auth/callback", params={"code": "valid-code"})

    assert response.status_code == 400
    assert "sesión con Google venció" in response.text
    assert "exchange_params" not in sdk
    assert client.cookies.get(supabase_auth.PENDING_AUTH_COOKIE) is None


def test_continue_requires_both_contexts(client, auth_db):
    no_context = client.get("/registro/continuar")
    begin_registration(client, auth_db)
    invitation_only = client.get("/registro/continuar")

    assert no_context.status_code == 400
    assert invitation_only.status_code == 400
    assert "sesión de registro venció" in invitation_only.text


@pytest.mark.parametrize("invalidate", ["invitation", "agreement"])
def test_continue_revalidates_database_state(client, auth_db, invalidate):
    invitation, agreement, _ = begin_oauth(client, auth_db)
    callback = client.get(
        "/auth/callback",
        params={"code": "valid-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    if invalidate == "invitation":
        invitation.estado = "vencida"
    else:
        agreement.esta_vigente = False
    auth_db.commit()

    response = client.get("/registro/continuar")

    assert response.status_code == 400
    assert "Tu cuenta de Google fue verificada correctamente" not in response.text


def test_continue_shows_only_safe_google_identity(client, auth_db):
    invitation, agreement, _ = begin_oauth(client, auth_db)
    callback = client.get(
        "/auth/callback",
        params={"code": "valid-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 303

    response = client.get("/registro/continuar")

    assert response.status_code == 200
    assert "Tu cuenta de Google fue verificada correctamente." in response.text
    assert "vincularemos esta cuenta con el WhatsApp" in response.text
    assert '<form id="finalize-registration-form" method="post" action="/registro/finalizar">' in response.text
    assert "Finalizar registro" in response.text
    assert "persona@example.com" in response.text
    for secret in (
        invitation.whatsapp_id,
        str(invitation.id),
        str(agreement.id),
        invitation.token_hash,
        "access-secret",
        "refresh-secret",
    ):
        assert secret not in response.text


def test_oauth_flow_does_not_write_onboarding_records(client, auth_db):
    invitation, _, _ = begin_oauth(client, auth_db)
    client.get(
        "/auth/callback",
        params={"code": "valid-code"},
        follow_redirects=False,
    )
    client.get("/registro/continuar")
    auth_db.expire_all()

    stored_invitation = auth_db.get(OnboardingInvitacion, invitation.id)
    assert auth_db.query(Usuario).count() == 0
    assert auth_db.query(AcuerdoAceptado).count() == 0
    assert stored_invitation.estado == "pendiente"
    assert stored_invitation.usuario_id is None
    assert stored_invitation.consumida_en is None


def test_mock_auth_is_disabled_in_production(monkeypatch, client):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_MOCK_AUTH", "true")

    dev_login = client.get("/dev-login", follow_redirects=False)
    magic_login = client.get(
        "/login",
        params={"token": "texto-arbitrario"},
        follow_redirects=False,
    )

    assert dev_login.status_code == 404
    assert magic_login.status_code == 200
    assert "luka_session" not in dev_login.headers.get("set-cookie", "")
    assert "luka_session" not in magic_login.headers.get("set-cookie", "")


def test_mock_auth_can_remain_enabled_in_development(client):
    dev_login = client.get("/dev-login", follow_redirects=False)
    magic_login = client.get(
        "/login",
        params={"token": "texto-arbitrario"},
        follow_redirects=False,
    )

    assert dev_login.status_code == 303
    assert magic_login.status_code == 303
    assert "luka_session" in dev_login.headers["set-cookie"]
    assert "luka_session" in magic_login.headers["set-cookie"]


def reach_finalization(client, db):
    invitation, agreement, _ = begin_oauth(client, db)
    callback = client.get(
        "/auth/callback",
        params={"code": "valid-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    return invitation, agreement


def test_finalize_requires_onboarding_and_pending_context(client, auth_db):
    missing_both = client.post("/registro/finalizar")
    begin_registration(client, auth_db)
    missing_pending = client.post("/registro/finalizar")

    assert missing_both.status_code == 400
    assert missing_pending.status_code == 400
    assert "sesión de registro venció" in missing_pending.text


def test_finalize_rejects_invalid_signed_context(client, auth_db):
    reach_finalization(client, auth_db)
    client.cookies.set(supabase_auth.ONBOARDING_COOKIE, "firma-invalida")

    response = client.post("/registro/finalizar")

    assert response.status_code == 400
    assert auth_db.query(Usuario).count() == 0


def test_finalize_rejects_expired_signed_context(
    client, auth_db, monkeypatch
):
    reach_finalization(client, auth_db)
    current_time = itsdangerous.timed.time.time()
    monkeypatch.setattr(
        itsdangerous.timed.time,
        "time",
        lambda: current_time + supabase_auth.ONBOARDING_CONTEXT_MAX_AGE + 1,
    )

    response = client.post("/registro/finalizar")

    assert response.status_code == 400
    assert auth_db.query(Usuario).count() == 0


def test_finalize_requires_supabase_session_cookie(client, auth_db):
    reach_finalization(client, auth_db)
    for name in list(client.cookies.keys()):
        if name.startswith(supabase_auth.SUPABASE_SESSION_COOKIE):
            client.cookies.delete(name)

    response = client.post("/registro/finalizar")

    assert response.status_code == 401
    assert "sesión de Google venció" in response.text
    assert auth_db.query(Usuario).count() == 0


def test_finalize_handles_get_user_failure_without_database_changes(
    client, auth_db, sdk
):
    reach_finalization(client, auth_db)
    sdk["user_error"] = True

    response = client.post("/registro/finalizar")

    assert response.status_code == 502
    assert "error transitorio" in response.text
    assert "invalid authenticated user" not in response.text
    assert auth_db.query(Usuario).count() == 0


def test_finalize_treats_invalid_supabase_session_as_terminal(
    client, auth_db, sdk
):
    reach_finalization(client, auth_db)
    sdk["user_exception"] = AuthInvalidJwtError(
        "sensitive JWT detail that must not be exposed"
    )

    response = client.post("/registro/finalizar")

    assert response.status_code == 401
    assert "sesión de Google venció" in response.text
    assert "sensitive JWT detail" not in response.text
    assert client.cookies.get(supabase_auth.ONBOARDING_COOKIE) is None
    assert client.cookies.get(supabase_auth.PENDING_AUTH_COOKIE) is None
    assert auth_db.query(Usuario).count() == 0


def test_finalize_calls_get_user_before_sql_or_transaction(
    client, auth_db, sdk, monkeypatch
):
    import app.main as main_module

    reach_finalization(client, auth_db)
    original_finalize = main_module.finalize_onboarding

    def record_transaction_state(db, *args, **kwargs):
        sdk["transaction_before_service"] = db.in_transaction()
        return original_finalize(db, *args, **kwargs)

    def record_sql(*_args):
        sdk["sql_seen"] = True

    monkeypatch.setattr(
        main_module,
        "finalize_onboarding",
        record_transaction_state,
    )
    event.listen(auth_db.get_bind(), "before_cursor_execute", record_sql)
    sdk["sql_seen"] = False
    try:
        response = client.post("/registro/finalizar")
    finally:
        event.remove(auth_db.get_bind(), "before_cursor_execute", record_sql)

    assert response.status_code == 200
    assert sdk["sql_seen_before_get_user"] is False
    assert sdk["transaction_before_service"] is False
    assert sdk["sql_seen"] is True


@pytest.mark.parametrize(
    ("sdk_change", "expected_message"),
    [
        ({"auth_user_id": "no-es-uuid"}, "identidad de Google ya no es válida"),
        (
            {"identity_provider": "github", "metadata_provider": "github"},
            "identidad de Google ya no es válida",
        ),
        ({"identities": []}, "identidad de Google ya no es válida"),
        ({"email_confirmed_at": None}, "identidad de Google ya no es válida"),
        (
            {"email": "otra-persona@example.com"},
            "identidad de Google cambió durante el registro",
        ),
    ],
)
def test_finalize_revalidates_and_compares_fresh_google_identity(
    client,
    auth_db,
    sdk,
    sdk_change,
    expected_message,
):
    reach_finalization(client, auth_db)
    sdk.update(sdk_change)

    response = client.post("/registro/finalizar")

    assert response.status_code in {401, 409}
    assert expected_message in response.text
    assert auth_db.query(Usuario).count() == 0
    assert auth_db.query(AcuerdoAceptado).count() == 0


def test_finalize_success_revalidates_without_browser_identity_fields(
    client, auth_db, sdk
):
    invitation, agreement = reach_finalization(client, auth_db)
    token_hash = invitation.token_hash

    response = client.post("/registro/finalizar")

    auth_db.expire_all()
    user = auth_db.query(Usuario).one()
    acceptance = auth_db.query(AcuerdoAceptado).one()
    stored_invitation = auth_db.get(OnboardingInvitacion, invitation.id)
    assert response.status_code == 200
    assert "Tu registro se completó correctamente." in response.text
    assert "Ya podés volver a WhatsApp y comenzar a usar Luka." in response.text
    assert sdk["get_user_token"] is None
    assert user.email == "persona@example.com"
    assert user.nombre == "Persona Google"
    assert str(user.auth_user_id) == "76aecc76-0e88-4bae-a08f-c3c3297ed20a"
    assert user.whatsapp_id == invitation.whatsapp_id
    assert acceptance.usuario_id == user.id
    assert acceptance.version_acuerdo_id == agreement.id
    assert stored_invitation.estado == "consumida"
    assert stored_invitation.token_hash == token_hash
    assert response.headers["cache-control"] == "private, no-store"


def test_finalize_uses_safe_name_fallback(client, auth_db, sdk):
    reach_finalization(client, auth_db)
    sdk["user_metadata"] = {"full_name": "\x00\n"}

    response = client.post("/registro/finalizar")

    assert response.status_code == 200
    assert auth_db.query(Usuario).one().nombre == "persona"


def test_finalize_success_clears_every_temporary_cookie_and_not_dashboard_session(
    client, auth_db
):
    reach_finalization(client, auth_db)

    response = client.post("/registro/finalizar")

    for name in client.cookies.keys():
        assert name not in {
            supabase_auth.ONBOARDING_COOKIE,
            supabase_auth.PENDING_AUTH_COOKIE,
        }
        assert not name.startswith(supabase_auth.SUPABASE_PKCE_COOKIE)
        assert not name.startswith(supabase_auth.SUPABASE_SESSION_COOKIE)
    temporary_cookie_headers = [
        header
        for header in response.headers.get_list("set-cookie")
        if "luka_onboarding=" in header
        or "luka_pending_google=" in header
        or "luka_sb_pkce" in header
        or "luka_sb_session" in header
    ]
    assert temporary_cookie_headers
    assert all("Max-Age=0" in header for header in temporary_cookie_headers)
    assert "luka_session" not in response.headers.get("set-cookie", "")


@pytest.mark.parametrize("terminal_state", ["vencida", "consumida"])
def test_finalize_rejects_terminal_invitation_and_clears_context(
    client, auth_db, terminal_state
):
    invitation, _ = reach_finalization(client, auth_db)
    if terminal_state == "consumida":
        user = Usuario(nombre="Existente", email="existente@example.com")
        auth_db.add(user)
        auth_db.flush()
        invitation.usuario_id = user.id
        invitation.consumida_en = datetime.now(timezone.utc)
    invitation.estado = terminal_state
    auth_db.commit()

    response = client.post("/registro/finalizar")

    assert response.status_code in {409, 410}
    assert client.cookies.get(supabase_auth.ONBOARDING_COOKIE) is None
    assert auth_db.query(AcuerdoAceptado).count() == 0


def test_finalize_rejects_changed_terms(client, auth_db):
    _, agreement = reach_finalization(client, auth_db)
    agreement.esta_vigente = False
    auth_db.commit()

    response = client.post("/registro/finalizar")

    assert response.status_code == 409
    assert "términos cambiaron" in response.text
    assert auth_db.query(Usuario).count() == 0


def test_finalize_identity_conflict_is_generic_and_atomic(client, auth_db):
    invitation, _ = reach_finalization(client, auth_db)
    conflicting_user = Usuario(
        nombre="Otra persona",
        email="persona@example.com",
        auth_user_id=uuid.UUID("c9277fba-17e1-4f7f-a19c-6dac97f84168"),
    )
    auth_db.add(conflicting_user)
    auth_db.commit()

    response = client.post("/registro/finalizar")

    auth_db.refresh(invitation)
    assert response.status_code == 409
    assert "algunos datos ya están asociados a otra identidad" in response.text
    assert "persona@example.com" not in response.text
    assert invitation.whatsapp_id not in response.text
    assert str(conflicting_user.auth_user_id) not in response.text
    assert invitation.estado == "pendiente"
    assert auth_db.query(AcuerdoAceptado).count() == 0


def test_integrity_error_response_hides_sql_and_constraint_names(
    client, auth_db
):
    invitation, _ = reach_finalization(client, auth_db)
    private_constraint = "uq_private_auth_user_id_constraint"

    def fail_acceptance_insert(
        _connection,
        _cursor,
        statement,
        parameters,
        _context,
        _executemany,
    ):
        if "insert into acuerdo_aceptado" in statement.lower():
            raise IntegrityError(
                statement,
                parameters,
                Exception(private_constraint),
            )

    event.listen(
        auth_db.get_bind(),
        "before_cursor_execute",
        fail_acceptance_insert,
    )
    try:
        response = client.post("/registro/finalizar")
    finally:
        event.remove(
            auth_db.get_bind(),
            "before_cursor_execute",
            fail_acceptance_insert,
        )

    auth_db.expire_all()
    stored_invitation = auth_db.get(OnboardingInvitacion, invitation.id)
    assert response.status_code == 409
    assert "algunos datos ya están asociados a otra identidad" in response.text
    assert private_constraint not in response.text
    assert "INSERT INTO" not in response.text
    assert auth_db.query(Usuario).count() == 0
    assert auth_db.query(AcuerdoAceptado).count() == 0
    assert stored_invitation.estado == "pendiente"


def test_finalize_interface_blocks_double_submit_and_exposes_no_identifiers(
    client, auth_db
):
    invitation, agreement = reach_finalization(client, auth_db)

    response = client.get("/registro/continuar")

    assert 'method="post" action="/registro/finalizar"' in response.text
    assert "finalizeButton.disabled = true" in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text
    for value in (
        invitation.whatsapp_id,
        invitation.token_hash,
        str(invitation.id),
        str(agreement.id),
        "76aecc76-0e88-4bae-a08f-c3c3297ed20a",
    ):
        assert value not in response.text
