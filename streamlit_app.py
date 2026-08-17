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
from datetime import datetime

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

st.sidebar.success("✅ API key loaded")

st.title("🛡️ Claims Triage Agent")
st.markdown("Upload a claim document. The AI will extract all details automatically.")

# ── Claim Details (editable, auto-filled from previous extraction) ───────────
st.subheader("📋 Claim Details")
st.caption("These fields auto-populate from your document. You can edit them if needed.")

# Get stored values from session state (set after previous processing)
stored_policy = st.session_state.get("extracted_policy", "")
stored_type = st.session_state.get("extracted_type", "")
stored_date_str = st.session_state.get("extracted_date", "")

col1, col2 = st.columns(2)
with col1:
    policy_number = st.text_input(
        "Policy Number",
        value=stored_policy,
        placeholder="e.g. POL-M-78452"
    )
    
    # Build claim type options with extracted type first if not in list
    type_options = ["", "health", "motor", "home", "travel"]
    if stored_type and stored_type not in type_options:
        type_options.append(stored_type)
    
    try:
        type_index = type_options.index(stored_type)
    except ValueError:
        type_index = 0
    
    claim_type = st.selectbox("Claim Type", type_options, index=type_index)

with col2:
    date_val = None
    if stored_date_str:
        try:
            date_val = datetime.strptime(stored_date_str, "%Y-%m-%d").date()
        except:
            pass
    incident_date = st.date_input("Incident Date", value=date_val)

# ── File uploader with auto-clear on new upload ──────────────────────────────
uploaded_file = st.file_uploader("📄 Upload Claim Document", type=["txt", "pdf"], accept_multiple_files=False)

# Clear previous result when a NEW file is uploaded
if uploaded_file is not None:
    # Check if this is a different file from last time
    current_file_name = uploaded_file.name
    last_file_name = st.session_state.get("last_uploaded_file", "")
    
    if current_file_name != last_file_name:
        # New file uploaded — clear previous result and extracted fields
        st.session_state.pop("last_result", None)
        st.session_state.pop("extracted_policy", None)
        st.session_state.pop("extracted_type", None)
        st.session_state.pop("extracted_date", None)
        st.session_state["last_uploaded_file"] = current_file_name
        st.rerun()

def run_async_in_thread(coro):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()

# ── Results display area (persists across reruns via session state) ──────────
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    d = result["decision"]
    extracted_dict = result.get("extracted_dict", {})
    
    st.divider()
    
    # ── Extracted info FIRST ──
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
    
    # Full Extracted Data FIRST (after decision)
    with st.expander("🔍 Full Extracted Data"):
        st.json(extracted_dict)
    
    # Policy Citations LAST (at the very bottom)
    with st.expander("📚 Policy Citations"):
        for i, c in enumerate(d.policy_citations, 1):
            st.markdown(f"**{i}.** {c}")
    
    st.caption(f"⏱️ {result.get('elapsed_ms', 0)} ms | Trace ID: `{result.get('trace_id', '')}`")

# ── Process button ───────────────────────────────────────────────────────────
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
                    
                    # Store in session state for display AND field auto-fill
                    st.session_state["extracted_policy"] = extracted_dict.get("policy_number", "")
                    st.session_state["extracted_type"] = extracted_dict.get("claim_type", "")
                    st.session_state["extracted_date"] = extracted_dict.get("incident_date", "")
                    
                    # Store full result for display
                    st.session_state["last_result"] = {
                        "decision": d,
                        "extracted_dict": extracted_dict,
                        "trace_id": trace_id,
                        "elapsed_ms": int((time.time()-start)*1000)
                    }
                    
                    # Clear file uploader and rerun to show results + filled fields
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Crash: {e}")
                st.code(traceback.format_exc())

st.divider()
st.caption("Built for Moring AI interview")