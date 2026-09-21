"""Cloudflare Python Worker entrypoint for the migration spike."""

from workers import asgi

from app.main import app


Default = asgi.entrypoint(app)
