# Investigación: frameworks JavaScript para migrar el frontend de LUKA

- **Fecha del informe:** 23 de septiembre de 2026
- **Alcance:** análisis de frameworks JavaScript para migrar las tecnologías del frontend de LUKA
  (`luka_frontend`) y evolucionar el producto con una landing page.
- **Método:** relevamiento del repositorio local, documentación oficial vía Context7
  (Astro, SvelteKit, Qwik, SolidStart, Nuxt), blogs y comunicados oficiales de cada proyecto,
  documentación oficial de Supabase, y consulta directa a las APIs de npm y GitHub el
  23/09/2026. No incluye opiniones ni recomendaciones: solo datos, capacidades y estado de
  cada tecnología.

---

## 1. Estado actual del frontend de LUKA

### 1.1 Stack

| Componente | Detalle | Evidencia |
|---|---|---|
| Servidor | FastAPI 0.115.5 + Uvicorn 0.32.1 | `requirements.txt` |
| Plantillas | Jinja2 3.1.4 (12 plantillas HTML + iconos SVG) | `app/templates/` |
| Reactividad | HTMX 2.0.3 (CDN, `defer`) | `app/templates/base.html` |
| Gráficos | Chart.js 4.4.6 (CDN, `defer`) | `app/templates/base.html` |
| Estilos | CSS propio: `style.css` 25.193 B, `admin_flows.css` 9.967 B, `registro.css` 5.707 B | `static/css/` |
| JS propio | `admin_flows.js` 19.762 B (solo panel de flujos) | `static/js/` |
| Auth | Supabase Auth (Google OAuth + magic link) con cookies de sesión server-side | `app/services/supabase_auth.py`, `app/auth.py` |
| Datos | SQLAlchemy 2.0.36 → PostgreSQL (Supabase, pooler puerto 6543) | `requirements.txt`, `README.md` |
| Backend externo | API de `luka` (bot de WhatsApp) protegida con `FLOW_ADMIN_API_KEY` | `app/services/conversation_flow_admin.py` |
| Despliegue | Render, plan free (`render.yaml`), servicio Python con spin-down por inactividad | `render.yaml` |

### 1.2 Superficie funcional (25 rutas)

| Grupo | Rutas | Evidencia |
|---|---|---|
| Onboarding | `/registro`, `/registro/continuar`, `/registro/finalizar` | `app/main.py:137,422,477` |
| Auth | `/auth/google`, `/auth/callback`, `/login`, `/dev-login`, `/logout` | `app/main.py:177,279,664,708,724` |
| Dashboard | `/`, claves `/api/graficos/distribucion\|cartera\|flujo` | `app/main.py:949,1060,1074,1088` |
| Parciales HTMX | `/dashboard/actualizar`, `/partials/charts`, `/partials/transactions` | `app/main.py:1107,1141,1161` |
| Exportación | `/exportar/csv` | `app/main.py:990` |
| Panel de flujos | `/admin/flujos` (+ API borrador/validar/publicar/retirar) | `app/main.py:771-892` |

### 1.3 Implicancias de migración (funciones que requieren cómputo server-side)

1. **Sesión con cookies** (magic link / OAuth) y validación de identidad.
2. **Consultas SQL** al Postgres compartido (hoy vía SQLAlchemy; no se porta 1:1 a JS).
3. **Exportación CSV** generada en servidor.
4. **Proxy al backend `luka`** con `FLOW_ADMIN_API_KEY`, que no debe exponerse al navegador.
5. **Landing page**: contenido público, sin datos de usuario; puede resolverse con HTML estático.

---

## 2. Criterios de comparación utilizados

- Versión estable publicada al 23/09/2026 y cadencia de releases.
- Adopción: descargas semanales en npm y estrellas en GitHub (medición del 23/09/2026).
- Peso entregado al cliente: JS por defecto y tamaño típico de bundles según comparativas 2026.
- Modos de render: estático/prerender, SSR, CSR e híbrido.
- Capacidad de endpoints server-side (necesaria para auth, CSV y secretos).
- Soporte oficial de Supabase para SSR/auth por framework.
- Adaptadores y plataformas de despliegue soportadas.
- Gobernanza, licencia y estado de mantenimiento del proyecto.

