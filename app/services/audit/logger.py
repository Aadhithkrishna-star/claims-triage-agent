import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "audit.db")


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


def log_step(trace_id: str, status: str, message: str = "", 
             node: str = "", step_name: str = "", claim_id: str = ""):
    """Accepts both 'node' and 'step_name' for compatibility."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_logs (trace_id, claim_id, node, timestamp, status, message) VALUES (?, ?, ?, ?, ?, ?)",
        (trace_id, claim_id, step_name or node, datetime.utcnow().isoformat(), status, message)
    )
    conn.commit()
    conn.close()


def log_audit(claim_id: str, node: str, status: str, message: str = ""):
    log_step(trace_id=claim_id, claim_id=claim_id, node=node, status=status, message=message)