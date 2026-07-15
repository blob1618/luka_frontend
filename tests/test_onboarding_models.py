import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.database import (
    AcuerdoAceptado,
    AcuerdoVersion,
    Base,
    OnboardingInvitacion,
    Usuario,
)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'onboarding.db'}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_user(**overrides):
    values = {
        "nombre": "Usuario de prueba",
        "email": f"{uuid.uuid4()}@example.com",
    }
    values.update(overrides)
    return Usuario(**values)


def make_invitation(**overrides):
    creado_en = datetime.now(timezone.utc).replace(microsecond=0)
    values = {
        "whatsapp_id": f"54911{uuid.uuid4().int % 10**8:08d}",
        "token_hash": uuid.uuid4().hex,
        "estado": "pendiente",
        "expira_en": creado_en + timedelta(hours=1),
        "creado_en": creado_en,
        "actualizado_en": creado_en,
    }
    values.update(overrides)
    return OnboardingInvitacion(**values)


def make_agreement_version(**overrides):
    values = {
        "version": f"v-{uuid.uuid4()}",
        "contenido": "Contenido legal de prueba estructural",
    }
    values.update(overrides)
    return AcuerdoVersion(**values)


def make_acceptance(user, version, **overrides):
    values = {
        "usuario_id": user.id,
        "version_acuerdo_id": version.id,
        "aceptado_en": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return AcuerdoAceptado(**values)


def test_multiple_users_allow_null_auth_user_id(db):
    db.add_all([make_user(), make_user()])
    db.commit()

    assert db.query(Usuario).count() == 2


def test_duplicate_non_null_auth_user_id_is_rejected(db):
    auth_user_id = uuid.uuid4()
    db.add(make_user(auth_user_id=auth_user_id))
    db.commit()

    db.add(make_user(auth_user_id=auth_user_id))
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_non_null_whatsapp_id_is_rejected(db):
    whatsapp_id = "5491112345678"
    db.add(make_user(whatsapp_id=whatsapp_id))
    db.commit()

    db.add(make_user(whatsapp_id=whatsapp_id))
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize("whatsapp_id", ["", "   "])
def test_empty_user_whatsapp_id_is_rejected(db, whatsapp_id):
    db.add(make_user(whatsapp_id=whatsapp_id))

    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize(
    ("field", "value"),
    [("whatsapp_id", ""), ("whatsapp_id", "   "), ("token_hash", "")],
)
def test_empty_invitation_identifiers_are_rejected(db, field, value):
    invitation = make_invitation()
    setattr(invitation, field, value)
    db.add(invitation)

    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_token_hash_is_rejected(db):
    token_hash = uuid.uuid4().hex
    db.add(make_invitation(token_hash=token_hash))
    db.commit()

    db.add(make_invitation(token_hash=token_hash))
    with pytest.raises(IntegrityError):
        db.flush()


def test_only_one_pending_invitation_per_whatsapp_id(db):
    whatsapp_id = "5491198765432"
    db.add(make_invitation(whatsapp_id=whatsapp_id))
    db.commit()

    db.add(make_invitation(whatsapp_id=whatsapp_id))
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize("terminal_state", ["consumida", "revocada", "vencida"])
def test_terminal_invitation_allows_a_new_pending_one(db, terminal_state):
    whatsapp_id = "5491155555555"
    now = datetime.now(timezone.utc)
    terminal_values = {"estado": terminal_state, "whatsapp_id": whatsapp_id}

    if terminal_state == "consumida":
        user = make_user()
        db.add(user)
        db.flush()
        terminal_values.update(usuario_id=user.id, consumida_en=now)
    elif terminal_state == "revocada":
        terminal_values["revocada_en"] = now

    db.add(make_invitation(**terminal_values))
    db.commit()

    db.add(make_invitation(whatsapp_id=whatsapp_id))
    db.commit()

    assert (
        db.query(OnboardingInvitacion)
        .filter(OnboardingInvitacion.whatsapp_id == whatsapp_id)
        .count()
        == 2
    )


def test_unknown_invitation_state_is_rejected(db):
    db.add(make_invitation(estado="desconocida"))

    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize("field", ["intentos", "reenvios"])
def test_negative_invitation_counters_are_rejected(db, field):
    invitation = make_invitation(**{field: -1})
    db.add(invitation)

    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(seconds=-1)])
