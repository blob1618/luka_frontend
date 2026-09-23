# 00 · Plan de limpieza y preparación para la migración a Astro

| Campo | Valor |
|---|---|
| **Objetivo** | Migrar el frontend de LUKA (FastAPI + Jinja2 + HTMX) a Astro SSR con acceso directo a Postgres y auth `@supabase/ssr`, en fases, sin cortar el servicio en producción. |
| **Estado** | `v1.0` — 2026-09-23 |
| **Alcance** | Repositorio `luka_frontend`: landing pública, registro/onboarding, dashboard, APIs de gráficos, export CSV y panel de flujos. No incluye cambios en el repo `luka/` (bot de WhatsApp) ni en el esquema de la base compartida. |
| **Documentos relacionados** | `docs/investigacion-frameworks-js-2026.md` (base técnica y versiones); `docs/migracion-astro/01-inventario-paridad.md` (inventario de rutas, tests y variables de entorno — este plan lo referencia y no lo duplica); `docs/marca/00-luka-brand-compass.md` y `docs/marca/tokens/` (decisiones de marca cerradas). |

---

## 1. Contexto y hallazgos

### 1.1 Stack actual

| Componente | Detalle | Evidencia |
|---|---|---|
| Servidor | FastAPI 0.115.5 + Uvicorn 0.32.1 | `requirements.txt` |
| Plantillas | Jinja2 3.1.4 (12 plantillas HTML: 9 páginas + 3 parciales; 25 iconos SVG) | `app/templates/` |
| Reactividad | HTMX 2.0.3 (CDN, `defer`) | `app/templates/base.html` |
| Gráficos | Chart.js 4.4.6 (CDN, `defer`) | `app/templates/base.html` |
| Estilos | CSS propio: `style.css` 25.193 B, `admin_flows.css` 9.967 B, `registro.css` 5.707 B | `static/css/` |
| JS propio | `admin_flows.js` 19.762 B (solo panel de flujos) | `static/js/` |
| Datos | SQLAlchemy 2.0.36 + `psycopg[binary]` 3.3.4 → PostgreSQL de Supabase (pooler puerto 6543) | `requirements.txt`, `.env.example` |
| Auth | `supabase` 2.31.0 (PKCE, Google OAuth + magic link) + cookie de sesión propia firmada con `SECRET_KEY` (`itsdangerous`) | `app/services/supabase_auth.py`, `app/auth.py` |
| Despliegue | Render plan free (`render.yaml`), spin-down por inactividad | `render.yaml`, investigación §6.4 |

### 1.2 Superficie funcional y cobertura

- **25 rutas** en `app/main.py` (onboarding, auth, dashboard, parciales HTMX, exportación, panel de flujos). El detalle por ruta y su destino en Astro vive en `01-inventario-paridad.md`.
- **113 tests** en `tests/`, con esta distribución (conteo al 2026-09-23):

| Archivo | Tests | Fase destino |
|---|---|---|
| `test_registration.py` | 18 | F1 |
| `test_onboarding_finalization.py` | 21 | F1 |
| `test_supabase_auth.py` | 35 | F1 |
| `test_main.py` | 2 | F1/F2 (según ruta) |
| `test_dashboard_login.py` | 19 | F2 |
| `test_dashboard_queries.py` | 11 | F2 |
| `test_conversation_flow_admin.py` | 7 | F2 |

### 1.3 Autenticación con cookies (PKCE)

- Flujo PKCE confirmado: `flow_type="pkce"` (`app/services/supabase_auth.py:421`), cookie de verificador `luka_sb_pkce` (10 min) y cookies de sesión Supabase (15 min), más cookies de contexto de onboarding (30 min) y auth pendiente (15 min).
- Existe además una cookie de sesión propia, `luka_session`, firmada con `SECRET_KEY` (`app/auth.py:23-31`); `/dev-login` la emite para desarrollo con `ENABLE_MOCK_AUTH` (`app/auth.py:38`, `app/main.py:716`).
- `@supabase/ssr` cubre este patrón de cookies; la equivalencia exacta de nombres/expiración y la decisión sobre conservar o no `luka_session` se resuelven en F1 (los tests de `test_supabase_auth.py` son el contrato de referencia).

