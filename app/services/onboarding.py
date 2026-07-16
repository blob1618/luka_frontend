import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.database import AcuerdoVersion, OnboardingInvitacion


MAX_TOKEN_LENGTH = 4096


@dataclass(frozen=True)
class RegistrationValidation:
    status: str
    invitation_id: Optional[uuid.UUID] = None
    agreement_version_id: Optional[uuid.UUID] = None
    invitation_expires_at: Optional[datetime] = None
    agreement_version: Optional[str] = None
    agreement_content: Optional[str] = None
    agreement_effective_from: Optional[datetime] = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_registration_token(
    db: Session,
    token: Optional[str],
    *,
    now: Optional[datetime] = None,
) -> RegistrationValidation:
    """Validate an onboarding token without mutating invitation state."""
    if not token or not token.strip() or len(token) > MAX_TOKEN_LENGTH:
        return RegistrationValidation(status="invalid")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    try:
        invitation = (
            db.query(OnboardingInvitacion)
            .filter(OnboardingInvitacion.token_hash == token_hash)
            .one_or_none()
        )

        if invitation is None or invitation.estado == "revocada":
            return RegistrationValidation(status="invalid")
        if invitation.estado == "consumida":
            return RegistrationValidation(status="consumed")
        if invitation.estado == "vencida":
            return RegistrationValidation(status="expired")
        if invitation.estado != "pendiente":
            return RegistrationValidation(status="invalid")

        current_time = _as_utc(now or datetime.now(timezone.utc))
        if _as_utc(invitation.expira_en) <= current_time:
            return RegistrationValidation(status="expired")

        agreement = (
            db.query(AcuerdoVersion)
            .filter(AcuerdoVersion.esta_vigente.is_(True))
            .one_or_none()
        )
        if agreement is None:
            return RegistrationValidation(status="terms_unavailable")

        return RegistrationValidation(
            status="valid",
            invitation_id=invitation.id,
            agreement_version_id=agreement.id,
            invitation_expires_at=invitation.expira_en,
            agreement_version=agreement.version,
            agreement_content=agreement.contenido,
            agreement_effective_from=agreement.vigente_desde,
        )
    except SQLAlchemyError:
        return RegistrationValidation(status="error")


def validate_registration_context(
    db: Session,
    invitation_id: str,
    agreement_version_id: str,
    *,
    now: Optional[datetime] = None,
) -> RegistrationValidation:
    """Revalidate signed onboarding identifiers without trusting cookie state."""
    try:
        parsed_invitation_id = uuid.UUID(invitation_id)
        parsed_agreement_id = uuid.UUID(agreement_version_id)
    except (TypeError, ValueError, AttributeError):
        return RegistrationValidation(status="invalid")

    try:
        invitation = (
            db.query(OnboardingInvitacion)
            .filter(OnboardingInvitacion.id == parsed_invitation_id)
            .one_or_none()
        )
        if invitation is None or invitation.estado == "revocada":
            return RegistrationValidation(status="invalid")
        if invitation.estado == "consumida":
            return RegistrationValidation(status="consumed")
        if invitation.estado == "vencida":
            return RegistrationValidation(status="expired")
        if invitation.estado != "pendiente":
            return RegistrationValidation(status="invalid")

        current_time = _as_utc(now or datetime.now(timezone.utc))
        if _as_utc(invitation.expira_en) <= current_time:
            return RegistrationValidation(status="expired")

        agreement = (
            db.query(AcuerdoVersion)
            .filter(
                AcuerdoVersion.id == parsed_agreement_id,
                AcuerdoVersion.esta_vigente.is_(True),
            )
            .one_or_none()
        )
        if agreement is None:
            return RegistrationValidation(status="terms_unavailable")

        return RegistrationValidation(
            status="valid",
            invitation_id=invitation.id,
            agreement_version_id=agreement.id,
            invitation_expires_at=invitation.expira_en,
            agreement_version=agreement.version,
            agreement_content=agreement.contenido,
            agreement_effective_from=agreement.vigente_desde,
        )
    except SQLAlchemyError:
        return RegistrationValidation(status="error")
