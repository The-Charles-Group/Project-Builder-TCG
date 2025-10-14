"""
Enhanced brain store with confidence adjustment tracking
"""
from __future__ import annotations
import os, sqlite3, json, time, hashlib, threading
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime

DEFAULT_DB = os.getenv("BRAIN_DB_PATH", "/tmp/brain.sqlite3")
_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);

-- Episode tracking (learning sessions)
CREATE TABLE IF NOT EXISTS episodes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  rfp_hash TEXT NOT NULL,
  industry TEXT,
  metadata TEXT,
  selections TEXT
);

-- Draft weights (unpublished adjustments)
CREATE TABLE IF NOT EXISTS weights_draft(
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta REAL NOT NULL,
  support INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL,
  PRIMARY KEY(deliverable_code, token)
);

-- Published weights (active adjustments)
CREATE TABLE IF NOT EXISTS weights_published(
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta REAL NOT NULL,
  support INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL,
  PRIMARY KEY(deliverable_code, token)
);

-- Episode updates (changes per episode)
CREATE TABLE IF NOT EXISTS episode_updates(
  episode_id INTEGER NOT NULL,
  deliverable_code TEXT NOT NULL,
  token TEXT NOT NULL,
  delta_change REAL NOT NULL
);

-- Confidence adjustments (human feedback)
CREATE TABLE IF NOT EXISTS confidence_adjustments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  deliverable_code TEXT NOT NULL,
  deliverable_name TEXT NOT NULL,
  original_confidence REAL NOT NULL,
  adjusted_confidence REAL NOT NULL,
  reason TEXT,
  notes TEXT,
  admin_user TEXT,
  timestamp INTEGER NOT NULL,
  episode_id INTEGER,
  applied INTEGER DEFAULT 0,
  FOREIGN KEY(episode_id) REFERENCES episodes(id)
);

-- Direct confidence overrides (manual overrides per deliverable)
CREATE TABLE IF NOT EXISTS confidence_overrides(
  deliverable_code TEXT PRIMARY KEY,
  deliverable_name TEXT NOT NULL,
  confidence_adjustment REAL NOT NULL,
  reason TEXT,
  admin_user TEXT,
  updated_ts INTEGER NOT NULL,
  active INTEGER DEFAULT 1
);

-- Mode change history
CREATE TABLE IF NOT EXISTS mode_changes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_mode TEXT NOT NULL,
  to_mode TEXT NOT NULL,
  admin_user TEXT,
  timestamp INTEGER NOT NULL,
  reason TEXT
);

-- Audit log for all admin actions
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  details TEXT,
  admin_user TEXT,
  timestamp INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_confidence_deliverable ON confidence_adjustments(deliverable_code);