### 1.4 `public/` no se sirve en producción hoy

- FastAPI monta únicamente `static/` (`app/main.py:90`); `public/` (logos, favicons) no tiene ruta de servido y por lo tanto no está disponible en producción actual.
- `public/` contiene los assets definitivos de marca: `logo-luka.svg`, `logo-luka-claro.svg`, `logo-luka-oscuro.svg`, `logo-luka-mono.svg`, `favicon.svg`, `favicon-32.png`, `favicon-512.png`, `apple-touch-icon.png`.
- Consecuencia: F0 debe resolver el servido de `public/` en Astro (ver F0) y la landing es la primera oportunidad real de usarlos.

### 1.5 `render.yaml` sincronizado (corregido 2026-09-23)

**Hallazgo original:** `render.yaml` declaraba `MOCK_WHATSAPP_ID` (variable muerta, sin referencias en el repo) y omitía 7 variables que la app lee de verdad. Sin `APP_ENV=production` + `AUTH_COOKIE_SECURE=true` y sin las variables de Supabase, `cookie_secure_enabled()`/`get_auth_settings()` lanzan `AuthConfigurationError` (`app/services/supabase_auth.py:127-150`): el registro OAuth no puede completarse con ese deploy.

**Corrección aplicada en la preparación** (`render.yaml` alineado con `.env.example`, 12 variables):

| Variable | `.env.example` | `render.yaml` final |
|---|---|---|
| `APP_ENV` | sí | sí (`sync: false`) |
| `APP_BASE_URL` | sí | sí (`sync: false`) |
| `SUPABASE_URL` | sí | sí (`sync: false`) |
| `SUPABASE_PUBLISHABLE_KEY` | sí | sí (`sync: false`) |
| `AUTH_COOKIE_SECURE` | sí | sí (`sync: false`) |
| `ENABLE_MOCK_AUTH` | sí | sí (`sync: false`) |
| `SECRET_KEY` | sí | sí (`generateValue: true`) |
| `MOCK_AUTH_USER_ID` | sí | sí (`sync: false`) |
| `DATABASE_URL` | sí | sí (`sync: false`) |
| `LUKA_BACKEND_URL` | sí | sí (`sync: false`) |
| `FLOW_ADMIN_API_KEY` | sí | sí (`sync: false`) |
| `FLOW_ADMIN_AUTH_USER_IDS` | sí | sí (`sync: false`) |
| `MOCK_WHATSAPP_ID` | no | **eliminada** |

Pendiente operativo (no de código): cargar los valores reales de las variables `sync: false` en el dashboard de Render; el YAML solo declara su existencia. Parseo validado con `js-yaml` (2026-09-23).

### 1.6 CI solo Python

`.github/workflows/ci.yml` corre Ruff + pytest con `DATABASE_URL=sqlite:///./luka.db`. No hay job de Node: F0 agrega el job de `web/` sin tocar el job existente (que se retira con FastAPI en F2).

### 1.7 Marca lista para consumir

- Tokens: `docs/marca/tokens/tokens.css` (6.717 B, 155 líneas, tema oscuro por defecto + `[data-theme="light"]`) y `design-tokens.json` como fuente de verdad (D5.3).
- Tipografía decidida (D3.4): Space Grotesk (display), Inter con cifras tabulares (UI/datos), JetBrains Mono. `tokens.css` no declara `font-family` ni `@font-face`: el aprovisionamiento de fuentes es tarea de F0.
- Isotipo definitivo integrado (D3.3) en `docs/marca/assets/` y `public/`.

### 1.8 Limpieza ya ejecutada (2026-09-23)

