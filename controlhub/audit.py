import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "audit.db"
GENESIS = "0" * 64


def _conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute(
        "CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts TEXT, actor TEXT, action TEXT, tool TEXT, decision TEXT, detail TEXT, "
        "prev_hash TEXT, hash TEXT)"
    )
    return c


def _digest(prev, ts, actor, action, tool, decision, detail) -> str:
    payload = json.dumps([ts, actor, action, tool, decision, detail], ensure_ascii=False)
    return hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()


def log(actor: str, action: str, tool: str, decision: str, detail: str = "") -> None:
    c = _conn()
    try:
        row = c.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev = row[0] if row else GENESIS
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        h = _digest(prev, ts, actor, action, tool, decision, detail)
        c.execute(
            "INSERT INTO audit (ts, actor, action, tool, decision, detail, prev_hash, hash) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ts, actor, action, tool, decision, detail, prev, h),
        )
        c.commit()
    finally:
        c.close()


def verify_chain() -> tuple[bool, int | None]:
    """Returns (True, None) if intact, else (False, id of first broken row)."""
    c = _conn()
    try:
        prev = GENESIS
        for id_, ts, actor, action, tool, decision, detail, p, h in c.execute(
            "SELECT id, ts, actor, action, tool, decision, detail, prev_hash, hash "
            "FROM audit ORDER BY id"
        ):
            if p != prev or _digest(prev, ts, actor, action, tool, decision, detail) != h:
                return False, id_
            prev = h
        return True, None
    finally:
        c.close()


def list_entries(limit: int = 100) -> list[dict]:
    c = _conn()
    try:
        cols = ["id", "ts", "actor", "action", "tool", "decision", "detail", "prev_hash", "hash"]
        rows = c.execute(
            "SELECT id, ts, actor, action, tool, decision, detail, prev_hash, hash "
            "FROM audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        c.close()