"""
FastAPI route definitions.
Phase 5: Agent + Guardrails + Audit Logging.
"""
import uuid
import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.schemas import ClaimResponse, ClaimType
from app.core.logging import logger
from app.services.agent.triage_agent import run_triage
from app.services.audit.logger import get_logs_by_trace_id, get_recent_logs
from app.services.evaluation.benchmark import run_benchmark


router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "claims-triage-agent"}


@router.post("/claims/upload", response_model=ClaimResponse)
async def upload_claim(
    policy_number: str = Form(...),
    claim_type: ClaimType = Form(...),
    incident_date: str = Form(...),
    document: UploadFile = File(...),
):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"[{trace_id}] Received claim: {policy_number}, type={claim_type}")
    
    file_bytes = await document.read()
    
    result = await run_triage(
        trace_id=trace_id,
        file_bytes=file_bytes,
        filename=document.filename,
        policy_number=policy_number,
        claim_type=claim_type.value,
        incident_date=incident_date,
    )
    
    processing_time = int((time.time() - start_time) * 1000)
    
    if result.get("error"):
        logger.error(f"[{trace_id}] Agent failed: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])
    
    return ClaimResponse(
        trace_id=trace_id,
        status=result["decision"].status,
        extracted_data=result["extracted_data"],
        decision=result["decision"],
        processing_time_ms=processing_time,
        created_at=datetime.utcnow(),
    )


@router.post("/evaluate")
async def run_evaluation():
    """
    Run the benchmark evaluation suite.
    Returns accuracy, latency, and per-test results.
    """
    logger.info("Starting benchmark evaluation")
    report = await run_benchmark()
    return report.to_dict()

@router.get("/claims/{trace_id}")
async def get_claim_status(trace_id: str):
    """Get full audit trail for a claim."""
    logs = get_logs_by_trace_id(trace_id)
    if not logs:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"trace_id": trace_id, "audit_trail": logs}


@router.get("/audit/logs")
async def get_audit_logs(limit: int = 50):
    """Get recent audit logs."""
    logs = get_recent_logs(limit)
    return {"logs": logs, "count": len(logs)}