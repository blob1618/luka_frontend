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

from app.models.database import Expense, Budget, Reminder, User

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


def get_or_create_user(db: Session, whatsapp_id: str) -> User:
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
    if not user:
        user = User(whatsapp_id=whatsapp_id)
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
    q = db.query(Expense).filter(Expense.user_id == user_id)
    if date_from:
        q = q.filter(Expense.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Expense.created_at <= datetime.combine(date_to, datetime.max.time()))

    expenses = q.all()
    total = sum(e.amount for e in expenses) if expenses else Decimal("0")

    # top category
    cat_totals: dict[str, Decimal] = {}
    for e in expenses:
        cat_totals[e.category] = cat_totals.get(e.category, Decimal("0")) + e.amount
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
        Expense.category,
        func.sum(Expense.amount).label("total")
    ).filter(Expense.user_id == user_id)

    if date_from:
        q = q.filter(Expense.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Expense.created_at <= datetime.combine(date_to, datetime.max.time()))

    rows = q.group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()
    return [
        {
            "category": r.category,
            "total": float(r.total),
            "color": CATEGORY_COLORS.get(r.category, "#64748b"),
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
        func.date(Expense.created_at).label("day"),
        func.sum(Expense.amount).label("total")
    ).filter(Expense.user_id == user_id)

    if date_from:
        q = q.filter(Expense.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Expense.created_at <= datetime.combine(date_to, datetime.max.time()))

    rows = q.group_by(func.date(Expense.created_at)).order_by(func.date(Expense.created_at)).all()
    return [{"day": str(r.day), "total": float(r.total)} for r in rows]


def get_recent_transactions(
    db: Session,
    user_id: int,
    limit: int = 15,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    q = db.query(Expense).filter(Expense.user_id == user_id)
    if date_from:
        q = q.filter(Expense.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Expense.created_at <= datetime.combine(date_to, datetime.max.time()))

    rows = q.order_by(Expense.created_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "amount": float(e.amount),
            "category": e.category,
            "description": e.description or "—",
            "date": e.created_at.strftime("%d %b %Y"),
            "time": e.created_at.strftime("%H:%M"),
            "color": CATEGORY_COLORS.get(e.category, "#64748b"),
        }
        for e in rows
    ]


def get_budgets_with_usage(
    db: Session,
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    result = []
    for b in budgets:
        q = db.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.category == b.category,
        )
        if date_from:
            q = q.filter(Expense.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            q = q.filter(Expense.created_at <= datetime.combine(date_to, datetime.max.time()))

        spent = float(q.scalar() or 0)
        limit = float(b.limit_amount)
        pct = min(round((spent / limit) * 100) if limit > 0 else 0, 100)
        result.append({
            "category": b.category,
            "limit": limit,
            "spent": spent,
            "remaining": max(limit - spent, 0),
            "pct": pct,
            "color": CATEGORY_COLORS.get(b.category, "#64748b"),
            "over": spent > limit,
        })
    return result