CREATE INDEX IF NOT EXISTS idx_confidence_timestamp ON confidence_adjustments(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
"""

def _connect(db_path: str = DEFAULT_DB):
    os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init(db_path: str = DEFAULT_DB):
    """Initialize database with all required tables"""
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
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()

# ================ Settings Management ================

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

# ================ Episode Management ================

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

# ================ Weight Management ================

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
    """Publish draft weights to production and mark adjustments as applied"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            # Copy draft to published
            conn.execute("DELETE FROM weights_published")
            conn.execute("INSERT INTO weights_published(deliverable_code,token,delta,support,updated_ts) SELECT deliverable_code,token,delta,support,updated_ts FROM weights_draft")
            
            # Mark confidence adjustments as applied
            conn.execute("UPDATE confidence_adjustments SET applied=1 WHERE applied=0")
            
            # Audit log
            audit_log_action("publish_draft", "Published all draft weights to production", None, db_path)
            
            conn.commit()
        finally:
            conn.close()

def reset_all(db_path: str = DEFAULT_DB):
    """Reset all learning data but preserve audit log"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            for table in ("weights_draft","weights_published","episodes","episode_updates","confidence_adjustments","confidence_overrides"):
                conn.execute(f"DELETE FROM {table}")
            
            # Audit log
            audit_log_action("reset_all", "Cleared all learning data", None, db_path)
            
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
            
            # Also remove associated confidence adjustments
            conn.execute("DELETE FROM confidence_adjustments WHERE episode_id=?", (eid,))
            
            # Audit log
            audit_log_action("undo_episode", f"Undid episode {eid}", None, db_path)
            
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

# ================ Confidence Adjustment Management ================

def add_confidence_adjustment(
    deliverable_code: str, 
    deliverable_name: str,
    original_confidence: float,
    adjusted_confidence: float,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    admin_user: Optional[str] = None,
    episode_id: Optional[int] = None,
    db_path: str = DEFAULT_DB
) -> int:
    """Add a confidence adjustment record"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            ts = int(time.time()*1000)
            conn.execute(
                """INSERT INTO confidence_adjustments(
                    deliverable_code, deliverable_name, original_confidence, 
                    adjusted_confidence, reason, notes, admin_user, timestamp, episode_id
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (deliverable_code, deliverable_name, original_confidence, adjusted_confidence, 
                 reason, notes, admin_user, ts, episode_id)
            )
            adj_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            
            # Audit log
            details = f"Adjusted {deliverable_code} from {original_confidence:.2f} to {adjusted_confidence:.2f}"
            audit_log_action("add_adjustment", details, admin_user, db_path)
            
            conn.commit()
            return int(adj_id)
        finally:
            conn.close()

def get_confidence_adjustments(
    limit: int = 50, 
    offset: int = 0,
    deliverable_code: Optional[str] = None,
    only_pending: bool = False,
    db_path: str = DEFAULT_DB
) -> List[Dict[str,Any]]:
    """Get confidence adjustment history"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            query = "SELECT * FROM confidence_adjustments WHERE 1=1"
            params = []
            
            if deliverable_code:
                query += " AND deliverable_code=?"
                params.append(deliverable_code)
            
            if only_pending:
                query += " AND applied=0"
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def set_confidence_override(
    deliverable_code: str,
    deliverable_name: str,
    confidence_adjustment: float,
    reason: Optional[str] = None,
    admin_user: Optional[str] = None,
    db_path: str = DEFAULT_DB
):
    """Set a direct confidence override for a deliverable"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            ts = int(time.time()*1000)
            conn.execute(
                """INSERT OR REPLACE INTO confidence_overrides(
                    deliverable_code, deliverable_name, confidence_adjustment, 
                    reason, admin_user, updated_ts
                ) VALUES(?,?,?,?,?,?)""",
                (deliverable_code, deliverable_name, confidence_adjustment, reason, admin_user, ts)
            )
            
            # Audit log
            details = f"Set override for {deliverable_code}: {confidence_adjustment:+.2f}"
            audit_log_action("set_override", details, admin_user, db_path)
            
            conn.commit()
        finally:
            conn.close()

def get_confidence_overrides(active_only: bool = True, db_path: str = DEFAULT_DB) -> Dict[str, float]:
    """Get all active confidence overrides as a dict"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            query = "SELECT deliverable_code, confidence_adjustment FROM confidence_overrides"
            if active_only:
                query += " WHERE active=1"
            
            rows = conn.execute(query).fetchall()
            return {r["deliverable_code"]: float(r["confidence_adjustment"]) for r in rows}
        finally:
            conn.close()

# ================ Mode Management ================

def log_mode_change(
    from_mode: str,
    to_mode: str,
    admin_user: Optional[str] = None,
    reason: Optional[str] = None,
    db_path: str = DEFAULT_DB
):
    """Log a mode change"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            ts = int(time.time()*1000)
            conn.execute(
                "INSERT INTO mode_changes(from_mode,to_mode,admin_user,timestamp,reason) VALUES(?,?,?,?,?)",
                (from_mode, to_mode, admin_user, ts, reason)
            )
            
            # Audit log
            details = f"Changed mode from {from_mode} to {to_mode}"
            audit_log_action("mode_change", details, admin_user, db_path)
            
            conn.commit()
        finally:
            conn.close()

def get_mode_history(limit: int = 10, db_path: str = DEFAULT_DB) -> List[Dict[str,Any]]:
    """Get mode change history"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            rows = conn.execute("SELECT * FROM mode_changes ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

# ================ Audit Management ================

def audit_log_action(
    action: str,
    details: Optional[str] = None,
    admin_user: Optional[str] = None,
    db_path: str = DEFAULT_DB
):
    """Log an admin action for audit trail"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            ts = int(time.time()*1000)
            conn.execute(
                "INSERT INTO audit_log(action,details,admin_user,timestamp) VALUES(?,?,?,?)",
                (action, details, admin_user, ts)
            )
            conn.commit()
        finally:
            conn.close()

def get_audit_log(limit: int = 100, offset: int = 0, db_path: str = DEFAULT_DB) -> List[Dict[str,Any]]:
    """Get audit log entries"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

# ================ Statistics ================

def get_statistics(db_path: str = DEFAULT_DB) -> Dict[str,Any]:
    """Get comprehensive statistics about the learning brain"""
    with _LOCK:
        conn = _connect(db_path)
        try:
            stats = {}
            
            # Count adjustments
            r = conn.execute("SELECT COUNT(*) as total, SUM(applied) as applied FROM confidence_adjustments").fetchone()
            stats["total_adjustments"] = r["total"] or 0
            stats["applied_adjustments"] = r["applied"] or 0
            stats["pending_adjustments"] = stats["total_adjustments"] - stats["applied_adjustments"]
            
            # Count overrides
            r = conn.execute("SELECT COUNT(*) as count FROM confidence_overrides WHERE active=1").fetchone()
            stats["active_overrides"] = r["count"] or 0
            
            # Count episodes
            r = conn.execute("SELECT COUNT(*) as count FROM episodes").fetchone()
            stats["total_episodes"] = r["count"] or 0
            
            # Last activity
            r = conn.execute("SELECT MAX(timestamp) as last FROM confidence_adjustments").fetchone()
            stats["last_adjustment"] = r["last"] if r and r["last"] else None
            
            r = conn.execute("SELECT MAX(timestamp) as last FROM mode_changes").fetchone()
            stats["last_mode_change"] = r["last"] if r and r["last"] else None
            
            # Average adjustment magnitude
            r = conn.execute("SELECT AVG(ABS(adjusted_confidence - original_confidence)) as avg_delta FROM confidence_adjustments").fetchone()
            stats["avg_adjustment_delta"] = float(r["avg_delta"]) if r and r["avg_delta"] else 0.0
            
            return stats
        finally:
            conn.close()