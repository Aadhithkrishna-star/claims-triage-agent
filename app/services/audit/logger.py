import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "audit_v2.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            claim_id TEXT,
            node TEXT,
            timestamp TEXT,
            status TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def _safe_str(value):
    """Convert any value to a SQLite-safe string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def log_step(**kwargs):
    trace_id = _safe_str(kwargs.get("trace_id", kwargs.get("claim_id", "unknown")))
    claim_id = _safe_str(kwargs.get("claim_id", trace_id))
    node = _safe_str(kwargs.get("node", kwargs.get("step_name", kwargs.get("step", "unknown"))))
    status = _safe_str(kwargs.get("status", "unknown"))
    
    # message could be a dict from input_data or error
    message = kwargs.get("message", kwargs.get("input_data", kwargs.get("error", "")))
    message = _safe_str(message)
    
    # Also handle latency_ms and other numeric fields
    latency = kwargs.get("latency_ms")
    if latency is not None:
        message = f"{message} | latency_ms={latency}"
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_logs (trace_id, claim_id, node, timestamp, status, message) VALUES (?, ?, ?, ?, ?, ?)",
        (trace_id, claim_id, node, datetime.utcnow().isoformat(), status, message)
    )
    conn.commit()
    conn.close()


def log_audit(claim_id: str, node: str, status: str, message: str = ""):
    log_step(trace_id=claim_id, claim_id=claim_id, node=node, status=status, message=message)