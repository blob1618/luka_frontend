"""Regenerate the Python template bundle consumed by Cloudflare Workers."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = ROOT / "app" / "templates"
OUTPUT = ROOT / "app" / "template_bundle.py"


def main() -> None:
    template_files = sorted(
        path
        for path in TEMPLATE_ROOT.rglob("*")
        if path.suffix in {".html", ".svg"}
    )
    templates = {
        path.relative_to(TEMPLATE_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in template_files
    }
    lines = [
        '"""Generated Jinja templates for the Cloudflare Workers filesystem snapshot."""',
        "",
        "TEMPLATES = {",
    ]
    lines.extend(f"    {name!r}: {content!r}," for name, content in templates.items())
    lines.extend(["}", ""])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
