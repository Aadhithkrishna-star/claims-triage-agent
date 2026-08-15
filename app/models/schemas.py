"""
Pydantic models for request/response validation.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    HUMAN_REVIEW = "human_review"
    ESCALATED = "escalated"


class ClaimType(str, Enum):
    HEALTH = "health"
    MOTOR = "motor"
    HOME = "home"
    TRAVEL = "travel"


class ClaimUploadRequest(BaseModel):
    policy_number: str = Field(..., description="Customer policy number")
    claim_type: ClaimType = Field(..., description="Type of insurance claim")
    incident_date: str = Field(..., description="Date of incident (YYYY-MM-DD)")


class ClaimExtractedData(BaseModel):
    claimant_name: str
    policy_number: str
    claim_amount: float
    incident_date: str
    claim_type: ClaimType
    injury_type: Optional[str] = None
    description: Optional[str] = None


class TriageDecision(BaseModel):
    status: ClaimStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    policy_citations: List[str] = []
    fraud_signals: List[str] = []
    recommended_action: str


class ClaimResponse(BaseModel):
    trace_id: str
    status: ClaimStatus
    extracted_data: ClaimExtractedData
    decision: TriageDecision
    processing_time_ms: int
    created_at: datetime


class AuditLogEntry(BaseModel):
    trace_id: str
    timestamp: datetime
    step_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    latency_ms: int
    cost_usd: float
    model_version: Optional[str] = None