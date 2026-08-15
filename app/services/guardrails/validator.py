"""
Guardrails: Input validation, PII redaction, output validation.
Ensures safety and compliance before data reaches the agent.
"""
import re
from typing import Tuple, Optional
from app.core.logging import logger


# PII patterns for Indian context
PII_PATTERNS = {
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "phone": r"\b(?:\+91\s?)?[6-9]\d{9}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}


def redact_pii(text: str) -> str:
    """
    Remove sensitive PII from text before logging or displaying.
    Returns redacted text.
    """
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        redacted = re.sub(pattern, f"[REDACTED-{pii_type.upper()}]", redacted)
    return redacted


def validate_file_upload(filename: str, file_bytes: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file before processing.
    Returns (is_valid, error_message).
    """
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10 MB
    if len(file_bytes) > max_size:
        return False, f"File too large: {len(file_bytes)} bytes. Max: {max_size} bytes"
    
    # Check file extension
    allowed_extensions = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}
    ext = filename.lower()[filename.rfind("."):]
    if ext not in allowed_extensions:
        return False, f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


def validate_extracted_data(data_dict: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate structured data extracted by LLM.
    Ensures required fields are present and reasonable.
    """
    required_fields = ["claimant_name", "policy_number", "claim_amount", "incident_date", "claim_type"]
    
    for field in required_fields:
        if field not in data_dict or data_dict[field] is None:
            return False, f"Missing required field: {field}"
    
    # Validate claim amount is reasonable
    amount = data_dict.get("claim_amount", 0)
    if amount < 0:
        return False, f"Invalid claim amount: {amount}. Must be >= 0"
    if amount > 10_000_000:  # 1 Crore
        return False, f"Claim amount suspiciously high: {amount}. Flagged for review"
    
    # Validate date format roughly
    date_str = data_dict.get("incident_date", "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False, f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
    
    return True, None


def sanitize_for_audit(text: str) -> str:
    """
    Prepare text for audit logging: redact PII and truncate if too long.
    """
    redacted = redact_pii(text)
    # Truncate to 2000 chars to keep DB rows manageable
    if len(redacted) > 2000:
        redacted = redacted[:2000] + "...[truncated]"
    return redacted