import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    create_session_token,
    decode_magic_link_token,
    get_current_user,
    mock_auth_enabled,
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
from app.models.database import get_db, MovimientoFinanciero, Categoria
from app.services.onboarding import (
    RegistrationValidation,
    validate_registration_context,
    validate_registration_token,
)
from app.services.supabase_auth import (
    ONBOARDING_COOKIE,
    PENDING_AUTH_COOKIE,
    PENDING_AUTH_MAX_AGE,
    AuthConfigurationError,
    CookieAuthStorage,
    create_onboarding_context,
    create_pending_auth_context,
    create_supabase_auth_client,
    cookie_secure_enabled,
    delete_auth_cookie,
    extract_verified_google_identity,
    load_onboarding_context,
    load_pending_auth_context,
    set_private_cookie,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ya no creamos tablas desde el frontend, se gestionan en el backend
    yield


app = FastAPI(title="LUKA Dashboard", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="app/templates")


def _secure_cookie_fallback() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def _auth_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _auth_error(
    request: Request,
    message: str,
    *,
    status_code: int = 400,
):
    return _auth_response(
        templates.TemplateResponse(
            "auth_error.html",
            {"request": request, "message": message},
            status_code=status_code,
        )
    )


def _clear_all_onboarding_cookies(response, *, secure: bool) -> None:
    delete_auth_cookie(response, ONBOARDING_COOKIE, secure=secure)
    _clear_google_auth_cookies(response, secure=secure)


def _clear_google_auth_cookies(response, *, secure: bool) -> None:
    delete_auth_cookie(response, PENDING_AUTH_COOKIE, secure=secure)
    CookieAuthStorage.clear_known_cookies(response, secure=secure)


@app.get("/registro", response_class=HTMLResponse)
async def registration_page(
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    registration = validate_registration_token(db, token)
    secure = _secure_cookie_fallback()
    context_cookie = None
    context_max_age = None
    if registration.status == "valid":
        try:
            secure = cookie_secure_enabled()
            context_cookie, context_max_age = create_onboarding_context(
                registration.invitation_id,
                registration.agreement_version_id,
                registration.invitation_expires_at,
            )
        except (AuthConfigurationError, ValueError):
            registration = RegistrationValidation(status="configuration_error")

    response = templates.TemplateResponse(
        "registro.html",
        {"request": request, "registration": registration},
    )
    if context_cookie and context_max_age:
        set_private_cookie(
            response,
            ONBOARDING_COOKIE,
            context_cookie,
            max_age=context_max_age,
            secure=secure,
        )
        delete_auth_cookie(response, PENDING_AUTH_COOKIE, secure=secure)
        CookieAuthStorage.clear_known_cookies(response, secure=secure)
    else:
        _clear_all_onboarding_cookies(response, secure=secure)
    return _auth_response(response)


@app.post("/auth/google")
async def start_google_auth(
    request: Request,
    terms_accepted: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        context = load_onboarding_context(request)
    except AuthConfigurationError:
        return _auth_error(
            request,
            "La autenticación no está disponible temporalmente. Intentá más tarde.",
            status_code=503,
        )
    if context is None:
        response = _auth_error(
            request,
            "Tu sesión de registro venció. Volvé a abrir el enlace de WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    if terms_accepted != "accepted":
        return _auth_error(
            request,
            "Debés aceptar los términos y la política de privacidad para continuar.",
        )

    registration = validate_registration_context(
        db,
        context.invitation_id,
        context.agreement_version_id,
    )
    if registration.status == "expired":
        response = _auth_error(
            request,
            "El enlace venció antes de iniciar Google. Solicitá uno nuevo por WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    if registration.status == "terms_unavailable":
        response = _auth_error(
            request,
            "Los términos cambiaron. Volvé a abrir el enlace de registro para revisarlos.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    if registration.status != "valid":
        response = _auth_error(
            request,
            "No pudimos validar tu registro. Solicitá un nuevo enlace por WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response

    supabase_auth = None
    try:
        supabase_auth = create_supabase_auth_client(request)
        oauth = supabase_auth.client.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {"redirect_to": supabase_auth.settings.callback_url},
            }
        )
        if not getattr(oauth, "url", None):
            raise ValueError("Missing OAuth redirect URL")
        response = RedirectResponse(url=oauth.url, status_code=303)
        supabase_auth.apply_cookies(response)
        return _auth_response(response)
    except AuthConfigurationError:
        response = _auth_error(
            request,
            "La autenticación no está disponible temporalmente. Intentá más tarde.",
            status_code=503,
        )
        _clear_google_auth_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    except Exception:
        return _auth_error(
            request,
            "No pudimos iniciar Google. Intentá nuevamente en unos minutos.",
            status_code=502,
        )
    finally:
        if supabase_auth is not None:
            supabase_auth.close()


@app.get("/auth/callback")
async def google_auth_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if error:
        message = (
            "La autenticación con Google fue cancelada. Intentá nuevamente."
            if error == "access_denied"
            else "Google no pudo completar la autenticación. Intentá nuevamente."
        )
        response = _auth_error(request, message)
        _clear_google_auth_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    if not code or len(code) > 4096:
        response = _auth_error(
            request,
            "No recibimos una respuesta válida de Google. Intentá nuevamente.",
        )
        _clear_google_auth_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response

    try:
        context = load_onboarding_context(request)
    except AuthConfigurationError:
        return _auth_error(
            request,
            "La autenticación no está disponible temporalmente. Intentá más tarde.",
            status_code=503,
        )
    if context is None:
        response = _auth_error(
            request,
            "Tu sesión de registro venció. Volvé a abrir el enlace de WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response

    registration = validate_registration_context(
        db,
        context.invitation_id,
        context.agreement_version_id,
    )
    if registration.status == "expired":
        response = _auth_error(
            request,
            "El enlace venció durante Google OAuth. Solicitá uno nuevo por WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    if registration.status != "valid":
        response = _auth_error(
            request,
            "Tu sesión de registro ya no es válida. Volvé a abrir el enlace.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response

    has_pkce_cookie = any(
        name == "luka_sb_pkce" or name.startswith("luka_sb_pkce.")
        for name in request.cookies
    )
    if not has_pkce_cookie:
        response = _auth_error(
            request,
            "Tu sesión con Google venció. Volvé a iniciar la autenticación.",
        )
        _clear_google_auth_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response

    supabase_auth = None
    try:
        supabase_auth = create_supabase_auth_client(request)
        exchange = supabase_auth.client.auth.exchange_code_for_session(
            {"auth_code": code}
        )
        session = getattr(exchange, "session", None)
        access_token = getattr(session, "access_token", None)
        if not access_token:
            raise ValueError("Missing exchanged session")
        verified_user = supabase_auth.client.auth.get_user(access_token)
        identity = extract_verified_google_identity(verified_user)

        response = RedirectResponse(url="/registro/continuar", status_code=303)
        pending_cookie = create_pending_auth_context(identity, context.raw_cookie)
        set_private_cookie(
            response,
            PENDING_AUTH_COOKIE,
            pending_cookie,
            max_age=PENDING_AUTH_MAX_AGE,
            secure=supabase_auth.settings.cookie_secure,
        )
        supabase_auth.apply_cookies(response)
        return _auth_response(response)
    except AuthConfigurationError:
        response = _auth_error(
            request,
            "La autenticación no está disponible temporalmente. Intentá más tarde.",
            status_code=503,
        )
        _clear_google_auth_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    except Exception:
        response = _auth_error(
            request,
            "No pudimos validar la sesión de Google. Iniciá la autenticación nuevamente.",
        )
        secure = (
            supabase_auth.settings.cookie_secure
            if supabase_auth is not None
            else _secure_cookie_fallback()
        )
        delete_auth_cookie(response, PENDING_AUTH_COOKIE, secure=secure)
        CookieAuthStorage.clear_known_cookies(response, secure=secure)
        return response
    finally:
        if supabase_auth is not None:
            supabase_auth.close()


@app.get("/registro/continuar", response_class=HTMLResponse)
async def continue_registration(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        context = load_onboarding_context(request)
        identity = (
            load_pending_auth_context(request, context.raw_cookie) if context else None
        )
    except AuthConfigurationError:
        return _auth_error(
            request,
            "La autenticación no está disponible temporalmente. Intentá más tarde.",
            status_code=503,
        )
    if context is None or identity is None:
        return _auth_error(
            request,
            "Tu sesión de registro venció. Volvé a iniciar desde el enlace de WhatsApp.",
        )

    registration = validate_registration_context(
        db,
        context.invitation_id,
        context.agreement_version_id,
    )
    if registration.status == "expired":
        response = _auth_error(
            request,
            "El enlace venció durante Google OAuth. Solicitá uno nuevo por WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response
    if registration.status != "valid":
        response = _auth_error(
            request,
            "El registro ya no está disponible. Volvé a abrir el enlace de WhatsApp.",
        )
        _clear_all_onboarding_cookies(
            response,
            secure=_secure_cookie_fallback(),
        )
        return response

    response = templates.TemplateResponse(
        "registro_continuar.html",
        {"request": request, "email": identity.email},
    )
    return _auth_response(response)


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
            return _auth_response(response)
    return _auth_response(
        templates.TemplateResponse(
            "login.html", {"request": request, "error": bool(token)}
        )
    )


@app.get("/dev-login", response_class=RedirectResponse)
async def dev_login(request: Request):
    """Shortcut for local development — bypass WhatsApp entirely."""
    if not mock_auth_enabled():
        return _auth_error(request, "Ruta no disponible.", status_code=404)
    response = RedirectResponse(url="/", status_code=303)
    from app.auth import MOCK_WHATSAPP_ID

    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(MOCK_WHATSAPP_ID),
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return _auth_response(response)


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return _auth_response(response)


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
    dias_racha = get_dias_racha(db, user.id)  # TODO: lógica real pendiente

    return templates.TemplateResponse(
        "dashboard.html",
        {
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
        },
    )


@app.get("/exportar/csv")
async def exportar_csv(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    whatsapp_id: str = Depends(get_current_user),
):
    user = get_user(db, whatsapp_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    d_from, d_to, _, _ = _get_default_dates(date_from, date_to)

    def iter_csv():
        q = (
            db.query(MovimientoFinanciero, Categoria)
            .join(
                Categoria,
                MovimientoFinanciero.categoria_id == Categoria.id,
                isouter=True,
            )
            .filter(MovimientoFinanciero.usuario_id == user.id)
        )
        if d_from:
            q = q.filter(MovimientoFinanciero.fecha_movimiento >= d_from)
        if d_to:
            q = q.filter(MovimientoFinanciero.fecha_movimiento <= d_to)

        q = q.order_by(
            MovimientoFinanciero.fecha_movimiento.desc(),
            MovimientoFinanciero.creado_en.desc(),
        )

        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["Fecha", "Monto", "Moneda", "Categoria", "Descripcion"]
        )
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in q.yield_per(100):
            writer.writerow(
                {
                    "Fecha": row.MovimientoFinanciero.fecha_movimiento.strftime(
                        "%Y-%m-%d"
                    ),
                    "Monto": float(row.MovimientoFinanciero.cantidad),
                    "Moneda": row.MovimientoFinanciero.moneda or "ARS",
                    "Categoria": row.Categoria.nombre if row.Categoria else "Otro",
                    "Descripcion": row.MovimientoFinanciero.descripcion or "",
                }
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    headers = {"Content-Disposition": "attachment; filename=transacciones.csv"}
    return StreamingResponse(iter_csv(), media_type="text/csv", headers=headers)


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
    dias_racha = get_dias_racha(db, user.id)  # TODO: lógica real pendiente

    response = templates.TemplateResponse(
        "partials/stats.html",
        {
            "request": request,
            "stats": stats,
            "patrimonio": patrimonio,
            "consumo": consumo,
            "dias_racha": dias_racha,
        },
    )

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

    return templates.TemplateResponse(
        "partials/charts.html",
        {
            "request": request,
        },
    )


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
        db,
        user.id,
        date_from=d_from,
        date_to=d_to,
    )
    return templates.TemplateResponse(
        "partials/transactions.html",
        {
            "request": request,
            "transactions": transactions,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Error handlers — redirect to login on 401
# ─────────────────────────────────────────────────────────────────────────────


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return RedirectResponse(url="/login", status_code=303)
