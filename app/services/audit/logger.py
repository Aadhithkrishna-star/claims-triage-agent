import sqlite3
import os
from datetime import datetime

# Use the same path everywhere — Streamlit Cloud persists /mount/src but not /tmp
DB_PATH = os.path.join(os.path.dirname(__file__), "audit.db")


def init_db():
    """Create the audit_logs table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT,
            node TEXT,
            timestamp TEXT,
            status TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_audit(claim_id: str, node: str, status: str, message: str = ""):
    """Write a single audit log row."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_logs (claim_id, node, timestamp, status, message) VALUES (?, ?, ?, ?, ?)",
        (claim_id, node, datetime.utcnow().isoformat(), status, message)
    )
    conn.commit()
    conn.close()