"""Runtime configuration helpers shared by local, Render, and Workers deploys."""

from __future__ import annotations

import importlib
import os
from typing import Any


def _cloudflare_env() -> Any | None:
    """Return the Workers binding environment when running inside Cloudflare."""
    try:
        workers = importlib.import_module("workers")
        return getattr(workers, "env", None)
    except (ImportError, RuntimeError):
        return None


def get_setting(name: str, default: str = "") -> str:
    """Read a Worker binding first, then fall back to a process environment value."""
    worker_env = _cloudflare_env()
    if worker_env is not None:
        try:
            value = getattr(worker_env, name)
        except (AttributeError, RuntimeError):
            value = None
        if value is not None:
            return str(value)
    return os.getenv(name, default)


def is_cloudflare_runtime() -> bool:
    return get_setting("CLOUDFLARE_RUNTIME", "false").strip().lower() == "true"


def get_database_url() -> str:
    """Use Hyperdrive when bound, otherwise preserve the existing DATABASE_URL path."""
    worker_env = _cloudflare_env()
    if worker_env is not None:
        try:
            hyperdrive = getattr(worker_env, "HYPERDRIVE")
            connection_string = getattr(hyperdrive, "connectionString")
        except (AttributeError, RuntimeError):
            connection_string = None
        if connection_string:
            return str(connection_string)
    return get_setting("DATABASE_URL", "sqlite:///./luka.db")
