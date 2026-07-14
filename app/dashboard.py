"""
dashboard.py — Data aggregation logic for the dashboard.

All functions receive a db session + user_id + optional date range
and return plain Python dicts/lists ready to pass into Jinja2 templates.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.database import MovimientoFinanciero, LimiteCategoria, Usuario, Categoria

CATEGORY_COLORS = {
    "Comida": "#6366f1",
    "Transporte": "#8b5cf6",
    "Entretenimiento": "#ec4899",
    "Salud": "#14b8a6",
    "Educación": "#f59e0b",
    "Hogar": "#10b981",
    "Ropa": "#f97316",
    "Otro": "#64748b",
}

# TODO: Reemplazar con cotización cacheada real (ej. desde Redis o tabla de config en BD).
# Por ahora hardcodeado para no llamar a la API externa en tiempo real.
USD_TO_ARS_RATE: float = 1300.0


def get_user(db: Session, whatsapp_id: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.whatsapp_id == whatsapp_id).first()


def get_summary_stats(
    db: Session,
    user_id: uuid.UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Return total spent, number of transactions, top category."""
    q = db.query(MovimientoFinanciero, Categoria).join(
        Categoria, MovimientoFinanciero.categoria_id == Categoria.id, isouter=True
    ).filter(
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == 'egreso'
    )
    if date_from:
        q = q.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
    if date_to:
        q = q.filter(MovimientoFinanciero.fecha_movimiento <= date_to)

    expenses = q.all()
    total = sum(e.MovimientoFinanciero.cantidad for e in expenses) if expenses else Decimal("0")

    # query for income
    q_in = db.query(MovimientoFinanciero).filter(
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == 'ingreso'
    )
    if date_from:
        q_in = q_in.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
    if date_to:
        q_in = q_in.filter(MovimientoFinanciero.fecha_movimiento <= date_to)
    
    incomes = q_in.all()
    total_income = sum(i.cantidad for i in incomes) if incomes else Decimal("0")

    # top category
    cat_totals: dict[str, Decimal] = {}
    for e in expenses:
        cat_name = e.Categoria.nombre if e.Categoria else "Otro"
        cat_totals[cat_name] = cat_totals.get(cat_name, Decimal("0")) + Decimal(str(e.MovimientoFinanciero.cantidad))
    top_category = max(cat_totals, key=cat_totals.get) if cat_totals else "—"

    end_date = min(date_to, date.today()) if date_to else date.today()
    start_date = date_from or end_date
    days_range = max(1, (end_date - start_date).days + 1)

    return {
        "total_spent": float(total),
        "total_income": float(total_income),
        "transaction_count": len(expenses) + len(incomes),
        "top_category": top_category,
        "avg_per_day": float(total / days_range),
    }


