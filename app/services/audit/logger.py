"""
Audit logging to SQLite database.
Every agent action is trace-keyed and stored for compliance.
"""
import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger


def init_audit_db():
    """
    Create the audit log table if it doesn't exist.
    Call this once at app startup.
    """
    conn = sqlite3.connect(str(settings.AUDIT_DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            step_name TEXT NOT NULL,
            input_data TEXT,
            output_data TEXT,
            latency_ms INTEGER,
            cost_usd REAL DEFAULT 0.0,
            model_version TEXT,
            status TEXT DEFAULT 'success'
        )
    """)
    
    # Index for fast trace_id lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trace_id ON audit_logs(trace_id)
    """)
    
    conn.commit()
    conn.close()
    logger.info("Audit database initialized")


def log_step(
    trace_id: str,
    step_name: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    latency_ms: int = 0,
    cost_usd: float = 0.0,
    model_version: Optional[str] = None,
    status: str = "success",
):
    """
    Log a single agent step to the audit database.
    """
    try:
        conn = sqlite3.connect(str(settings.AUDIT_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_logs 
            (trace_id, timestamp, step_name, input_data, output_data, latency_ms, cost_usd, model_version, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace_id,
            datetime.utcnow().isoformat(),
            step_name,
            json.dumps(input_data, default=str),
            json.dumps(output_data, default=str),
            latency_ms,
            cost_usd,
            model_version or settings.LLM_MODEL,
            status,
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def get_logs_by_trace_id(trace_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all audit logs for a given trace_id.
    """
    conn = sqlite3.connect(str(settings.AUDIT_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM audit_logs WHERE trace_id = ? ORDER BY timestamp",
        (trace_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve recent audit logs.
    """
    conn = sqlite3.connect(str(settings.AUDIT_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]