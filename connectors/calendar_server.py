import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.mcp_compat import FastMCP

mcp = FastMCP("calendar")
FAKE = os.getenv("FAKE_MODE", "1") == "1"
TZ_NAME = os.getenv("TZ_NAME", "Asia/Kolkata")
TZ = timezone(timedelta(minutes=int(os.getenv("TZ_OFFSET_MINUTES", "330"))))


def _service():
    from googleapiclient.discovery import build
    from connectors.google_auth import get_credentials
    return build("calendar", "v3", credentials=get_credentials(), cache_discovery=False)


def _rfc(s: str) -> str:
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)
    return d.isoformat()


@mcp.tool()
def list_events(start: str, end: str) -> str:
    """List events between two ISO datetimes. Returns a JSON list."""
    if FAKE:
        return json.dumps([])
    res = _service().events().list(
        calendarId="primary", timeMin=_rfc(start), timeMax=_rfc(end),
        singleEvents=True, orderBy="startTime", maxResults=20,
    ).execute()
    return json.dumps([
        {"summary": e.get("summary", "(no title)"),
         "start": e["start"].get("dateTime", e["start"].get("date")),
         "end": e["end"].get("dateTime", e["end"].get("date"))}
        for e in res.get("items", [])
    ])


@mcp.tool()
def create_event(title: str, start: str, end: str, description: str = "") -> str:
    """Create a calendar event. Returns the event id as JSON."""
    if FAKE:
        return json.dumps({"event_id": "fake-event-1"})
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": _rfc(start), "timeZone": TZ_NAME},
        "end": {"dateTime": _rfc(end), "timeZone": TZ_NAME},
        "reminders": {"useDefault": True},
    }
    ev = _service().events().insert(calendarId="primary", body=body).execute()
    return json.dumps({"event_id": ev["id"]})


@mcp.tool()
def delete_event(event_id: str) -> str:
    """Delete a calendar event by id."""
    if FAKE:
        return json.dumps({"deleted": event_id})
    _service().events().delete(calendarId="primary", eventId=event_id).execute()
    return json.dumps({"deleted": event_id})


if __name__ == "__main__":
    mcp.run()