def get_expenses_by_category(
    db: Session,
    user_id: uuid.UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    """Return [{category, total, color}] sorted by total desc."""
    q = db.query(
        Categoria.nombre.label("categoria_nombre"),
        func.sum(MovimientoFinanciero.cantidad).label("total")
    ).join(
        Categoria, MovimientoFinanciero.categoria_id == Categoria.id, isouter=True
    ).filter(
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == 'egreso'
    )

    if date_from:
        q = q.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
    if date_to:
        q = q.filter(MovimientoFinanciero.fecha_movimiento <= date_to)

    rows = q.group_by(Categoria.nombre).order_by(func.sum(MovimientoFinanciero.cantidad).desc()).all()
    return [
        {
            "category": r.categoria_nombre or "Otro",
            "total": float(r.total),
            "color": CATEGORY_COLORS.get(r.categoria_nombre or "Otro", "#64748b"),
        }
        for r in rows
    ]


def get_expenses_by_day(
    db: Session,
    user_id: uuid.UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    """Return [{date_label, total}] for the line chart."""
    q = db.query(
        MovimientoFinanciero.fecha_movimiento.label("day"),
        func.sum(MovimientoFinanciero.cantidad).label("total")
    ).filter(
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == 'egreso'
    )

    if date_from:
        q = q.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
    if date_to:
        q = q.filter(MovimientoFinanciero.fecha_movimiento <= date_to)

    rows = q.group_by(MovimientoFinanciero.fecha_movimiento).order_by(MovimientoFinanciero.fecha_movimiento).all()
    return [{"day": str(r.day), "total": float(r.total)} for r in rows]


def get_recent_transactions(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 15,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    q = db.query(MovimientoFinanciero, Categoria).join(
        Categoria, MovimientoFinanciero.categoria_id == Categoria.id, isouter=True
    ).filter(
        MovimientoFinanciero.usuario_id == user_id
    )
    if date_from:
        q = q.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
    if date_to:
        q = q.filter(MovimientoFinanciero.fecha_movimiento <= date_to)

    rows = q.order_by(MovimientoFinanciero.creado_en.desc()).limit(limit).all()
    return [
        {
            "id": str(e.MovimientoFinanciero.id),
            "amount": float(e.MovimientoFinanciero.cantidad),
            "tipo": e.MovimientoFinanciero.tipo,
            "moneda": e.MovimientoFinanciero.moneda,
            "category": e.Categoria.nombre if e.Categoria else "Otro",
            "description": e.MovimientoFinanciero.descripcion or "—",
            "date": e.MovimientoFinanciero.fecha_movimiento.strftime("%d %b %Y"),
            "time": e.MovimientoFinanciero.creado_en.strftime("%H:%M") if e.MovimientoFinanciero.creado_en else "00:00",
            "color": CATEGORY_COLORS.get(e.Categoria.nombre if e.Categoria else "Otro", "#64748b") if e.MovimientoFinanciero.tipo == 'egreso' else "#10b981",
        }
        for e in rows
    ]


def get_budgets_with_usage(
    db: Session,
    user_id: uuid.UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    budgets = db.query(LimiteCategoria, Categoria).join(
        Categoria, LimiteCategoria.categoria_id == Categoria.id, isouter=True
    ).filter(LimiteCategoria.usuario_id == user_id).all()
    
    result = []
    for b in budgets:
        q = db.query(func.sum(MovimientoFinanciero.cantidad)).filter(
            MovimientoFinanciero.usuario_id == user_id,
            MovimientoFinanciero.categoria_id == b.LimiteCategoria.categoria_id,
            MovimientoFinanciero.tipo == 'egreso'
        )
        if date_from:
            q = q.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
        if date_to:
            q = q.filter(MovimientoFinanciero.fecha_movimiento <= date_to)

        spent = float(q.scalar() or 0)
        limit = float(b.LimiteCategoria.cantidad_max)
        pct = min(round((spent / limit) * 100) if limit > 0 else 0, 100)
        
        cat_name = b.Categoria.nombre if b.Categoria else "Otro"
        result.append({
            "category": cat_name,
            "limit": limit,
            "spent": spent,
            "remaining": max(limit - spent, 0),
            "pct": pct,
            "color": CATEGORY_COLORS.get(cat_name, "#64748b"),
            "over": spent > limit,
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# NEW KPIs
# ─────────────────────────────────────────────────────────────────────────────

def get_patrimonio_neto(db: Session, user_id: uuid.UUID) -> dict:
    """
    Total de capital neto expresado en ARS.
    Suma ingresos - egresos. Los movimientos en USD se convierten usando
    la cotización hardcodeada USD_TO_ARS_RATE.

    TODO: Integrar cotización cacheada real desde Redis / tabla de config en BD.
          No debe llamar a la API externa en tiempo real.
    """
    rows = db.query(
        MovimientoFinanciero.tipo,
        MovimientoFinanciero.moneda,
        func.sum(MovimientoFinanciero.cantidad).label("total"),
    ).filter(
        MovimientoFinanciero.usuario_id == user_id,
    ).group_by(
        MovimientoFinanciero.tipo,
        MovimientoFinanciero.moneda,
    ).all()

    patrimonio = Decimal("0")
    usd_rate = Decimal(str(USD_TO_ARS_RATE))

    for r in rows:
        amount = Decimal(str(r.total or 0))
        if r.moneda and r.moneda.upper() == "USD":
            amount_ars = amount * usd_rate
        else:
            amount_ars = amount

        if r.tipo == "ingreso":
            patrimonio += amount_ars
        else:
            patrimonio -= amount_ars

    return {
        "total_ars": float(patrimonio),
        "usd_rate": float(USD_TO_ARS_RATE),
        "is_positive": patrimonio >= 0,
    }


def get_consumo_presupuesto(
    db: Session,
    user_id: uuid.UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """
    Porcentaje global gastado sobre el límite mensual total de todos los presupuestos.
    """
    budgets = db.query(LimiteCategoria).filter(LimiteCategoria.usuario_id == user_id).all()
    if not budgets:
        return {"pct": 0, "spent": 0.0, "limit": 0.0}

    total_limit = sum(float(b.cantidad_max) for b in budgets)
    if total_limit == 0:
        return {"pct": 0, "spent": 0.0, "limit": 0.0}

    # Sum all egress movements for those categories
    categoria_ids = [b.categoria_id for b in budgets]
    q = db.query(func.sum(MovimientoFinanciero.cantidad)).filter(
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == "egreso",
        MovimientoFinanciero.categoria_id.in_(categoria_ids),
    )
    if date_from:
        q = q.filter(MovimientoFinanciero.fecha_movimiento >= date_from)
    if date_to:
        q = q.filter(MovimientoFinanciero.fecha_movimiento <= date_to)

    total_spent = float(q.scalar() or 0)
    pct = min(round((total_spent / total_limit) * 100), 100)

    return {
        "pct": pct,
        "spent": total_spent,
        "limit": total_limit,
        "over": total_spent > total_limit,
    }


def get_monthly_flow(
    db: Session,
    user_id: uuid.UUID,
    months: int = 6,
) -> list[dict]:
    """
    Ingresos vs Egresos por mes (últimos N meses).
    Devuelve [{month, ingresos, egresos}] para el gráfico de barras agrupadas.
    """
    rows = db.query(
        extract("year", MovimientoFinanciero.fecha_movimiento).label("year"),
        extract("month", MovimientoFinanciero.fecha_movimiento).label("month"),
        MovimientoFinanciero.tipo,
        func.sum(MovimientoFinanciero.cantidad).label("total"),
    ).filter(
        MovimientoFinanciero.usuario_id == user_id,
    ).group_by("year", "month", MovimientoFinanciero.tipo).order_by("year", "month").all()

    # Build a dict keyed by (year, month)
    flow_map: dict[tuple, dict] = {}
    for r in rows:
        key = (int(r.year), int(r.month))
        if key not in flow_map:
            flow_map[key] = {"ingresos": 0.0, "egresos": 0.0}
        if r.tipo == "ingreso":
            flow_map[key]["ingresos"] = float(r.total or 0)
        else:
            flow_map[key]["egresos"] = float(r.total or 0)

    # Sort and take last N months
    MONTH_NAMES_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    sorted_keys = sorted(flow_map.keys())[-months:]
    return [
        {
            "month": f"{MONTH_NAMES_ES[k[1]-1]} {k[0]}",
            "ingresos": flow_map[k]["ingresos"],
            "egresos": flow_map[k]["egresos"],
        }
        for k in sorted_keys
    ]


def get_portfolio_by_currency(
    db: Session,
    user_id: uuid.UUID,
    months: int = 6,
) -> list[dict]:
    """
    Composición de cartera por moneda (ARS vs USD) mes a mes.
    Devuelve [{month, ARS, USD}] para el gráfico de barras apiladas.
    Solo egresos para ver distribución de gasto, o todos los movimientos para patrimonio.
    """
    rows = db.query(
        extract("year", MovimientoFinanciero.fecha_movimiento).label("year"),
        extract("month", MovimientoFinanciero.fecha_movimiento).label("month"),
        MovimientoFinanciero.moneda,
        func.sum(MovimientoFinanciero.cantidad).label("total"),
    ).filter(
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == "egreso",
    ).group_by("year", "month", MovimientoFinanciero.moneda).order_by("year", "month").all()

    portfolio_map: dict[tuple, dict] = {}
    usd_rate = float(USD_TO_ARS_RATE)
    for r in rows:
        key = (int(r.year), int(r.month))
        if key not in portfolio_map:
            portfolio_map[key] = {"ARS": 0.0, "USD": 0.0}
        moneda = (r.moneda or "ARS").upper()
        amount = float(r.total or 0)

        if moneda == "USD":
            portfolio_map[key]["USD"] += amount * usd_rate
        else:
            portfolio_map[key]["ARS"] += amount

    MONTH_NAMES_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    sorted_keys = sorted(portfolio_map.keys())[-months:]
    return [
        {
            "month": f"{MONTH_NAMES_ES[k[1]-1]} {k[0]}",
            "ARS": portfolio_map[k].get("ARS", 0.0),
            "USD": portfolio_map[k].get("USD", 0.0),
        }
        for k in sorted_keys
    ]


def get_dias_racha(db: Session, user_id: uuid.UUID) -> int:
    """
    TODO: Implementar conteo de días consecutivos con al menos 1 movimiento registrado.
          Determinar qué tipo de movimiento cuenta para mantener la racha (ingreso/egreso/ambos).
          Por ahora retorna 0 como placeholder.
    """
    return 0
