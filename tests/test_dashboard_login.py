"""
Tests for STK-89: real WhatsApp magic-link login for already-registered users.

Covers app.auth.consume_dashboard_login_token (unit), the /login route
end-to-end, the removed insecure SECRET_KEY fallback, and cross-user data
isolation on the dashboard once logged in via auth_user_id.
"""

import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import consume_dashboard_login_token, create_session_token, decode_session_token
from app.main import app
from app.models.database import (
    Base,
    DashboardLoginLink,
    MovimientoFinanciero,
    Usuario,
    get_db,
)
from app.services.supabase_auth import AuthConfigurationError


@pytest.fixture(autouse=True)
def auth_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_key")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("ENABLE_MOCK_AUTH", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-stk-89")


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'dashboard-login.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with testing_session() as session:
        yield session
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(db):
    with TestClient(app, base_url="http://localhost:8000") as test_client:
        yield test_client


def create_linked_user(db, **overrides):
    values = {
        "nombre": "Usuario vinculado",
        "email": f"{uuid.uuid4()}@example.com",
        "whatsapp_id": None,
        "auth_user_id": uuid.uuid4(),
    }
    values.update(overrides)
    user = Usuario(**values)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_login_link(db, usuario_id, token, **overrides):
    values = {
        "usuario_id": usuario_id,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "estado": "pendiente",
        "expira_en": datetime.now(timezone.utc) + timedelta(minutes=10),
        "creado_en": datetime.now(timezone.utc),
        "actualizado_en": datetime.now(timezone.utc),
    }
    values.update(overrides)
    link = DashboardLoginLink(**values)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


# --- consume_dashboard_login_token (unit) -------------------------------------


def test_valid_token_returns_auth_user_id_and_marks_consumed(db):
    user = create_linked_user(db)
    link = create_login_link(db, user.id, "good-token")

    result = consume_dashboard_login_token("good-token", db)

    assert result == str(user.auth_user_id)
    db.refresh(link)
    assert link.estado == "consumido"
    assert link.consumido_en is not None


def test_reused_token_is_rejected(db):
    user = create_linked_user(db)
    create_login_link(db, user.id, "one-shot")

    first = consume_dashboard_login_token("one-shot", db)
    second = consume_dashboard_login_token("one-shot", db)

    assert first == str(user.auth_user_id)
    assert second is None


def test_expired_token_is_rejected_and_marked_vencido(db):
    user = create_linked_user(db)
    link = create_login_link(
        db,
        user.id,
        "old-token",
        expira_en=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    result = consume_dashboard_login_token("old-token", db)

    assert result is None
    db.refresh(link)
    assert link.estado == "vencido"


def test_unknown_token_is_rejected(db):
    assert consume_dashboard_login_token("does-not-exist", db) is None


def test_unlinked_user_token_is_rejected(db):
    """Defensive: the bot never issues links for unlinked users, but the
    frontend must not trust that blindly."""
    user = create_linked_user(db, auth_user_id=None)
    create_login_link(db, user.id, "orphan-token")

    assert consume_dashboard_login_token("orphan-token", db) is None


# --- no insecure SECRET_KEY fallback -------------------------------------------


def test_production_without_real_secret_key_blocks_session_creation(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(AuthConfigurationError):
        create_session_token(str(uuid.uuid4()))


def test_production_with_dev_placeholder_secret_blocks_session_decoding(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("SECRET_KEY", "change-me-to-a-random-secret-in-production")

    with pytest.raises(AuthConfigurationError):
        decode_session_token("irrelevant")


# --- /login end-to-end (real magic link) ---------------------------------------


def test_login_with_valid_token_sets_session_and_redirects_to_dashboard(client, db):
    user = create_linked_user(db)
    create_login_link(db, user.id, "web-token")

    response = client.get("/login", params={"token": "web-token"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "luka_session" in response.cookies


def test_login_with_expired_token_shows_error_without_session(client, db):
    user = create_linked_user(db)
    create_login_link(
        db,
        user.id,
        "stale-token",
        expira_en=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    response = client.get("/login", params={"token": "stale-token"}, follow_redirects=False)

    assert response.status_code == 200
    assert "luka_session" not in response.cookies


def test_login_with_reused_token_is_rejected(client, db):
    user = create_linked_user(db)
    create_login_link(db, user.id, "single-use")

    first = client.get("/login", params={"token": "single-use"}, follow_redirects=False)
    client.cookies.clear()
    second = client.get("/login", params={"token": "single-use"}, follow_redirects=False)

    assert first.status_code == 303
    assert second.status_code == 200
    assert "luka_session" not in second.cookies


# --- cross-user isolation -------------------------------------------------------


def test_dashboard_only_shows_the_authenticated_users_own_data(client, db):
    user_a = create_linked_user(db, email="a@example.com")
    user_b = create_linked_user(db, email="b@example.com")
    db.add(
        MovimientoFinanciero(
            usuario_id=user_a.id,
            tipo="egreso",
            cantidad=100,
            moneda="ARS",
            descripcion="Gasto de A",
            fecha_movimiento=date.today(),
        )
    )
    db.add(
        MovimientoFinanciero(
            usuario_id=user_b.id,
            tipo="egreso",
            cantidad=999,
            moneda="ARS",
            descripcion="Gasto de B",
            fecha_movimiento=date.today(),
        )
    )
    db.commit()

    create_login_link(db, user_a.id, "token-a")
    login_a = client.get("/login", params={"token": "token-a"}, follow_redirects=False)
    session_cookie_a = login_a.cookies["luka_session"]

    client.cookies.clear()
    client.cookies.set("luka_session", session_cookie_a)
    dashboard_a = client.get("/")

    assert dashboard_a.status_code == 200
    assert "Gasto de A" in dashboard_a.text
    assert "Gasto de B" not in dashboard_a.text
