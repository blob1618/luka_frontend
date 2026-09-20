"""
Tests for STK-177: Exclusion of canceled movements (anulado_en is not null)
from dashboard queries, KPIs, charts, and CSV export.
"""

import csv
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import create_session_token
from app.dashboard import (
    get_budgets_with_usage,
    get_consumo_presupuesto,
    get_expenses_by_category,
    get_expenses_by_day,
    get_monthly_flow,
    get_patrimonio_neto,
    get_portfolio_by_currency,
    get_recent_transactions,
    get_summary_stats,
)
from app.main import app
from app.models.database import (
    Base,
    Categoria,
    LimiteCategoria,
    MovimientoFinanciero,
    Usuario,
    get_db,
)


@pytest.fixture(autouse=True)
def auth_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_key")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("ENABLE_MOCK_AUTH", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-stk-177")


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_dashboard_queries.db'}",
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


def create_user(db, **overrides):
    values = {
        "nombre": "Test User",
        "email": f"{uuid.uuid4()}@example.com",
        "whatsapp_id": f"wa-{uuid.uuid4()}",
        "auth_user_id": uuid.uuid4(),
    }
    values.update(overrides)
    user = Usuario(**values)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_category(db, user_id, nombre, **overrides):
    values = {
        "usuario_id": user_id,
        "nombre": nombre,
        "es_default": False,
        "esta_eliminado": False,
    }
    values.update(overrides)
    cat = Categoria(**values)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def create_movement(db, user_id, **overrides):
    values = {
        "usuario_id": user_id,
        "tipo": "egreso",
        "cantidad": Decimal("1000.00"),
        "moneda": "ARS",
        "descripcion": "Movimiento de prueba",
        "fecha_movimiento": date(2026, 5, 15),
        "origen": "whatsapp_text",
        "anulado_en": None,
    }
    values.update(overrides)
    mov = MovimientoFinanciero(**values)
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov


def create_budget(db, user_id, categoria_id, cantidad_max, **overrides):
    values = {
        "usuario_id": user_id,
        "categoria_id": categoria_id,
        "cantidad_max": Decimal(str(cantidad_max)),
        "inicio_periodo": date(2026, 5, 1),
        "fin_periodo": date(2026, 5, 31),
    }
    values.update(overrides)
    budget = LimiteCategoria(**values)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


# --- 1. get_summary_stats -----------------------------------------------------


def test_get_summary_stats_excludes_anulados(db):
    user = create_user(db)
    cat = create_category(db, user.id, "Comida")
    now = datetime.now(timezone.utc)

    # Active egreso: 5000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("5000.00"),
        categoria_id=cat.id,
        fecha_movimiento=date(2026, 5, 10),
    )
    # Anulado egreso: 3000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("3000.00"),
        categoria_id=cat.id,
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 10),
    )
    # Active ingreso: 12000
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        cantidad=Decimal("12000.00"),
        fecha_movimiento=date(2026, 5, 10),
    )
    # Anulado ingreso: 7000
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        cantidad=Decimal("7000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 10),
    )

    stats = get_summary_stats(
        db,
        user.id,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert stats["total_spent"] == 5000.0
    assert stats["total_income"] == 12000.0
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Comida"


# --- 2. get_expenses_by_category ----------------------------------------------


def test_get_expenses_by_category_excludes_anulados(db):
    user = create_user(db)
    cat_food = create_category(db, user.id, "Comida")
    cat_transport = create_category(db, user.id, "Transporte")
    cat_health = create_category(db, user.id, "Salud")
    now = datetime.now(timezone.utc)

    # Comida: Active 4000, Anulado 10000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("4000.00"),
        categoria_id=cat_food.id,
    )
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("10000.00"),
        categoria_id=cat_food.id,
        anulado_en=now,
    )

    # Transporte: Active 6000, Anulado 2000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("6000.00"),
        categoria_id=cat_transport.id,
    )
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("2000.00"),
        categoria_id=cat_transport.id,
        anulado_en=now,
    )

    # Salud: Only Anulado 5000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("5000.00"),
        categoria_id=cat_health.id,
        anulado_en=now,
    )

    result = get_expenses_by_category(db, user.id)

    assert len(result) == 2
    assert result[0]["category"] == "Transporte"
    assert result[0]["total"] == 6000.0
    assert result[1]["category"] == "Comida"
    assert result[1]["total"] == 4000.0