| Acción | Evidencia |
|---|---|
| Isotipo definitivo (color/claro/oscuro/mono) + favicon SVG/PNG + apple-touch en `public/`; set canónico en `docs/marca/assets/`; metadata C2PA eliminada (~70 KB → ~7 KB por SVG) | `docs/marca/00-luka-brand-compass.md` changelog `v0.3.0` |
| `render.yaml` alineado con `.env.example`; `MOCK_WHATSAPP_ID` eliminada | §1.5 |
| Link muerto «Presupuestos» eliminado del sidebar (el handler `/` ignora `view`) y su icono `icon_nav_budgets.svg` retirado (quedó sin referencias) | `app/templates/base.html`; `app/templates/components/icons/` (25 SVG) |
| README: sección de variables de entorno completa (12) | `README.md` |
| `.gitignore`: `.venv/` y `.playwright-mcp/` | `.gitignore` |
| Suite verificada tras la limpieza: `ruff` OK y `pytest` **141 passed** (venv local) | 2026-09-23 |

No se tocó: CSS/templates/JS de la app (se reemplazan en Astro), `app/services/`, `app/models/`, tests ni el repo `luka/`.

---

## 2. Decisiones

### 2.1 Cerradas (no se re-litigan)

1. **Framework:** Astro SSR (línea 7.3.x) con adaptador `@astrojs/node` en modo `standalone`.
2. **Datos:** acceso directo a Postgres con `postgres.js` (alternativa evaluada: Drizzle). Sin ORM pesado: las migraciones del esquema pertenecen a `luka/` (contrato documentado en `README.md`).
3. **Auth:** `@supabase/ssr` (el proyecto ya usa PKCE).
4. **Estrategia:** migración por fases. Primero landing + registro/onboarding (bajo riesgo), después dashboard/APIs/CSV/admin.
5. **Coexistencia:** Astro vive en `web/` dentro de este mismo repositorio; FastAPI permanece operativo hasta el cutover y se retira al final de F2.
6. **Landing pública:** dentro del alcance (página estática, 0 KB de JS).
7. **Repo `luka/`:** no se toca en esta etapa; sus pendientes quedan diferidos (§7).

### 2.2 Pendientes

| Decisión | Estado | Criterios / recomendación |
|---|---|---|
| **Hosting** | Pendiente (§4) | Se planifica asumiendo Render Node; Cloudflare Pages/Workers queda como alternativa sujeta a cold start, costo y complejidad de Postgres. |
| **Driver Postgres** | Recomendación: `postgres.js` | Es la ruta documentada para runtime Node, sin capa de esquema que duplique lo que ya gobierna `luka/`. Drizzle se justificaría solo si aparecen consultas tipadas reutilizables o introspección; reevaluar al portar `dashboard.py` en F2. |
| **Dominio / subdominio** | Pendiente | Definir dominio canónico de la landing y si el dashboard conserva host actual (p. ej. `app.` vs raíz). Requisito para SEO (F1) y para el cutover (F2). |
| **Política de retiro de FastAPI** | Pendiente | No borrar `app/`, `static/` ni tests Python hasta: checklist de paridad cerrado + ventana de rollback cumplida + cero tráfico en el servicio viejo. El borrado va en un PR separado. |

---

## 3. Fases

### F0 · Scaffold de `web/`

**Objetivo:** dejar un proyecto Astro que compila, consume la marca y tiene CI propio, sin tocar el servicio en producción.

