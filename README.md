# 🏦 MAK-Agent: Enterprise Finance Architecture with Autonomous Self-Healing

`MAK-Agent` is an autonomous enterprise AI platform built with **CrewAI**, **LangGraph**, **LiteLLM**, **Groq (Llama 3.1 8B / 3.3 70B)**, and **Streamlit**. It features a 5-agent Finance Department ecosystem, a token-compressing LangGraph state pipeline, a resilient fallback LLM router, and an autonomous self-healing debugging loop.

---

## 🏛️ Finance & Rescue Ecosystem Roster

| Agent | Role | Domain & Capabilities |
| :--- | :--- | :--- |
| **CFO** | Chief Financial Officer | Executive capital allocation & board strategy synthesis. |
| **Corp Finance Analyst** | Corporate Finance Specialist | Discounted Cash Flow (DCF), Net Present Value (NPV) & IRR. |
| **Risk Manager** | Enterprise Risk Agent | Risk identification, Value at Risk (VaR), volatility & stress testing. |
| **Treasury Manager** | Treasury & Liquidity Manager | Working capital optimization, cash conversion cycle & liquidity risk. |
| **Capital Structure Analyst**| Capital Structure Specialist | Debt/equity mix optimization, leverage ratios & WACC calculation. |
| **Context Summarizer** | Token Compression Agent | High-density 300-word state compression (prevents context snowballing). |
| **Doctor** | Lead Systems Debugger | Plain-English stack trace parsing & root-cause diagnosis. |
| **Surgeon** | Senior Software Engineer | Autonomous source-code patching (`FileWriterTool`) with HITL approval. |

---

## 📂 Project Architecture

```text
MAK-agent/
├── self_healing.py        # Autonomous debugging rescue crew (Doctor & Surgeon agents)
├── finance_department.py  # FinanceDepartment ecosystem class & resilient fallback router
├── main.py                # LangGraph stateful execution graph & token compression pipeline
├── app.py                 # Streamlit UI with error-catch wrapper & self-healing trigger
├── requirements.txt       # Project dependencies (crewai, langgraph, litellm, streamlit, etc.)
└── output/
    └── agency_report.txt  # Automatically persisted executive reports
```

---

## 🔄 Core Pipeline Phases

### Phase 1: Resilient Fallback LLM Router
Automatically routes requests between `groq/llama-3.1-8b-instant` and `groq/llama-3.3-70b-versatile` with exponential backoff ($2\text{s}, 4\text{s}, 8\text{s}\dots$) on HTTP 429 RateLimitErrors.

### Phase 2: LangGraph State & Token Compression
Nodes execute sequentially through `AgencyState`. Intermediate reports are passed to the Context Compression Specialist to maintain high-density $\le 300$-word state updates, eliminating context window snowballing.

### Phase 3: Autonomous Self-Healing Mechanic
When runtime exceptions occur, `app.py` catches the stack trace and triggers `trigger_rescue_mission(error_traceback)`. The Doctor diagnoses the crash, and the Surgeon generates a source-code patch requiring Human-in-the-Loop terminal approval before overwriting files.

---

## 🛠️ Tech Stack

- **Orchestration**: [CrewAI](https://github.com/crewAIInc/crewAI) + [LangGraph](https://github.com/langchain-ai/langgraph)
- **Routing**: [LiteLLM](https://github.com/BerriAI/litellm)
- **LLM Engine**: [Groq](https://groq.com) (`llama-3.1-8b-instant` / `llama-3.3-70b-versatile`)
- **UI**: Streamlit (Dark-mode Glassmorphism UI)
- **Python**: Python 3.12 (`uv` environment)

---

## 🚀 Quickstart Guide

```bash
# 1. Clone & Navigate
git clone https://github.com/maqibkhan777/MAK-Agent.git
cd MAK-Agent

# 2. Virtual Environment Setup
uv venv --python 3.12 .venv
.\.venv\Scripts\python.exe -m uv pip install -r requirements.txt -p .venv

# 3. Environment Variables (.env)
GROQ_API_KEY=your_groq_api_key_here
SERPER_API_KEY=your_serper_api_key_here

# 4. Launch Streamlit Web UI
.\.venv\Scripts\streamlit.exe run app.py
```

---

## 📜 License

MIT License.