# --- 3. get_expenses_by_day ---------------------------------------------------


def test_get_expenses_by_day_excludes_anulados(db):
    user = create_user(db)
    now = datetime.now(timezone.utc)

    # Day 1: Active 1500, Anulado 2500
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("1500.00"),
        fecha_movimiento=date(2026, 5, 10),
    )
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("2500.00"),
        fecha_movimiento=date(2026, 5, 10),
        anulado_en=now,
    )

    # Day 2: Only Anulado 4000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("4000.00"),
        fecha_movimiento=date(2026, 5, 11),
        anulado_en=now,
    )

    result = get_expenses_by_day(db, user.id)

    assert len(result) == 1
    assert result[0]["day"] == "2026-05-10"
    assert result[0]["total"] == 1500.0


# --- 4. get_recent_transactions -----------------------------------------------


def test_get_recent_transactions_excludes_anulados(db):
    user = create_user(db)
    now = datetime.now(timezone.utc)

    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("1200.00"),
        descripcion="Activo egreso",
    )
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("9999.00"),
        descripcion="Anulado egreso",
        anulado_en=now,
    )
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        cantidad=Decimal("3500.00"),
        descripcion="Activo ingreso",
    )
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        cantidad=Decimal("8888.00"),
        descripcion="Anulado ingreso",
        anulado_en=now,
    )

    result = get_recent_transactions(db, user.id)

    amounts = [r["amount"] for r in result]
    descriptions = [r["description"] for r in result]

    assert len(result) == 2
    assert 1200.0 in amounts
    assert 3500.0 in amounts
    assert 9999.0 not in amounts
    assert 8888.0 not in amounts
    assert "Activo egreso" in descriptions
    assert "Activo ingreso" in descriptions
    assert "Anulado egreso" not in descriptions
    assert "Anulado ingreso" not in descriptions


# --- 5. get_budgets_with_usage ------------------------------------------------


def test_get_budgets_with_usage_excludes_anulados(db):
    user = create_user(db)
    cat = create_category(db, user.id, "Comida")
    create_budget(db, user.id, cat.id, 10000.0)
    now = datetime.now(timezone.utc)

    # Active egreso: 4000
    create_movement(
        db,
        user.id,
        categoria_id=cat.id,
        tipo="egreso",
        cantidad=Decimal("4000.00"),
        fecha_movimiento=date(2026, 5, 10),
    )
    # Anulado egreso: 8000 (would exceed 10000 limit if included)
    create_movement(
        db,
        user.id,
        categoria_id=cat.id,
        tipo="egreso",
        cantidad=Decimal("8000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 10),
    )

    result = get_budgets_with_usage(
        db,
        user.id,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert len(result) == 1
    assert result[0]["category"] == "Comida"
    assert result[0]["limit"] == 10000.0
    assert result[0]["spent"] == 4000.0
    assert result[0]["remaining"] == 6000.0
    assert result[0]["pct"] == 40
    assert result[0]["over"] is False


# --- 6. get_patrimonio_neto ---------------------------------------------------


def test_get_patrimonio_neto_excludes_anulados(db):
    user = create_user(db)
    now = datetime.now(timezone.utc)

    # Active ingreso ARS: 20000
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        moneda="ARS",
        cantidad=Decimal("20000.00"),
    )
    # Anulado ingreso ARS: 50000
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        moneda="ARS",
        cantidad=Decimal("50000.00"),
        anulado_en=now,
    )
    # Active egreso ARS: 5000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="ARS",
        cantidad=Decimal("5000.00"),
    )
    # Anulado egreso ARS: 15000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="ARS",
        cantidad=Decimal("15000.00"),
        anulado_en=now,
    )

    # Active ingreso USD: 10 (at rate 1300 = 13000 ARS)
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        moneda="USD",
        cantidad=Decimal("10.00"),
    )
    # Anulado ingreso USD: 100
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        moneda="USD",
        cantidad=Decimal("100.00"),
        anulado_en=now,
    )
    # Active egreso USD: 2 (at rate 1300 = 2600 ARS)
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="USD",
        cantidad=Decimal("2.00"),
    )
    # Anulado egreso USD: 20
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="USD",
        cantidad=Decimal("20.00"),
        anulado_en=now,
    )

    # Expected:
    # ARS net: 20000 - 5000 = 15000
    # USD net: (10 - 2) * 1300 = 10400
    # Total ARS: 15000 + 10400 = 25400.0
    result = get_patrimonio_neto(db, user.id)

    assert result["total_ars"] == 25400.0
    assert result["is_positive"] is True


