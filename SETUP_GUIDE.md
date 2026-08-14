# 🚀 MAK Enterprise OS — Complete Setup & Installation Guide

Welcome to **MAK Enterprise OS**, an autonomous multi-agent enterprise framework powered by **LangGraph**, **CrewAI**, **LiteLLM**, **Streamlit**, and **Docker**.

This guide walks you step-by-step through setting up your environment, installing necessary dependencies, configuring API keys, and launching your local command center.

---

## 📋 Table of Contents
1. [Prerequisites & Downloads](#-prerequisites--downloads)
2. [Step 1: Clone or Download the Codebase](#step-1-clone-or-download-the-codebase)
3. [Step 2: Create a Virtual Environment (`.venv`)](#step-2-create-a-virtual-environment-venv)
4. [Step 3: Install Required Dependencies](#step-3-install-required-dependencies)
5. [Step 4: Configure Environment Variables (`.env`)](#step-4-configure-environment-variables-env)
6. [Step 5: Launch the Streamlit Dashboard](#step-5-launch-the-streamlit-dashboard)
7. [Step 6: Docker Sandbox Deployment (Alternative)](#step-6-docker-sandbox-deployment-alternative)
8. [🤖 Managing Autonomous Tasks](#-managing-autonomous-tasks-autonomy-engine)
9. [💡 Troubleshooting & Pro Tips](#-troubleshooting--pro-tips)

---

## 🛠️ Prerequisites & Downloads

Before starting, ensure you have the following installed on your machine:

| Software | Required Version | Download Link | Description |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10 – 3.12 | [python.org/downloads](https://www.python.org/downloads/) | Programming language environment (**Check "Add Python to PATH"**) |
| **VS Code** | Latest | [code.visualstudio.com](https://code.visualstudio.com/) | Recommended Code Editor & Terminal |
| **Git** | Latest | [git-scm.com/downloads](https://git-scm.com/downloads/) | Version control to clone repository |
| **Docker Desktop** *(Optional)* | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) | Container runtime for sandbox deployments |
| **Groq API Key** | Free Tier Available | [console.groq.com](https://console.groq.com/keys) | Primary inference engine (`llama-3.1-8b-instant` & `llama-3.3-70b-versatile`) |
| **OpenRouter Key** *(Optional)* | Free Tier Available | [openrouter.ai](https://openrouter.ai/keys) | Optional backup LLM API key |

---

## Step 1: Clone or Download the Codebase

Open your terminal (PowerShell, Command Prompt, or VS Code Terminal) and navigate to your preferred project directory:

```bash
cd d:\MAK-agent
```

If downloading from Git:
```bash
git clone https://github.com/maqibkhan777/MAK-Agent.git .
```

---

## Step 2: Create a Virtual Environment (`.venv`)

A virtual environment isolates project dependencies so they don't interfere with system Python.

1. Open PowerShell inside the project directory (`d:\MAK-agent`).
2. Run the command to build the virtual environment:

```powershell
python -m venv .venv
```

3. Activate the virtual environment:
   - **Windows PowerShell**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - *If PowerShell reports an ExecutionPolicy error, run `Set-ExecutionPolicy Unrestricted -Scope Process` first.*
   - **Windows Command Prompt (cmd)**:
     ```cmd
     .venv\Scripts\activate.bat
     ```

---

## Step 3: Install Required Dependencies

With `.venv` active, install all required Python libraries in one command:

```powershell
pip install -r requirements.txt
```

### What gets installed?
- **CrewAI & LangGraph**: Multi-agent framework, sequential task execution, and stateful graph routing.
- **LiteLLM & LangChain Groq**: Resilient API router with automatic fallbacks and rate limit retry backoff.
- **Streamlit**: Web-based executive command center interface.
- **Web & SEO Tools**: `googlesearch-python` (live Google SERP scraper), `duckduckgo-search` (live search), `beautifulsoup4` (B2B homepage scraper), `playwright` (headless browser controller).
- **Financial & Media Tools**: `yfinance` (real-time stock market data), `feedparser` (RSS trend scraper), `youtube-transcript-api` (viral hook analyzer).
- **Embeddings & Memory**: `sentence-transformers` (`all-MiniLM-L6-v2`) for local long-term memory.
- **Audio & Scheduling**: `gTTS` (Google Text-to-Speech audio briefings), `schedule` (cron background engine).
- **Telemetry**: `arize-phoenix` & `openinference-instrumentation-langchain` for LLM observability.

*(Optional Playwright Browser Setup)*:
```powershell
python -m playwright install --with-deps chromium
```

---

## Step 4: Configure Environment Variables (`.env`)

Create a file named `.env` in the root folder (`d:\MAK-agent\.env`) and configure your API keys:

```ini
# Primary High-Speed Inference Engine (Required)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional Fallback Provider (Free tier supported)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here

# Optional Web Search Tool API Key
SERPER_API_KEY=your_serper_dev_key_here
```

> [!NOTE]
> `GROQ_API_KEY` is required. The system automatically handles fallback routing and rate limits (429 handling) if primary LLMs hit quotas.

---

## Step 5: Launch the Headless FastAPI Server

To start the headless FastAPI server orchestrating the LangGraph engine, run:

```powershell
python server.py
# Or with uvicorn:
# .\.venv\Scripts\uvicorn.exe server:app --host 0.0.0.0 --port 8000 --reload
```

Your API documentation and interactive Swagger UI will be available at:
`http://localhost:8000/docs`

### Windows One-Click Shortcuts:
- **Terminal Console Launch**: Double-click [`run_mak.bat`](file:///d:/MAK-agent/run_mak.bat).

---

## Step 6: Docker Sandbox Deployment (Alternative)

To run the entire system inside a containerized Docker sandbox with volume persistence:

```bash
# 1. Build and launch container in background
docker compose up -d --build

# 2. Access FastAPI Backend Docs at: http://localhost:8000/docs
# 3. Access Arize Phoenix UI at: http://localhost:6060

# View container logs
docker compose logs -f

# Shut down container
docker compose down
```

---

## 💡 Troubleshooting & Pro Tips

### 1. VS Code "Problems Tab" Warnings
If VS Code shows red squigglies under imports:
- Open Command Palette (`Ctrl + Shift + P`).
- Type **Python: Select Interpreter**.
- Choose: `.\.venv\Scripts\python.exe`.

### 2. Testing the Chat Endpoint
You can send a POST request directly via `curl` or Postman:
```bash
curl -X POST "http://localhost:8000/api/chat" -H "Content-Type: application/json" -d "{\"prompt\": \"Conduct a DCF valuation for a $10M project\"}"
```

### 3. Human-in-the-Loop (HITL) Code Execution Pause
When the Engineering Department's `Code Surgeon` proposes Python file writes:
- The system pauses and prompts in the terminal: `Approve these code changes? (y/n):`.
- Type `y` to approve and write changes to disk, or type `n` to abort execution.

### 4. Automatic Self-Healing Debugger
If any unexpected runtime crash occurs during an agent run:
- The system automatically triggers the **Doctor (Diagnostician)** and **Surgeon (Code Fixer)** agents to inspect the stack trace and generate a proposed patch.
