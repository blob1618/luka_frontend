import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.models.database import (
    AcuerdoVersion,
    Base,
    OnboardingInvitacion,
    get_db,
)


INVALID_MESSAGE = (
    "Este enlace de registro no es válido. Solicitá uno nuevo desde WhatsApp."
)


@pytest.fixture
def registration_db(tmp_path):
    database_path = tmp_path / "registration.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
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
        yield db, database_path

    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(registration_db):
    return TestClient(app)


def add_invitation(db: Session, token: str, **overrides) -> OnboardingInvitacion:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    values = {
        "whatsapp_id": "5491112345678",
        "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "estado": "pendiente",
        "expira_en": now + timedelta(hours=1),
        "creado_en": now,
        "actualizado_en": now,
    }
    values.update(overrides)
    invitation = OnboardingInvitacion(**values)
    db.add(invitation)
    db.commit()
    return invitation


def add_agreement(db: Session, **overrides) -> AcuerdoVersion:
    values = {
        "version": "2026-07",
        "contenido": "Términos completos y política de privacidad de prueba.",
        "esta_vigente": True,
        "vigente_desde": datetime(2026, 7, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    agreement = AcuerdoVersion(**values)
    db.add(agreement)
    db.commit()
    return agreement


def test_registration_without_token_is_invalid(client):
    response = client.get("/registro")

    assert response.status_code == 200
    assert INVALID_MESSAGE in response.text


def test_unknown_token_is_invalid(client):
    response = client.get("/registro?token=no-existe")

    assert response.status_code == 200
    assert INVALID_MESSAGE in response.text


def test_valid_token_is_looked_up_by_sha256(client, registration_db):
    db, _ = registration_db
    token = "token-original-super-seguro"
    invitation = add_invitation(db, token)
    add_agreement(db)

    response = client.get("/registro", params={"token": token})

    assert response.status_code == 200
    assert "Registrá tu cuenta" in response.text
    assert invitation.token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()


def test_original_token_is_not_stored(client, registration_db):
    db, database_path = registration_db
    token = "token-que-no-debe-guardarse"
    add_invitation(db, token)
    add_agreement(db)

    client.get("/registro", params={"token": token})
    db.close()

    assert token.encode("utf-8") not in database_path.read_bytes()


def test_pending_unexpired_invitation_shows_valid_registration(
    client, registration_db
):
    db, _ = registration_db
    token = "pendiente-vigente"
    add_invitation(db, token)
    add_agreement(db)

    response = client.get("/registro", params={"token": token})

    assert "Registrá tu cuenta" in response.text
    assert "Leí y acepto los términos" in response.text
    assert '<form method="post" action="/auth/google">' in response.text
    assert 'name="terms_accepted"' in response.text
    assert 'id="google-button" type="submit" disabled' in response.text


def test_pending_expired_invitation_shows_expired(client, registration_db):
    db, _ = registration_db
    token = "pendiente-expirada"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    add_invitation(
        db,
        token,
        creado_en=now - timedelta(hours=2),
        actualizado_en=now - timedelta(hours=2),
        expira_en=now - timedelta(hours=1),
    )

    response = client.get("/registro", params={"token": token})

    assert "Este enlace venció." in response.text


def test_expired_state_invitation_shows_expired(client, registration_db):
    db, _ = registration_db
    token = "estado-vencida"
    add_invitation(db, token, estado="vencida")

    response = client.get("/registro", params={"token": token})

    assert "Este enlace venció." in response.text


def test_consumed_invitation_shows_consumed(client, registration_db):
    db, _ = registration_db
    token = "estado-consumida"
    now = datetime.now(timezone.utc)
    from app.models.database import Usuario

    user = Usuario(nombre="Prueba", email="prueba@example.com")
    db.add(user)
    db.flush()
    add_invitation(
        db,
        token,
        estado="consumida",
        usuario_id=user.id,
        consumida_en=now,
    )

    response = client.get("/registro", params={"token": token})

    assert "Este enlace ya fue utilizado." in response.text


def test_revoked_invitation_is_invalid(client, registration_db):
    db, _ = registration_db
    token = "estado-revocada"
    add_invitation(
        db,
        token,
        estado="revocada",
        revocada_en=datetime.now(timezone.utc),
    )

    response = client.get("/registro", params={"token": token})

    assert INVALID_MESSAGE in response.text


def test_valid_invitation_without_current_agreement_blocks_registration(
    client, registration_db
):
    db, _ = registration_db
    token = "sin-terminos"
    add_invitation(db, token)

    response = client.get("/registro", params={"token": token})

    assert (
        "El registro no está disponible temporalmente porque los términos "
        "todavía no fueron publicados."
    ) in response.text
    assert 'id="terms-accepted"' not in response.text
    assert 'id="google-button"' not in response.text


def test_current_agreement_shows_version_content_and_effective_date(
    client, registration_db
):
    db, _ = registration_db
    token = "con-terminos"
    add_invitation(db, token)
    agreement = add_agreement(db)

    response = client.get("/registro", params={"token": token})

    assert agreement.version in response.text
    assert agreement.contenido in response.text
    assert "01/07/2026" in response.text


def test_inactive_agreement_is_not_used(client, registration_db):
    db, _ = registration_db
    token = "terminos-inactivos"
    add_invitation(db, token)
    add_agreement(
        db,
        esta_vigente=False,
        vigente_desde=None,
        contenido="Contenido inactivo que no debe mostrarse",
    )

    response = client.get("/registro", params={"token": token})

    assert "términos todavía no fueron publicados" in response.text
    assert "Contenido inactivo que no debe mostrarse" not in response.text


def test_phone_is_not_exposed_in_html(client, registration_db):
    db, _ = registration_db
    token = "telefono-privado"
    phone = "5491199998888"
    add_invitation(db, token, whatsapp_id=phone)
    add_agreement(db)

    response = client.get("/registro", params={"token": token})

    assert phone not in response.text


def test_hash_is_not_exposed_in_html(client, registration_db):
    db, _ = registration_db
    token = "hash-privado"
    invitation = add_invitation(db, token)
    add_agreement(db)

    response = client.get("/registro", params={"token": token})

    assert invitation.token_hash not in response.text
    assert token not in response.text


@pytest.mark.parametrize(
    ("token", "state", "extra"),
    [
        ("invalida", "revocada", {"revocada_en": datetime.now(timezone.utc)}),
        ("vencida", "vencida", {}),
    ],
)
def test_invalid_states_do_not_show_controls(
    client, registration_db, token, state, extra
):
    db, _ = registration_db
    add_invitation(db, token, estado=state, **extra)

    response = client.get("/registro", params={"token": token})

    assert 'id="terms-accepted"' not in response.text
    assert 'id="google-button"' not in response.text


def test_database_error_is_controlled_and_hides_technical_details():
    detail = "password=secreto host=db-interno"

    class FailingSession:
        def query(self, _model):
            raise OperationalError("SELECT privado", {}, Exception(detail))

    def override_get_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get("/registro?token=token-valido")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "No pudimos verificar el enlace." in response.text
    assert detail not in response.text
    assert "OperationalError" not in response.text


def test_login_and_dashboard_keep_their_previous_behavior(client):
    login_response = client.get("/login")
    dashboard_response = client.get("/", follow_redirects=False)

    assert login_response.status_code == 200
    assert "LUKA" in login_response.text
    assert dashboard_response.status_code == 303
    assert dashboard_response.headers["location"] == "/login"


def test_registration_has_noindex_nofollow(client):
    response = client.get("/registro")

    assert '<meta name="robots" content="noindex, nofollow"' in response.text