---

## 3. Frameworks analizados

### 3.1 Astro

| Dato | Valor | Fuente |
|---|---|---|
| Última versión (npm `astro`) | **7.3.4** | npm registry, 23/09/2026 |
| Descargas npm | **4.159.730/semana** | npm API, 23/09/2026 |
| Estrellas GitHub | **62.756** (`withastro/astro`) | GitHub API, 23/09/2026 |
| Licencia / gobernanza | MIT; el equipo de The Astro Technology Company se incorporó a Cloudflare (16/01/2026); se anunció que Astro sigue open source, MIT, con gobernanza abierta y soporte a múltiples plataformas | Comunicado Cloudflare y blog de Astro (16/01/2026) |
| Hitos recientes | Astro 6 (beta en ene-2026, estable en el primer trimestre); **Astro 7 GA 22/06/2026** (compilador `.astro` reescrito en Rust, Vite 8 + Rolldown, builds 15-61% más rápidos); Astro 7.2 (06/08/2026) con builds estáticos incrementales experimentales | Blog oficial de Astro |
| Peso por defecto | **0 KB de JavaScript** en páginas sin islas; solo se hidrata lo marcado con directivas `client:*` | Documentación oficial de Astro |
| Modos de render | Estático por defecto (`output: 'static'`); SSR on-demand con adaptadores (`@astrojs/node` `standalone`, Cloudflare, Vercel, Netlify y otros) | Docs Context7 `/withastro/docs` |
| Capacidades | Islas (`client:load/visible/idle`), Server Islands (`server:defer`), endpoints y Actions server-side, CSP integrado, API de fuentes, Live Content Collections, route caching estable en 7.0 | Docs oficiales |
| Supabase (SSR/auth) | Quickstart oficial con `@supabase/ssr` + adaptador Node (`supabase.com/docs/guides/auth/quickstarts/astrojs`); Astro figura entre los frameworks soportados en la guía "Creating a Supabase client for SSR" | Documentación oficial de Supabase |
| Despliegue | Estático en cualquier CDN (Cloudflare Pages, Netlify, Vercel) o SSR en Node/edge | Docs oficiales |

### 3.2 SvelteKit

| Dato | Valor | Fuente |
|---|---|---|
| Última versión | **@sveltejs/kit 2.70.3** (Svelte 5.57.1) | npm registry, 23/09/2026 |
| Descargas npm | **1.888.619/semana** (kit); `svelte` 4.236.198/semana | npm API, 23/09/2026 |
| Estrellas GitHub | **20.826** (`sveltejs/kit`); `sveltejs/svelte` 88.171 | GitHub API, 23/09/2026 |
| Licencia / gobernanza | MIT; mantenido por el equipo de Svelte; Vercel lo lista entre los frameworks que apoya (junto a Next.js, Turborepo y AI SDK) en el anuncio de NuxtLabs (08/07/2025) | Blog de Vercel |
| Hitos recientes | Svelte 5 (runas) como línea estable; **SvelteKit 3 en Release Candidate desde el 13/08/2026** (seguirá en `@next` hasta GA); funciones remotas y formularios remotos en desarrollo activo durante 2026 | Blog oficial de Svelte |
| Peso típico | ~15-30 KB gzip por página de contenido (comparativa 2026: ignax.dev, pkgpulse) | Terceros + docs |
| Modos de render | Prerender por página/layout (`export const prerender = true`), SSR por defecto, CSR, SPA con fallback; `adapter-static`, `adapter-node`, adaptadores Vercel/Netlify/Cloudflare | Docs Context7 `/websites/svelte_dev_kit` |
| Capacidades | Form actions con progressive enhancement, endpoints `+server`, hooks de sesión, funciones remotas, preload de fuentes | Docs oficiales |
| Supabase (SSR/auth) | Guía oficial dedicada (`supabase.com/docs/guides/auth/server-side/sveltekit`), quickstart de SvelteKit, tutorial de app de usuarios | Documentación oficial de Supabase |
| Despliegue | Node (Render y otros), Vercel, Netlify, Cloudflare, estático | Docs oficiales |

