import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.mcp_compat import FastMCP

mcp = FastMCP("gmail")
FAKE = os.getenv("FAKE_MODE", "1") == "1"


def _fixtures() -> list:
    for p in (ROOT / "tests" / "fixtures" / "emails.json", ROOT / "shared" / "sample_emails.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return []


def _need_real():
    raise NotImplementedError("Real Gmail mode is not built yet. Run with FAKE_MODE=1.")


@mcp.tool()
def search_billing_emails(max_results: int = 20) -> str:
    """Return billing-related emails as a JSON list of EmailDoc objects."""
    if not FAKE:
        _need_real()
    return json.dumps(_fixtures()[:max_results])


@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> str:
    """Create a Gmail draft (never sends). Returns the draft id as JSON."""
    if not FAKE:
        _need_real()
    return json.dumps({"draft_id": "fake-draft-1"})


@mcp.tool()
def delete_draft(draft_id: str) -> str:
    """Delete a draft by id."""
    if not FAKE:
        _need_real()
    return json.dumps({"deleted": draft_id})


if __name__ == "__main__":
    mcp.run()