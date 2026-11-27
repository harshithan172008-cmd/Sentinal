"""Serve Sentinel's static frontend with a local-only API bridge to its Python backend.

This entry point deliberately forces FAKE_MODE=1 and USE_LLM=0. It is for local
integration demos only; it does not expose live Gmail, Calendar, or model access.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import threading
import tempfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "sentinel-frontend"

# This local bridge must never accidentally switch to real connectors or a model.
os.environ["FAKE_MODE"] = "1"
os.environ["USE_LLM"] = "0"
os.environ["BILLS_DIR"] = str((ROOT / "tests" / "fixtures" / "bills").resolve())

import sys
sys.path.insert(0, str(ROOT))

from agent.pipeline import run_scan
from controlhub import approvals, audit, storage
from controlhub.gateway import Gateway, REDACTOR_IS_STUB

# The custom Streamlit backend and local frontend demo must never share databases.
# Keep demo records, the encryption key, and the audit chain in a temporary folder.
_DEMO_STATE = tempfile.TemporaryDirectory(prefix="sentinel-frontend-")
_DEMO_DIR = Path(_DEMO_STATE.name)
storage.DB_DIR = _DEMO_DIR
storage.DB_PATH = _DEMO_DIR / "sentinel.db"
storage.KEY_PATH = _DEMO_DIR / "secret.key"
audit.DB_PATH = _DEMO_DIR / "audit.db"

GATEWAY = Gateway()
SCAN_LOCK = threading.Lock()
LAST_SCAN_AT: str | None = None
MAX_BODY_BYTES = 64 * 1024


def _subscription(item) -> dict:
    data = item.model_dump()
    if REDACTOR_IS_STUB:
        data.pop("source_snippet", None)
    return data


def _proposal(item) -> dict:
    data = item.model_dump()
    details = data.get("details", {})
    if item.kind == "reminder":
        data["details"] = {key: details[key] for key in ("title", "start", "end") if key in details}
    elif item.kind == "draft":
        data["details"] = {key: details[key] for key in ("to", "subject", "body") if key in details}
    else:
        data["details"] = {key: details[key] for key in ("merchant", "amount", "renewal_date", "status", "old_amount") if key in details}
    if REDACTOR_IS_STUB:
        data["source_snippet"] = ""
    return data


def _state() -> dict:
    inbox = []
    for view in GATEWAY.views:
        if REDACTOR_IS_STUB:
            subject = "Billing message (subject hidden because redactor is unavailable)"
            body = "Message body hidden because redaction is unavailable."
        else:
            subject = view.get("masked_subject") or "Billing message"
            body = view.get("masked") or ""
        inbox.append({
            "id": str(view.get("id", "")),
            "subject": subject,
            "date": str(view.get("date", "")),
            "source": str(view.get("source", "local")),
            "flags": list(view.get("flags", [])),
            "masked_body": body,
        })
    valid, broken_at = audit.verify_chain()
    entries = audit.list_entries(100)
    safe_entries = [{
        key: entry.get(key) for key in ("id", "ts", "actor", "action", "tool", "decision", "hash")
    } | {"detail": "Details retained in the local audit store."} for entry in entries]
    return {
        "ok": True,
        "backend_connected": True,
        "mode": "sample",
        "live_connectors_enabled": False,
        "redactor_active": not REDACTOR_IS_STUB,
        "killed": GATEWAY.killed,
        "last_scan_at": LAST_SCAN_AT,
        "subscriptions": [_subscription(item) for item in storage.list_subscriptions()],
        "proposals": [_proposal(item) for item in approvals.list_all()],
        "inbox": inbox,
        "audit": safe_entries,
        "audit_integrity": {"valid": valid, "broken_at": broken_at},
    }


def _local_host(host: str, port: int) -> bool:
    try:
        parsed = urlsplit(f"http://{host}")
        return parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == port
    except ValueError:
        return False


def _valid_edits(proposal_id: str, edits: object) -> dict:
    if not isinstance(edits, dict):
        raise ValueError("edits must be a JSON object")
    item = approvals.get(proposal_id)
    if not item or item.status != "pending":
        raise ValueError("proposal is not pending")
    if item.kind == "draft":
        allowed = {key: edits[key] for key in ("to", "subject", "body") if key in edits}
        for key, value in allowed.items():
            if not isinstance(value, str) or len(value) > (254 if key == "to" else 5000):
                raise ValueError(f"invalid {key}")
        if "to" in allowed and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", allowed["to"]):
            raise ValueError("enter a valid email address before approving a draft")
        return allowed
    if item.kind == "reminder":
        allowed = {key: edits[key] for key in ("title", "start", "end") if key in edits}
        if "title" in allowed and (not isinstance(allowed["title"], str) or len(allowed["title"]) > 200):
            raise ValueError("invalid reminder title")
        for key in ("start", "end"):
            if key in allowed:
                if not isinstance(allowed[key], str) or len(allowed[key]) > 40:
                    raise ValueError(f"invalid {key}")
                datetime.fromisoformat(allowed[key])
        return allowed
    return {}


class Handler(SimpleHTTPRequestHandler):
    server_version = "SentinelLocal/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    @property
    def listen_port(self) -> int:
        return self.server.server_address[1]

    def log_message(self, fmt: str, *args) -> None:
        print(f"[sentinel-web] {self.address_string()} {fmt % args}")

    def _json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _request_origin_ok(self) -> bool:
        host = self.headers.get("Host", "")
        if not _local_host(host, self.listen_port):
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme != "http" or parsed.netloc.lower() != host.lower():
                return False
        return True

    def _body(self) -> dict:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if size < 0 or size > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(size) if size else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid JSON body") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if not parsed.path.startswith("/api/"):
            if not _local_host(self.headers.get("Host", ""), self.listen_port):
                self._json(403, {"ok": False, "error": "loopback access only"})
                return
            return super().do_GET()
        if not self._request_origin_ok():
            self._json(403, {"ok": False, "error": "same-origin loopback requests only"})
            return
        if parsed.path in ("/api/health", "/api/state"):
            self._json(200, _state())
            return
        self._json(404, {"ok": False, "error": "API route not found"})

    def do_POST(self) -> None:
        if not self._request_origin_ok():
            self._json(403, {"ok": False, "error": "same-origin loopback requests only"})
            return
        parsed = urlsplit(self.path)
        try:
            body = self._body()
            if parsed.path == "/api/scan":
                if REDACTOR_IS_STUB:
                    self._json(503, {"ok": False, "error": "Scanning is disabled because the privacy redactor is unavailable."})
                    return
                global LAST_SCAN_AT
                with SCAN_LOCK:
                    result = asyncio.run(run_scan(GATEWAY))
                    if result.get("status") == "ok":
                        LAST_SCAN_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")
                if result.get("status") != "ok":
                    self._json(409, {"ok": False, "error": result.get("reason", "scan blocked"), "state": _state()})
                    return
                self._json(200, {"ok": True, "state": _state()})
                return
            if parsed.path == "/api/kill":
                GATEWAY.kill()
                self._json(200, {"ok": True, "state": _state()})
                return
            if parsed.path == "/api/resume":
                GATEWAY.killed = False
                audit.log("user", "resume", "-", "allow", "local demo access restored")
                self._json(200, {"ok": True, "state": _state()})
                return
            if parsed.path == "/api/simulate-block":
                result = asyncio.run(GATEWAY.call("gmail.forward", {"to": "blocked@example.invalid"}, actor="demo"))
                self._json(200, {"ok": True, "blocked": result.get("status") == "blocked", "state": _state()})
                return
            if parsed.path == "/api/audit/verify":
                valid, broken_at = audit.verify_chain()
                self._json(200, {"ok": True, "valid": valid, "broken_at": broken_at, "state": _state()})
                return
            match = re.fullmatch(r"/api/approvals/([^/]+)/(approve|reject|undo)", parsed.path)
            if match:
                proposal_id, action = unquote(match.group(1)), match.group(2)
                if action == "approve":
                    edits = _valid_edits(proposal_id, body.get("edits", {}))
                    result = asyncio.run(approvals.approve(GATEWAY, proposal_id, edits or None))
                elif action == "reject":
                    approvals.reject(proposal_id)
                    result = {"status": "ok"}
                else:
                    result = asyncio.run(approvals.undo(GATEWAY, proposal_id))
                if result.get("status") != "ok":
                    self._json(409, {"ok": False, "error": result.get("reason", "action not completed"), "state": _state()})
                    return
                self._json(200, {"ok": True, "state": _state()})
                return
            self._json(404, {"ok": False, "error": "API route not found"})
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(500, {"ok": False, "error": f"backend error: {type(exc).__name__}"})

    def do_OPTIONS(self) -> None:
        self._json(405, {"ok": False, "error": "cross-origin requests are not supported"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sentinel's local frontend and safe demo backend")
    parser.add_argument("--port", type=int, default=8000, help="loopback HTTP port (default: 8000)")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    if not FRONTEND.is_dir() or not (FRONTEND / "index.html").is_file():
        parser.error(f"frontend files not found at {FRONTEND}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Sentinel local demo: http://127.0.0.1:{args.port}")
    print("Demo mode is forced on: sample fixtures only; no live Gmail, Calendar, or model access.")
    print("Localhost only. Demo data is isolated in a temporary folder and removed when the process exits.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Sentinel local demo...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
