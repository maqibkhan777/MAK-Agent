import sys
import os
import concurrent.futures
from typing import Optional

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

if not os.getenv("CHROMA_HUGGINGFACE_API_KEY"):
    os.environ["CHROMA_HUGGINGFACE_API_KEY"] = "dummy"

from crewai import Agent, Task, Crew
from crewai_tools import FileReadTool, FileWriterTool
from finance_department import get_resilient_llm

EMBEDDER_CONFIG = {"provider": "huggingface", "config": {"model": "all-MiniLM-L6-v2"}}


def trigger_rescue_mission(
    error_traceback: str,
    task_context: str = "",
    target_file: Optional[str] = None
) -> str:
    """
    Autonomous debugging & self-healing workflow triggered upon runtime exceptions or tool failures.
    - Doctor: Analyzes stack traces, system logs, or tool failures to pinpoint the root cause.
    - Surgeon: Reads faulty source files, applies exact code fixes/patches, or formulates recovery solutions.
    - Safely executes across both interactive terminal and headless FastAPI/Electron environments.
    """
    print("\n" + "=" * 78)
    print(" 🚨 [SELF-HEALER ACTIVATED] Autonomous Rescue Mission Initiated...")
    print("=" * 78 + "\n")

    llm = get_resilient_llm()
    file_read = FileReadTool()
    file_write = FileWriterTool()

    context_str = f"\nTask Context: '{task_context}'" if task_context else ""
    target_str = f"\nTarget File: '{target_file}'" if target_file else ""

    # 1. Doctor Agent (Root Cause Diagnostician)
    doctor = Agent(
        role="Lead Systems Debugger & Diagnostician",
        goal="Parse execution failures, tool errors, or Python tracebacks and explain exactly why the failure occurred in structured, plain English.",
        backstory=(
            "You are the Lead Systems Debugger for MAK Enterprise AI Agency. You excel at dissecting "
            "runtime stack traces, tool execution timeouts, command line failures, and environment errors. "
            "You isolate root causes with mathematical precision without unnecessary jargon."
        ),
        tools=[file_read],
        verbose=True,
        llm=llm
    )

    # 2. Surgeon Agent (Code Fixer & System Remediation Specialist)
    surgeon = Agent(
        role="Senior Software Engineer & System Healer",
        goal="Fix the root cause of the crash by patching source code or providing an actionable, step-by-step remediation plan.",
        backstory=(
            "You are the Senior Software Engineer & System Healer. When code breaks, you inspect the files, "
            "write clean, error-free patches, and fix the broken logic. When system or tool commands fail, "
            "you formulate the exact corrective commands and architectural adjustments."
        ),
        tools=[file_read, file_write],
        verbose=True,
        llm=llm
    )

    # 3. Tasks
    diagnosis_task = Task(
        description=(
            f"Analyze the following failure details and error logs:{context_str}{target_str}\n\n"
            f"FAILURE LOG / ERROR TRACEBACK:\n```\n{error_traceback}\n```\n\n"
            "Identify: 1) The exact cause of the failure, 2) Target components or files involved, "
            "and 3) The required technical remediation."
        ),
        expected_output="A structured diagnosis detailing root cause, failing components, and required solution.",
        agent=doctor
    )

    surgeon_task = Task(
        description=(
            "Based on the Doctor's diagnosis, execute the remediation. If a specific Python file is broken "
            "and needs modification, read it with FileReadTool, apply the fix, and rewrite it with FileWriterTool. "
            "If the issue is environment/tool-related, provide the complete, ready-to-run resolution report."
        ),
        expected_output="A comprehensive self-healing summary detailing the applied patch or actionable recovery solution.",
        agent=surgeon
    )

    # 4. Rescue Crew
    rescue_crew = Crew(
        agents=[doctor, surgeon],
        tasks=[diagnosis_task, surgeon_task],
        memory=False,
        verbose=True
    )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(rescue_crew.kickoff)
            result = str(future.result())
    except Exception as e:
        print(f"[Self-Healing Execution Notice]: {e}")
        result = str(rescue_crew.kickoff())

    formatted_result = (
        f"### 🛠️ Autonomous Self-Healing Report\n\n"
        f"**Failure Detected**: `{task_context or 'System Operation'}`\n\n"
        f"{result}\n"
    )
    return formatted_result