# --- 7. get_consumo_presupuesto -----------------------------------------------


def test_get_consumo_presupuesto_excludes_anulados(db):
    user = create_user(db)
    cat = create_category(db, user.id, "Comida")
    create_budget(db, user.id, cat.id, 10000.0)
    now = datetime.now(timezone.utc)

    # Active egreso: 3000
    create_movement(
        db,
        user.id,
        categoria_id=cat.id,
        tipo="egreso",
        cantidad=Decimal("3000.00"),
        fecha_movimiento=date(2026, 5, 10),
    )
    # Anulado egreso: 9000
    create_movement(
        db,
        user.id,
        categoria_id=cat.id,
        tipo="egreso",
        cantidad=Decimal("9000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 10),
    )

    result = get_consumo_presupuesto(
        db,
        user.id,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert result["limit"] == 10000.0
    assert result["spent"] == 3000.0
    assert result["pct"] == 30
    assert result["over"] is False


# --- 8. get_monthly_flow ------------------------------------------------------


def test_get_monthly_flow_excludes_anulados(db):
    user = create_user(db)
    now = datetime.now(timezone.utc)

    # Active ingreso: 10000
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        cantidad=Decimal("10000.00"),
        fecha_movimiento=date(2026, 5, 5),
    )
    # Anulado ingreso: 5000
    create_movement(
        db,
        user.id,
        tipo="ingreso",
        cantidad=Decimal("5000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 6),
    )
    # Active egreso: 4000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("4000.00"),
        fecha_movimiento=date(2026, 5, 15),
    )
    # Anulado egreso: 6000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        cantidad=Decimal("6000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 16),
    )

    result = get_monthly_flow(
        db,
        user.id,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert len(result) == 1
    assert result[0]["month"] == "May 2026"
    assert result[0]["ingresos"] == 10000.0
    assert result[0]["egresos"] == 4000.0


# --- 9. get_portfolio_by_currency ---------------------------------------------


def test_get_portfolio_by_currency_excludes_anulados(db):
    user = create_user(db)
    now = datetime.now(timezone.utc)

    # Active egreso ARS: 3000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="ARS",
        cantidad=Decimal("3000.00"),
        fecha_movimiento=date(2026, 5, 10),
    )
    # Anulado egreso ARS: 8000
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="ARS",
        cantidad=Decimal("8000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 10),
    )
    # Active egreso USD: 10 (at 1300 = 13000 ARS)
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="USD",
        cantidad=Decimal("10.00"),
        fecha_movimiento=date(2026, 5, 12),
    )
    # Anulado egreso USD: 50
    create_movement(
        db,
        user.id,
        tipo="egreso",
        moneda="USD",
        cantidad=Decimal("50.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 12),
    )

    result = get_portfolio_by_currency(
        db,
        user.id,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert len(result) == 1
    assert result[0]["month"] == "May 2026"
    assert result[0]["ARS"] == 3000.0
    assert result[0]["USD"] == 13000.0


# --- 10. exportar_csv endpoint ------------------------------------------------


def test_exportar_csv_endpoint_excludes_anulados(client, db):
    user_a = create_user(db, email="user_a@example.com")
    user_b = create_user(db, email="user_b@example.com")
    cat_a = create_category(db, user_a.id, "Servicios")
    cat_b = create_category(db, user_b.id, "Servicios")
    now = datetime.now(timezone.utc)

    # User A: Active movement
    create_movement(
        db,
        user_a.id,
        tipo="egreso",
        cantidad=Decimal("1500.00"),
        moneda="ARS",
        categoria_id=cat_a.id,
        descripcion="Gasto Activo A",
        fecha_movimiento=date(2026, 5, 10),
    )
    # User A: Anulado movement
    create_movement(
        db,
        user_a.id,
        tipo="egreso",
        cantidad=Decimal("9999.00"),
        moneda="ARS",
        categoria_id=cat_a.id,
        descripcion="Gasto Anulado A",
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 11),
    )
    # User B: Active movement (isolation check)
    create_movement(
        db,
        user_b.id,
        tipo="egreso",
        cantidad=Decimal("4200.00"),
        moneda="ARS",
        categoria_id=cat_b.id,
        descripcion="Gasto Activo B",
        fecha_movimiento=date(2026, 5, 10),
    )

    # Authenticate as User A
    session_token = create_session_token(str(user_a.auth_user_id))
    client.cookies.set("luka_session", session_token)

    response = client.get(
        "/exportar/csv",
        params={"date_from": "2026-05-01", "date_to": "2026-05-31"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    csv_reader = csv.DictReader(io.StringIO(response.text))
    rows = list(csv_reader)

    assert len(rows) == 1
    assert rows[0]["Descripcion"] == "Gasto Activo A"
    assert float(rows[0]["Monto"]) == 1500.0
    assert rows[0]["Categoria"] == "Servicios"
    assert rows[0]["Moneda"] == "ARS"
    assert rows[0]["Fecha"] == "2026-05-10"

    # Verify anulado and other user's data are completely absent
    csv_raw = response.text
    assert "Gasto Anulado A" not in csv_raw
    assert "9999" not in csv_raw
    assert "Gasto Activo B" not in csv_raw
    assert "4200" not in csv_raw


# --- 11. Isolation and date range preservation -------------------------------


def test_queries_preserve_user_isolation_and_date_ranges(db):
    user_a = create_user(db, email="iso_a@example.com")
    user_b = create_user(db, email="iso_b@example.com")
    now = datetime.now(timezone.utc)

    # User A - inside range, active
    create_movement(
        db,
        user_a.id,
        tipo="egreso",
        cantidad=Decimal("1000.00"),
        fecha_movimiento=date(2026, 5, 15),
    )
    # User A - inside range, anulado
    create_movement(
        db,
        user_a.id,
        tipo="egreso",
        cantidad=Decimal("3000.00"),
        anulado_en=now,
        fecha_movimiento=date(2026, 5, 15),
    )
    # User A - outside range, active
    create_movement(
        db,
        user_a.id,
        tipo="egreso",
        cantidad=Decimal("2000.00"),
        fecha_movimiento=date(2026, 4, 15),
    )
    # User B - inside range, active
    create_movement(
        db,
        user_b.id,
        tipo="egreso",
        cantidad=Decimal("7000.00"),
        fecha_movimiento=date(2026, 5, 15),
    )

    stats = get_summary_stats(
        db,
        user_a.id,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert stats["total_spent"] == 1000.0
    assert stats["transaction_count"] == 1
