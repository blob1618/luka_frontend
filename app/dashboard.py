"""
dashboard.py — Data aggregation logic for the dashboard.

All functions receive a db session + user_id + optional date range
and return plain Python dicts/lists ready to pass into Jinja2 templates.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import MovimientoFinanciero, LimiteCategoria, Recordatorio, Usuario, Categoria

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

    # top category
    cat_totals: dict[str, Decimal] = {}
    for e in expenses:
        cat_name = e.Categoria.nombre if e.Categoria else "Otro"
        cat_totals[cat_name] = cat_totals.get(cat_name, Decimal("0")) + Decimal(str(e.MovimientoFinanciero.cantidad))
    top_category = max(cat_totals, key=cat_totals.get) if cat_totals else "—"

    return {
        "total_spent": float(total),
        "transaction_count": len(expenses),
        "top_category": top_category,
        "avg_per_day": float(total / max(1, (
            (date_to or date.today()) - (date_from or date.today())
        ).days + 1)),
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
        MovimientoFinanciero.usuario_id == user_id,
        MovimientoFinanciero.tipo == 'egreso'
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
            "category": e.Categoria.nombre if e.Categoria else "Otro",
            "description": e.MovimientoFinanciero.descripcion or "—",
            "date": e.MovimientoFinanciero.fecha_movimiento.strftime("%d %b %Y"),
            "time": e.MovimientoFinanciero.creado_en.strftime("%H:%M") if e.MovimientoFinanciero.creado_en else "00:00",
            "color": CATEGORY_COLORS.get(e.Categoria.nombre if e.Categoria else "Otro", "#64748b"),
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
