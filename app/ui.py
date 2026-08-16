"""
Streamlit UI - MOCK VERSION for testing deployment.
"""
import streamlit as st
import uuid
import time
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Claims Triage Agent", layout="wide")

# Check API key
if not os.getenv("GROQ_API_KEY"):
    st.sidebar.warning("⚠️ GROQ_API_KEY not set (mock mode)")
else:
    st.sidebar.success("✅ API Key found")

st.title("🛡️ Regulated Claims Triage Agent")
st.markdown("**MOCK MODE** - Testing UI without ML models")

col1, col2 = st.columns(2)

with col1:
    policy_number = st.text_input("Policy Number", "POL-H-12345")
    claim_type = st.selectbox("Claim Type", ["health", "motor", "home", "travel"])
    incident_date = st.date_input("Incident Date")

with col2:
    uploaded_file = st.file_uploader("Upload Claim Document", type=["txt", "pdf"])

if st.button("🚀 Process Claim", type="primary"):
    if not uploaded_file:
        st.error("Please upload a claim document.")
    else:
        with st.spinner("Simulating processing..."):
            time.sleep(2)  # Fake delay
            
            trace_id = str(uuid.uuid4())
            
            # Mock result
            st.success("Claim processed successfully! (MOCK)")
            st.code(f"Trace ID: {trace_id}")
            
            st.markdown("""
            <div style='padding: 20px; border-radius: 10px; background-color: green20; border-left: 5px solid green;'>
                <h3 style='margin: 0; color: green;'>Decision: Auto Approved</h3>
                <p><strong>Confidence:</strong> 0.95</p>
                <p><strong>Reason:</strong> Claim amount below threshold</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📋 Extracted Data"):
                st.json({"policy_number": policy_number, "claim_type": claim_type, "amount": 25000})

st.divider()
st.caption("MOCK MODE - For deployment testing only")