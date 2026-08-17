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
import json
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

# ── Sidebar: Recent Claims History ───────────────────────────────────────────
st.sidebar.divider()
st.sidebar.subheader("📜 Recent Claims")

if "claim_history" not in st.session_state:
    st.session_state.claim_history = []

for claim in st.session_state.claim_history:
    color_dot = {"auto_approved":"🟢","human_review":"🟡","escalated":"🔴"}.get(claim["decision"], "⚪")
    st.sidebar.caption(f"{color_dot} `{claim['policy']}` | {claim['decision'][:4].upper()} | {claim['time']}")

st.title("🛡️ Claims Triage Agent")
st.markdown("Upload a claim document. The AI will extract all details automatically.")

# ── Claim Details (editable, auto-filled from previous extraction) ─────────
st.subheader("📋 Claim Details")
st.caption("These fields auto-populate from your document. You can edit them if needed.")

stored_policy = st.session_state.get("extracted_policy", "")
stored_type = st.session_state.get("extracted_type", "")
stored_date_str = st.session_state.get("extracted_date", "")

type_options = ["", "health", "motor", "home", "travel"]
if stored_type and stored_type not in type_options:
    type_options.append(stored_type)

try:
    type_index = type_options.index(stored_type)
except ValueError:
    type_index = 0

policy_number = st.text_input("Policy Number", value=stored_policy, placeholder="e.g. POL-M-78452")
claim_type = st.selectbox("Claim Type", type_options, index=type_index)

date_val = None
if stored_date_str:
    try:
        date_val = datetime.strptime(stored_date_str, "%Y-%m-%d").date()
    except:
        pass
incident_date = st.date_input("Incident Date", value=date_val)

# ── File uploader with auto-clear on new upload ────────────────────────────
uploaded_file = st.file_uploader("📄 Upload Claim Document", type=["txt", "pdf"], accept_multiple_files=False)

if uploaded_file is not None:
    current_file_name = uploaded_file.name
    last_file_name = st.session_state.get("last_uploaded_file", "")
    
    if current_file_name != last_file_name:
        st.session_state.pop("last_result", None)
        st.session_state.pop("extracted_policy", None)
        st.session_state.pop("extracted_type", None)
        st.session_state.pop("extracted_date", None)
        st.session_state["last_uploaded_file"] = current_file_name
        st.rerun()

# ── Decision Simulator ───────────────────────────────────────────────────────
with st.expander("🔮 Decision Simulator"):
    sim_cols = st.columns(2)
    with sim_cols[0]:
        sim_amount = st.number_input("Claim Amount (₹)", min_value=0, max_value=5000000, value=75000, step=1000)
    with sim_cols[1]:
        sim_type = st.selectbox("Claim Type", ["health", "motor", "home", "travel"], key="sim_type")
    
    if sim_amount > 100000 and sim_type == "motor":
        st.error("🔴 Would escalate: Motor claims over ₹1L require senior adjuster")
    elif sim_amount > 500000:
        st.warning("🟡 Would review: High-value claim")
    else:
        st.success("🟢 Would auto-approve: Within threshold")

def run_async_in_thread(coro):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()

