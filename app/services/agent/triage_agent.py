"""
LangGraph-based triage agent with guardrails and audit logging.
"""
import time
from typing import TypedDict, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import ClaimExtractedData, TriageDecision, ClaimStatus
from app.services.document.parser import extract_text_from_file
from app.services.document.extractor import extract_claim_data
from app.services.rag.retriever import retrieve_policy_context
from app.services.guardrails.validator import (
    validate_file_upload,
    validate_extracted_data,
    sanitize_for_audit,
)
from app.services.audit.logger import log_step


class AgentState(TypedDict):
    trace_id: str
    file_bytes: bytes
    filename: str
    policy_number: str
    claim_type: str
    incident_date: str
    raw_text: Optional[str]
    extracted_data: Optional[ClaimExtractedData]
    policy_citations: List[str]
    decision: Optional[TriageDecision]
    error: Optional[str]


async def node_extract(state: AgentState) -> AgentState:
    """Extract text and structured data."""
    logger.info(f"[{state['trace_id']}] Node: EXTRACT")
    start = time.time()
    
    try:
        # GUARDRAIL: Validate file before processing
        is_valid, error_msg = validate_file_upload(
            state["filename"], state["file_bytes"]
        )
        if not is_valid:
            log_step(
                trace_id=state["trace_id"],
                step_name="input_validation",
                input_data={"filename": state["filename"], "size": len(state["file_bytes"])},
                output_data={"error": error_msg},
                status="rejected",
            )
            return {**state, "error": error_msg}
        
        raw_text = await extract_text_from_file(
            state["file_bytes"], state["filename"]
        )
        extracted_data = await extract_claim_data(raw_text)
        
        # GUARDRAIL: Validate extracted data
        is_valid, error_msg = validate_extracted_data(extracted_data.model_dump())
        if not is_valid:
            log_step(
                trace_id=state["trace_id"],
                step_name="extraction_validation",
                input_data={"raw_text_length": len(raw_text)},
                output_data={"error": error_msg},
                status="rejected",
            )
            return {**state, "error": error_msg}
        
        latency = int((time.time() - start) * 1000)
        log_step(
            trace_id=state["trace_id"],
            step_name="extract",
            input_data={"filename": state["filename"]},
            output_data={
                "claimant_name": extracted_data.claimant_name,
                "claim_amount": extracted_data.claim_amount,
            },
            latency_ms=latency,
        )
        
        return {**state, "raw_text": raw_text, "extracted_data": extracted_data}
        
    except Exception as e:
        logger.error(f"[{state['trace_id']}] Extract failed: {e}")
        log_step(
            trace_id=state["trace_id"],
            step_name="extract",
            input_data={"filename": state["filename"]},
            output_data={"error": str(e)},
            status="error",
        )
        return {**state, "error": f"Extraction failed: {e}"}


async def node_retrieve(state: AgentState) -> AgentState:
    """Retrieve relevant policy clauses."""
    logger.info(f"[{state['trace_id']}] Node: RETRIEVE")
    start = time.time()
    
    if state.get("error"):
        return state
    
    extracted = state["extracted_data"]
    query = (
        f"{extracted.claim_type} claim for "
        f"{extracted.injury_type or 'incident'} "
        f"amount {extracted.claim_amount}"
    )
    
    citations = await retrieve_policy_context(
        query=query,
        claim_type=state["claim_type"],
        k=3,
    )
    
    latency = int((time.time() - start) * 1000)
    log_step(
        trace_id=state["trace_id"],
        step_name="retrieve",
        input_data={"query": query},
        output_data={"citations_count": len(citations)},
        latency_ms=latency,
    )
    
    return {**state, "policy_citations": citations}


