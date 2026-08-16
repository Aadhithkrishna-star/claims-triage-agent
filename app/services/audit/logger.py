import sqlite3
import os
from datetime import datetime

# Use a NEW filename so old schema is abandoned
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


def log_step(**kwargs):
    trace_id = kwargs.get("trace_id", kwargs.get("claim_id", "unknown"))
    claim_id = kwargs.get("claim_id", trace_id)
    node = kwargs.get("node", kwargs.get("step_name", kwargs.get("step", "unknown")))
    status = kwargs.get("status", "unknown")
    message = kwargs.get("message", kwargs.get("input_data", kwargs.get("error", str(kwargs))))
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_logs (trace_id, claim_id, node, timestamp, status, message) VALUES (?, ?, ?, ?, ?, ?)",
        (trace_id, claim_id, node, datetime.utcnow().isoformat(), status, message)
    )
    conn.commit()
    conn.close()


def log_audit(claim_id: str, node: str, status: str, message: str = ""):
    log_step(trace_id=claim_id, claim_id=claim_id, node=node, status=status, message=message)