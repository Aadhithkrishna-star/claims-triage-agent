"""
Streamlit UI for the Claims Triage Agent.
Run with: streamlit run app/ui.py
"""
import streamlit as st
import requests
import json

API_URL = "http://localhost:8000/api/v1"


st.set_page_config(page_title="Claims Triage Agent", layout="wide")

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
        with st.spinner("Processing claim through AI agent..."):
            # Call API
            files = {"document": (uploaded_file.name, uploaded_file.getvalue())}
            data = {
                "policy_number": policy_number,
                "claim_type": claim_type,
                "incident_date": incident_date.strftime("%Y-%m-%d"),
            }
            
            try:
                response = requests.post(
                    f"{API_URL}/claims/upload",
                    data=data,
                    files=files,
                    timeout=60,
                )
                result = response.json()
                
                if response.status_code == 200:
                    # Display results
                    st.success("Claim processed successfully!")
                    
                    # Trace ID
                    st.code(f"Trace ID: {result['trace_id']}", language="text")
                    
                    # Decision card
                    status = result["status"]
                    status_colors = {
                        "auto_approved": "green",
                        "human_review": "orange",
                        "escalated": "red",
                    }
                    color = status_colors.get(status, "gray")
                    
                    st.markdown(f"""
                    <div style='padding: 20px; border-radius: 10px; background-color: {color}20; border-left: 5px solid {color};'>
                        <h3 style='margin: 0; color: {color};'>Decision: {status.replace("_", " ").title()}</h3>
                        <p style='margin: 5px 0;'><strong>Confidence:</strong> {result['decision']['confidence']}</p>
                        <p style='margin: 5px 0;'><strong>Reason:</strong> {result['decision']['reason']}</p>
                        <p style='margin: 5px 0;'><strong>Action:</strong> {result['decision']['recommended_action']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Extracted data
                    with st.expander("📋 Extracted Data"):
                        st.json(result["extracted_data"])
                    
                    # Policy citations
                    with st.expander("📚 Policy Citations"):
                        for i, citation in enumerate(result["decision"]["policy_citations"], 1):
                            st.markdown(f"**{i}.** {citation}")
                    
                    # Performance
                    st.caption(f"⏱️ Processing time: {result['processing_time_ms']} ms")
                    
                else:
                    st.error(f"Error: {result.get('detail', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"Failed to connect to API: {e}")
                st.info("Make sure the FastAPI server is running: `uvicorn app.main:app --reload`")

# Footer
st.divider()
st.caption("Built for Moring AI interview | Open-source stack | ₹0 cost")