**Tareas:**
1. Crear `web/` con Astro 7.3.x + `@astrojs/node` (`standalone`), TypeScript estricto.
2. Consumir tokens sin duplicarlos: `web/src/styles/global.css` importa `docs/marca/tokens/tokens.css` (Vite permite importar fuera del root). Si el build no lo tolera, copiar el archivo y anotar la deuda de sincronización.
3. Aprovisionar fuentes Space Grotesk + Inter (cifras tabulares) + JetBrains Mono; aplicar la clase `.tabular` de los tokens a datos numéricos.
4. Servir logos/favicons desde una sola copia: `publicDir` apuntando a `../public/`; si el build lo rechaza, copiar los 8 archivos a `web/public/`.
5. `web/.env.example` con subconjunto: `APP_ENV`, `APP_BASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `AUTH_COOKIE_SECURE`, `DATABASE_URL`, y `SECRET_KEY` solo si F1 conserva la cookie `luka_session`. Las claves del panel de flujos (`LUKA_BACKEND_URL`, `FLOW_ADMIN_API_KEY`, `FLOW_ADMIN_AUTH_USER_IDS`) se agregan en F2.
6. `web/README.md`: comandos (`dev`, `build`, `preview`), variables y relación con el resto del repo.
7. Job nuevo de CI para `web/` (install + build) en `.github/workflows/ci.yml`, junto al job Python existente.

**Criterios de salida (verificables):**
- `npm run build` en `web/` termina en verde y genera salida estática/SSR sin errores de tipos.
- Una página mínima renderiza con variables de `tokens.css` aplicadas (tema oscuro y `[data-theme="light"]`).
- El job de CI de `web/` corre y pasa; el job Python sigue pasando.
- `web/.env.example` y `web/README.md` existen y listan lo indicado.

**Riesgos específicos:** import de tokens/fuentes fuera del root de Vite (mitigar con copia + deuda anotada); `publicDir` fuera del proyecto (idem); divergencia de versiones Node local vs CI (fijar versión en el workflow).

### F1 · Landing + registro/onboarding

**Objetivo:** landing pública indexable y flujo de registro/onboarding completo en Astro, sin datos de dashboard.

**Tareas:**
1. Landing estática: prerender, 0 KB de JS de framework, metadatos SEO (title, description, canonical, Open Graph), assets de marca de `public/`, copy según `docs/marca/02-identidad-verbal.md`.
2. Páginas de registro (`/registro`, `/registro/continuar`, `/registro/finalizar`) con el contrato actual: aceptación de términos, Google OAuth y magic link.
3. Auth con `@supabase/ssr`: clientes browser/server, intercambio PKCE y cookies; decidir explícitamente si se conserva `luka_session` o si la sesión Supabase es la única fuente.
4. Portar los tests de registro/onboarding/auth a `web/` (equivalencia 1:1 con `test_registration.py`, `test_onboarding_finalization.py`, `test_supabase_auth.py` y las rutas de `test_main.py` que apliquen).
5. Verificación de contraste y cifras tabulares contra tokens (checklist visual de `docs/marca/05`).

**Criterios de salida (verificables):**
- Flujo completo registro → callback → finalización funciona contra el entorno de staging de Supabase, incluida la reentrada a `/registro/continuar` y los estados de invitación inválida/consumida.
- Landing prerenderizada: su HTML no carga JS de framework (verificable en el build).
- Tests portados verdes en CI; los tests Python equivalentes siguen verdes (convivencia).
- Nada de F1 consulta datos de dashboard ni toca `/exportar/csv`.

**Riesgos específicos:** cambio de nombres/atributos de cookies rompe sesiones existentes (mitigar aceptando re-login en el cambio y probando contra el mismo proyecto Supabase); duplicación temporal de la lógica de onboarding entre Python y Astro (mitigar con el inventario como contrato y congelando cambios en la versión Python); SEO del dominio nuevo (definir canónico antes de publicar).

### F2 · Dashboard + APIs + CSV + admin

**Objetivo:** paridad 1:1 del área privada en Astro y retiro de FastAPI.

**Tareas:**
1. Data layer con `postgres.js`: portar las consultas de `app/dashboard.py` y `app/models/` según el inventario de `01-inventario-paridad.md`; sin DDL ni migraciones (esas viven en `luka/`).
2. Dashboard con gráficos Chart.js y parciales equivalentes a HTMX (`/dashboard/actualizar`, `/partials/charts`, `/partials/transactions`) o su reemplazo directo en Astro.
3. Export CSV en servidor (`/exportar/csv`), sin exponer credenciales al navegador.
4. Panel de flujos: proxy server-side a la API de `luka/` con `FLOW_ADMIN_API_KEY`, autorización con `FLOW_ADMIN_AUTH_USER_IDS` y paridad con `admin_flows.js`.
5. Portar los tests restantes (`test_dashboard_login.py`, `test_dashboard_queries.py`, `test_conversation_flow_admin.py`).
6. Verificar que `render.yaml` siga sincronizado (ya corregido 2026-09-23, §1.5/§1.8) y cargar los valores reales de las variables `sync: false` en Render; desplegar `web/` y hacer cutover de dominio/subdominio.
7. Retiro de FastAPI: borrar `app/`, `static/` y tests Python, y decidir si `web/` pasa a la raíz del repo o queda en `web/`.

**Criterios de salida (verificables):**
- Checklist de paridad 1:1 de `01-inventario-paridad.md` cerrado: cada ruta y cada test tiene equivalente verificado.
- Rollback ensayado: se puede volver al servicio FastAPI repuntando el dominio, con el servicio viejo aún desplegado y la base intacta.
- Panel de flujos opera contra la API real de `luka/` sin que `FLOW_ADMIN_API_KEY` aparezca en respuestas ni en bundles del cliente.
- CI final: jobs de `web/` verdes; job Python retirado junto con el código.

**Riesgos específicos:** divergencia de resultados entre SQLAlchemy y `postgres.js` (mitigar comparando salidas de cada endpoint antes del cutover); permisos de DB insuficientes para el usuario del pooler (verificar antes de portar consultas); dos servicios free de Render con spin-down independiente durante la convivencia (mitigar haciendo el corte por dominio y no dejando ambos públicos); pérdida de cobertura al retirar tests Python (mitigar con el mapeo del inventario y el gate de paridad).

---

## 4. Deploy

| Criterio | Render (asumido para planificar) | Cloudflare (Pages + Workers) |
|---|---|---|
| Cold start | Plan free con spin-down por inactividad (investigación §6.4) | Sin cold start en CDN/Workers |
| Postgres directo | Sí, `postgres.js` contra el pooler 6543 | Requiere Hyperdrive o Supabase Data API |
| Adaptador Astro | `@astrojs/node` (`standalone`) | `@astrojs/cloudflare` |
| Landing estática | Servida por el mismo servicio Node | CDN, sin costo de cómputo |
| Costo | Free (con spin-down) | Free en capas estáticas/Workers; Hyperdrive según plan |
| Complejidad operativa | Una sola plataforma (la actual), sin infra nueva | Nueva plataforma + pieza de conexión a Postgres |

**Decisión pendiente.** Criterios para cerrarla: si el cold start del dashboard es aceptable en free y se prioriza simplicidad operativa → Render Node; si el dashboard necesita respuesta sin cold start y se acepta sumar Hyperdrive o Data API → Cloudflare. El modelo híbrido (landing estática en CDN + dashboard en Render) queda fuera de esta etapa.

---

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Auth/cookies | Sesiones invalidadas por diferencias entre `luka_sb_*`/`luka_session` y `@supabase/ssr` | Probar contra el mismo proyecto Supabase en staging; aceptar re-login en el cambio; no tocar las cookies viejas hasta el cutover |
| Permisos de DB | Consultas portadas fallan o escriben de más | Sin DDL desde `web/`; validar cada consulta contra el inventario; usar el mismo usuario/pooler restringido |
| Doble servicio free durante la convivencia | Dos servicios que se suspenden por separado; confusión de tráfico | Corte por dominio/subdominio; no publicitar ambas URLs; el servicio viejo queda como rollback, no como espejo |
| SEO / dominio | Landing nueva sin indexar o canibalizando al dominio viejo | Definir canónico antes de publicar; metadatos y sitemap en F1; redirecciones al cutover |
| Pérdida de cobertura de tests | Regresiones silenciosas al retirar pytest | Mapeo test→test en el inventario; gate de paridad en F2; no borrar Python hasta el checklist cerrado |
| Deriva de datos | Dashboard Astro muestra números distintos a FastAPI | Comparación de salidas por endpoint antes del cutover; conservar `USD_TO_ARS_RATE` solo si se decide mantener paridad (§7) |

---

## 6. Rollback por fase

| Fase | Qué se conserva | Cómo se vuelve atrás |
|---|---|---|
| F0 | Todo FastAPI y su deploy intactos | Borrar `web/` y su job de CI; producción nunca se tocó |
| F1 | FastAPI en producción; Astro solo en staging/preview | Dejar de usar staging; el flujo real sigue en FastAPI; no hay cambios de dominio |
| F2 | Servicio FastAPI desplegado, base intacta, `render.yaml` viejo recuperable por git | Repuntar dominio/subdominio al servicio FastAPI; restaurar `render.yaml`; el borrado de `app/`, `static/` y tests ocurre solo después de cerrar la ventana de rollback, en un PR separado |

---

## 7. Pendientes diferidos (no se ejecutan en esta etapa)

| Pendiente | Repo | Archivo | Estado |
|---|---|---|---|
| D2.6 — Copys de degradación en voz Luka (reemplazo de «Se perdió el contexto») | `luka/` | `app/services/dispatcher.py` (ocurrencias en líneas 2596, 2629, 2671, 2720, 2786, 2829, 2885, 2956, 3643, 3675, 3774) | Copy aprobado 2026-09-23; implementación pendiente (`docs/marca/02-identidad-verbal.md:87`) |
| D3.6 — Categorías con tildes + `UPDATE` de filas existentes | Semillas en `luka_frontend/`; migración de datos en `luka/` (contrato de `README.md`) | `luka_frontend/app/services/onboarding_finalization.py:19-29` (`"Educacion"`); filas existentes requieren `UPDATE categorias` | Aprobado 2026-09-23; migración pendiente. Al 2026-09-23 no existe migración escrita en `luka/` (búsqueda sin resultados) |
| STK-222 — Reacciones ✅/❌ del contrato de feedback | `luka/` | `app/api/whatsapp.py:629` (`send_whatsapp_reaction`, base de STK-180 ⏳) | D4.3 aprobado; implementación pendiente (`docs/marca/04-ux-conductual.md:184`) |
| Paleta categórica de gráficos | `luka/` | `app/services/movement_chart.py:22` (`PALETTE = ("#3066BE", "#087F8C", "#7A5195", "#BB5A24", "#A33757", "#58752D")`) | A migrar a tokens categóricos (`docs/marca/00-luka-brand-compass.md:135`) |
| Cotización USD | `luka_frontend/` (no `luka/`) | `app/dashboard.py:34-36` (`USD_TO_ARS_RATE = 1300.0`, hardcodeada; TODOs en 34 y 300 apuntan a Redis/tabla de config, **no** a variable de entorno) | Sin decisión de fuente real. Como `dashboard.py` se porta en F2, este pendiente entra al alcance de F2 (paridad con el valor hardcodeado o integración real) |

---

## 8. Fuentes

- `docs/investigacion-frameworks-js-2026.md` (Astro 7.3.4, `@astrojs/node`, `@supabase/ssr`, SQLAlchemy sin equivalencia 1:1, cold starts, requisitos de runtime server-side).
- Repositorio: `README.md`, `render.yaml`, `.env.example`, `.github/workflows/ci.yml`, `requirements.txt`, `app/main.py`, `app/auth.py`, `app/services/supabase_auth.py`, `app/services/onboarding_finalization.py`, `app/dashboard.py`, `app/templates/`, `tests/`, `public/`.
- Marca: `docs/marca/00-luka-brand-compass.md`, `docs/marca/02-identidad-verbal.md`, `docs/marca/03-identidad-visual.md`, `docs/marca/04-ux-conductual.md`, `docs/marca/tokens/tokens.css`.
- Repo `luka/` (solo lectura, verificación de pendientes): `app/services/dispatcher.py`, `app/services/movement_chart.py`, `app/api/whatsapp.py`.
- `docs/migracion-astro/01-inventario-paridad.md` (documento hermano: rutas, tests y variables de entorno).
