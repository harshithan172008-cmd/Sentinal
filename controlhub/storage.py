import json
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from shared.schemas import Subscription

DB_DIR = Path(__file__).resolve().parents[1] / "db"
DB_PATH = DB_DIR / "sentinel.db"
KEY_PATH = DB_DIR / "secret.key"


def _fernet() -> Fernet:
    DB_DIR.mkdir(exist_ok=True)
    if not KEY_PATH.exists():
        KEY_PATH.write_bytes(Fernet.generate_key())
    return Fernet(KEY_PATH.read_bytes())


def _conn():
    DB_DIR.mkdir(exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS kv (kind TEXT, id TEXT, data BLOB, PRIMARY KEY (kind, id))")
    return c


def put(kind: str, id_: str, obj: dict) -> None:
    blob = _fernet().encrypt(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    c = _conn()
    try:
        c.execute("INSERT OR REPLACE INTO kv (kind, id, data) VALUES (?,?,?)", (kind, id_, blob))
        c.commit()
    finally:
        c.close()


def get(kind: str, id_: str):
    c = _conn()
    try:
        row = c.execute("SELECT data FROM kv WHERE kind=? AND id=?", (kind, id_)).fetchone()
    finally:
        c.close()
    return json.loads(_fernet().decrypt(row[0])) if row else None


def all_(kind: str) -> list[dict]:
    c = _conn()
    try:
        rows = c.execute("SELECT data FROM kv WHERE kind=?", (kind,)).fetchall()
    finally:
        c.close()
    f = _fernet()
    return [json.loads(f.decrypt(r[0])) for r in rows]


def list_subscriptions() -> list[Subscription]:
    return [Subscription(**d) for d in all_("subscription")]


def wipe_all() -> None:
    for p in (DB_PATH, KEY_PATH):
        if p.exists():
            p.unlink()