# ── Results display area ───────────────────────────────────────────────────
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    d = result["decision"]
    extracted_dict = result.get("extracted_dict", {})
    
    st.divider()
    
    # ── Extracted info ──
    st.subheader("📋 Extracted Information")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Claimant", extracted_dict.get("claimant_name", "N/A"))
        st.metric("Policy", extracted_dict.get("policy_number", "N/A"))
        st.metric("Type", extracted_dict.get("claim_type", "N/A"))
    with c2:
        amt = extracted_dict.get("claim_amount", 0) or 0
        st.metric("Amount", f"₹{amt:,}")
        st.metric("Date", extracted_dict.get("incident_date", "N/A"))
        st.metric("Injury/Damage", extracted_dict.get("injury_type") or "N/A")
    
    # ── Confidence gauge ──
    confidence_val = float(getattr(d, 'confidence', 0.85)) if isinstance(getattr(d, 'confidence', 0.85), (int, float)) else 0.85
    st.progress(min(confidence_val, 1.0), text=f"Confidence: {confidence_val:.0%}")
    
    # ── Decision box ──
    color = {"auto_approved":"green","human_review":"orange","escalated":"red"}.get(getattr(d, 'status', ''), "gray")
    st.markdown(f"""
    <div style='padding:20px;border-radius:10px;background:{color}20;border-left:5px solid {color};margin-top:20px;'>
        <h3 style='margin:0;color:{color}'>Decision: {getattr(d, 'status', 'unknown').replace('_',' ').title()}</h3>
        <p><b>Reason:</b> {getattr(d, 'reason', 'N/A')}</p>
        <p><b>Recommended Action:</b> {getattr(d, 'recommended_action', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Feedback ──
    st.subheader("Was this decision helpful?")
    fb_cols = st.columns(3)
    trace_id = result.get('trace_id', 'unknown')
    with fb_cols[0]:
        if st.button("👍 Correct", key=f"correct_{trace_id}", use_container_width=True):
            st.session_state[f"feedback_{trace_id}"] = "correct"
            st.success("Thanks!")
    with fb_cols[1]:
        if st.button("👎 Incorrect", key=f"wrong_{trace_id}", use_container_width=True):
            st.session_state[f"feedback_{trace_id}"] = "incorrect"
            st.warning("Flagged for review.")
    with fb_cols[2]:
        if st.button("🤔 Uncertain", key=f"uncertain_{trace_id}", use_container_width=True):
            st.session_state[f"feedback_{trace_id}"] = "uncertain"
            st.info("Noted.")
    
    # ── Expanders ──
    with st.expander("🔍 Full Extracted Data"):
        st.json(extracted_dict)
    
    with st.expander("📚 Policy Citations"):
        for i, c in enumerate(getattr(d, 'policy_citations', []), 1):
            st.markdown(f"**{i}.** {c}")
    
    # ── Export ──
    export_data = {
        "trace_id": trace_id,
        "extracted_data": extracted_dict,
        "decision": {
            "status": getattr(d, 'status', ''),
            "confidence": confidence_val,
            "reason": getattr(d, 'reason', ''),
            "action": getattr(d, 'recommended_action', '')
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    st.download_button(
        label="📥 Download Claim Report (JSON)",
        data=json.dumps(export_data, indent=2),
        file_name=f"claim_{trace_id[:8]}.json",
        mime="application/json"
    )
    
    st.caption(f"⏱️ {result.get('elapsed_ms', 0)} ms | Trace ID: `{trace_id}`")

# ── Process button ─────────────────────────────────────────────────────────
if st.button("🚀 Process Claim", type="primary", disabled=not uploaded_file):
    if not uploaded_file:
        st.error("Please upload a document.")
    else:
        trace_id = str(uuid.uuid4())
        start = time.time()
        
        # Step-by-step progress
        progress_bar = st.progress(0, text="Initializing...")
        steps = [
            (0.2, "📄 Extracting document data..."),
            (0.5, "🔍 Retrieving policy sections..."),
            (0.8, "⚖️ Analyzing and deciding..."),
            (1.0, "✅ Finalizing...")
        ]
        
        for progress, step_text in steps:
            progress_bar.progress(progress, text=step_text)
            time.sleep(0.3)
        
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
            progress_bar.empty()
            
            if result.get("error"):
                st.error(f"Error: {result['error']}")
                with st.expander("Debug info"):
                    st.json(result)
            else:
                d = result["decision"]
                extracted = result.get("extracted_data")
                
                if hasattr(extracted, "dict"):
                    extracted_dict = extracted.dict()
                elif hasattr(extracted, "model_dump"):
                    extracted_dict = extracted.model_dump()
                else:
                    extracted_dict = extracted or {}
                
                # Store for display and auto-fill
                st.session_state["extracted_policy"] = extracted_dict.get("policy_number", "")
                st.session_state["extracted_type"] = extracted_dict.get("claim_type", "")
                st.session_state["extracted_date"] = extracted_dict.get("incident_date", "")
                
                st.session_state["last_result"] = {
                    "decision": d,
                    "extracted_dict": extracted_dict,
                    "trace_id": trace_id,
                    "elapsed_ms": int((time.time()-start)*1000)
                }
                
                # Add to history
                new_claim = {
                    "trace_id": trace_id,
                    "policy": extracted_dict.get("policy_number", "N/A"),
                    "decision": getattr(d, 'status', 'unknown'),
                    "time": time.strftime("%H:%M:%S")
                }
                if not any(c["trace_id"] == trace_id for c in st.session_state.claim_history):
                    st.session_state.claim_history.insert(0, new_claim)
                    st.session_state.claim_history = st.session_state.claim_history[:5]
                
                st.rerun()
                
        except Exception as e:
            progress_bar.empty()
            st.error(f"Crash: {e}")
            st.code(traceback.format_exc())

st.divider()
