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

# Initialize debugpy DAP listener for IDE live attachment
def init_debugpy_listener(host: str = "127.0.0.1", port: int = 5678):
    """Initializes debugpy DAP bridge on startup for IDE process attachment without restarts."""
    try:
        import debugpy
        debugpy.listen((host, port))
        print(f"🐞 [MAK Server] debugpy listening on {host}:{port} (DAP bridge ready for IDE attach)")
    except RuntimeError:
        print(f"ℹ️ [MAK Server] debugpy listener already running on {host}:{port}")
    except Exception as e:
        print(f"⚠️ [MAK Server] debugpy initialization notice: {e}")

init_debugpy_listener()

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


class CognifyRequest(BaseModel):
    directory_path: str = "./company_knowledge_base"

class MemoryQueryRequest(BaseModel):
    query: str
    search_type: str = "GRAPH"


@app.post("/api/memory/cognify", tags=["Cognee Knowledge Graph"])
async def trigger_cognify_knowledge_base(req: CognifyRequest):
    """Ingests documentation from directory and builds persistent Cognee Knowledge Graph + LanceDB index."""
    try:
        from memory_layer import cognify_knowledge_base
        summary = await cognify_knowledge_base(req.directory_path)
        return {
            "status": "success",
            "message": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search", tags=["Cognee Knowledge Graph"])
def search_cognified_memory(req: MemoryQueryRequest):
    """Queries the persistent Cognee Knowledge Graph and vector database."""
    try:
        from memory_layer import query_memory
        result = query_memory(query=req.query, search_type=req.search_type)
        return {
            "status": "success",
            "query": req.query,
            "search_type": req.search_type,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Ensure debugpy listener is active when FastAPI initializes."""
    init_debugpy_listener()


# =====================================================================
# Human-in-the-Loop (HITL) Code & Dynamic Tool Approval Endpoints
# =====================================================================
class ToolProposalRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the dynamic tool to propose")
    requirement: str = Field(..., description="Functional requirements and implementation prompt")

class ToolApprovalRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the dynamic tool to approve or reject")
    approved: bool = Field(default=True, description="True to deploy tool to registry, False to discard")

class CodeValidationRequest(BaseModel):
    code: str = Field(..., description="Raw Python code to validate syntax")

class CodeApplyRequest(BaseModel):
    file_path: str = Field(..., description="Target file path to write")
    code_content: str = Field(..., description="Proposed Python code content")
    approved: bool = Field(default=False, description="Explicit Human-in-the-Loop approval boolean flag")


@app.post("/api/tools/propose", tags=["HITL Code & Tool Safety"])
def propose_dynamic_tool_endpoint(req: ToolProposalRequest):
    """
    Synthesizes and tests a tool in sandbox containment.
    Returns a structured payload with status AWAITING_APPROVAL, halting execution until approved.
    """
    try:
        from master_orchestrator import propose_and_sandbox_tool
        payload = propose_and_sandbox_tool(tool_name=req.tool_name, requirement=req.requirement)
        return {
            "status": "success",
            "proposal": payload
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool proposal failed: {e}")


@app.post("/api/tools/approve", tags=["HITL Code & Tool Safety"])
def approve_dynamic_tool_endpoint(req: ToolApprovalRequest):
    """
    HITL Approval Gate: Explicit human authorization to ingest a verified sandboxed script
    into the active runtime tool registry or reject and remove it.
    """
    try:
        from master_orchestrator import approve_and_deploy_tool
        result = approve_and_deploy_tool(tool_name=req.tool_name, approved=req.approved)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool approval resolution failed: {e}")


@app.get("/api/tools/catalog", tags=["HITL Code & Tool Safety"])
def get_tools_catalog_endpoint():
    """Lists all dynamically created and approved tools in the active catalog."""
    try:
        from dynamic_tool_loader import list_dynamic_tools_catalog
        catalog = list_dynamic_tools_catalog()
        return {
            "status": "success",
            "tools": catalog,
            "count": len(catalog)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tool catalog: {e}")


@app.post("/api/hitl/code/validate", tags=["HITL Code & Tool Safety"])
def validate_code_syntax_endpoint(req: CodeValidationRequest):
    """Validates Python code syntax using AST parser before proposing changes."""
    try:
        from engineering_department import python_syntax_checker
        validation = python_syntax_checker.func(req.code)
        is_valid = "Syntax is valid." in validation
        return {
            "status": "success" if is_valid else "invalid",
            "valid": is_valid,
            "details": validation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Syntax validation failed: {e}")


@app.post("/api/hitl/code/apply", tags=["HITL Code & Tool Safety"])
def apply_code_change_hitl_endpoint(req: CodeApplyRequest):
    """
    Enforces strict Human-in-the-Loop approval gate before writing code changes to disk.
    Rejects requests where approved is False.
    """
    if not req.approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HITL Gate Blocked: Explicit human approval ('approved': true) is required before code changes can be written to disk."
        )
    try:
        from engineering_department import python_syntax_checker
        syntax_res = python_syntax_checker.func(req.code_content)
        if "Syntax is valid." not in syntax_res:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code syntax check failed: {syntax_res}"
            )
        
        # Write file safely
        target_abs = os.path.abspath(req.file_path)
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(req.code_content)
        return {
            "status": "success",
            "message": f"HITL Approved: File successfully written to {req.file_path}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)

