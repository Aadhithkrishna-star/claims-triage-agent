"""
Streamlit UI for the Claims Triage Agent.
Diagnostic version to find the crash point.
"""
import streamlit as st
import uuid
import time
import os
import sys
from pathlib import Path
import asyncio
import concurrent.futures
import traceback

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Claims Triage Agent", layout="wide")

# Check API key
groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    st.error("⚠️ GROQ_API_KEY not found in environment!")
    st.info("Go to Streamlit Cloud Settings → Secrets and add your key.")
    st.stop()
else:
    st.sidebar.success("✅ API Key found")

st.title("🛡️ Regulated Claims Triage Agent")
st.markdown("Upload an insurance claim document to get an AI-powered routing decision.")

with st.sidebar:
    st.header("About")
    st.markdown("""
    - **Groq LLM** for entity extraction  
    - **Local embeddings** (MiniLM) for policy retrieval  
    - **FAISS** for vector search  
    - **LangGraph** for agent orchestration  
    """)
    
    st.header("Thresholds")
    st.markdown("""
    | Type | Auto-Approve | Human Review | Escalate |
    |------|-------------|--------------|----------|
    | Health | < ₹50K | ₹50K-2L | > ₹2L |
    | Motor | < ₹25K | ₹25K-1L | > ₹1L |
    """)

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

def run_async_in_thread(coro):
    """Run async code in a separate thread to avoid event loop conflicts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()

if st.button("🚀 Process Claim", type="primary"):
    if not uploaded_file:
        st.error("Please upload a claim document.")
    else:
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        file_bytes = uploaded_file.getvalue()
        
        st.info("Step 1/5: Starting processing...")
        
        try:
            st.info("Step 2/5: Importing triage agent...")
            from app.services.agent.triage_agent import run_triage
            st.success("Step 2/5: Import successful ✅")
            
            st.info("Step 3/5: Loading AI models & FAISS index... (this takes ~20s)")
            
            async def process():
                return await run_triage(
                    trace_id=trace_id,
                    file_bytes=file_bytes,
                    filename=uploaded_file.name,
                    policy_number=policy_number,
                    claim_type=claim_type,
                    incident_date=incident_date.strftime("%Y-%m-%d"),
                )
            
            result = run_async_in_thread(process())
            
            st.success("Step 4/5: Processing complete ✅")
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if result.get("error"):
                st.error(f"Agent Error: {result['error']}")
            else:
                st.success("Step 5/5: Rendering results ✅")
                decision = result["decision"]
                
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
            st.error(f"❌ Error at Step ?: {str(e)}")
            with st.expander("Full error traceback"):
                st.code(traceback.format_exc())

st.divider()
st.caption("Built for Moring AI interview | Open-source stack | ₹0 cost")