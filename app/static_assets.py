"""Content-based URLs keep templates and their static assets on the same version."""

from hashlib import sha256
from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def static_asset_url(path: str) -> str:
    version = sha256((STATIC_DIR / path).read_bytes()).hexdigest()[:16]
    return f"/static/{path}?v={version}"
