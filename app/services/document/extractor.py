"""
Use Groq LLM to extract structured claim data from raw text.
"""
import json
import os
import streamlit as st
from openai import OpenAI
from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import ClaimExtractedData


# Prompt template - we fill in {text} later
EXTRACTION_PROMPT = """You are an insurance claims data extraction engine.

Extract structured information from the claim document below.
Return ONLY a valid JSON object. No explanation. No markdown formatting.

Required JSON format:
{
    "claimant_name": "full name of claimant",
    "policy_number": "policy number string",
    "claim_amount": 75000,
    "incident_date": "2024-03-15",
    "claim_type": "health",
    "injury_type": "appendicitis",
    "description": "brief description of incident"
}

Rules:
- claim_amount: number only, no currency symbols or commas
- incident_date: must be YYYY-MM-DD format
- claim_type: must be exactly one of: health, motor, home, travel
- injury_type: type of injury/illness/damage, or null if not applicable
- description: 1-2 sentence summary, or null
- If any field is missing or unclear, use null for optional fields (injury_type, description)
- For claim_amount, if you see "Rs. 75,000" return 75000

Claim document text:
{{TEXT}}
"""


def _get_llm_client():
    """Create Groq client lazily so secrets are loaded first."""
    api_key = settings.LLM_API_KEY or os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found. Check Streamlit secrets or environment variables.")
    return OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL)


async def extract_claim_data(text: str) -> ClaimExtractedData:
    """
    Send text to Groq LLM and get structured claim data back.
    """
    try:
        llm_client = _get_llm_client()
        
        response = llm_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured insurance data and return only JSON."
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT.replace("{{TEXT}}", text)
                }
            ],
            temperature=0,
            max_tokens=800,
        )
        
        raw_output = response.choices[0].message.content
        logger.info(f"LLM raw output: {raw_output[:200]}...")
        
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        data_dict = json.loads(cleaned)
        extracted = ClaimExtractedData(**data_dict)
        
        logger.info(f"Successfully extracted claim for: {extracted.claimant_name}")
        return extracted
        
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}\nRaw: {raw_output}")
        raise ValueError(f"LLM returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise