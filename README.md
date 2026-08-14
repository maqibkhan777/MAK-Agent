# 🏛️ MAK-Agent: Autonomous Enterprise OS & Multi-Department Studio

[![LangGraph](https://img.shields.io/badge/Orchestrator-LangGraph-blue.svg)](https://github.com/langchain-ai/langgraph)
[![CrewAI](https://img.shields.io/badge/Agent_Framework-CrewAI-red.svg)](https://github.com/crewAIInc/crewAI)
[![LiteLLM](https://img.shields.io/badge/Router-LiteLLM-green.svg)](https://github.com/BerriAI/litellm)
[![Groq](https://img.shields.io/badge/Inference-Groq_Llama_3.3_70B-orange.svg)](https://groq.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b.svg)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Container-Docker_Compose-2496ed.svg)](https://www.docker.com/)

`MAK-Agent` is an autonomous enterprise AI operating system built with **LangGraph**, **CrewAI**, **LiteLLM**, **Groq (Llama 3.1 8B / 3.3 70B)**, and **Streamlit**. It coordinates specialized multi-agent departments, strict Pydantic output guardrails, real-time web scrapers, local vector memory, an autonomous background cron engine, Docker containerization, and an automated self-healing debugger.

---

## 🏢 Enterprise Department Roster

| Department | Key Agents | Core Mission & Specialized Tools |
| :--- | :--- | :--- |
| **🕵️ Triage Gatekeeper** | Chief of Staff | Ingests user intent, searches Central RAG Knowledge Base, executes Chain-of-Thought routing to appropriate departments. |
| **🏦 Finance & Risk** | CFO, Corporate Finance Analyst, Risk, Treasury, Capital Structure, M&A, Controller, Valuation, Credit, FP&A | DCF valuation, capital budgeting, WACC minimization, VaR analysis. Equipped with **Live Market Data Puller (`yfinance`)** and **Live Search**. |
| **📣 Marketing Studio** | CMO, SEO & Trend Analyst, Lead Copywriter, Social Media Manager | Organic brand strategy, landing page copy, social posting. Equipped with **Live SEO Scraper (`googlesearch-python`)**, **Playwright Dynamic Browser**, and **Social Action API**. |
| **📈 B2B Sales Engine** | Lead Gen Specialist, VP of Sales, SDR, Solutions Architect | Lead qualification, account dossiers, cold outreach. Equipped with **B2B Company Scraper (`duckduckgo-search` + `bs4`)** and strict **`SalesEmail`** guardrails. |
| **💻 Software House** | Code Surgeon, Senior QA Tester, CTO, Senior Developer | Clean Python implementations, edge-case testing, LangGraph compatibility. Armed with **AST Python Syntax Checker** and **HITL File Writer** (Human-in-the-Loop approval). |
| **🎬 Content House** | Creative Director, Scriptwriter, Hook Specialist, Graphic Designer, Video Producer | 5-agent omnichannel media studio. Equipped with **RSS Trend Scraper (`feedparser`)**, **YouTube Hook Analyzer (`youtube-transcript-api`)**, and **`OmnichannelDeliverable`** guardrails. |
| **👨‍🏫 Education** | Finance Tutor | Step-by-step educational breakdowns of complex financial formulas and metrics. |
| **🚑 Self-Healing Rescue** | Doctor (Diagnostician), Surgeon (Code Fixer) | Automated crash detection, stack-trace diagnosis, and source-code self-repair with human terminal confirmation. |

---

## 🛠️ Specialized Tool Ecosystem

- 📊 **Live Market Data Puller (`yfinance`)**: Real-time stock prices, 52-week high/low, revenue, EBITDA, P/E ratios, and profit margins.
- 🔍 **Live SEO Scraper (`googlesearch-python`)**: Live organic Google SERP competitor rankings and meta descriptions.
- 🌐 **B2B Company Scraper (`duckduckgo-search` + `BeautifulSoup`)**: Scrapes target company homepages and extracts value propositions.
- 🛡️ **AST Python Syntax Checker (`ast`)**: Pre-compiles Python source code to detect syntax errors before human review.
- 🔒 **HITL File Writer**: Interactive Human-in-the-Loop terminal pause (`Approve these code changes? (y/n)`) prior to file writing.
- 📡 **RSS Trend Scraper (`feedparser`)**: Real-time industry RSS feed ingestion and narrative extraction.
- 🎥 **YouTube Hook Analyzer (`youtube-transcript-api`)**: Reverse-engineers viral opening 60-second video hooks.
- 🎭 **Dynamic Browser Tool (`Playwright`)**: Headless browser automation for JavaScript-rendered web pages.
- 🔎 **Live Internet Search (`DuckDuckGo`)**: Keyless live web research for breaking news and company data.

---

## 🛡️ Pydantic Guardrail Schemas

- **`SalesEmail`**: Enforces consultative executive tone and programmatically rejects forbidden promotional terms like *"100% free"* or *"guarantee"*.
- **`OmnichannelDeliverable`**: Standardizes multi-channel content across `written_post`, `video_script` (with text-on-screen cues), `b_roll_instructions`, and `image_generation_prompt` (Midjourney/DALL-E 3).
- **`RoutingDecision`**: Requires step-by-step reasoning before selecting active department routes.

---

## 📂 Project Architecture

```text
MAK-agent/
├── desktop_client/              # Native Electron + Vite + React + Tailwind Desktop App
│   ├── electron/main.js         # Electron 1200x800 hidden titlebar desktop window
│   ├── src/App.jsx              # Modern Dark-Themed Multi-Department Chat Client
│   └── package.json             # Desktop app dependencies and build scripts
├── server.py                    # Headless FastAPI Server with /api/chat & CORS middleware
├── main.py                      # Master LangGraph Orchestrator & multi-department StateGraph
├── finance_department.py        # Finance Department (12+ specialists & resilient LLM router)
├── marketing_department.py      # Marketing Department (SEO scraper, browser & social tools)
├── sales_department.py          # Sales Department (B2B scraper & SalesEmail guardrail)
├── engineering_department.py    # Engineering Department (AST syntax checker & HITL file writer)
├── content_house_department.py  # Content House (5-agent studio & OmnichannelDeliverable)
├── custom_tools.py              # Shared tools (Live Search, Playwright Browser, Social API)
├── self_healing.py              # Autonomous Debugger (Doctor & Surgeon rescue crew)
├── db_manager.py                # SQLite persistence manager for scheduled tasks
├── autonomous_worker.py         # Autonomous background worker with TTS audio synthesis
├── company_knowledge_base/      # Central Company Brain (RAG directory for SOPs & brand voice)
├── requirements.txt             # Categorized dependency manifest
├── Dockerfile                   # Python 3.11-slim container definition
├── docker-compose.yml           # Multi-port container orchestration with persistent volumes
├── launch_desktop.bat           # One-click Electron Desktop App launcher
└── run_mak.bat                  # Real-time console terminal launcher
```

---

## 🚀 Quickstart Guide

### 1. Launch the Headless FastAPI Server
```powershell
# In root directory:
python server.py
# Or run with uvicorn:
# uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Launch the Native Electron Desktop Client
```powershell
# Navigate to desktop_client directory:
cd desktop_client
npm run electron:dev

# Or simply double-click: launch_desktop.bat
```
```

---

## 🤖 Autonomy Engine & Observability

- **Background Scheduling**: Set recurring prompts in the Streamlit **🤖 Autonomy Engine** tab. The background worker evaluates jobs every 60s, executes them through LangGraph, and speaks executive briefings aloud via `gTTS` audio (`output/briefing_task_<id>.mp3`).
- **Arize Phoenix Observability**: Real-time tracing and telemetry for all LLM calls and LangChain spans accessible at `http://localhost:6060`.

---

## 📜 License

MIT License.