def test_expiration_must_be_after_creation(db, delta):
    creado_en = datetime.now(timezone.utc).replace(microsecond=0)
    db.add(
        make_invitation(
            creado_en=creado_en,
            actualizado_en=creado_en,
            expira_en=creado_en + delta,
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


STATE_MATRIX_INVALID_CASES = [
    ("pendiente", "usuario_id", "user"),
    ("pendiente", "consumida_en", "now"),
    ("pendiente", "revocada_en", "now"),
    ("consumida", "usuario_id", None),
    ("consumida", "consumida_en", None),
    ("consumida", "revocada_en", "now"),
    ("revocada", "usuario_id", "user"),
    ("revocada", "consumida_en", "now"),
    ("revocada", "revocada_en", None),
    ("vencida", "usuario_id", "user"),
    ("vencida", "consumida_en", "now"),
    ("vencida", "revocada_en", "now"),
]


@pytest.mark.parametrize(
    ("estado", "invalid_field", "invalid_value"), STATE_MATRIX_INVALID_CASES
)
def test_invitation_state_matrix_rejects_every_invalid_field(
    db, estado, invalid_field, invalid_value
):
    user = make_user()
    db.add(user)
    db.flush()
    now = datetime.now(timezone.utc)
    valid_values = {
        "pendiente": {},
        "consumida": {"usuario_id": user.id, "consumida_en": now},
        "revocada": {"revocada_en": now},
        "vencida": {},
    }
    invitation = make_invitation(estado=estado, **valid_values[estado])
    replacement = {"user": user.id, "now": now}.get(
        invalid_value, invalid_value
    )
    setattr(invitation, invalid_field, replacement)
    db.add(invitation)

    with pytest.raises(IntegrityError):
        db.flush()


def test_referenced_user_cannot_be_deleted(db):
    user = make_user()
    db.add(user)
    db.flush()
    db.add(
        make_invitation(
            estado="consumida",
            usuario_id=user.id,
            consumida_en=datetime.now(timezone.utc),
        )
    )
    db.commit()

    db.delete(user)
    with pytest.raises(IntegrityError):
        db.flush()


def test_current_agreement_requires_effective_date(db):
    db.add(make_agreement_version(esta_vigente=True, vigente_desde=None))

    with pytest.raises(IntegrityError):
        db.flush()


def test_only_one_agreement_version_can_be_current(db):
    now = datetime.now(timezone.utc)
    db.add(make_agreement_version(esta_vigente=True, vigente_desde=now))
    db.commit()

    db.add(make_agreement_version(esta_vigente=True, vigente_desde=now))
    with pytest.raises(IntegrityError):
        db.flush()


def test_agreement_version_must_be_unique(db):
    version = "2026-07"
    db.add(make_agreement_version(version=version))
    db.commit()

    db.add(make_agreement_version(version=version))
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_acceptance_for_user_and_version_is_rejected(db):
    user = make_user()
    version = make_agreement_version()
    db.add_all([user, version])
    db.flush()
    db.add(make_acceptance(user, version))
    db.commit()

    db.add(make_acceptance(user, version))
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize(
    "required_field", ["usuario_id", "version_acuerdo_id", "aceptado_en"]
)
def test_acceptance_required_fields_reject_null(db, required_field):
    user = make_user()
    version = make_agreement_version()
    db.add_all([user, version])
    db.flush()
    acceptance = make_acceptance(user, version)
    setattr(acceptance, required_field, None)
    db.add(acceptance)

    with pytest.raises(IntegrityError):
        db.flush()


def test_acceptance_origin_defaults_to_web_onboarding(db):
    user = make_user()
    version = make_agreement_version()
    db.add_all([user, version])
    db.flush()
    acceptance = make_acceptance(user, version)
    db.add(acceptance)
    db.flush()

    assert acceptance.origen == "web_onboarding"


def test_legacy_unknown_origin_can_be_persisted(db):
    user = make_user()
    version = make_agreement_version()
    db.add_all([user, version])
    db.flush()
    acceptance = make_acceptance(user, version, origen="legacy_desconocido")
    db.add(acceptance)
    db.commit()

    assert acceptance.origen == "legacy_desconocido"
