import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query, Session

from app.models.database import (
    AcuerdoAceptado,
    AcuerdoVersion,
    Base,
    MovimientoFinanciero,
    OnboardingInvitacion,
    Usuario,
)
from app.services.onboarding_finalization import (
    VerifiedIdentity,
    finalize_onboarding,
    normalize_display_name,
)


AUTH_USER_ID = uuid.UUID("76aecc76-0e88-4bae-a08f-c3c3297ed20a")
NOW = datetime(2026, 7, 16, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'finalization.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def identity(**overrides):
    values = {
        "auth_user_id": str(AUTH_USER_ID),
        "provider": "google",
        "email": "persona@example.com",
    }
    values.update(overrides)
    return VerifiedIdentity(**values)


def add_invitation(db, **overrides):
    values = {
        "whatsapp_id": "5491112345678",
        "token_hash": uuid.uuid4().hex,
        "estado": "pendiente",
        "expira_en": NOW + timedelta(hours=1),
        "creado_en": NOW - timedelta(minutes=5),
        "actualizado_en": NOW - timedelta(minutes=5),
    }
    values.update(overrides)
    invitation = OnboardingInvitacion(**values)
    db.add(invitation)
    db.commit()
    return invitation


def add_agreement(db, **overrides):
    values = {
        "version": f"v-{uuid.uuid4()}",
        "contenido": "Acuerdo de prueba",
        "esta_vigente": True,
        "vigente_desde": NOW - timedelta(days=1),
    }
    values.update(overrides)
    agreement = AcuerdoVersion(**values)
    db.add(agreement)
    db.commit()
    return agreement


def add_user(db, **overrides):
    values = {
        "nombre": "Nombre anterior",
        "email": f"{uuid.uuid4()}@example.com",
    }
    values.update(overrides)
    user = Usuario(**values)
    db.add(user)
    db.commit()
    return user


def finalize(db, invitation, agreement, **overrides):
    values = {
        "verified_identity": identity(),
        "display_name": "Persona Google",
        "now": NOW,
    }
    values.update(overrides)
    return finalize_onboarding(
        db,
        invitation.id,
        agreement.id,
        **values,
    )


def test_invitation_not_found(db):
    agreement = add_agreement(db)

    result = finalize_onboarding(
        db, uuid.uuid4(), agreement.id, identity(), "Persona", now=NOW
    )

    assert result.status == "invitation_not_found"
    assert db.query(Usuario).count() == 0


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"estado": "revocada", "revocada_en": NOW},
            "invitation_revoked",
        ),
        ({"estado": "vencida"}, "invitation_expired"),
        (
            {
                "creado_en": NOW - timedelta(hours=2),
                "actualizado_en": NOW - timedelta(hours=2),
                "expira_en": NOW - timedelta(seconds=1),
            },
            "invitation_expired",
        ),
    ],
)
def test_rejects_revoked_and_expired_invitations(db, overrides, expected):
    invitation = add_invitation(db, **overrides)
    agreement = add_agreement(db)

    assert finalize(db, invitation, agreement).status == expected


def test_consumed_invitation_is_not_idempotent_success(db):
    user = add_user(db, email="persona@example.com")
    invitation = add_invitation(
        db,
        estado="consumida",
        usuario_id=user.id,
        consumida_en=NOW,
    )
    agreement = add_agreement(db)

    result = finalize(db, invitation, agreement)

    assert result.status == "invitation_consumed"
    assert db.query(AcuerdoAceptado).count() == 0


def test_agreement_must_exist_and_remain_current(db):
    invitation = add_invitation(db)

    missing = finalize_onboarding(
        db, invitation.id, uuid.uuid4(), identity(), "Persona", now=NOW
    )
    assert missing.status == "agreement_not_found"

    agreement = add_agreement(db, esta_vigente=False, vigente_desde=None)
    changed = finalize(db, invitation, agreement)
    assert changed.status == "agreement_changed"
    assert db.query(Usuario).count() == 0


