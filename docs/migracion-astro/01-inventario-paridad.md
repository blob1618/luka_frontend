# 01 — Inventario de paridad para la migración a Astro

- **Propósito:** inventario verificable de todo lo que el frontend actual (FastAPI + Jinja2 + HTMX + Chart.js + SQLAlchemy) expone, para usarlo como insumo de paridad de la migración a Astro y como checklist de corte en F2.
- **Estado:** v1.0 — 2026-09-23.
- **Alcance:** repositorio `luka_frontend`. Método: lectura directa de los archivos citados; conteos con `Select-String` (grep) sobre `tests/`; sin modificar el repositorio.
- **Cómo usarlo:** cada fila de §2, §3, §4 y §5 debe quedar cubierta por `web/`; §8 es la lista de verificación antes de apagar FastAPI.
- **Fuera de alcance:** el plan de fases y la limpieza previa son de `docs/migracion-astro/00-plan-limpieza-preparacion.md` (otro agente; al 2026-09-23 el directorio `docs/migracion-astro/` no existía en el repo). Este documento no lo duplica.

### Resumen de paridad

| Superficie | Cantidad | Fuente |
|------------|----------|--------|
| Rutas HTTP | 25 | `@app.<método>` en `app/main.py` |
| Cookies de auth | 5 | `app/auth.py:31`, `app/services/supabase_auth.py:26-29` |
| Funciones de consulta | 11 + 1 query inline (CSV) | `app/dashboard.py`, `app/main.py:1003-1049` |
| Tablas consumidas | 8 de 10 declaradas | `app/models/database.py` |
| Variables de entorno | 12 | `.env.example` |
| Tests | 113 funciones en 7 archivos | grep sobre `tests/test_*.py` |
| Plantillas | 9 HTML + 3 parciales + 25 SVG | `app/templates/` |

---

## 2. Rutas (25)

Todas las rutas están en `app/main.py`; el mount de estáticos es `/static` → `static/` (`app/main.py:90`). El handler global de 401 redirige a `/login` (`app/main.py:1194-1196`), por lo que **todo endpoint autenticado debe replicar esa redirección** (middleware en Astro). Los 4 endpoints `/api/graficos/*` y los 3 parciales requieren `luka_session`; hoy el 401 se convierte en 303.

