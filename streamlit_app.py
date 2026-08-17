import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import uuid
import time
import os
import asyncio
import concurrent.futures
import traceback

st.set_page_config(page_title="Claims Triage Agent", layout="wide")

# ── Initialize audit database (hardened) ─────────────────────────────────────
try:
    from app.services.audit.logger import init_db
    init_db()
except Exception as e:
    import logging
    logging.warning(f"Audit DB init skipped: {e}")

# Check API key
groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    st.error("⚠️ GROQ_API_KEY not found!")
    st.info("Go to Streamlit Cloud → Settings → Secrets. Add: GROQ_API_KEY = 'gsk_...' then REBOOT.")
    st.stop()

st.sidebar.success(f"✅ Key loaded: {groq_key[:10]}...")

st.title("🛡️ Claims Triage Agent")
st.markdown("Upload a claim document. The AI will extract all details automatically.")

# ── Optional overrides (always visible, not in expander) ─────────────────────
st.subheader("Manual Overrides (optional)")
st.caption("Leave blank to auto-extract from document")

col1, col2 = st.columns(2)
with col1:
    override_policy = st.text_input("Policy Number", placeholder="Auto-extracted from document")
    override_type = st.selectbox(
        "Claim Type", 
        ["", "health", "motor", "home", "travel"],
        index=0
    )
with col2:
    override_date = st.date_input("Incident Date", value=None)

uploaded_file = st.file_uploader("📄 Upload Claim Document", type=["txt", "pdf"], accept_multiple_files=False)

def run_async_in_thread(coro):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()

if st.button("🚀 Process Claim", type="primary", disabled=not uploaded_file):
    if not uploaded_file:
        st.error("Please upload a document.")
    else:
        trace_id = str(uuid.uuid4())
        start = time.time()
        
        with st.spinner("Processing claim... (~30s first time)"):
            try:
                from app.services.agent.triage_agent import run_triage
                
                async def process():
                    return await run_triage(
                        trace_id=trace_id,
                        file_bytes=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                        policy_number=override_policy if override_policy else None,
                        claim_type=override_type if override_type else None,
                        incident_date=override_date.strftime("%Y-%m-%d") if override_date else None,
                    )
                
                result = run_async_in_thread(process())
                
                if result.get("error"):
                    st.error(f"Error: {result['error']}")
                    with st.expander("Debug info"):
                        st.json(result)
                else:
                    d = result["decision"]
                    extracted = result.get("extracted_data")
                    
                    # Handle both dict and Pydantic model
                    if hasattr(extracted, "dict"):
                        extracted_dict = extracted.dict()
                    elif hasattr(extracted, "model_dump"):
                        extracted_dict = extracted.model_dump()
                    else:
                        extracted_dict = extracted or {}
                    
                    # Show extracted info
                    st.subheader("📋 Extracted Information")
                    info_cols = st.columns(3)
                    with info_cols[0]:
                        st.metric("Claimant", extracted_dict.get("claimant_name", "N/A"))
                        st.metric("Policy", extracted_dict.get("policy_number", "N/A"))
                    with info_cols[1]:
                        st.metric("Type", extracted_dict.get("claim_type", "N/A"))
                        amt = extracted_dict.get("claim_amount", 0) or 0
                        st.metric("Amount", f"₹{amt:,}")
                    with info_cols[2]:
                        st.metric("Date", extracted_dict.get("incident_date", "N/A"))
                        st.metric("Injury/Damage", extracted_dict.get("injury_type") or "N/A")
                    
                    # Decision box
                    color = {"auto_approved":"green","human_review":"orange","escalated":"red"}.get(d.status,"gray")
                    st.markdown(f"""
                    <div style='padding:20px;border-radius:10px;background:{color}20;border-left:5px solid {color};margin-top:20px;'>
                        <h3 style='margin:0;color:{color}'>Decision: {d.status.replace('_',' ').title()}</h3>
                        <p><b>Confidence:</b> {d.confidence}</p>
                        <p><b>Reason:</b> {d.reason}</p>
                        <p><b>Recommended Action:</b> {d.recommended_action}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("📚 Policy Citations"):
                        for i, c in enumerate(d.policy_citations, 1):
                            st.markdown(f"**{i}.** {c}")
                    
                    with st.expander("🔍 Full Extracted Data"):
                        st.json(extracted_dict)
                    
                    st.caption(f"⏱️ Processed in {int((time.time()-start)*1000)} ms | Trace ID: `{trace_id}`")
                    
            except Exception as e:
                st.error(f"Crash: {e}")
                st.code(traceback.format_exc())

st.divider()
st.caption("Built for Moring AI interview")