"""Siembra la base SQLite local con un usuario dev y datos de ejemplo.

Uso, desde la raíz del proyecto:

    python -m scripts.seed_dev

Luego abrí http://localhost:8001/dev-login
"""

import uuid
from datetime import date
from decimal import Decimal

from app.auth import MOCK_AUTH_USER_ID
from app.models.database import (
    Base,
    Categoria,
    LimiteCategoria,
    MovimientoFinanciero,
    SessionLocal,
    Usuario,
    engine,
)


def main() -> None:
    backend = engine.url.get_backend_name()
    if backend != "sqlite":
        raise SystemExit(
            f"seed_dev solo escribe en SQLite local, no en {backend!r}. "
            "Quitá DATABASE_URL del .env o apuntala a sqlite:///./luka.db"
        )

    auth_uuid = uuid.UUID(MOCK_AUTH_USER_ID)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        user = db.query(Usuario).filter(Usuario.auth_user_id == auth_uuid).first()
        if user is None:
            user = Usuario(
                nombre="Usuario Dev",
                email="dev@luka.local",
                whatsapp_id="5490000000000",
                auth_user_id=auth_uuid,
            )
            db.add(user)
            db.flush()

        if db.query(Categoria).filter(Categoria.usuario_id == user.id).count():
            print(f"Ya hay datos para {user.email}; no se siembra de nuevo.")
            print("Abrí http://localhost:8001/dev-login")
            return

        comida = Categoria(usuario_id=user.id, nombre="Comida", es_default=True)
        transporte = Categoria(usuario_id=user.id, nombre="Transporte", es_default=True)
        otro = Categoria(usuario_id=user.id, nombre="Otro", es_default=True)
        db.add_all([comida, transporte, otro])
        db.flush()

        hoy = date.today()
        primero = hoy.replace(day=1)
        db.add_all(
            [
                LimiteCategoria(
                    usuario_id=user.id,
                    categoria_id=comida.id,
                    cantidad_max=Decimal("50000"),
                    inicio_periodo=primero,
                    fin_periodo=hoy,
                ),
                LimiteCategoria(
                    usuario_id=user.id,
                    categoria_id=transporte.id,
                    cantidad_max=Decimal("20000"),
                    inicio_periodo=primero,
                    fin_periodo=hoy,
                ),
            ]
        )
        db.add_all(
            [
                MovimientoFinanciero(
                    usuario_id=user.id,
                    tipo="ingreso",
                    cantidad=Decimal("850000"),
                    moneda="ARS",
                    descripcion="Sueldo",
                    fecha_movimiento=hoy,
                ),
                MovimientoFinanciero(
                    usuario_id=user.id,
                    categoria_id=comida.id,
                    tipo="egreso",
                    cantidad=Decimal("12500"),
                    moneda="ARS",
                    descripcion="Supermercado",
                    fecha_movimiento=hoy,
                ),
                MovimientoFinanciero(
                    usuario_id=user.id,
                    categoria_id=transporte.id,
                    tipo="egreso",
                    cantidad=Decimal("4800"),
                    moneda="ARS",
                    descripcion="SUBE",
                    fecha_movimiento=hoy,
                ),
                MovimientoFinanciero(
                    usuario_id=user.id,
                    categoria_id=otro.id,
                    tipo="egreso",
                    cantidad=Decimal("7000"),
                    moneda="ARS",
                    descripcion="Farmacia",
                    fecha_movimiento=hoy,
                ),
                MovimientoFinanciero(
                    usuario_id=user.id,
                    categoria_id=comida.id,
                    tipo="egreso",
                    cantidad=Decimal("3200"),
                    moneda="ARS",
                    descripcion="Verdulería",
                    fecha_movimiento=primero,
                ),
                MovimientoFinanciero(
                    usuario_id=user.id,
                    tipo="ingreso",
                    cantidad=Decimal("150"),
                    moneda="USD",
                    descripcion="Freelance",
                    fecha_movimiento=primero,
                ),
            ]
        )
        db.commit()
        print(f"Listo. Usuario dev: {user.email} (auth_user_id={auth_uuid})")
        print("Abrí http://localhost:8001/dev-login")


if __name__ == "__main__":
    main()