### 3.3 Nuxt

| Dato | Valor | Fuente |
|---|---|---|
| Última versión | **4.5.2** (Vue 3.5.43) | npm registry, 23/09/2026 |
| Descargas npm | **1.555.417/semana** (`nuxt`); `vue` 12.038.101/semana | npm API, 23/09/2026 |
| Estrellas GitHub | **60.893** (`nuxt/nuxt`) | GitHub API, 23/09/2026 |
| Licencia / gobernanza | MIT; NuxtLabs (empresa que financiaba al equipo) fue adquirida por Vercel el 08/07/2025; el framework Nuxt permanece como proyecto independiente con roadmap público y gobernanza abierta | Comunicados NuxtLabs y Vercel (08/07/2025) |
| Ciclo de vida | Nuxt 4 estable (16/07/2025), **Nuxt 3 EOL el 31/07/2026**, Nuxt 5 estimado para Q4 2026 (migración a Nitro v3) | Roadmap oficial de Nuxt |
| Hitos recientes | Nuxt 4.5 (18/07/2026): Vite 8, Rspack 2, SSR streaming experimental, base para Nuxt 5 | Blog oficial de Nuxt |
| Peso típico | ~50-100 KB gzip en aplicaciones típicas (comparativas 2026) | Terceros |
| Modos de render | SSR, SSG (`nuxt generate`), CSR (`ssr: false`) e híbrido por ruta con `routeRules` (`prerender`, `cache`, `redirect`) | Docs Context7 `/websites/nuxt_4_x` |
| Capacidades | Server routes vía Nitro, módulos oficiales (i18n, UI, Content, Image), typed pages, view transitions estables | Docs oficiales |
| Supabase (SSR/auth) | `@supabase/ssr` incluye pestaña Nuxt con `runtimeConfig`; quickstart oficial de Nuxt en la guía de inicio | Documentación oficial de Supabase |
| Despliegue | Preset Node (Render y otros), Vercel, Netlify, Cloudflare, estático | Docs oficiales |

### 3.4 Hono (+ HTMX)

| Dato | Valor | Fuente |
|---|---|---|
| Última versión | **4.13.8** | npm registry, 23/09/2026 |
| Descargas npm | **46.132.378/semana**; el número incluye uso como dependencia transitiva de otras herramientas | npm API, 23/09/2026 |
| Estrellas GitHub | **32.302** (`honojs/hono`) | GitHub API, 23/09/2026 |
| Licencia | MIT | Repositorio oficial |
| Peso | Framework de servidor orientado a edge con runtime mínimo; HTMX 2.x pesa ~14 KB gzip y ya se usa en el proyecto | htmx.org, `base.html` |
| Modos de render | SSR/API en Node, Bun, Deno y Cloudflare Workers; generación estática con el helper `hono/ssg`; JSX server-side con `hono/jsx` | Docs oficiales |
| Capacidades | Router, middleware, validación, JSX SSR; sin sistema de contenido, imágenes o i18n integrados (a construir) | Docs oficiales |
| Supabase (SSR/auth) | Quickstart oficial "Hono" (auth anónima + lecturas con RLS) y Hono listado entre los frameworks soportados por `@supabase/ssr` | Documentación oficial de Supabase |
| Despliegue | Workers (sin cold start), Node (Render), Bun, Deno, Lambda y otros | Docs oficiales |
| Encaje con el código actual | Permite conservar plantillas/HTMX/Chart.js y reemplazar únicamente el runtime Python por un servidor JS | Análisis de estructura del repo |

### 3.5 Eleventy (11ty)

