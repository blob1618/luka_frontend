import uuid
from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.types import JSON, Uuid

from app.runtime import get_setting

# Obtener DATABASE_URL del entorno, usando SQLite como fallback para desarrollo local
DATABASE_URL = get_setting("DATABASE_URL", "sqlite:///./luka.db")


def _normalize_database_url(database_url: str, postgres_driver: str = "psycopg") -> str:
    if database_url.startswith(("postgres://", "postgresql://")):
        _, suffix = database_url.split("://", 1)
        return f"postgresql+{postgres_driver}://{suffix}"
    return database_url


def _create_database_engine(database_url: str):
    return create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    )


DATABASE_URL = _normalize_database_url(DATABASE_URL)
engine = _create_database_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def configure_database(database_url: str, *, postgres_driver: str = "psycopg") -> None:
    """Rebind SQLAlchemy once request-scoped Cloudflare bindings are available."""
    global DATABASE_URL, engine, SessionLocal

    normalized_url = _normalize_database_url(database_url, postgres_driver)
    if normalized_url == DATABASE_URL:
        return

    previous_engine = engine
    DATABASE_URL = normalized_url
    engine = _create_database_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    previous_engine.dispose()

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    creado_en = Column(DateTime(timezone=True), default=func.now())
    actualizado_en = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    whatsapp_id = Column(String, nullable=True)
    # La FK real a auth.users existe solo en la migración PostgreSQL canónica de /luka.
    auth_user_id = Column(Uuid(as_uuid=True), nullable=True)


class OnboardingInvitacion(Base):
    __tablename__ = "onboarding_invitacion"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_id = Column(String, nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    estado = Column(String, nullable=False, default="pendiente")
    expira_en = Column(DateTime(timezone=True), nullable=False)
    intentos = Column(Integer, nullable=False, default=0)
    reenvios = Column(Integer, nullable=False, default=0)
    ultimo_envio_en = Column(DateTime(timezone=True), nullable=True)
    usuario_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=True,
    )
    consumida_en = Column(DateTime(timezone=True), nullable=True)
    revocada_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=func.now())
    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )


class DashboardLoginLink(Base):
    __tablename__ = "dashboard_login_link"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String, nullable=False, unique=True)
    estado = Column(String, nullable=False, default="pendiente")
    expira_en = Column(DateTime(timezone=True), nullable=False)
    reenvios = Column(Integer, nullable=False, default=0)
    ultimo_envio_en = Column(DateTime(timezone=True), nullable=True)
    consumido_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=func.now())
    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )


class AcuerdoVersion(Base):
    __tablename__ = "acuerdo_version"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String, nullable=False, unique=True)
    contenido = Column(String, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    esta_vigente = Column(Boolean, nullable=False, default=False)
    vigente_desde = Column(DateTime(timezone=True), nullable=True)


class AcuerdoAceptado(Base):
    __tablename__ = "acuerdo_aceptado"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    version_acuerdo_id = Column(
        Uuid(as_uuid=True), ForeignKey("acuerdo_version.id"), nullable=False
    )
    aceptado_en = Column(DateTime(timezone=True), nullable=False)
    origen = Column(String, nullable=False, default="web_onboarding")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid(as_uuid=True), ForeignKey("usuario.id"))
    nombre = Column(String, nullable=False)
    es_default = Column(Boolean, default=False)
    esta_eliminado = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)


class LimiteCategoria(Base):
    __tablename__ = "limite_categoria"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    categoria_id = Column(
        Uuid(as_uuid=True), ForeignKey("categorias.id"), nullable=False
    )
    cantidad_max = Column(Numeric, nullable=False)
    inicio_periodo = Column(Date, nullable=False)
    fin_periodo = Column(Date, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Recordatorio(Base):
    __tablename__ = "recordatorio"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(String)
    recordar_en = Column(DateTime, nullable=False)
    es_recurrente = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Evento(Base):
    __tablename__ = "evento"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid(as_uuid=True))
    agregar_tipo = Column(String, nullable=False)
    agregar_id = Column(Uuid(as_uuid=True), nullable=False)
    tipo_evento = Column(String, nullable=False)
    carga = Column(JSON)
    creado_en = Column(DateTime, default=datetime.utcnow)


class MovimientoFinanciero(Base):
    __tablename__ = "movimientos_financieros"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    categoria_id = Column(Uuid(as_uuid=True), ForeignKey("categorias.id"))
    tipo = Column(String, nullable=False)
    cantidad = Column(Numeric, nullable=False)
    moneda = Column(String, nullable=False, default="ARS")
    descripcion = Column(String)
    fecha_movimiento = Column(Date, nullable=False, default=date.today)
    origen = Column(String, nullable=False, default="whatsapp_text")
    whatsapp_message_id = Column(String)
    anulado_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=func.now())
    actualizado_en = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
