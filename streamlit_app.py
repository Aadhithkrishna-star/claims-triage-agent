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
st.markdown("Upload a claim document to get an AI-powered routing decision.")

# ── Form inputs (no hardcoded defaults) ──────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    policy_number = st.text_input("Policy Number", placeholder="e.g. POL-H-12345")
    claim_type = st.selectbox(
        "Claim Type", 
        ["", "health", "motor", "home", "travel"],
        index=0,
        help="Select the claim type, or leave blank to auto-detect from document"
    )
    incident_date = st.date_input("Incident Date", value=None)

with col2:
    uploaded_file = st.file_uploader("Upload Claim Document", type=["txt", "pdf"])

def run_async_in_thread(coro):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()

# ── Validation ───────────────────────────────────────────────────────────────
if st.button("🚀 Process Claim", type="primary"):
    if not uploaded_file:
        st.error("Please upload a document.")
    elif not policy_number.strip():
        st.error("Please enter a policy number.")
    elif not claim_type:
        st.error("Please select a claim type.")
    elif incident_date is None:
        st.error("Please select an incident date.")
    else:
        trace_id = str(uuid.uuid4())
        start = time.time()
        
        with st.spinner("Processing... (~30s first time)"):
            try:
                from app.services.agent.triage_agent import run_triage
                
                async def process():
                    return await run_triage(
                        trace_id=trace_id,
                        file_bytes=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                        policy_number=policy_number.strip(),
                        claim_type=claim_type,
                        incident_date=incident_date.strftime("%Y-%m-%d"),
                    )
                
                result = run_async_in_thread(process())
                
                if result.get("error"):
                    st.error(f"Error: {result['error']}")
                    with st.expander("Debug info"):
                        st.json(result)
                else:
                    d = result["decision"]
                    
                    # ── Cross-validation: extracted type vs selected type ──
                    extracted_type = result.get("extracted_data", {}).get("claim_type", "").lower()
                    if extracted_type and extracted_type != claim_type:
                        st.warning(f"⚠️ Mismatch detected: You selected **{claim_type}**, but the document indicates **{extracted_type}**. Please verify.")
                    
                    color = {"auto_approved":"green","human_review":"orange","escalated":"red"}.get(d.status,"gray")
                    st.markdown(f"""
                    <div style='padding:20px;border-radius:10px;background:{color}20;border-left:5px solid {color}'>
                        <h3 style='margin:0;color:{color}'>Decision: {d.status.replace('_',' ').title()}</h3>
                        <p><b>Confidence:</b> {d.confidence}</p>
                        <p><b>Reason:</b> {d.reason}</p>
                        <p><b>Action:</b> {d.recommended_action}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("📋 Extracted Data"):
                        st.json(result["extracted_data"])
                    with st.expander("📚 Policy Citations"):
                        for i, c in enumerate(d.policy_citations, 1):
                            st.markdown(f"**{i}.** {c}")
                    st.caption(f"⏱️ {int((time.time()-start)*1000)} ms")
                    
            except Exception as e:
                st.error(f"Crash: {e}")
                st.code(traceback.format_exc())

st.divider()
st.caption("Built for Moring AI interview")