async def node_decide(state: AgentState) -> AgentState:
    """Apply deterministic business rules."""
    logger.info(f"[{state['trace_id']}] Node: DECIDE")
    start = time.time()
    
    if state.get("error"):
        return state
    
    extracted = state["extracted_data"]
    citations = state["policy_citations"]
    amount = extracted.claim_amount
    
    # Amount-based routing
       # Claim-type-specific thresholds
    thresholds = {
        "health": {"auto": 50000, "escalate": 200000},
        "motor": {"auto": 25000, "escalate": 100000},
        "home": {"auto": 50000, "escalate": 200000},
        "travel": {"auto": 25000, "escalate": 100000},
    }
    
    t = thresholds.get(state["claim_type"], {"auto": 50000, "escalate": 200000})
    
    if amount < t["auto"]:
        status = ClaimStatus.AUTO_APPROVED
        reason = f"Claim amount Rs. {amount} is below auto-approval threshold of Rs. {t['auto']}."
        confidence = 0.95
    elif amount < t["escalate"]:
        status = ClaimStatus.HUMAN_REVIEW
        reason = f"Claim amount Rs. {amount} requires human review (between Rs. {t['auto']} and Rs. {t['escalate']})."
        confidence = 0.85
    else:
        status = ClaimStatus.ESCALATED
        reason = f"Claim amount Rs. {amount} exceeds Rs. {t['escalate']}. Must be escalated."
        confidence = 0.90
    
    # Contextual exclusion check
    exclusion_keywords = ["not covered", "exclusion", "excluded", "void"]
    claim_context = (
        f"{extracted.injury_type or ''} {extracted.description or ''}"
    ).lower()
    
    for citation in citations:
        citation_lower = citation.lower()
        has_exclusion = any(kw in citation_lower for kw in exclusion_keywords)
        has_context = any(
            word in citation_lower
            for word in claim_context.split()
            if len(word) > 3
        )
        if has_exclusion and has_context:
            status = ClaimStatus.HUMAN_REVIEW
            reason += " Retrieved policy cites exclusion potentially relevant to this condition."
            confidence = 0.80
            break
    
    # Pre-existing condition flag
    if extracted.injury_type and "pre-existing" in extracted.injury_type.lower():
        status = ClaimStatus.HUMAN_REVIEW
        reason += " Pre-existing condition flagged for manual verification."
        confidence = 0.75
    
    decision = TriageDecision(
        status=status,
        confidence=confidence,
        reason=reason,
        policy_citations=citations,
        fraud_signals=[],
        recommended_action=_get_recommended_action(status),
    )
    
    latency = int((time.time() - start) * 1000)
    log_step(
        trace_id=state["trace_id"],
        step_name="decide",
        input_data={"claim_amount": amount},
        output_data={
            "status": status.value,
            "confidence": confidence,
            "reason": sanitize_for_audit(reason),
        },
        latency_ms=latency,
    )
    
    return {**state, "decision": decision}


def _get_recommended_action(status: ClaimStatus) -> str:
    mapping = {
        ClaimStatus.AUTO_APPROVED: "Process payment and notify claimant",
        ClaimStatus.HUMAN_REVIEW: "Queue for adjuster review within 24 hours",
        ClaimStatus.ESCALATED: "Escalate to senior adjuster immediately",
    }
    return mapping.get(status, "Review manually")


def build_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("extract", node_extract)
    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("decide", node_decide)
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "retrieve")
    workflow.add_edge("retrieve", "decide")
    workflow.add_edge("decide", END)
    return workflow.compile()


triage_agent = build_agent()


async def run_triage(
    trace_id: str,
    file_bytes: bytes,
    filename: str,
    policy_number: str,
    claim_type: str,
    incident_date: str,
) -> dict:
    initial_state = {
        "trace_id": trace_id,
        "file_bytes": file_bytes,
        "filename": filename,
        "policy_number": policy_number,
        "claim_type": claim_type,
        "incident_date": incident_date,
        "raw_text": None,
        "extracted_data": None,
        "policy_citations": [],
        "decision": None,
        "error": None,
    }
    final_state = await triage_agent.ainvoke(initial_state)
    return final_state