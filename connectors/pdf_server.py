import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.mcp_compat import FastMCP

mcp = FastMCP("pdf")


def _bills_dir() -> Path:
    env = os.getenv("BILLS_DIR")
    if env:
        return Path(env).resolve()
    for p in (ROOT / "bills", ROOT / "tests" / "fixtures" / "bills"):
        if p.exists():
            return p.resolve()
    return (ROOT / "bills").resolve()


def _safe(rel: str) -> Path:
    """Resolve a path and refuse anything outside the bills folder."""
    base = _bills_dir()
    target = (base / rel).resolve() if rel else base
    if target != base and base not in target.parents:
        raise PermissionError("path is outside the bills folder")
    return target


def _extract_text(path: Path) -> str:
    import pdfplumber
    text = ""
    ocr_pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = (page.extract_text() or "").strip()
            if len(t) < 50:
                try:
                    ocr_pages.append(page.to_image(resolution=300).original)
                except Exception:
                    pass
            text += t + "\n"
    if len(text.strip()) < 50 and ocr_pages:
        try:
            import pytesseract
            text = "\n".join(pytesseract.image_to_string(img) for img in ocr_pages)
        except Exception:
            pass  # Tesseract not installed: keep whatever text we have
    return text.strip()


@mcp.tool()
def list_bills(folder: str = "") -> str:
    """List PDF bills inside the chosen bills folder. Returns a JSON list of relative paths."""
    base = _safe(folder)
    if not base.exists():
        return json.dumps([])
    root = _bills_dir()
    return json.dumps(sorted(str(p.relative_to(root)).replace("\\", "/") for p in base.rglob("*.pdf")))


@mcp.tool()
def read_bill(path: str) -> str:
    """Read one PDF bill and return it as an EmailDoc JSON object."""
    p = _safe(path)
    if p.suffix.lower() != ".pdf" or not p.is_file():
        raise FileNotFoundError("not a PDF file in the bills folder")
    text = _extract_text(p)
    first = (text.splitlines() or [""])[0]
    slug = re.sub(r"[^a-z0-9]", "", (first.split() or ["bill"])[0].lower()) or "bill"
    m = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text)
    date = m.group(1) if m else datetime.fromtimestamp(p.stat().st_mtime).date().isoformat()
    return json.dumps({
        "id": f"pdf-{p.stem}",
        "sender": f"bill@{slug}.pdf",
        "subject": first or p.stem,
        "date": date,
        "body_text": text,
        "source": "pdf",
    })


if __name__ == "__main__":
    mcp.run()