| Dato | Valor | Fuente |
|---|---|---|
| Última versión | **3.1.6** (jun-2026); 4.0.0 en alpha | npm registry y 11ty.dev, 23/09/2026 |
| Descargas npm | **162.952/semana** | npm API, 23/09/2026 |
| Estrellas GitHub | **19.929** (`11ty/eleventy`) | GitHub API, 23/09/2026 |
| Licencia / gobernanza | MIT; desde sep-2024 el proyecto pertenece a Font Awesome; en mar-2026 pasó a llamarse "Build Awesome" | 11ty.dev, Wikipedia (Eleventy) |
| Hitos recientes | v3.0 (oct-2024), v3.1 (may-2025, "11% más rápido y 22% más chico"), v3.1.6 (jun-2026), v4.0.0-alpha | 11ty.dev y Wikipedia |
| Peso | **0 KB de JS de framework**; genera HTML/CSS y no impone runtime de cliente | Docs oficiales |
| Modos de render | Generación estática (SSG) únicamente; no incluye servidor en runtime ni SSR | Docs oficiales |
| Capacidades | Multi-template (Liquid, Nunjucks, Markdown, HTML, etc.), plugins, servidor de desarrollo con recarga en vivo | Docs oficiales |
| Supabase | Solo cliente de navegador (`supabase-js`); no hay guía oficial de auth SSR para Eleventy | Docs de Supabase (no figura entre los frameworks de la guía SSR) |
| Despliegue | Cualquier hosting estático (Netlify, Cloudflare Pages, Vercel, GitHub Pages) | Docs oficiales |
| Límite funcional | No cubre auth, endpoints ni consultas server-side; requeriría una API aparte o mantener el backend actual para el dashboard | Análisis de estructura del repo |

---

## 4. Tabla comparativa (datos al 23/09/2026)

| Criterio | Astro | SvelteKit | Nuxt | Hono + HTMX | Eleventy |
|---|---|---|---|---|---|
| Última versión | 7.3.4 | 2.70.3 (3 RC) | 4.5.2 | 4.13.8 | 3.1.6 (4 alpha) |
| Descargas npm/semana | 4.159.730 | 1.888.619 | 1.555.417 | 46.132.378* | 162.952 |
| Estrellas GitHub | 62.756 | 20.826 (kit) | 60.893 | 32.302 | 19.929 |
| Licencia | MIT | MIT | MIT | MIT | MIT |
| JS por defecto | 0 KB | ~15-30 KB gzip | ~50-100 KB gzip | ~0-14 KB (HTMX) | 0 KB |
| Landing estática / SEO | Sí (estático por defecto) | Sí (`prerender`) | Sí (`prerender`/`generate`) | Sí (`hono/ssg`) | Sí (único modo) |
| SSR / endpoints | Sí (adaptadores) | Sí (Node/edge) | Sí (Nitro) | Sí (Node/edge) | No |
| Auth SSR Supabase oficial | Sí | Sí | Sí | Sí | No |
| Soporte multi-framework de UI | Sí (React, Svelte, Vue, Solid, Preact) | No (Svelte) | No (Vue) | No (JSX propio o HTMX) | N/A (agnóstico, sin componentes) |
| Adaptador Node (Render) | `@astrojs/node` | `adapter-node` | preset Node | `@hono/node-server` | N/A |
| Despliegue estático | Sí | Sí (`adapter-static`) | Sí | Sí (`hono/ssg`) | Sí |

\* Hono incluye uso como dependencia transitiva de otras herramientas; su descarga directa como framework es menor.

---

## 5. Otros frameworks evaluados fuera del grupo de 5

| Framework | Datos al 23/09/2026 | Motivo de exclusión del grupo |
|---|---|---|
| Qwik (`@builder.io/qwik`) | v1.20.0; 50.612 descargas/semana; 22.069 ★. La línea **v2 sigue en beta**: `@qwik.dev/core` 2.0.0-beta.43 (01/09/2026); el README oficial declara "This is the branch for Qwik v2, currently in beta" | No cuenta con versión v2 estable |
| SolidStart (`@solidjs/start`) | v2.0.5 estable (04/08/2026); 94.756 descargas/semana; `solidjs/solid-start` 5.922 ★. El 19/09/2026 se reportó su paso a **mantenimiento**: sus capacidades se incorporan a Solid 2, que está en **Release Candidate** (blog de Solid, 13/08/2026) | Proyecto en mantenimiento y sucesor aún no estable |
| Next.js (`next`) | v16.3.6; 42.734.285 descargas/semana; 142.407 ★; bundles típicos de ~85-250 KB (comparativas 2026) | Framework con mayor peso de salida entre los evaluados |
| React Router 7 / Remix, Fresh (Deno), Preact + Vite, TanStack Start | Sin medición específica en esta investigación | Se mantuvieron fuera del grupo de 5 por no aportar capacidades distintas a las ya cubiertas por los finalistas |

---

## 6. Consideraciones técnicas registradas durante la investigación

### 6.1 Autenticación

- Supabase mantiene el paquete `@supabase/ssr` (clientes browser + server con cookies) con
  guías/quickstarts oficiales para: Next.js, SvelteKit, Astro, Remix, React Router, Express,
  Hono y Nuxt; además existen quickstarts de producto para Astro, SvelteKit, Nuxt, Hono y SolidJS.
- El proyecto actual usa el flujo PKCE con cookies (`app/services/supabase_auth.py`), equivalente
  al patrón que documenta `@supabase/ssr`.
- Eleventy no figura en las guías SSR oficiales de Supabase.

### 6.2 Acceso a datos

- SQLAlchemy no tiene equivalencia directa en JS. Rutas documentadas:
  - **Supabase Data API** (`supabase-js` / REST) con políticas RLS en las tablas.
  - **Cliente Postgres en JS** (p. ej. `postgres.js`, Drizzle) en runtime Node.
- En Cloudflare Workers, la conexión directa a Postgres requiere Hyperdrive; la Data API de
  Supabase no tiene ese requisito (documentación de Supabase/Cloudflare).
- El repo `luka_frontend` documenta que las migraciones de la base compartida pertenecen a
  `blob1618/luka` y que este repositorio solo mantiene modelos consumidores (`README.md`).

### 6.3 Secretos y funciones server-side

- `FLOW_ADMIN_API_KEY` y `SECRET_KEY` se usan hoy solo en servidor (`app/services/conversation_flow_admin.py`,
  `app/auth.py`). Cualquier opción que conserve esos flujos necesita un runtime server:
  Astro SSR, SvelteKit, Nuxt, Hono o una API aparte en el caso de Eleventy.

### 6.4 Despliegue y cold starts

- `render.yaml` define un servicio Python en plan free, con spin-down por inactividad.
- Los hostings estáticos (Cloudflare Pages, Netlify, Vercel) no tienen cold start por tratarse
  de CDN; Cloudflare Workers tampoco aplica cold start en su modelo de ejecución.
- Astro, SvelteKit, Nuxt y Hono soportan adaptadores para Node y para plataformas edge/CDN.

### 6.5 Coexistencia con HTMX y Chart.js

- HTMX 2.x (~14 KB gzip) y Chart.js 4.4.6 pueden usarse en cualquiera de las 5 opciones; el
  proyecto ya los carga desde CDN en `app/templates/base.html`.
- Astro permite montar Chart.js dentro de islas o de páginas estáticas sin framework de UI.

### 6.6 Estado de versiones relevantes para planificación

| Proyecto | Línea estable | Próxima línea | Fecha/fase |
|---|---|---|---|
| Astro | 7.3.4 | — | GA 22/06/2026 |
| SvelteKit | 2.70.3 | 3.0 RC (`@next`) | RC 13/08/2026 |
| Svelte | 5.57.1 | — | estable |
| Nuxt | 4.5.2 | 5.x (Nitro v3) | estimado Q4 2026; Nuxt 3 EOL 31/07/2026 |
| Hono | 4.13.8 | — | estable |
| Eleventy | 3.1.6 | 4.0.0-alpha | alpha |
| Qwik | 1.20.0 | 2.0.0-beta.43 | beta desde 2025 |
| Solid | 1.9.15 | 2.0 RC | RC 13/08/2026 |
| SolidStart | 2.0.5 | — | mantenimiento desde 19/09/2026 (reportado) |
| Next.js | 16.3.6 | — | estable |

---

## 7. Metodología de recolección de métricas

- **Descargas npm:** API pública `api.npmjs.org/downloads/point/last-week/{paquete}`, consultada
  el 23/09/2026 para `astro`, `@sveltejs/kit`, `svelte`, `nuxt`, `vue`, `hono`,
  `@11ty/eleventy`, `@builder.io/qwik`, `@solidjs/start`, `solid-js`, `next`.
- **Versiones:** API `registry.npmjs.org/{paquete}/latest`, misma fecha.
- **Estrellas y actividad:** API `api.github.com/repos/{owner}/{repo}`, misma fecha.
- **Capacidades de render y despliegue:** documentación oficial consultada vía Context7
  (`/withastro/docs`, `/websites/svelte_dev_kit`, `/qwikdev/qwik`,
  `/websites/solidjs_solid-start_v2`, `/websites/nuxt_4_x`) y sitios oficiales.
- **Tamaños de bundle:** comparativas públicas de 2026 (pkgpulse.com, ignax.dev,
  dev.to "Next.js vs Remix vs Astro vs SvelteKit") y afirmaciones de los sitios oficiales
  (Astro: 0 KB por defecto; SvelteKit: bundles compilados más chicos; htmx.org: ~14 KB gzip).

---

## 8. Fuentes

### Oficiales

- Astro: `astro.build/blog/joining-cloudflare` (16/01/2026), `astro.build/blog/astro-7` (22/06/2026),
  `astro.build/blog/astro-720` (06/08/2026), `astro.build/` (muestra 7.3), `astro.build/blog/whats-new-*` (2026).
- Cloudflare: `cloudflare.com/press/press-releases/2026/cloudflare-acquires-astro-...` (16/01/2026),
  `blog.cloudflare.com/astro-joins-cloudflare` (16/01/2026).
- Svelte/SvelteKit: `svelte.dev/blog` ("The SvelteKit 3 Release Candidate is here", 13/08/2026;
  "What's new in Svelte: September 2026"; "What's new in Svelte: June 2026"; changelogs de `sveltejs/kit`).
- Nuxt: `nuxt.com/docs/4.x/community/roadmap` y `github.com/nuxt/nuxt` (Nuxt 4 estable 16/07/2025;
  Nuxt 5 Q4 2026; Nuxt 3 EOL 31/07/2026), blog de Nuxt 4.5 (18/07/2026).
- NuxtLabs/Vercel: `nuxtlabs.com` y `vercel.com/blog/nuxtlabs-joins-vercel` (08/07/2025).
- Qwik: `github.com/QwikDev/qwik` (README v2 en beta), releases `2.0.0-beta.43` (01/09/2026), `qwik.dev`.
- Solid: `start.solidjs.com`, discusión "SolidStart v2 is now Stable" (04/08/2026),
  `solidjs.com/blog/solid-2-0-rc-the-big-reveal` (13/08/2026); InfoQ, "SolidStart 2 ... enters
  maintenance" (19/09/2026).
- Eleventy: `11ty.dev` (v3.1.6; "Build Awesome"), Wikipedia "Eleventy (software)" (estable 3.1.6, jun-2026).
- Hono: `github.com/honojs/hono`, `hono.dev`.
- Supabase: `supabase.com/docs/guides/auth/quickstarts/astrojs`,
  `supabase.com/docs/guides/auth/server-side/sveltekit`,
  `supabase.com/docs/guides/auth/server-side/creating-a-client` (pestañas Next.js, SvelteKit,
  Astro, Remix, React Router, Express, Hono, Nuxt),
  `supabase.com/docs/guides/getting-started` (quickstarts de React, Next.js, Nuxt, Astro, Hono,
  SvelteKit, SolidJS, Vue, RedwoodJS, TanStack Start, Refine).

### Terceros citados

- pkgpulse.com: "Next.js vs Astro vs SvelteKit 2026" (16/03/2026), "Astro vs SvelteKit" (08/03/2026).
- ignax.dev: "Astro vs SvelteKit for Content Sites" (27/05/2026).
- dev.to: "Next.js vs Remix vs Astro vs SvelteKit in 2026" (24/02/2026),
  "Top 5 JavaScript Frameworks to Watch in 2026" (05/10/2025).
- github.com/MarioVieilledent/js-framework-comparison (tamaños de bundles minificados por framework).
- thenewstack.io: "Astro Redesigns Its Development Server" (17/01/2026).
