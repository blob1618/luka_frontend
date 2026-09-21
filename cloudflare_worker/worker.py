"""Cloudflare Python Worker entrypoint for the migration spike."""

from workers import WorkerEntrypoint, asgi

from app.main import app
from app.models.database import configure_database
from app.runtime import configure_worker_env, get_database_url


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Hyperdrive bindings may only be read from inside a request handler.
        configure_worker_env(self.env)
        configure_database(get_database_url(), postgres_driver="pg8000")

        if (request.headers.get("upgrade") or "").lower() == "websocket":
            return await asgi.websocket(app, request, self.env)
        return await asgi.fetch(app, request, self.env, self.ctx)
