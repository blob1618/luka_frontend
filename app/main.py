import csv
import io
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    create_session_token,
    decode_magic_link_token,
    get_current_user,
)
from app.dashboard import (
    get_budgets_with_usage,
    get_consumo_presupuesto,
    get_dias_racha,
    get_expenses_by_category,
    get_monthly_flow,
    get_patrimonio_neto,
    get_portfolio_by_currency,
    get_user,
    get_recent_transactions,
    get_summary_stats,
)
from app.models.database import get_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ya no creamos tablas desde el frontend, se gestionan en el backend
    yield


app = FastAPI(title="LUKA Dashboard", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="app/templates")


# ─────────────────────────────────────────────────────────────────────────────
# Auth routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, token: Optional[str] = None):
    """
    If ?token=xyz is provided (from the WhatsApp bot), validate and set session.
    Otherwise show the login page with instructions.
    """
    if token:
        whatsapp_id = decode_magic_link_token(token)
        if whatsapp_id:
            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(
                SESSION_COOKIE,
                create_session_token(whatsapp_id),
                httponly=True,
                max_age=60 * 60 * 24 * 7,
                samesite="lax",
            )
            return response
    return templates.TemplateResponse("login.html", {"request": request, "error": bool(token)})


@app.get("/dev-login", response_class=RedirectResponse)
async def dev_login():
    """Shortcut for local development — bypass WhatsApp entirely."""
    response = RedirectResponse(url="/", status_code=303)
    from app.auth import MOCK_WHATSAPP_ID
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(MOCK_WHATSAPP_ID),
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────────────────────────────────────


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None

def _get_default_dates(date_from: Optional[str], date_to: Optional[str]):
    d_from = _parse_date(date_from)
    d_to = _parse_date(date_to)
    if not d_from and not d_to:
        today = date.today()
        d_from = today.replace(day=1)
        d_to = today
        date_from = d_from.isoformat()
        date_to = d_to.isoformat()
    return d_from, d_to, date_from, date_to


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    d_from, d_to, date_from, date_to = _get_default_dates(date_from, date_to)

    stats = get_summary_stats(db, user.id, d_from, d_to)
    transactions = get_recent_transactions(db, user.id, date_from=d_from, date_to=d_to)
    budgets = get_budgets_with_usage(db, user.id, d_from, d_to)

    # ── KPIs ──────────────────────────────────────────────────────────
    patrimonio = get_patrimonio_neto(db, user.id, d_from, d_to)
    consumo = get_consumo_presupuesto(db, user.id, d_from, d_to)
    dias_racha = get_dias_racha(db, user.id)          # TODO: lógica real pendiente

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "whatsapp_id": whatsapp_id,
        "stats": stats,
        "transactions": transactions,
        "budgets": budgets,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "patrimonio": patrimonio,
        "consumo": consumo,
        "dias_racha": dias_racha,
    })


# ─────────────────────────────────────────────────────────────────────────────
# API Data Routes (Charts)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/graficos/distribucion")
async def api_graficos_distribucion(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)
    return get_expenses_by_category(db, user.id, d_from, d_to)

@app.get("/api/graficos/cartera")
async def api_graficos_cartera(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)
    return get_portfolio_by_currency(db, user.id, d_from, d_to)

@app.get("/api/graficos/flujo")
async def api_graficos_flujo(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)
    return get_monthly_flow(db, user.id, d_from, d_to)


# ─────────────────────────────────────────────────────────────────────────────
# HTMX partials (update only parts of the page without a full reload)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/dashboard/actualizar", response_class=HTMLResponse)
async def dashboard_actualizar(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)
    stats = get_summary_stats(db, user.id, d_from, d_to)
    patrimonio = get_patrimonio_neto(db, user.id, d_from, d_to)
    consumo = get_consumo_presupuesto(db, user.id, d_from, d_to)
    dias_racha = get_dias_racha(db, user.id)   # TODO: lógica real pendiente
    
    response = templates.TemplateResponse("partials/stats.html", {
        "request": request,
        "stats": stats,
        "patrimonio": patrimonio,
        "consumo": consumo,
        "dias_racha": dias_racha,
    })
    
    # Emitimos un evento a HTMX para que el frontend redibuje los gráficos y transacciones
    response.headers["HX-Trigger"] = "actualizarGraficos"
    return response


@app.get("/partials/charts", response_class=HTMLResponse)
async def partial_charts(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    return templates.TemplateResponse("partials/charts.html", {
        "request": request,
    })


@app.get("/partials/transactions", response_class=HTMLResponse)
async def partial_transactions(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)
    transactions = get_recent_transactions(
        db, user.id,
        date_from=d_from,
        date_to=d_to,
    )
    return templates.TemplateResponse("partials/transactions.html", {
        "request": request,
        "transactions": transactions,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/export/csv")
async def export_csv(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)
    transactions = get_recent_transactions(
        db, user.id, limit=10_000,
        date_from=d_from,
        date_to=d_to,
    )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "date", "time", "category", "description", "amount"])
    writer.writeheader()
    writer.writerows(transactions)

    filename = f"luka_gastos_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Error handlers — redirect to login on 401
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return RedirectResponse(url="/login", status_code=303)