def test_creates_new_user_acceptance_and_consumes_invitation(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    original_hash = invitation.token_hash

    result = finalize(db, invitation, agreement)

    assert result.status == "success"
    user = db.query(Usuario).one()
    acceptance = db.query(AcuerdoAceptado).one()
    db.refresh(invitation)
    assert user.nombre == "Persona Google"
    assert user.email == "persona@example.com"
    assert user.auth_user_id == AUTH_USER_ID
    assert user.whatsapp_id == invitation.whatsapp_id
    assert acceptance.usuario_id == user.id
    assert acceptance.version_acuerdo_id == agreement.id
    assert acceptance.aceptado_en.replace(tzinfo=timezone.utc) == NOW
    assert acceptance.origen == "web_onboarding"
    assert invitation.estado == "consumida"
    assert invitation.usuario_id == user.id
    assert invitation.consumida_en.replace(tzinfo=timezone.utc) == NOW
    assert invitation.actualizado_en.replace(tzinfo=timezone.utc) == NOW
    assert invitation.token_hash == original_hash
    assert db.query(MovimientoFinanciero).count() == 0


@pytest.mark.parametrize("matched_by", ["email", "whatsapp", "auth"])
def test_links_one_compatible_existing_user(db, matched_by):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    values = {"email": "persona@example.com"}
    if matched_by == "email":
        values["email"] = "Persona@Example.COM"
    elif matched_by == "whatsapp":
        values["whatsapp_id"] = invitation.whatsapp_id
    else:
        values["auth_user_id"] = AUTH_USER_ID
    user = add_user(db, **values)

    result = finalize(db, invitation, agreement)

    db.refresh(user)
    assert result.status == "success"
    assert db.query(Usuario).count() == 1
    assert user.email == "persona@example.com"
    assert user.auth_user_id == AUTH_USER_ID
    assert user.whatsapp_id == invitation.whatsapp_id
    assert user.nombre == "Persona Google"


@pytest.mark.parametrize(
    "user_values",
    [
        {
            "email": "otra@example.com",
            "auth_user_id": AUTH_USER_ID,
        },
        {
            "email": "otra@example.com",
            "whatsapp_id": "5491112345678",
        },
        {
            "email": "persona@example.com",
            "auth_user_id": uuid.UUID("c9277fba-17e1-4f7f-a19c-6dac97f84168"),
        },
        {
            "email": "persona@example.com",
            "whatsapp_id": "5491199999999",
        },
    ],
)
def test_rejects_incompatible_existing_identifiers(db, user_values):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    add_user(db, **user_values)

    result = finalize(db, invitation, agreement)

    db.refresh(invitation)
    assert result.status == "identity_conflict"
    assert invitation.estado == "pendiente"
    assert db.query(AcuerdoAceptado).count() == 0


def test_rejects_candidates_split_between_users(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    add_user(db, email="persona@example.com")
    add_user(db, whatsapp_id=invitation.whatsapp_id)

    result = finalize(db, invitation, agreement)

    assert result.status == "identity_conflict"
    assert db.query(Usuario).count() == 2


def test_rejects_duplicate_case_insensitive_emails(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    add_user(db, email="persona@example.com")
    add_user(db, email="PERSONA@EXAMPLE.COM")

    result = finalize(db, invitation, agreement)

    assert result.status == "identity_conflict"


def test_display_name_is_normalized_and_falls_back_safely(db):
    assert normalize_display_name("  Ana\x00   María\nPérez  ", "x@example.com") == (
        "Ana María Pérez"
    )
    assert normalize_display_name("\x00\n", "persona.segura@example.com") == (
        "persona.segura"
    )
    assert normalize_display_name(None, "@example.com") == "Usuario Luka"
    assert len(normalize_display_name("A" * 200, "x@example.com")) == 120


def test_existing_acceptance_is_not_duplicated(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    user = add_user(
        db,
        email="persona@example.com",
        whatsapp_id=invitation.whatsapp_id,
    )
    accepted_at = NOW - timedelta(days=1)
    db.add(
        AcuerdoAceptado(
            usuario_id=user.id,
            version_acuerdo_id=agreement.id,
            aceptado_en=accepted_at,
            origen="web_onboarding",
        )
    )
    db.commit()

    result = finalize(db, invitation, agreement)

    acceptance = db.query(AcuerdoAceptado).one()
    assert result.status == "success"
    assert db.query(AcuerdoAceptado).count() == 1
    assert acceptance.aceptado_en.replace(tzinfo=timezone.utc) == accepted_at


@pytest.mark.parametrize("failure_stage", ["user", "acceptance", "invitation"])
def test_database_failure_rolls_back_every_stage(db, failure_stage):
    invitation = add_invitation(db)
    agreement = add_agreement(db)

    @event.listens_for(db, "before_flush")
    def fail_selected_stage(session, _flush_context, _instances):
        if failure_stage == "user" and any(
            isinstance(item, Usuario) for item in session.new
        ):
            raise SQLAlchemyError("user write failed")
        if failure_stage == "acceptance" and any(
            isinstance(item, AcuerdoAceptado) for item in session.new
        ):
            raise SQLAlchemyError("acceptance write failed")
        if failure_stage == "invitation" and any(
            isinstance(item, OnboardingInvitacion) and item.estado == "consumida"
            for item in session.dirty
        ):
            raise SQLAlchemyError("invitation write failed")

    result = finalize(db, invitation, agreement)
    event.remove(db, "before_flush", fail_selected_stage)

    db.expire_all()
    stored = db.get(OnboardingInvitacion, invitation.id)
    assert result.status == "database_error"
    assert db.query(Usuario).count() == 0
    assert db.query(AcuerdoAceptado).count() == 0
    assert stored.estado == "pendiente"
    assert stored.usuario_id is None


def test_integrity_error_is_safe_conflict_and_rolls_back(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)

    @event.listens_for(db, "before_flush")
    def simulate_unique_race(session, _flush_context, _instances):
        if any(isinstance(item, AcuerdoAceptado) for item in session.new):
            raise IntegrityError("private SQL", {}, Exception("private constraint"))

    result = finalize(db, invitation, agreement)
    event.remove(db, "before_flush", simulate_unique_race)

    db.expire_all()
    assert result.status == "identity_conflict"
    assert db.query(Usuario).count() == 0
    assert db.get(OnboardingInvitacion, invitation.id).estado == "pendiente"


def test_second_finalization_is_rejected_without_duplicates(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)

    first = finalize(db, invitation, agreement)
    second = finalize(db, invitation, agreement)

    assert first.status == "success"
    assert second.status == "invitation_consumed"
    assert db.query(Usuario).count() == 1
    assert db.query(AcuerdoAceptado).count() == 1


def test_different_invitation_cannot_relink_same_identity_to_other_whatsapp(db):
    first_invitation = add_invitation(db)
    agreement = add_agreement(db)
    assert finalize(db, first_invitation, agreement).status == "success"
    second_invitation = add_invitation(db, whatsapp_id="5491199999999")

    result = finalize(db, second_invitation, agreement)

    db.refresh(second_invitation)
    assert result.status == "identity_conflict"
    assert db.query(Usuario).count() == 1
    assert db.query(AcuerdoAceptado).count() == 1
    assert second_invitation.estado == "pendiente"
    assert second_invitation.usuario_id is None


def test_existing_financial_data_is_unchanged(db):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    user = add_user(
        db,
        email="persona@example.com",
        whatsapp_id=invitation.whatsapp_id,
    )
    movement = MovimientoFinanciero(
        usuario_id=user.id,
        tipo="egreso",
        cantidad=Decimal("123.45"),
        moneda="ARS",
        descripcion="Movimiento previo",
        fecha_movimiento=NOW.date(),
        origen="whatsapp_text",
        whatsapp_message_id="wamid-existing",
    )
    db.add(movement)
    db.commit()

    result = finalize(db, invitation, agreement)

    db.refresh(movement)
    assert result.status == "success"
    assert db.query(MovimientoFinanciero).count() == 1
    assert movement.usuario_id == user.id
    assert movement.tipo == "egreso"
    assert movement.cantidad == Decimal("123.45")
    assert movement.descripcion == "Movimiento previo"
    assert movement.whatsapp_message_id == "wamid-existing"


def test_invitation_query_uses_for_update(db, monkeypatch):
    invitation = add_invitation(db)
    agreement = add_agreement(db)
    locked_entities = []
    original = Query.with_for_update

    def record_lock(query, *args, **kwargs):
        entity = query.column_descriptions[0].get("entity")
        locked_entities.append(entity)
        return original(query, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", record_lock)

    assert finalize(db, invitation, agreement).status == "success"
    assert OnboardingInvitacion in locked_entities
    assert Usuario in locked_entities
