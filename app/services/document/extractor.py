"""
Use Groq LLM to extract structured claim data from raw text.
"""
import json
from openai import OpenAI
from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import ClaimExtractedData


# Create Groq client (OpenAI-compatible)
llm_client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
)

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


async def extract_claim_data(text: str) -> ClaimExtractedData:
    """
    Send text to Groq LLM and get structured claim data back.
    """
    try:
        # Call Groq API (OpenAI-compatible)
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
            temperature=0,      # 0 = deterministic, no creativity
            max_tokens=800,     # Limit response length
        )
        
        # Get raw text from LLM
        raw_output = response.choices[0].message.content
        logger.info(f"LLM raw output: {raw_output[:200]}...")
        
        # Clean markdown code blocks if LLM wrapped JSON in ```
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]           # Remove ```json
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]           # Remove ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]          # Remove trailing ```
        cleaned = cleaned.strip()
        
        # Parse JSON string into Python dict
        data_dict = json.loads(cleaned)
        
        # Validate with Pydantic - catches wrong types, missing required fields
        extracted = ClaimExtractedData(**data_dict)
        
        logger.info(f"Successfully extracted claim for: {extracted.claimant_name}")
        return extracted
        
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}\nRaw: {raw_output}")
        raise ValueError(f"LLM returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise