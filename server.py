import sys
import os
import time
import json
import uuid
import datetime
from typing import List, Optional, Dict, Any

os.environ["RUNNING_IN_SERVER"] = "true"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Import the core LangGraph agency orchestrator, KeyVault, and Memory Engine
from main import run_agency
from key_vault import vault
from memory_engine import memory
import db_manager

# Initialize APScheduler for background automated jobs
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()
scheduler.start()

SCHEDULES_FILE = os.path.join(os.path.dirname(__file__), "scheduled_tasks_config.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "scheduled_history.json")

# In-memory history tracking
scheduled_history: List[Dict[str, Any]] = []

def _load_history():
    global scheduled_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                scheduled_history = json.load(f)
        except Exception:
            scheduled_history = []

def _save_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(scheduled_history[-50:], f, indent=2)
    except Exception as e:
        print(f"[Scheduler History Save Error]: {e}")

_load_history()

def execute_scheduled_job(job_id: str, job_name: str, prompt: str, department: str = "auto"):
    """Background worker executed by APScheduler."""
    print(f"\n[MAK Scheduled Task Triggered] Executing '{job_name}' (ID: {job_id}) at {datetime.datetime.now()}...")
    start_ts = time.time()
    status_str = "success"
    try:
        result = run_agency(prompt)
    except Exception as e:
        result = f"Error during scheduled execution: {e}"
        status_str = "failed"
    duration = round(time.time() - start_ts, 2)

    record = {
        "job_id": job_id,
        "job_name": job_name,
        "prompt": prompt,
        "department": department,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status_str,
        "duration_sec": duration,
        "result_preview": result[:300] + "..." if len(result) > 300 else result,
        "full_result": result
    }
    scheduled_history.insert(0, record)
    _save_history()
    print(f"[MAK Scheduled Task Complete] Job '{job_name}' finished in {duration}s with status: {status_str}")


# Initialize FastAPI application
app = FastAPI(
    title="MAK Autonomous Cognitive Core API",
    description="Headless production-ready FastAPI backend orchestrating LangGraph multi-department autonomous agency, multi-LLM key failover, and task scheduler.",
    version="2.0.0"
)

# CORS Middleware for desktop client and local integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# Request & Response Schemas
# =====================================================================
class Attachment(BaseModel):
    name: str = Field(..., description="File name of the uploaded attachment")
    type: str = Field(default="text/plain", description="MIME type or file extension")
    content: str = Field(..., description="Raw text or parsed content of the file")
    size: Optional[int] = Field(default=0, description="Size in bytes")


class ChatRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The user input or enterprise task prompt dispatched to the agent orchestrator.",
        json_schema_extra={"example": "Conduct a discounted cash flow valuation for a project with $5M initial outlay and $1.5M annual cash flows for 5 years at 10% discount rate."}
    )
    attachments: Optional[List[Attachment]] = Field(
        default=[],
        description="Optional list of parsed file attachments to provide as context."
    )
    session_id: Optional[str] = Field(
        default="default",
        description="Session identifier for multi-turn conversational context & cognitive memory."
    )
    chat_history: Optional[List[Dict[str, Any]]] = Field(
        default=[],
        description="Full multi-turn dialogue history from the client interface for complete context continuity."
    )


class ChatResponse(BaseModel):
    status: str = Field(default="success", description="Execution status of the agency pipeline.")
    response: str = Field(..., description="The final structured deliverable produced by the agency orchestrator.")
    active_department: Optional[str] = Field(default="Chief of Staff", description="Department that finalized the response.")


class KeyUpdateRequest(BaseModel):
    provider: str = Field(..., description="Provider name: groq, openai, openrouter, anthropic, gemini")
    keys: List[str] = Field(..., description="List of API keys for this provider pool")


class AddKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider name: groq, openai, openrouter, anthropic, gemini")
    key: str = Field(..., description="Single API key to add to the pool")


class ScheduleCreateRequest(BaseModel):
    name: str = Field(..., description="Descriptive name of the scheduled job")
    prompt: str = Field(..., description="The agentic prompt to execute automatically")
    schedule_type: str = Field(default="interval", description="'interval' (every X mins) or 'daily' (at HH:MM) or 'cron'")
    interval_minutes: Optional[int] = Field(default=60, description="Interval in minutes if type is 'interval'")
    daily_time: Optional[str] = Field(default="09:00", description="HH:MM format in 24h for daily jobs")
    cron_expr: Optional[str] = Field(default="0 9 * * *", description="Standard 5-field cron expression if type is 'cron'")
    department: Optional[str] = Field(default="auto", description="Target department")


# =====================================================================
# API Endpoints
# =====================================================================

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": "MAK Autonomous Cognitive Core Backend",
        "version": "2.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "keys": "/api/settings/keys",
            "schedules": "/api/schedules",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "key_vault": vault.get_status()
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Agent Orchestrator"])
def chat_endpoint(request: ChatRequest):
    """
    Accepts a ChatRequest (prompt + optional attachments + multi-turn history), passes the composite text to LangGraph,
    and returns the final agentic response.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt cannot be empty."
        )

    # Augment prompt with attachments context if supplied
    composite_prompt = request.prompt.strip()
    if request.attachments:
        attachment_blocks = []
        for att in request.attachments:
            attachment_blocks.append(
                f"\n--- [ATTACHED FILE: {att.name} ({att.type}, {att.size} bytes)] ---\n"
                f"{att.content}\n"
                f"--- [END OF ATTACHMENT: {att.name}] ---"
            )
        composite_prompt = f"{composite_prompt}\n\n[USER PROVIDED FILE ATTACHMENTS]:\n" + "\n".join(attachment_blocks)

    try:
        final_output = run_agency(
            composite_prompt,
            session_id=request.session_id or "default",
            chat_history=request.chat_history or []
        )
        return ChatResponse(
            status="success",
            response=final_output,
            active_department="MAK Agency Core"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent orchestration pipeline failed: {str(e)}"
        )


# =====================================================================
# Multi-LLM Key Vault & Failover Endpoints
# =====================================================================

@app.get("/api/settings/keys", tags=["Key Vault"])
def get_key_vault_status():
    """Returns current active keys, masked lists, and pool capacity for all providers."""
    return {
        "status": "success",
        "providers": vault.get_status()
    }


@app.post("/api/settings/keys", tags=["Key Vault"])
def update_provider_keys(req: KeyUpdateRequest):
    """Replaces the key list for a provider (e.g. updating Groq failover pool)."""
    vault.update_provider_keys(req.provider, req.keys)
    return {
        "status": "success",
        "message": f"Updated {len(req.keys)} keys for provider '{req.provider}'",
        "providers": vault.get_status()
    }


@app.post("/api/settings/keys/add", tags=["Key Vault"])
def add_provider_key(req: AddKeyRequest):
    """Adds a new key to a provider's rotation pool."""
    success = vault.add_key(req.provider, req.key)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid provider or empty key.")
    return {
        "status": "success",
        "message": f"Added key to provider '{req.provider}'",
        "providers": vault.get_status()
    }


@app.delete("/api/settings/keys/{provider}/{index}", tags=["Key Vault"])
def delete_provider_key(provider: str, index: int):
    """Removes a key from a provider pool by index."""
    success = vault.remove_key(provider, index)
    if not success:
        raise HTTPException(status_code=400, detail="Key index not found or invalid provider.")
    return {
        "status": "success",
        "message": f"Removed key index {index} from '{provider}'",
        "providers": vault.get_status()
    }


# =====================================================================
# Autonomous Task Scheduler Endpoints
# =====================================================================

@app.get("/api/schedules", tags=["Task Scheduler"])
def list_schedules():
    """Lists all configured and running scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "Paused"
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run,
            "trigger": str(job.trigger)
        })
    return {
        "status": "success",
        "active_jobs": jobs,
        "total_jobs": len(jobs)
    }


@app.post("/api/schedules", tags=["Task Scheduler"])
def create_schedule(req: ScheduleCreateRequest):
    """Creates a new automated background schedule."""
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    if req.schedule_type == "daily":
        parts = req.daily_time.split(":")
        hour = int(parts[0]) if len(parts) > 0 else 9
        minute = int(parts[1]) if len(parts) > 1 else 0
        trigger = CronTrigger(hour=hour, minute=minute)
    elif req.schedule_type == "cron":
        trigger = CronTrigger.from_crontab(req.cron_expr)
    else:  # interval
        mins = max(1, req.interval_minutes or 60)
        trigger = IntervalTrigger(minutes=mins)

    scheduler.add_job(
        execute_scheduled_job,
        trigger=trigger,
        id=job_id,
        name=req.name,
        kwargs={"job_id": job_id, "job_name": req.name, "prompt": req.prompt, "department": req.department or "auto"},
        replace_existing=True
    )

    return {
        "status": "success",
        "message": f"Scheduled job '{req.name}' registered successfully.",
        "job_id": job_id
    }


@app.delete("/api/schedules/{job_id}", tags=["Task Scheduler"])
def delete_schedule(job_id: str):
    """Cancels and removes a scheduled job."""
    try:
        scheduler.remove_job(job_id)
        return {"status": "success", "message": f"Job {job_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {e}")


@app.post("/api/schedules/{job_id}/run", tags=["Task Scheduler"])
def run_schedule_now(job_id: str):
    """Immediately triggers a scheduled job in a background thread."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    # Execute immediately
    import threading
    kwargs = job.kwargs
    threading.Thread(
        target=execute_scheduled_job,
        kwargs=kwargs,
        daemon=True
    ).start()

    return {"status": "success", "message": f"Triggered job '{job.name}' immediately."}


@app.get("/api/schedules/history", tags=["Task Scheduler"])
def get_schedule_history():
    """Returns execution logs and outputs of past scheduled background runs."""
    return {
        "status": "success",
        "history": scheduled_history
    }


# =====================================================================
# Cognitive Memory & Adaptive Persona Impression Endpoints
# =====================================================================

@app.get("/api/memory/profile", tags=["Cognitive Memory"])
def get_cognitive_memory_profile():
    """Returns the synthesized user impression profile, learned preferences, and active projects."""
    profile = memory.get_profile_data()
    return {
        "status": "success",
        "profile": profile
    }


@app.get("/api/memory/history", tags=["Cognitive Memory"])
def get_memory_chat_history(session_id: str = "default", limit: int = 50):
    """Returns persistent SQLite chat history for conversational continuity."""
    history = db_manager.get_recent_chat_history(session_id=session_id, limit=limit)
    return {
        "status": "success",
        "session_id": session_id,
        "history": history
    }


@app.post("/api/memory/clear", tags=["Cognitive Memory"])
def clear_cognitive_memory(session_id: Optional[str] = None):
    """Clears multi-turn conversation memory history."""
    memory.clear_memory(session_id=session_id)
    return {
        "status": "success",
        "message": "Cognitive conversation memory cleared successfully."
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
