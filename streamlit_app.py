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

# ── Claim Details (editable, auto-filled after extraction) ───────────────────
st.subheader("📋 Claim Details")
st.caption("These fields auto-populate from your document. You can edit them if needed.")

col1, col2 = st.columns(2)
with col1:
    policy_number = st.text_input(
        "Policy Number",
        value=st.session_state.get("extracted_policy", ""),
        placeholder="e.g. POL-M-78452"
    )
    claim_type = st.selectbox(
        "Claim Type",
        ["", "health", "motor", "home", "travel"],
        index=["", "health", "motor", "home", "travel"].index(st.session_state.get("extracted_type", "")) if st.session_state.get("extracted_type", "") in ["", "health", "motor", "home", "travel"] else 0
    )
with col2:
    # Convert stored date string to date object for date_input
    from datetime import datetime
    date_val = None
    if st.session_state.get("extracted_date"):
        try:
            date_val = datetime.strptime(st.session_state["extracted_date"], "%Y-%m-%d").date()
        except:
            pass
    incident_date = st.date_input("Incident Date", value=date_val)

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
                        policy_number=policy_number if policy_number else None,
                        claim_type=claim_type if claim_type else None,
                        incident_date=incident_date.strftime("%Y-%m-%d") if incident_date else None,
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
                    
                    # ── Store extracted values in session state to auto-fill fields ──
                    st.session_state["extracted_policy"] = extracted_dict.get("policy_number", "")
                    st.session_state["extracted_type"] = extracted_dict.get("claim_type", "")
                    st.session_state["extracted_date"] = extracted_dict.get("incident_date", "")
                    
                    # ── Show extracted info FIRST (swapped position) ──
                    st.subheader("📋 Extracted Information")
                    info_cols = st.columns(4)
                    with info_cols[0]:
                        st.metric("Claimant", extracted_dict.get("claimant_name", "N/A"))
                    with info_cols[1]:
                        st.metric("Policy", extracted_dict.get("policy_number", "N/A"))
                        st.metric("Type", extracted_dict.get("claim_type", "N/A"))
                    with info_cols[2]:
                        amt = extracted_dict.get("claim_amount", 0) or 0
                        st.metric("Amount", f"₹{amt:,}")
                        st.metric("Date", extracted_dict.get("incident_date", "N/A"))
                    with info_cols[3]:
                        st.metric("Injury/Damage", extracted_dict.get("injury_type") or "N/A")
                    
                    # ── Decision box SECOND ──
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
                    
                    # Rerun to auto-fill the input fields with extracted data
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Crash: {e}")
                st.code(traceback.format_exc())

st.divider()
st.caption("Built for Moring AI interview")