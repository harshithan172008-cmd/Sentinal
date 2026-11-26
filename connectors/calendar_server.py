import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.mcp_compat import FastMCP

mcp = FastMCP("calendar")
FAKE = os.getenv("FAKE_MODE", "1") == "1"


def _need_real():
    raise NotImplementedError("Real Calendar mode is not built yet. Run with FAKE_MODE=1.")


@mcp.tool()
def list_events(start: str, end: str) -> str:
    """List calendar events between two ISO datetimes."""
    if not FAKE:
        _need_real()
    return json.dumps([])


@mcp.tool()
def create_event(title: str, start: str, end: str, description: str = "") -> str:
    """Create a calendar event. Returns the event id as JSON."""
    if not FAKE:
        _need_real()
    return json.dumps({"event_id": "fake-event-1"})


@mcp.tool()
def delete_event(event_id: str) -> str:
    """Delete a calendar event by id."""
    if not FAKE:
        _need_real()
    return json.dumps({"deleted": event_id})


if __name__ == "__main__":
    mcp.run()