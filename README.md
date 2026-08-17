# 🛡️ Claims Triage Agent

### Enterprise AI Application | Insurance Claims Triage System


🚀 [Live Demo](https://claims-triage-agent-waa3retvpk6goouzxyhedd.streamlit.app/)  
<sup>↗️ Ctrl+Click or Right-click → "Open link in new tab"</sup>

 💻 **[Source Code](https://github.com/aadhithkrishna/star-claims-triage-agent)**

An AI-powered insurance claims triage system built with **LangGraph, Groq LLM, FAISS, Sentence Transformers, Pydantic, SQLite, and Streamlit**.

The system automatically analyzes insurance claim documents, retrieves relevant policy information, and determines whether a claim should be **auto-approved, sent for human review, or escalated**.

Designed with a strong focus on **reliability, auditability, explainability, and production readiness** for regulated enterprise environments

---
## 🚀 What This Project Does

The Claims Triage Agent processes insurance claim documents through an agentic workflow:

```text
                    ┌──────────────────┐
                    │   Claim Document │
                    │    PDF / TXT     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     EXTRACT      │
                    │    Groq LLM      │
                    │                  │
                    │ Structured Claim │
                    │      Data        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     RETRIEVE     │
                    │                  │
                    │ FAISS + Sentence │
                    │   Transformers   │
                    │                  │
                    │ Relevant Policy  │
                    │    Sections      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │      DECIDE      │
                    │    LangGraph     │
                    │                  │
                    │ Triage Decision  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        Auto Approved   Human Review    Escalated
```

Every claim generates a **traceable audit record** containing execution details, decision reasoning, confidence, and policy citations.

---

## ✨ Key Capabilities

| Capability                | Implementation                                     |
| ------------------------- | -------------------------------------------------- |
| 📄 Document Ingestion     | PDF and TXT claim document uploads                 |
| 🤖 LLM Extraction         | Groq LLM with deterministic structured JSON output |
| 🔍 Policy Retrieval       | FAISS + Sentence Transformers semantic search      |
| ⚖️ Agentic Triage         | LangGraph orchestration                            |
| 🔄 Retry & Error Handling | Node-level error handling and retries              |
| 📊 Audit Logging          | SQLite-backed audit trail                          |
| 🆔 Traceability           | Unique trace IDs for claim executions              |
| 🧠 Explainability         | Confidence scores, reasoning, and policy citations |
| 🛡️ Validation            | Pydantic schemas                                   |
| 🌐 Production UI          | Streamlit                                          |
| ☁️ Deployment             | Streamlit Cloud                                    |

---

# 🏗️ Architecture

The application follows a three-stage LangGraph workflow:

```text
┌──────────────────────────────────────────────────────────────┐
│                        CLAIM INPUT                           │
│                     PDF / TXT Document                       │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         EXTRACT                              │
│                                                              │
│  Groq LLM                                                    │
│  • Claimant information                                      │
│  • Policy number                                             │
│  • Claim amount                                              │
│  • Claim date                                                │
│  • Injury / claim type                                       │
│  • Description                                               │
│                                                              │
│  Output → Structured Pydantic Model                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         RETRIEVE                             │
│                                                              │
│  Sentence Transformers                                      │
│          ↓                                                   │
│     Embeddings                                               │
│          ↓                                                   │
│       FAISS                                                  │
│          ↓                                                   │
│  Relevant Policy Sections                                    │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                          DECIDE                              │
│                                                              │
│  LangGraph Decision Node                                    │
│                                                              │
│  • Claim information                                         │
│  • Retrieved policy context                                   │
│  • Claim amount                                               │
│  • Coverage information                                       │
│  • Potential fraud indicators                                │
│                                                              │
└─────────────────────────────┬────────────────────────────────┘
                              │
             ┌────────────────┼─────────────────┐
             ▼                ▼                 ▼
       AUTO APPROVED     HUMAN REVIEW       ESCALATED
```

---

# 🧠 Agent Workflow

## 1. EXTRACT

The uploaded claim document is passed to the Groq LLM.

The model extracts structured information including:

```json
{
  "claimant_name": "Rahul Sharma",
  "policy_number": "POL-H-12345",
  "claim_date": "2024-03-15",
  "claim_type": "Health",
  "claim_amount": 75000,
  "description": "Emergency appendectomy at Apollo Hospital, Chennai"
}
```

The output is validated using **Pydantic** to ensure predictable downstream processing.

---

## 2. RETRIEVE

The extracted claim information is used to identify relevant sections of the insurance policy.

The retrieval pipeline uses:

```text
Policy Documents
       ↓
Sentence Transformer
       ↓
Vector Embeddings
       ↓
FAISS Index
       ↓
Semantic Similarity Search
       ↓
Relevant Policy Sections
```

This allows the decision agent to reason over the actual policy context rather than relying exclusively on the LLM's internal knowledge.

---

## 3. DECIDE

The decision node combines:

* Extracted claim information
* Retrieved policy sections
* Coverage rules
* Claim amount
* Potential fraud indicators
* Policy thresholds

The agent produces a structured triage decision.

Possible outcomes:

```text
auto_approved
human_review
escalated
```

Example:

```json
{
  "decision": "auto_approved",
  "confidence": 0.92,
  "reason": "Health claim under threshold, valid policy, no fraud indicators",
  "policy_citations": [
    "Section 3.2 — Emergency procedures covered"
  ]
}
```

---

# 🛡️ Reliability & Production Design

The project was intentionally designed around common production failure scenarios.

### Lazy-Loaded API Client

The Groq client is initialized at runtime instead of import time.

This prevents Streamlit secrets from being accessed before the application runtime has initialized.

```text
Application Startup
        ↓
Streamlit Initialization
        ↓
Secrets Available
        ↓
LLM Client Initialization
```

---

### Graceful Audit Database Failure

Audit logging should not prevent the claims application from starting.

Database initialization is therefore wrapped with defensive error handling.

```python
try:
    init_db()
except Exception:
    logger.exception("Audit database initialization failed")
```

The application can continue operating even when audit initialization encounters an unexpected failure.

---

### Defensive Logging

The audit logger accepts flexible keyword arguments and safely converts complex Python objects before SQLite insertion.

Supported values include:

* Strings
* Numbers
* Dictionaries
* Lists
* Optional / missing values

This prevents SQLite binding errors caused by unsupported Python object types.

---

### Deterministic LLM Output

The extraction pipeline uses:

* `temperature=0`
* Structured output expectations
* Pydantic validation
* JSON parsing
* Markdown/code-fence cleanup

The goal is to make downstream processing predictable and reproducible.

---

# 🧰 Tech Stack

| Layer           | Technology            |
| --------------- | --------------------- |
| Agent Framework | LangGraph             |
| LLM             | Groq API              |
| LLM Model       | Llama 3 70B           |
| Embeddings      | Sentence Transformers |
| Vector Database | FAISS                 |
| Data Validation | Pydantic              |
| Audit Storage   | SQLite                |
| Frontend        | Streamlit             |
| Language        | Python                |
| Deployment      | Streamlit Cloud       |

---

# 📂 Project Structure

```text
star-claims-triage-agent/
│
├── streamlit_app.py
├── requirements.txt
├── README.md
│
├── app/
│   │
│   ├── services/
│   │   │
│   │   ├── agent/
│   │   │   └── triage_agent.py
│   │   │       └── LangGraph workflow
│   │   │
│   │   ├── document/
│   │   │   └── extractor.py
│   │   │       └── Groq LLM document extraction
│   │   │
│   │   ├── policy/
│   │   │   └── retriever.py
│   │   │       └── FAISS policy retrieval
│   │   │
│   │   └── audit/
│   │       └── logger.py
│   │           └── SQLite audit logging
│   │
│   ├── core/
│   │   ├── config.py
│   │   │   └── Application configuration
│   │   │
│   │   └── logging.py
│   │       └── Structured application logging
│   │
│   └── models/
│       └── schemas.py
│           └── Pydantic data models
│
└── requirements.txt
```

---

# ⚡ Quick Start

## 1. Clone the Repository

```bash
git clone https://github.com/aadhithkrishna/star-claims-triage-agent.git

cd star-claims-triage-agent
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Groq API Key

### Linux / macOS

```bash
export GROQ_API_KEY="gsk_..."
```

### Windows PowerShell

```powershell
$env:GROQ_API_KEY="gsk_..."
```

Alternatively, create a `.env` file:

```env
GROQ_API_KEY=gsk_...
```

> Never commit your API key to GitHub.

---

## 5. Run the Application

```bash
streamlit run streamlit_app.py
```

The application will be available at:

```text
http://localhost:8501
```

---

# ☁️ Deploy to Streamlit Cloud

The application can be deployed directly from GitHub.

### Step 1 — Push to GitHub

```bash
git add .
git commit -m "Initial claims triage agent"
git push
```

### Step 2 — Connect Repository

Open Streamlit Cloud and connect the GitHub repository.

### Step 3 — Configure Secrets

Add the following secret:

```toml
GROQ_API_KEY = "gsk_..."
```

### Step 4 — Deploy

Set the main application file to:

```text
streamlit_app.py
```

Deploy the application.

---

# 🧪 Example

## Input

```text
Claimant: Rahul Sharma
Policy: POL-H-12345
Date: 2024-03-15
Type: Health
Amount: Rs. 75,000
Description: Emergency appendectomy at Apollo Hospital, Chennai.
```

## Output

```text
Decision: auto_approved

Confidence: 0.92

Reason:
Health claim under threshold, valid policy,
no fraud indicators.

Policy Citations:
Section 3.2 — Emergency procedures covered

Latency:
~2.3 seconds
```

---

# 📊 Auditability

Each claim execution is associated with a unique trace ID.

Example execution:

```text
Trace ID: 7f3d2e1a

EXTRACT
├── Started
├── Completed
└── Structured claim generated

RETRIEVE
├── Started
├── FAISS search executed
└── Policy context retrieved

DECIDE
├── Started
├── Decision generated
└── Completed

FINAL
└── auto_approved
```

This provides visibility into the individual stages of an agent execution.

---

# 🎯 Design Decisions

| Challenge                                | Solution                            |
| ---------------------------------------- | ----------------------------------- |
| Secrets unavailable during module import | Lazy-loaded LLM client              |
| Audit schema changes                     | Automatic schema migration          |
| Complex values passed to SQLite          | Defensive `_safe_str()` conversion  |
| Non-deterministic LLM responses          | `temperature=0` + structured output |
| Invalid LLM output                       | Pydantic validation                 |
| Application failure caused by audit DB   | Graceful degradation                |
| Policy-aware decision making             | FAISS semantic retrieval            |
| Agent workflow complexity                | LangGraph state graph               |
| Enterprise traceability                  | Trace IDs + SQLite audit logs       |

---

# 🏢 Enterprise Readiness

| Requirement               | Status                                      |
| ------------------------- | ------------------------------------------- |
| Audit trail per claim     | ✅ SQLite + trace IDs                        |
| Explainable decisions     | ✅ Reasoning + confidence + policy citations |
| Structured outputs        | ✅ Pydantic validation                       |
| Error handling            | ✅ Defensive exception handling              |
| Retry handling            | ✅ LangGraph workflow                        |
| Environment configuration | ✅ Pydantic + Streamlit secrets              |
| Document processing       | ✅ PDF + TXT                                 |
| Semantic policy retrieval | ✅ FAISS + Sentence Transformers             |
| Production UI             | ✅ Streamlit                                 |
| Cloud deployment          | ✅ Streamlit Cloud                           |

---

# 🔐 Security Considerations

This project is designed as a demonstration of production-oriented architecture.

For a real insurance deployment, additional controls would be required, including:

* Authentication and authorization
* Role-based access control
* Encryption at rest and in transit
* PII redaction
* Secrets management
* Data retention policies
* Model access controls
* Human-in-the-loop approval workflows
* Regulatory compliance controls
* Comprehensive monitoring and alerting
* Production-grade database infrastructure

No real customer or personally identifiable insurance data should be committed to this repository.

---

# 🚧 Future Improvements

Potential production enhancements include:

* [ ] PostgreSQL instead of SQLite
* [ ] Redis-based state management
* [ ] Production authentication and RBAC
* [ ] PII detection and redaction
* [ ] Human-in-the-loop approval interface
* [ ] LangSmith observability
* [ ] Prometheus/Grafana metrics
* [ ] Automated evaluation framework
* [ ] Retrieval quality evaluation
* [ ] LLM response evaluation
* [ ] Policy version management
* [ ] Multi-document claim processing
* [ ] Async document processing
* [ ] Background job queue
* [ ] Containerized deployment
* [ ] CI/CD pipeline
* [ ] Automated unit and integration tests

---

# 📈 Example End-to-End Flow

```text
User uploads claim
        │
        ▼
Document extraction
        │
        ▼
Groq LLM
        │
        ▼
Structured claim data
        │
        ▼
Pydantic validation
        │
        ▼
Policy semantic search
        │
        ▼
FAISS
        │
        ▼
Relevant policy context
        │
        ▼
LangGraph DECIDE node
        │
        ├───────────────┐
        ▼               ▼
Auto Approval      Human Review
        │               │
        └───────┬───────┘
                ▼
          Audit Logger
                │
                ▼
            SQLite
```

---

# 💡 Why LangGraph?

LangGraph provides explicit control over the agent workflow instead of treating the application as a simple LLM prompt chain.

The graph makes it possible to:

* Maintain state between nodes
* Define deterministic workflow transitions
* Implement retries
* Handle failures
* Add human-in-the-loop steps
* Track execution state
* Extend the system with additional agents

Current workflow:

```text
EXTRACT → RETRIEVE → DECIDE
```

Future workflows could evolve into:

```text
EXTRACT
   ↓
VALIDATE
   ↓
RETRIEVE POLICY
   ↓
FRAUD CHECK
   ↓
COVERAGE CHECK
   ↓
DECIDE
   ↓
HUMAN REVIEW
```

---

# 📌 Project Highlights

This project demonstrates practical experience with:

**Generative AI**

* LLM application development
* Structured LLM outputs
* Prompt engineering
* Deterministic inference
* LLM-based information extraction

**RAG**

* Document embeddings
* Semantic search
* FAISS
* Sentence Transformers
* Context retrieval

**Agentic AI**

* LangGraph
* Stateful workflows
* Node-based orchestration
* Retry/error handling
* Decision routing

**Production Engineering**

* Defensive programming
* Runtime configuration
* Secrets management
* Structured logging
* Auditability
* Graceful degradation

**Deployment**

* Streamlit
* GitHub
* Streamlit Cloud
* Environment-based configuration

---



GitHub:
https://github.com/aadhithkrishna

---
