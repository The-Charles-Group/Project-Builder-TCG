
from __future__ import annotations
import os, sqlite3, json, time, hashlib, threading
from typing import Any, Dict, List, Tuple

DEFAULT_DB = os.getenv("BRAIN_DB_PATH", "/tmp/brain.sqlite3")
_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS episodes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  rfp_hash TEXT NOT NULL,
  industry TEXT,
  metadata TEXT,
  selections TEXT
);
CREATE TABLE IF NOT EXISTS weights_draft(
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta REAL NOT NULL,
  support INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL,
  PRIMARY KEY(deliverable_code, token)
);
CREATE TABLE IF NOT EXISTS weights_published(
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta REAL NOT NULL,
  support INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL,
  PRIMARY KEY(deliverable_code, token)
);
CREATE TABLE IF NOT EXISTS episode_updates(
  episode_id INTEGER NOT NULL,
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta_change REAL NOT NULL
);
"""

def _connect(db_path: str = DEFAULT_DB):
    os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init(db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            for stmt in SCHEMA.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(s+';')
            conn.commit()
        finally:
            conn.close()

def _hash_text(text: str) -> str:
    import hashlib
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()

def get_setting(key: str, default: str = "", db_path: str = DEFAULT_DB) -> str:
    with _LOCK:
        conn = _connect(db_path)
        try:
            r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return r["value"] if r else default
        finally:
            conn.close()

def set_setting(key: str, value: str, db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
            conn.commit()
        finally:
            conn.close()

def add_episode(rfp_text: str, selections: Dict[str, Any], industry: str | None, metadata: Dict[str, Any], db_path: str = DEFAULT_DB) -> int:
    with _LOCK:
        conn = _connect(db_path)
        try:
            ts = int(time.time()*1000)
            rfp_hash = _hash_text(rfp_text)
            conn.execute(
                "INSERT INTO episodes(ts,rfp_hash,industry,metadata,selections) VALUES(?,?,?,?,?)",
                (ts, rfp_hash, industry or "", json.dumps(metadata or {}), json.dumps(selections or {}))
            )
            eid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            conn.commit()
            return int(eid)
        finally:
            conn.close()

def list_episodes(limit: int = 50, offset: int = 0, db_path: str = DEFAULT_DB) -> List[Dict[str,Any]]:
    with _LOCK:
        conn = _connect(db_path)
        try:
            rows = conn.execute("SELECT id,ts,rfp_hash,industry,metadata,selections FROM episodes ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            return [{
                "id": r["id"], "ts": r["ts"], "rfp_hash": r["rfp_hash"],
                "industry": r["industry"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "selections": json.loads(r["selections"] or "{}"),
            } for r in rows]
        finally:
            conn.close()

def upsert_draft_updates(episode_id: int, updates: List[Tuple[str,str,float]], support_inc: int = 1, db_path: str = DEFAULT_DB):
    now = int(time.time()*1000)
    with _LOCK:
        conn = _connect(db_path)
        try:
            for code, token, delta_change in updates:
                row = conn.execute("SELECT delta,support FROM weights_draft WHERE deliverable_code=? AND token=?", (code, token)).fetchone()
                if row:
                    new_delta = float(row["delta"]) + float(delta_change)
                    new_support = int(row["support"]) + int(support_inc)
                    conn.execute("UPDATE weights_draft SET delta=?, support=?, updated_ts=? WHERE deliverable_code=? AND token=?", (new_delta, new_support, now, code, token))
                else:
                    conn.execute("INSERT INTO weights_draft(deliverable_code,token,delta,support,updated_ts) VALUES(?,?,?,?,?)", (code, token, float(delta_change), int(support_inc), now))
                conn.execute("INSERT INTO episode_updates(episode_id,deliverable_code,token,delta_change) VALUES(?,?,?,?)", (episode_id, code, token, float(delta_change)))
            conn.commit()
        finally:
            conn.close()

def publish_draft(db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            conn.execute("DELETE FROM weights_published")
            conn.execute("INSERT INTO weights_published(deliverable_code,token,delta,support,updated_ts) SELECT deliverable_code,token,delta,support,updated_ts FROM weights_draft")
            conn.commit()
        finally:
            conn.close()

def reset_all(db_path: str = DEFAULT_DB):
    with _LOCK:
        conn = _connect(db_path)
        try:
            for table in ("weights_draft","weights_published","episodes","episode_updates"):
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
        finally:
            conn.close()

def undo_last_episode(db_path: str = DEFAULT_DB) -> bool:
    with _LOCK:
        conn = _connect(db_path)
        try:
            row = conn.execute("SELECT id FROM episodes ORDER BY id DESC LIMIT 1").fetchone()
            if not row: return False
            eid = int(row["id"])
            upd = conn.execute("SELECT deliverable_code,token,delta_change FROM episode_updates WHERE episode_id=?", (eid,)).fetchall()
            for r in upd:
                code, token, change = r["deliverable_code"], r["token"], float(r["delta_change"])
                row2 = conn.execute("SELECT delta,support FROM weights_draft WHERE deliverable_code=? AND token=?", (code, token)).fetchone()
                if row2:
                    new_delta = float(row2["delta"]) - change
                    new_support = max(0, int(row2["support"]) - 1)
                    conn.execute("UPDATE weights_draft SET delta=?, support=? WHERE deliverable_code=? AND token=?", (new_delta, new_support, code, token))
            conn.execute("DELETE FROM episode_updates WHERE episode_id=?", (eid,))
            conn.execute("DELETE FROM episodes WHERE id=?", (eid,))
            conn.commit()
            return True
        finally:
            conn.close()

def get_weights(which: str = "published", limit: int = 200, db_path: str = DEFAULT_DB) -> List[Dict[str,Any]]:
    table = "weights_published" if which == "published" else "weights_draft"
    with _LOCK:
        conn = _connect(db_path)
        try:
            rows = conn.execute(f"SELECT deliverable_code,token,delta,support,updated_ts FROM {table} ORDER BY ABS(delta) DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
