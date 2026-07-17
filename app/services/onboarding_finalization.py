import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional
from unicodedata import category

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.database import (
    AcuerdoAceptado,
    AcuerdoVersion,
    OnboardingInvitacion,
    Usuario,
)


FinalizationStatus = Literal[
    "success",
    "invalid_identity",
    "invitation_not_found",
    "invitation_revoked",
    "invitation_expired",
    "invitation_consumed",
    "invitation_invalid",
    "agreement_not_found",
    "agreement_changed",
    "identity_conflict",
    "database_error",
]


@dataclass(frozen=True)
class VerifiedIdentity:
    auth_user_id: str
    provider: str
    email: str


@dataclass(frozen=True)
class OnboardingFinalizationResult:
    status: FinalizationStatus
    user_id: Optional[uuid.UUID] = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clean_profile_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    without_controls = "".join(
        " " if category(character).startswith("C") else character
        for character in value
    )
    return " ".join(without_controls.split())[:120].strip()


def normalize_display_name(value: object, verified_email: str) -> str:
    """Normalize untrusted profile text without using it for identity decisions."""
    normalized = _clean_profile_text(value)
    if normalized:
        return normalized
    email_local_part = verified_email.strip().split("@", 1)[0]
    return _clean_profile_text(email_local_part) or "Usuario Luka"


def _parse_identity(identity: VerifiedIdentity) -> tuple[uuid.UUID, str] | None:
    if identity.provider != "google":
        return None
    try:
        auth_user_id = uuid.UUID(identity.auth_user_id)
    except (AttributeError, TypeError, ValueError):
        return None
    normalized_email = identity.email.strip().lower()
    if (
        not normalized_email
        or len(normalized_email) > 320
        or normalized_email.count("@") != 1
        or any(character in normalized_email for character in "\r\n\0")
    ):
        return None
    local_part, domain = normalized_email.split("@", 1)
    if not local_part or not domain:
        return None
    return auth_user_id, normalized_email


def finalize_onboarding(
    db: Session,
    invitation_id: object,
    agreement_version_id: object,
    verified_identity: VerifiedIdentity,
    display_name: object,
    now: Optional[datetime] = None,
) -> OnboardingFinalizationResult:
    """Atomically link an identity, record consent, and consume an invitation."""
    try:
        parsed_invitation_id = uuid.UUID(str(invitation_id))
        parsed_agreement_id = uuid.UUID(str(agreement_version_id))
    except (AttributeError, TypeError, ValueError):
        return OnboardingFinalizationResult(status="invitation_not_found")

    parsed_identity = _parse_identity(verified_identity)
    if parsed_identity is None:
        return OnboardingFinalizationResult(status="invalid_identity")
    auth_user_id, normalized_email = parsed_identity
    current_time = _as_utc(now or datetime.now(timezone.utc))
    normalized_name = normalize_display_name(display_name, normalized_email)

    try:
        with db.begin():
            invitation = (
                db.query(OnboardingInvitacion)
                .filter(OnboardingInvitacion.id == parsed_invitation_id)
                .with_for_update()
                .one_or_none()
            )
            if invitation is None:
                return OnboardingFinalizationResult(status="invitation_not_found")
            if invitation.estado == "revocada" or invitation.revocada_en is not None:
                return OnboardingFinalizationResult(status="invitation_revoked")
            if invitation.estado == "consumida":
                return OnboardingFinalizationResult(status="invitation_consumed")
            if invitation.estado == "vencida":
                return OnboardingFinalizationResult(status="invitation_expired")
            if invitation.estado != "pendiente":
                return OnboardingFinalizationResult(status="invitation_invalid")
            if invitation.usuario_id is not None or invitation.consumida_en is not None:
                return OnboardingFinalizationResult(status="invitation_invalid")
            if _as_utc(invitation.expira_en) <= current_time:
                return OnboardingFinalizationResult(status="invitation_expired")

            agreement = (
                db.query(AcuerdoVersion)
                .filter(AcuerdoVersion.id == parsed_agreement_id)
                .with_for_update()
                .one_or_none()
            )
            if agreement is None:
                return OnboardingFinalizationResult(status="agreement_not_found")
            if not agreement.esta_vigente or agreement.vigente_desde is None:
                return OnboardingFinalizationResult(status="agreement_changed")

            candidates = (
                db.query(Usuario)
                .filter(
                    or_(
                        Usuario.auth_user_id == auth_user_id,
                        func.lower(Usuario.email) == normalized_email,
                        Usuario.whatsapp_id == invitation.whatsapp_id,
                    )
                )
                .with_for_update()
                .all()
            )
            if len(candidates) > 1:
                return OnboardingFinalizationResult(status="identity_conflict")

            if not candidates:
                user = Usuario(
                    nombre=normalized_name,
                    email=normalized_email,
                    auth_user_id=auth_user_id,
                    whatsapp_id=invitation.whatsapp_id,
                )
                db.add(user)
                db.flush()
            else:
                user = candidates[0]
                compatible = (
                    user.auth_user_id in (None, auth_user_id)
                    and user.whatsapp_id in (None, invitation.whatsapp_id)
                    and user.email.strip().lower() == normalized_email
                )
                if not compatible:
                    return OnboardingFinalizationResult(status="identity_conflict")
                user.auth_user_id = auth_user_id
                user.whatsapp_id = invitation.whatsapp_id
                user.email = normalized_email
                user.nombre = normalized_name

            acceptance = (
                db.query(AcuerdoAceptado)
                .filter(
                    AcuerdoAceptado.usuario_id == user.id,
                    AcuerdoAceptado.version_acuerdo_id == agreement.id,
                )
                .with_for_update()
                .one_or_none()
            )
            if acceptance is None:
                db.add(
                    AcuerdoAceptado(
                        usuario_id=user.id,
                        version_acuerdo_id=agreement.id,
                        aceptado_en=current_time,
                        origen="web_onboarding",
                    )
                )

            invitation.estado = "consumida"
            invitation.usuario_id = user.id
            invitation.consumida_en = current_time
            invitation.actualizado_en = current_time
            db.flush()
            user_id = user.id
        return OnboardingFinalizationResult(status="success", user_id=user_id)
    except IntegrityError:
        db.rollback()
        return OnboardingFinalizationResult(status="identity_conflict")
    except SQLAlchemyError:
        db.rollback()
        return OnboardingFinalizationResult(status="database_error")
