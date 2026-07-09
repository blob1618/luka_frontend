"""
dashboard.py — Data aggregation logic for the dashboard.

All functions receive a db session + user_id + optional date range
and return plain Python dicts/lists ready to pass into Jinja2 templates.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import Gasto, Presupuesto, Recordatorio, Usuario

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


def get_or_create_user(db: Session, whatsapp_id: str) -> Usuario:
    user = db.query(Usuario).filter(Usuario.whatsapp_id == whatsapp_id).first()
    if not user:
        user = Usuario(whatsapp_id=whatsapp_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_summary_stats(
    db: Session,
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Return total spent, number of transactions, top category."""
    q = db.query(Gasto).filter(Gasto.usuario_id == user_id)
    if date_from:
        q = q.filter(Gasto.creado_en >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Gasto.creado_en <= datetime.combine(date_to, datetime.max.time()))

    expenses = q.all()
    total = sum(e.monto for e in expenses) if expenses else Decimal("0")

    # top category
    cat_totals: dict[str, Decimal] = {}
    for e in expenses:
        cat_totals[e.categoria] = cat_totals.get(e.categoria, Decimal("0")) + Decimal(str(e.monto))
    top_category = max(cat_totals, key=cat_totals.get) if cat_totals else "—"

    return {
        "total_spent": float(total),
        "transaction_count": len(expenses),
        "top_category": top_category,
        "avg_per_day": float(total / max(1, (
            (datetime.combine(date_to or date.today(), datetime.min.time()) -
             datetime.combine(date_from or date.today(), datetime.min.time())).days + 1
        ))),
    }


def get_expenses_by_category(
    db: Session,
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    """Return [{category, total, color}] sorted by total desc."""
    q = db.query(
        Gasto.categoria,
        func.sum(Gasto.monto).label("total")
    ).filter(Gasto.usuario_id == user_id)

    if date_from:
        q = q.filter(Gasto.creado_en >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Gasto.creado_en <= datetime.combine(date_to, datetime.max.time()))

    rows = q.group_by(Gasto.categoria).order_by(func.sum(Gasto.monto).desc()).all()
    return [
        {
            "category": r.categoria,
            "total": float(r.total),
            "color": CATEGORY_COLORS.get(r.categoria, "#64748b"),
        }
        for r in rows
    ]


def get_expenses_by_day(
    db: Session,
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    """Return [{date_label, total}] for the line chart."""
    q = db.query(
        func.date(Gasto.creado_en).label("day"),
        func.sum(Gasto.monto).label("total")
    ).filter(Gasto.usuario_id == user_id)

    if date_from:
        q = q.filter(Gasto.creado_en >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Gasto.creado_en <= datetime.combine(date_to, datetime.max.time()))

    rows = q.group_by(func.date(Gasto.creado_en)).order_by(func.date(Gasto.creado_en)).all()
    return [{"day": str(r.day), "total": float(r.total)} for r in rows]


def get_recent_transactions(
    db: Session,
    user_id: int,
    limit: int = 15,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    q = db.query(Gasto).filter(Gasto.usuario_id == user_id)
    if date_from:
        q = q.filter(Gasto.creado_en >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Gasto.creado_en <= datetime.combine(date_to, datetime.max.time()))

    rows = q.order_by(Gasto.creado_en.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "amount": float(e.monto),
            "category": e.categoria,
            "description": e.descripcion or "—",
            "date": e.creado_en.strftime("%d %b %Y"),
            "time": e.creado_en.strftime("%H:%M"),
            "color": CATEGORY_COLORS.get(e.categoria, "#64748b"),
        }
        for e in rows
    ]


def get_budgets_with_usage(
    db: Session,
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    budgets = db.query(Presupuesto).filter(Presupuesto.usuario_id == user_id).all()
    result = []
    for b in budgets:
        q = db.query(func.sum(Gasto.monto)).filter(
            Gasto.usuario_id == user_id,
            Gasto.categoria == b.categoria,
        )
        if date_from:
            q = q.filter(Gasto.creado_en >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            q = q.filter(Gasto.creado_en <= datetime.combine(date_to, datetime.max.time()))

        spent = float(q.scalar() or 0)
        limit = float(b.monto_limite)
        pct = min(round((spent / limit) * 100) if limit > 0 else 0, 100)
        result.append({
            "category": b.categoria,
            "limit": limit,
            "spent": spent,
            "remaining": max(limit - spent, 0),
            "pct": pct,
            "color": CATEGORY_COLORS.get(b.categoria, "#64748b"),
            "over": spent > limit,
        })
    return result
