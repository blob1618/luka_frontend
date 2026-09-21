"""Assemble the local Python source tree consumed by Wrangler."""

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE_APP = ROOT / "app"
WORKER_APP = ROOT / "cloudflare_worker" / "app"


def main() -> None:
    if WORKER_APP.exists():
        shutil.rmtree(WORKER_APP)
    for source in SOURCE_APP.rglob("*.py"):
        destination = WORKER_APP / source.relative_to(SOURCE_APP)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


if __name__ == "__main__":
    main()