| # | Método | Ruta | Propósito | Auth | Datos / Template | Destino Astro | Notas |
|---|--------|------|-----------|------|------------------|---------------|-------|
| 1 | GET | `/registro` | Mostrar términos vigentes y CTA de Google; setea `luka_onboarding` | Pública (token de invitación) | `validate_registration_token` → `registro.html` | `src/pages/registro.astro` | `app/main.py:137`; cookie creada en `main.py:150-169` |
| 2 | POST | `/auth/google` | Iniciar OAuth PKCE con Google | Pública (requiere `terms_accepted=accepted` + `luka_onboarding`) | Redirect 303 a Supabase | `src/pages/api/auth/google.ts` | `app/main.py:177`; revalida invitación en `main.py:207-241` |
| 3 | GET | `/auth/callback` | Intercambiar `code` PKCE y verificar identidad Google | Pública (requiere cookie `luka_sb_pkce`) | Redirect 303 a `/registro/continuar` | `src/pages/api/auth/callback.ts` | `app/main.py:279`; chequeo PKCE en `main.py:354-357` |
| 4 | GET | `/registro/continuar` | Mostrar email verificado y CTA de finalización | Pública (`luka_onboarding` + `luka_pending_google`) | `registro_continuar.html` | `src/pages/registro/continuar.astro` | `app/main.py:422` |
| 5 | POST | `/registro/finalizar` | Crear/vincular `Usuario`, registrar consentimiento y consumir invitación | Pública (cookies anteriores + `luka_sb_session`) | `finalize_onboarding` → `registro_completado.html` / `auth_error.html` | `src/pages/api/registro/finalizar.ts` | `app/main.py:477`; transacción en `onboarding_finalization.py:106-251` |
| 6 | GET | `/login` | Validar token del bot y crear sesión; si no hay token, instrucciones | Pública (token) | `consume_dashboard_login_token` → `login.html` | `src/pages/login.astro` | `app/main.py:664`; preserva `date_from`/`date_to` (`main.py:680-691`) |
| 7 | GET | `/dev-login` | Atajo local sin bot | Solo `APP_ENV=development` y `ENABLE_MOCK_AUTH=true` | Redirect 303 a `/` | `src/pages/api/dev-login.ts` | `app/main.py:708`; gate en `auth.py:35-39` |
| 8 | GET | `/logout` | Cerrar sesión | Sesión | Redirect 303 a `/login` | `src/pages/api/logout.ts` | `app/main.py:724`; solo borra `luka_session`, no cookies Supabase |
| 9 | GET | `/admin/flujos` | Listar flujos de conversación | Admin (allowlist) | `flow_admin_client.list()` → `admin_flows.html` | `src/pages/admin/flujos.astro` | `app/main.py:771`; gate `main.py:129-134` |
| 10 | GET | `/admin/flujos/nuevo` | Editor de flujo nuevo | Admin | `flow_admin_client.contracts()` → `admin_flow_editor.html` | `src/pages/admin/flujos/nuevo.astro` | `app/main.py:798` |
| 11 | POST | `/admin/flujos/api/validar` | Proxy de validación | Admin | JSON del backend `luka` | `src/pages/api/admin/flujos/validar.ts` | `app/main.py:825` |
| 12 | POST | `/admin/flujos/api` | Proxy de creación (201) | Admin | JSON del backend `luka` | `src/pages/api/admin/flujos/index.ts` | `app/main.py:836` |
| 13 | PUT | `/admin/flujos/api/{flow_id}/borrador` | Proxy guardar borrador | Admin | JSON del backend `luka` | `src/pages/api/admin/flujos/[flow_id]/borrador.ts` | `app/main.py:847` |
| 14 | DELETE | `/admin/flujos/api/{flow_id}/borrador` | Proxy descartar borrador | Admin | JSON del backend `luka` | (mismo archivo que #13) | `app/main.py:859` |
| 15 | POST | `/admin/flujos/api/{flow_id}/publicar` | Proxy publicar | Admin | JSON del backend `luka` | `src/pages/api/admin/flujos/[flow_id]/publicar.ts` | `app/main.py:870` |
| 16 | POST | `/admin/flujos/api/{flow_id}/retirar` | Proxy retirar | Admin | JSON del backend `luka` | `src/pages/api/admin/flujos/[flow_id]/retirar.ts` | `app/main.py:881` |
| 17 | GET | `/admin/flujos/{flow_id}` | Editor de flujo existente | Admin | `get` + `contracts()` en paralelo → `admin_flow_editor.html` | `src/pages/admin/flujos/[flow_id].astro` | `app/main.py:892`; `asyncio.gather` en `main.py:901-904` |
| 18 | GET | `/` | Dashboard completo | Sesión | 10 consultas de `app/dashboard.py` → `dashboard.html` | `src/pages/index.astro` | `app/main.py:949` |
| 19 | GET | `/exportar/csv` | Exportar movimientos a CSV (streaming) | Sesión | Query inline + `StreamingResponse` | `src/pages/api/exportar/csv.ts` | `app/main.py:990`; `yield_per(100)` en `main.py:1035` |
| 20 | GET | `/api/graficos/distribucion` | JSON egresos por categoría | Sesión | `get_expenses_by_category` | `src/pages/api/graficos/distribucion.ts` | `app/main.py:1060` |
| 21 | GET | `/api/graficos/cartera` | JSON cartera ARS/USD por mes | Sesión | `get_portfolio_by_currency` | `src/pages/api/graficos/cartera.ts` | `app/main.py:1074` |
| 22 | GET | `/api/graficos/flujo` | JSON ingresos vs egresos por mes | Sesión | `get_monthly_flow` | `src/pages/api/graficos/flujo.ts` | `app/main.py:1088` |
| 23 | GET | `/dashboard/actualizar` | Parcial KPIs + evento HTMX | Sesión | `partials/stats.html` + header `HX-Trigger` | `src/pages/api/dashboard/actualizar.ts` | `app/main.py:1107`; header en `main.py:1137` |
| 24 | GET | `/partials/charts` | Parcial con contenedores de gráficos | Sesión | `partials/charts.html` | Componente Astro (no endpoint) | `app/main.py:1141`; no consulta datos, solo markup |
| 25 | GET | `/partials/transactions` | Parcial con lista de movimientos | Sesión | `get_recent_transactions` → `partials/transactions.html` | Componente Astro o endpoint de parcial | `app/main.py:1161` |

**Total: 25 rutas** (contadas por decoradores `@app.<método>` en `app/main.py`). Las rutas 23-25 existen solo por HTMX 2.0.3 (`base.html:12`); en Astro pueden resolverse con componentes server-side + `client:load` para Chart.js, sin endpoints de parcial (decisión pendiente, §9).

---

## 3. Auth y cookies

### 3.1 Cookies

| Cookie | Propósito | TTL | Firma / formato | Destino en Astro |
|--------|-----------|-----|-----------------|------------------|
| `luka_session` | Sesión del dashboard (magic link y `/dev-login`) | 7 días (`auth.py:32`, `main.py:697`) | `itsdangerous.URLSafeTimedSerializer`, salt `"session"` (`auth.py:42-54`); **sin chunking** | Cookie propia firmada (HMAC Web Crypto) en `src/lib/session.ts`; conservar el nombre durante el corte |
| `luka_onboarding` | Contexto firmado de invitación (`i`, `a`) tras `/registro` | `min(30 min, restante de la invitación)` (`supabase_auth.py:31,188`) | Signed, salt `"luka-onboarding-context-v1"` (`supabase_auth.py:36`) | Cookie firmada propia; TTL corto ⇒ no hace falta compatibilidad con firmas viejas |
| `luka_pending_google` | Identidad Google verificada entre callback y finalización | 15 min (`supabase_auth.py:32`) | Signed, salt `"luka-pending-google-auth-v1"`; ata `sha256(luka_onboarding)` (`supabase_auth.py:217-230`) | Cookie firmada propia; comparar hashes con `crypto.subtle.digest` |
| `luka_sb_pkce` | Code verifier PKCE de Supabase | 10 min (`supabase_auth.py:33`) | Base64url chunked: manifiesto `v1:N` + `.<i>`, 3000 chars/chunk, máx. 8 (`supabase_auth.py:38-39,335-357`) | Reemplazada por el storage de `@supabase/ssr` (chunking propio, cookie `sb-<ref>-code-verifier`) |
| `luka_sb_session` | Sesión Supabase (access + refresh token) | 15 min (`supabase_auth.py:34`) | Mismo esquema chunked que PKCE (`supabase_auth.py:306-357`) | Reemplazada por `@supabase/ssr` (cookie `sb-<ref>-auth-token`) |

Todas las cookies de onboarding/Supabase se emiten con `httponly=True`, `samesite="lax"`, `path="/"` y `secure` según `AUTH_COOKIE_SECURE`/`APP_ENV` (`supabase_auth.py:262-288`). **`luka_session` no fija `secure`** en `main.py:693-699` ni en `main.py:714-720`: es la única cookie de sesión que puede viajar sin `Secure` en producción (ver §9).

### 3.2 Flujos

1. **Magic link del bot (`/link` → `/login?token=…`).** El bot (`DashboardLinkService` del repo `luka`) emite un token de un solo uso; `consume_dashboard_login_token` calcula `sha256`, busca en `dashboard_login_link` con `FOR UPDATE`, valida estado `pendiente` y expiración, marca `consumido` y devuelve `auth_user_id` (`auth.py:68-114`). `/login` crea `luka_session` (7 días) y redirige a `/` preservando `date_from`/`date_to` válidos (`main.py:677-700`). Los estados inválidos nunca se distinguen entre sí (`auth.py:79-80`).
2. **Google OAuth PKCE (registro).** `/registro?token=` valida la invitación y emite `luka_onboarding` (`main.py:143-174`); `POST /auth/google` exige términos aceptados, revalida invitación/acuerdo y llama `sign_in_with_oauth` con `redirect_to = APP_BASE_URL + /auth/callback` (`main.py:243-256`, `supabase_auth.py:74-76`). El SDK persiste el code verifier en `luka_sb_pkce` (`supabase_auth.py:335-357`). `/auth/callback` intercambia el code, obtiene el usuario y exige identidad Google verificada (`main.py:369-392`, `supabase_auth.py:437-478`), emite `luka_pending_google` + `luka_sb_session` y redirige a `/registro/continuar`. `POST /registro/finalizar` revalida la sesión con `get_user()` (sin confiar en campos del navegador), compara identidad fresca contra la pendiente y ejecuta `finalize_onboarding` en una transacción con `FOR UPDATE` (`main.py:505-592`); al terminar borra todas las cookies temporales (`main.py:594-600`).
3. **`/dev-login`.** Bypass local: solo con `APP_ENV=development` y `ENABLE_MOCK_AUTH=true` (`auth.py:35-39`); crea `luka_session` con `MOCK_AUTH_USER_ID` (`main.py:708-721`). En producción responde 404.
4. **`/logout`.** Borra `luka_session` y redirige a `/login` (`main.py:724-728`). No revoca la sesión de Supabase ni borra `luka_sb_session` (nota para paridad: decidir si en Astro se cierra también la sesión Supabase).

---

## 4. Datos

### 4.1 Funciones de consulta

Todas en `app/dashboard.py`; reciben `db`, `user_id` y rango de fechas opcional, y devuelven dicts listos para plantilla.

| Función | Tablas | Propósito | Notas para port a `postgres.js` |
|---------|--------|-----------|----------------------------------|
| `get_user` (`dashboard.py:39`) | `usuario` | Buscar por `whatsapp_id` | No la usan las rutas actuales; conservar solo si el admin la necesita |
| `get_user_by_auth_id` (`dashboard.py:43`) | `usuario` | Resolver usuario por `auth_user_id` (UUID) | Validar UUID antes de consultar (`dashboard.py:50-54`); en JS usar `crypto.randomUUID`/regex |
| `get_summary_stats` (`dashboard.py:57`) | `movimientos_financieros`, `categorias` | Totales, nº de movimientos, top categoría, promedio diario | LEFT JOIN (`isouter=True`, `dashboard.py:66-68`); hoy suma en Python: portar a `SUM`/`GROUP BY` en SQL |
| `get_expenses_by_category` (`dashboard.py:123`) | `movimientos_financieros`, `categorias` | Egresos agrupados por categoría + color | `GROUP BY` + `ORDER BY SUM(...) DESC` (`dashboard.py:150-154`); `COALESCE` para categoría nula |
| `get_expenses_by_day` (`dashboard.py:165`) | `movimientos_financieros` | Serie diaria de egresos | **Sin uso**: no está importada en `main.py` (grep). Descartar o portar solo si se agrega el gráfico |
| `get_recent_transactions` (`dashboard.py:194`) | `movimientos_financieros`, `categorias` | Últimos 15 movimientos (límite por defecto) | `ORDER BY creado_en DESC LIMIT 15` (`dashboard.py:216`); formatea fecha/hora en Python: mover formato a JS |
| `get_budgets_with_usage` (`dashboard.py:239`) | `limite_categoria`, `categorias`, `movimientos_financieros` | Presupuesto por categoría con gasto y % | N+1: una consulta de suma por presupuesto (`dashboard.py:254-265`); portar a un solo `GROUP BY` |
| `get_patrimonio_neto` (`dashboard.py:289`) | `movimientos_financieros` | Capital neto en ARS (USD × tasa fija) | `USD_TO_ARS_RATE = 1300.0` hardcodeado (`dashboard.py:36`); mantener la constante hasta integrar cotización |
| `get_consumo_presupuesto` (`dashboard.py:343`) | `limite_categoria`, `movimientos_financieros` | % global gastado sobre límite total | `IN (...)` con ids de categorías (`dashboard.py:363-369`) |
| `get_monthly_flow` (`dashboard.py:386`) | `movimientos_financieros` | Ingresos vs egresos por mes | `extract('year'/'month')` + `GROUP BY` por alias: en SQL crudo usar `GROUP BY 1,2` o repetir expresión; por defecto últimos 6 meses (`dashboard.py:444-445`) |
| `get_portfolio_by_currency` (`dashboard.py:457`) | `movimientos_financieros` | Cartera ARS/USD por mes (solo egresos) | Misma consideración de `GROUP BY`; convierte USD a ARS con la tasa fija (`dashboard.py:498-501`) |
| `get_dias_racha` (`dashboard.py:531`) | — | Placeholder, retorna `0` | **TODO sin implementar** (`dashboard.py:533-536`): no es deuda de la migración |

Además, `exportar_csv` consulta inline `movimientos_financieros` + `categorias` con LEFT JOIN y `yield_per(100)` (`main.py:1003-1049`): en `postgres.js` usar cursor/streaming o paginado por keyset.

### 4.2 Tablas consumidas

Declaradas en `app/models/database.py`:

| Tabla | Clase | ¿Consumida por rutas? |
|-------|-------|------------------------|
| `usuario` | `Usuario` (`database.py:47`) | Sí: `auth.py:103`, `dashboard.py:40,54`, `onboarding_finalization.py:163-198` |
| `onboarding_invitacion` | `OnboardingInvitacion` (`database.py:62`) | Sí: `onboarding.py:46-81`, `onboarding_finalization.py:130-243` |
| `dashboard_login_link` | `DashboardLoginLink` (`database.py:89`) | Sí: `auth.py:86-110` |
| `acuerdo_version` | `AcuerdoVersion` (`database.py:113`) | Sí: `onboarding.py:65-80`, `onboarding_finalization.py:151-160` |
| `acuerdo_aceptado` | `AcuerdoAceptado` (`database.py:124`) | Sí: `onboarding_finalization.py:200-217` |
| `categorias` | `Categoria` (`database.py:136`) | Sí: `dashboard.py`, `onboarding_finalization.py:219-237`, `main.py:1005` |
| `limite_categoria` | `LimiteCategoria` (`database.py:147`) | Sí: `dashboard.py:246,353` |
| `movimientos_financieros` | `MovimientoFinanciero` (`database.py:185`) | Sí: `dashboard.py`, `main.py:1005` |
| `recordatorio` | `Recordatorio` (`database.py:161`) | **No**: sin referencias fuera de `database.py` (grep) |
| `evento` | `Evento` (`database.py:173`) | **No**: sin referencias fuera de `database.py` (grep) |

**Contrato de datos:** las migraciones de la base compartida pertenecen al repo `blob1618/luka`; este repositorio solo mantiene modelos consumidores y no debe ejecutar `Base.metadata.create_all()` contra Supabase (`README.md`, sección "Contrato de base de datos compartido"; `main.py:84-86` confirma que el frontend ya no crea tablas). La migración a Astro hereda ese contrato: **ninguna migración nueva** en `web/`.

---

## 5. Variables de entorno

Matriz de las 12 variables de `.env.example` (todas presentes allí).

| Variable | Quién la usa (cita) | ¿Dev/Prod? | Equivalente en Astro |
|----------|---------------------|------------|----------------------|
| `APP_ENV` | `auth.py:37`, `main.py:96`, `supabase_auth.py:123,133,163` | Ambos (default `development`) | `import.meta.env.MODE`/`PROD`; conservar `APP_ENV` si se quiere paridad explícita |
| `APP_BASE_URL` | `supabase_auth.py:138-142`; base del `redirect_to` (`supabase_auth.py:74-76`) | Ambos; en prod exige `https` y sin path (`supabase_auth.py:103-119,137`) | `Astro.url.origin` o `APP_BASE_URL` server-side |
| `SUPABASE_URL` | `supabase_auth.py:143-147,418` | Ambos | `PUBLIC_SUPABASE_URL` (expuesta al cliente; es pública por diseño) |
| `SUPABASE_PUBLISHABLE_KEY` | `supabase_auth.py:148-150`; exige prefijo `sb_publishable_` y ≥20 chars | Ambos | `PUBLIC_SUPABASE_PUBLISHABLE_KEY` |
| `AUTH_COOKIE_SECURE` | `supabase_auth.py:126`; obligatoria `true` en prod (`supabase_auth.py:127-128`) | Ambos | Opciones `secure` del cookie helper de `@supabase/ssr`; puede derivarse de `import.meta.env.PROD` |
| `ENABLE_MOCK_AUTH` | `auth.py:38`; solo actúa si `APP_ENV=development` (`auth.py:39`) | Solo dev | `import.meta.env.DEV && ENABLE_MOCK_AUTH` |
| `SECRET_KEY` | `supabase_auth.py:161-169` (firma de cookies); reutilizada por `auth.py:42-46` | Ambos; en prod rechaza placeholders y <32 chars | Secreto HMAC para cookies firmadas propias (Web Crypto `subtle.sign`) |
| `MOCK_AUTH_USER_ID` | `auth.py:28-30`; consumida en `main.py:716` | Solo dev | Igual; solo para `/dev-login` |
| `DATABASE_URL` | `models/database.py:20`; reescribe a `postgresql+psycopg://` (`database.py:23-25`) | Ambos (fallback SQLite local) | Connection string de `postgres.js`; con transaction pooler (puerto 6543, `README.md`) usar `prepare: false` |
| `LUKA_BACKEND_URL` | `conversation_flow_admin.py:34,41` | Ambos | Env server-only (nunca `PUBLIC_*`) |
| `FLOW_ADMIN_API_KEY` | `conversation_flow_admin.py:35`; header `Authorization: Bearer` (`conversation_flow_admin.py:58`) | Ambos | Env server-only; no debe llegar al navegador |
| `FLOW_ADMIN_AUTH_USER_IDS` | `conversation_flow_admin.py:23-29` (CSV, case-insensitive) | Ambos | Env server-only |

**Discrepancias detectadas (estado al 2026-09-23):**

1. `render.yaml:13` declaraba `MOCK_WHATSAPP_ID`, sin referencias en el código: **corregido 2026-09-23** (eliminada en la preparación).
2. `render.yaml` no declaraba `APP_ENV`, `APP_BASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `AUTH_COOKIE_SECURE`, `ENABLE_MOCK_AUTH` ni `MOCK_AUTH_USER_ID`: **corregido 2026-09-23** (alineado con `.env.example`, 12 variables). Queda como pendiente operativo cargar los valores reales en el dashboard de Render; el hallazgo original sigue siendo válido como causa raíz: sin esas variables, `get_auth_settings()`/`cookie_secure_enabled()` lanzan `AuthConfigurationError` (`supabase_auth.py:127-150`) y el registro OAuth no se completa.
3. `.env.example:19` usa `LUKA_BACKEND_URL=http://localhost:8000`, el mismo origen/port que `APP_BASE_URL` (`:2`): válido solo si el backend `luka` corre local en ese puerto; en prod debe apuntar al backend real.
4. `luka_session` se emite sin `secure` (`main.py:693-699,714-720`) a diferencia del resto de las cookies (`supabase_auth.py:262-288`).
5. `.env.example:9` deja `SECRET_KEY` con el placeholder `change-me-...`, que producción rechaza a propósito (`supabase_auth.py:166`).
6. `requirements.txt` declara `python-jose[cryptography]==3.3.0`, sin imports en `app/` (grep: solo aparece `AuthInvalidJwtError` de `supabase_auth`); dependencia no usada.

---

## 6. Tests

Conteo: 113 funciones `def test_` en 7 archivos (método: `Select-String -Pattern '^\s*def test_' tests\test_*.py`). Hay 10 decoradores `@pytest.mark.parametrize` (4 en `test_onboarding_finalization.py`, 3 en `test_supabase_auth.py`, 1 en `test_conversation_flow_admin.py`, 1 en `test_dashboard_login.py`, 1 en `test_registration.py`), por lo que el total **ejecutado** es mayor a 113. Con el venv local creado en la preparación (`.venv`, 2026-09-23) la suite ejecutada da **141 passed** — ese número es la línea base de paridad. No existe `conftest.py` (raíz ni `tests/`): cada archivo define sus propios fixtures.

| Archivo | Nº tests | Qué cubre | Destino | Criterio |
|---------|----------|-----------|---------|----------|
| `tests/test_conversation_flow_admin.py` | 7 | Gate de admin por allowlist, listado/editor, proxies de mutación, no filtración de `FLOW_ADMIN_API_KEY`, errores de validación | Vitest (cliente/proxy) + Playwright (páginas admin) | Portar: el proxy a `luka` sigue existiendo en Astro con el mismo contrato JSON |
| `tests/test_dashboard_login.py` | 19 | `consume_dashboard_login_token` (unidad), `/login` end-to-end, propagación de fechas, rechazo de reuso/expirado, `SECRET_KEY` sin fallback inseguro, aislamiento por usuario | Vitest (consumo de token) + Playwright (E2E `/login`) | Reescribir: la firma de cookies cambia de `itsdangerous` a Web Crypto |
| `tests/test_dashboard_queries.py` | 11 | Exclusión de `anulado_en` en las 10 consultas/KPIs y en `/exportar/csv`; aislamiento por usuario y rangos de fecha | Vitest con Postgres de test | Reescribir contra SQL/`postgres.js`; mismo dataset semántico |
| `tests/test_main.py` | 2 | `/login` renderiza; `/` sin sesión redirige 303 a `/login` | Playwright | Portar tal cual |
| `tests/test_onboarding_finalization.py` | 21 | Invitación (estados/expiración/consumo), acuerdo vigente, vinculación de usuario existente, conflictos de identidad, rollback por etapa, `FOR UPDATE`, siembra de 9 categorías default, idempotencia | Vitest + Postgres de test | Reescribir: la transacción y los `FOR UPDATE` deben probarse explícitamente en `postgres.js` |
| `tests/test_registration.py` | 18 | `/registro` por estado de invitación/acuerdo, no exposición de teléfono/hash, estados sin controles, `noindex, nofollow` | Playwright + Vitest | Portar: seguridad (no filtrar PII/hash) es requisito de corte |
| `tests/test_supabase_auth.py` | 35 | Contexto firmado, OAuth PKCE, callback, cookies (httpOnly/lax/secure/TTL), identidad Google verificada, errores terminales, `/registro/continuar`, `/registro/finalizar` (revalidación, doble submit, limpieza de cookies) | Vitest (unidad de helpers) + Playwright (E2E OAuth simulado) | Reescribir: `@supabase/ssr` cambia nombres de cookies y storage; las aserciones de seguridad se conservan |

**Total verificado: 113 tests (funciones) en 7 archivos.**

---

## 7. Stack JS propuesto para `web/`

Datos de versión y soporte tomados de `docs/investigacion-frameworks-js-2026.md` (§3.1, §4, §6).

| Pieza | Versión / paquete | Rol |
|-------|-------------------|-----|
| Framework | `astro@7.3.x` | Páginas estáticas (landing, login, registro) + SSR para dashboard/admin |
| Adaptador | `@astrojs/node` (`standalone`) | Deploy en Render (reemplaza `uvicorn`); `render.yaml` pasa a Node |
| Auth | `@supabase/ssr` | Cookies server-side (reemplaza `CookieAuthStorage` y el chunking manual de `supabase_auth.py`) |
| Datos | `postgres.js` (recomendado) o Drizzle | SQL directo al Postgres de Supabase; `prepare: false` con pooler 6543 |
| Gráficos | `chart.js@4.4.6` | Igual que `base.html:13`; montar en isla o script de página |

**Estructura propuesta:**

```text
web/
├─ src/
│  ├─ pages/
│  │  ├─ index.astro                  # dashboard (§2 #18)
│  │  ├─ login.astro
│  │  ├─ registro.astro
│  │  ├─ registro/continuar.astro
│  │  ├─ admin/flujos/{index,nuevo,[flow_id]}.astro
│  │  └─ api/                         # #2-#8, #11-#16, #19-#23
│  ├─ components/                     # stats, charts, transactions, nav, iconos
│  ├─ lib/                            # supabase, session, db (postgres.js), dashboard queries
│  ├─ styles/                         # tokens + CSS
│  └─ middleware.ts                   # 401 → redirect /login (paridad main.py:1194)
├─ public/                            # estáticos (reemplaza el mount /static)
└─ astro.config.mjs                   # @astrojs/node standalone
```

**Reutilizable del repo actual (sin cambios):** `docs/marca/tokens/tokens.css` y `docs/marca/tokens/design-tokens.json` (tokens), logos/isotipos en `docs/marca/assets/` (`favicon.svg`, `isotipo-*.svg`), los 25 SVG vigentes de `app/templates/components/icons/` como componentes Astro (`icon_nav_budgets.svg` se retiró con el link muerto de «Presupuestos», 2026-09-23), `static/css/style.css` (25.193 B), `registro.css` (5.707 B) y `admin_flows.css` (9.967 B) como referencia visual, y `static/js/admin_flows.js` (19.762 B) como referencia de comportamiento del editor. HTMX 2.0.3 (`base.html:12`) puede conservarse o reemplazarse por islas; Chart.js y la fuente Inter (`base.html:10`) se mantienen.

---

## 8. Checklist de corte (F2)

**Rutas**
- [ ] Las 25 rutas de §2 responden con el mismo método y path (incluidas las 6 del panel admin).
- [ ] `/static/*` sirve los mismos assets desde `public/`.
- [ ] 401 en endpoints autenticados redirige 303 a `/login` (paridad `main.py:1194-1196`).

**Auth**
- [ ] Magic link: token de un solo uso, hash `sha256`, estados `pendiente/consumido/vencido` y `FOR UPDATE` verificados.
- [ ] Google PKCE completo: `/registro` → `/auth/google` → callback → `/registro/continuar` → `/registro/finalizar`.
- [ ] `/dev-login` responde 404 fuera de desarrollo.
- [ ] Cookies con `httponly`, `samesite=lax`, TTL y `secure` en producción; decidir y documentar el flag `secure` de `luka_session`.
- [ ] `/logout` cierra la sesión que corresponda (propia y/o Supabase) y redirige a `/login`.

**Datos**
- [ ] Las 10 consultas de §4.1 devuelven los mismos valores de negocio (anulados excluidos, tasa USD fija, top categoría, últimos 6 meses por defecto).
- [ ] `finalize_onboarding` es atómico: sin usuario/aceptación duplicados, invitación consumida una sola vez, 9 categorías sembradas solo si no hay activas.
- [ ] `/exportar/csv` genera el mismo encabezado y filas (`Fecha, Monto, Moneda, Categoria, Descripcion`) sin cargar todo en memoria.
- [ ] Ninguna migración ni `create_all` contra Supabase desde `web/`.

**Env**
- [ ] Las 12 variables de §5 definidas en el hosting, con `APP_ENV=production`, `AUTH_COOKIE_SECURE=true` y `SECRET_KEY` ≥32 chars aleatorio.
- [ ] `render.yaml`/config del hosting sin `MOCK_WHATSAPP_ID` y con las variables de Supabase y auth.
- [ ] `FLOW_ADMIN_API_KEY` y `SECRET_KEY` solo en runtime server (nunca `PUBLIC_*`).

**Tests**
- [ ] Los 113 tests tienen equivalente o justificación de descarte (§6).
- [ ] E2E de Playwright para magic link, OAuth (simulado), registro completo, logout y dashboard.
- [ ] Vitest para consultas, tokens y proxy admin.

**Corte**
- [ ] Tráfico de producción servido por `web/`; FastAPI en solo lectura o apagado.
- [ ] Rollback definido (DNS/redeploy del servicio Python) y probado.

---

## 9. Preguntas abiertas

1. **`luka_session` y `@supabase/ssr`:** ¿se mantiene la cookie propia firmada (compatible con sesiones en vuelo de 7 días) o se adopta la sesión Supabase como sesión de dashboard (implica re-loguear a todos al corte)?
2. **`luka_session` sin `Secure`** (`main.py:693-699,714-720`): ¿se corrige en FastAPI antes del corte o se arrastra el comportamiento a Astro por paridad?
3. **HTMX vs islas:** ¿se conservan los parciales 23-25 y HTMX 2.0.3, o se reemplazan por componentes Astro con `client:load`? Afecta el tamaño del port y los tests de parciales.
4. **Parámetros `date_from`/`date_to`:** hoy se propagan desde `/login` y el dashboard usa `YYYY-MM-DD` (`main.py:648-661,928-946`). ¿Se conserva el contrato de query params en las URLs de Astro?
5. **`get_dias_racha`** retorna `0` (placeholder, `dashboard.py:531-536`): ¿se implementa durante la migración o se mantiene el placeholder?
6. **Tasa USD** hardcodeada en 1300 (`dashboard.py:34-36`): ¿se integra cotización real en F2 o se mantiene la constante?
7. **Admin en el mismo deploy:** ¿el panel `/admin/flujos` migra en el mismo corte o queda en FastAPI como servicio aparte durante una fase?
8. **Backend `luka`:** ¿expondrá endpoints directos que hagan innecesario el proxy de `conversation_flow_admin.py`, o el proxy se reimplementa en Astro con `FLOW_ADMIN_API_KEY` server-side?
9. **Pooler de Supabase:** confirmar si `web/` usará el puerto 6543 (transaction pooler, requiere `prepare: false`) o una conexión directa, y si el plan de Render permite conexiones persistentes.
10. **Tests E2E de OAuth:** ¿habrá entorno Supabase de staging para Playwright o se simula el proveedor (como hace `FakeSupabaseAuth` hoy)?
