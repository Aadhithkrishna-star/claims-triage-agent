"""
Streamlit UI for the Claims Triage Agent.
Self-contained version for Streamlit Cloud deployment.
"""
import streamlit as st
import uuid
import time
import os
import sys
from pathlib import Path
import asyncio
import traceback

# Add repo root to path (for Streamlit Cloud)
sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Claims Triage Agent", layout="wide")

# Check API key early
if not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY not found!")
    st.info("Go to Streamlit Cloud Settings → Secrets and add: GROQ_API_KEY = 'your-key'")
    st.stop()

st.title("🛡️ Regulated Claims Triage Agent")
st.markdown("Upload an insurance claim document to get an AI-powered routing decision.")

# Sidebar info
with st.sidebar:
    st.header("About")
    st.markdown("""
    This agent uses:
    - **Groq LLM** (Llama 3.3 70B) for entity extraction
    - **Local embeddings** (MiniLM) for policy retrieval
    - **FAISS** for vector search
    - **LangGraph** for agent orchestration
    - **Deterministic rules** for regulated decision-making
    """)
    
    st.header("Thresholds")
    st.markdown("""
    | Claim Type | Auto-Approve | Human Review | Escalate |
    |-----------|-------------|--------------|----------|
    | Health | < ₹50K | ₹50K-2L | > ₹2L |
    | Motor | < ₹25K | ₹25K-1L | > ₹1L |
    """)

# Cache the heavy model loading
@st.cache_resource(show_spinner="Loading AI models... (one-time, ~30s)")
def load_triage_agent():
    from app.services.agent.triage_agent import run_triage
    return run_triage

# Main form
col1, col2 = st.columns(2)

with col1:
    policy_number = st.text_input("Policy Number", "POL-H-12345")
    claim_type = st.selectbox("Claim Type", ["health", "motor", "home", "travel"])
    incident_date = st.date_input("Incident Date")

with col2:
    uploaded_file = st.file_uploader(
        "Upload Claim Document",
        type=["txt", "pdf"],
        help="Upload a .txt or .pdf claim form"
    )

if st.button("🚀 Process Claim", type="primary"):
    if not uploaded_file:
        st.error("Please upload a claim document.")
    else:
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        file_bytes = uploaded_file.getvalue()
        
        try:
            run_triage = load_triage_agent()
            
            # Handle async in Streamlit
            async def process():
                return await run_triage(
                    trace_id=trace_id,
                    file_bytes=file_bytes,
                    filename=uploaded_file.name,
                    policy_number=policy_number,
                    claim_type=claim_type,
                    incident_date=incident_date.strftime("%Y-%m-%d"),
                )
            
            # Use nest_asyncio to handle nested event loops
            import nest_asyncio
            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(process())
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if result.get("error"):
                st.error(f"Agent Error: {result['error']}")
            else:
                decision = result["decision"]
                
                st.success("Claim processed successfully!")
                st.code(f"Trace ID: {trace_id}", language="text")
                
                status = decision.status
                status_colors = {
                    "auto_approved": "green",
                    "human_review": "orange",
                    "escalated": "red",
                }
                color = status_colors.get(status, "gray")
                
                st.markdown(f"""
                <div style='padding: 20px; border-radius: 10px; background-color: {color}20; border-left: 5px solid {color};'>
                    <h3 style='margin: 0; color: {color};'>Decision: {status.replace("_", " ").title()}</h3>
                    <p style='margin: 5px 0;'><strong>Confidence:</strong> {decision.confidence}</p>
                    <p style='margin: 5px 0;'><strong>Reason:</strong> {decision.reason}</p>
                    <p style='margin: 5px 0;'><strong>Action:</strong> {decision.recommended_action}</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("📋 Extracted Data"):
                    st.json(result["extracted_data"])
                
                with st.expander("📚 Policy Citations"):
                    for i, citation in enumerate(decision.policy_citations, 1):
                        st.markdown(f"**{i}.** {citation}")
                
                st.caption(f"⏱️ Processing time: {processing_time} ms")
                
        except Exception as e:
            st.error(f"Processing failed: {str(e)}")
            with st.expander("🔍 Error Details (for debugging)"):
                st.code(traceback.format_exc())

st.divider()
st.caption("Built for Moring AI interview | Open-source stack | ₹0 cost")