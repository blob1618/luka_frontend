# Cloudflare Workers Free migration spike

This branch deploys the existing FastAPI/Jinja application as a Python Worker.
It does not modify or replace the Render production service.

## Safe initial deployment

The checked-in Wrangler configuration uses production cookie behavior and disables
the local mock login. No database URL, authentication key, backend API key, or
other secret is committed. The `/health` and `/login` routes can be used to verify
the Worker and template/static-asset packaging before connecting production data.

## Cloudflare configuration

Configure the following encrypted Worker secrets in **Workers & Pages →
luka-frontend-cloudflare-spike → Settings → Variables and Secrets**:

- `SECRET_KEY`
- `SUPABASE_PUBLISHABLE_KEY`
- `FLOW_ADMIN_API_KEY`
- `FLOW_ADMIN_AUTH_USER_IDS`

Configure these non-secret variables in the same screen:

- `APP_BASE_URL`: the final HTTPS Worker or custom-domain origin
- `SUPABASE_URL`
- `LUKA_BACKEND_URL`

The database should use a Cloudflare Hyperdrive binding named `HYPERDRIVE`.
Create the Hyperdrive configuration with the existing Supabase PostgreSQL
connection string, then add this binding to `wrangler.jsonc`:

```json
"hyperdrive": [
  {
    "binding": "HYPERDRIVE",
    "id": "YOUR_HYPERDRIVE_CONFIGURATION_ID"
  }
]
```

Do not commit the original database connection string.

## OAuth and Luka backend

After the Worker URL is stable:

1. Add `<APP_BASE_URL>/auth/callback` to the allowed Supabase/Google OAuth redirects.
2. Set Luka backend `ONBOARDING_REGISTRATION_URL` to `<APP_BASE_URL>/registro` only
   after the full registration flow is verified.
3. Verify login links, cookies, dashboard queries, HTMX partials, CSV export, and
   the conversation-flow admin screens before moving traffic.

## Commands

```bash
uv sync
uv run python scripts/generate_cloudflare_templates.py
uv run python scripts/prepare_cloudflare_worker.py
uv run pywrangler dev
uv run pywrangler deploy
```

Jinja HTML and included SVG templates are bundled into `app/template_bundle.py`
for the Workers filesystem snapshot. Regenerate that module whenever either
kind of template changes:

```bash
uv run python scripts/generate_cloudflare_templates.py
```

`prepare_cloudflare_worker.py` then copies only application Python modules into
the scoped Worker source directory. This prevents Wrangler from uploading local
virtual environments, test files, or Render-only artifacts.

Cloudflare Free currently limits each dynamic request to 10 ms of CPU time. The
spike is successful only if authenticated server-rendered routes remain below that
limit under realistic data.

## Current free-tier finding

The Worker deploys successfully, serves templates and assets, and connects to the
existing PostgreSQL database through Hyperdrive with the pure-Python `pg8000`
driver. However, repeated database-backed login checks intermittently exceed the
Workers Free 10 ms CPU limit and return a Cloudflare 1102 error. Do not move
production traffic from Render until the application is reduced to a static/thin
frontend that calls the Luka backend, or the Worker is moved to a paid plan with a
higher CPU allowance.
