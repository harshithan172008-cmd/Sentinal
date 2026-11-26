import base64
import json
import os
import sys
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.mcp_compat import FastMCP

mcp = FastMCP("gmail")
FAKE = os.getenv("FAKE_MODE", "1") == "1"
QUERY = (
    'newer_than:90d (renewal OR renews OR invoice OR receipt OR trial OR subscription '
    'OR bill OR "price change" OR "payment due")'
)


def _fixtures() -> list:
    for p in (ROOT / "tests" / "fixtures" / "emails.json", ROOT / "shared" / "sample_emails.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return []


def _service():
    from googleapiclient.discovery import build
    from connectors.google_auth import get_credentials
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _walk(part: dict, out: dict) -> None:
    mime = part.get("mimeType", "")
    data = (part.get("body") or {}).get("data")
    if data and mime == "text/plain" and not out["text"]:
        out["text"] = _decode(data)
    elif data and mime == "text/html" and not out["html"]:
        out["html"] = _decode(data)
    for sub in part.get("parts") or []:
        _walk(sub, out)


def _to_doc(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    out = {"text": "", "html": ""}
    _walk(msg["payload"], out)
    try:
        date = parsedate_to_datetime(headers.get("date", "")).date().isoformat()
    except Exception:
        date = ""
    return {
        "id": msg["id"],
        "sender": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": date,
        "body_text": out["text"],
        "body_html": out["html"] or None,
        "source": "gmail",
    }


@mcp.tool()
def search_billing_emails(max_results: int = 20) -> str:
    """Return billing-related emails as a JSON list of EmailDoc objects."""
    if FAKE:
        return json.dumps(_fixtures()[:max_results])
    svc = _service()
    ids = svc.users().messages().list(userId="me", q=QUERY, maxResults=max_results).execute().get("messages", [])
    docs = [_to_doc(svc.users().messages().get(userId="me", id=m["id"], format="full").execute()) for m in ids]
    return json.dumps(docs)


@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> str:
    """Create a Gmail draft (never sends). Returns the draft id as JSON."""
    if FAKE:
        return json.dumps({"draft_id": "fake-draft-1"})
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    d = _service().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return json.dumps({"draft_id": d["id"]})


@mcp.tool()
def delete_draft(draft_id: str) -> str:
    """Delete a draft by id."""
    if FAKE:
        return json.dumps({"deleted": draft_id})
    _service().users().drafts().delete(userId="me", id=draft_id).execute()
    return json.dumps({"deleted": draft_id})


if __name__ == "__main__":
    mcp.run()