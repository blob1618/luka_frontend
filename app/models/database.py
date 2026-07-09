import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Column, Integer, String, Float, Numeric, DateTime, Date, Boolean, ForeignKey, create_engine, Uuid
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./luka_dev.db")

if DATABASE_URL.startswith("postgresql"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp_id = Column(String, unique=True, index=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    monto = Column(Float, nullable=False)
    categoria = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    categoria = Column(String, nullable=False)
    monto_limite = Column(Float, nullable=False)


class Recordatorio(Base):
    __tablename__ = "recordatorios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    titulo = Column(String, nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=False)
    activo = Column(Integer, default=1)


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid, nullable=False)
    nombre = Column(String, nullable=False)
    creada_en = Column(DateTime(timezone=True), default=datetime.utcnow)


class LimiteGasto(Base):
    __tablename__ = "limites_gasto"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid, nullable=False)
    categoria_id = Column(Uuid, ForeignKey("categorias.id"))
    monto_maximo = Column(Numeric(10, 2), nullable=False)
    periodo_inicio = Column(Date, nullable=False)
    periodo_fin = Column(Date, nullable=False)
    creado_en = Column(DateTime(timezone=True), default=datetime.utcnow)


class VersionConsentimiento(Base):
    __tablename__ = "versiones_consentimiento"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    version = Column(String, nullable=False)
    contenido = Column(String, nullable=False)
    fecha_publicacion = Column(DateTime(timezone=True), default=datetime.utcnow)
    es_activa = Column(Boolean, default=False)


class ConsentimientoUsuario(Base):
    __tablename__ = "consentimientos_usuario"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Uuid, nullable=False)
    version_id = Column(Uuid, ForeignKey("versiones_consentimiento.id"))
    aceptado = Column(Boolean, default=False)
    fecha_aceptacion = Column(DateTime(timezone=True), default=datetime.utcnow)
