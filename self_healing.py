import sys
import os
import re
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
from engineering_department import hitl_file_writer, python_syntax_checker
from mcp_debug_server import (
    trigger_ide_breakpoint,
    inspect_variable_value,
    record_debug_event
)

EMBEDDER_CONFIG = {"provider": "huggingface", "config": {"model": "all-MiniLM-L6-v2"}}


def trigger_rescue_mission(
    error_traceback: str,
    task_context: str = "",
    target_file: Optional[str] = None
) -> str:
    """
    Autonomous debugging & self-healing workflow triggered upon runtime exceptions or tool failures.
    - Doctor: Analyzes stack traces, inspects runtime variables, triggers IDE breakpoints, and diagnoses root causes.
    - Surgeon: Reads faulty source files, applies exact code fixes/patches with Human-in-the-Loop (HITL) protection.
    - MCP Debugger Bridge: Automatically routes failing file path, line number, and stack trace to the IDE workspace.
    """
    print("\n" + "=" * 78)
    print(" 🚨 [SELF-HEALER ACTIVATED] Autonomous Rescue Mission Initiated via MCP Debug Bridge...")
    print("=" * 78 + "\n")

    # 1. Parse traceback details for MCP Bridge Routing
    parsed_file = target_file or ""
    parsed_line = None
    parsed_error = "ExecutionError"

    file_matches = re.findall(r'File\s+"([^"]+)",\s+line\s+(\d+)', error_traceback)
    if file_matches:
        last_match = file_matches[-1]
        if not parsed_file:
            parsed_file = last_match[0]
        try:
            parsed_line = int(last_match[1])
        except (ValueError, TypeError):
            pass

    err_matches = re.findall(r'([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception|AssertionError):\s*(.*)', error_traceback)
    if err_matches:
        parsed_error = err_matches[-1][0]

    # 2. Route diagnostic metadata through MCP Debugger Bridge
    bridge_event = record_debug_event(
        event_type="SELF_HEALING_FAILURE_ROUTED",
        file_path=parsed_file,
        line_number=parsed_line,
        error_type=parsed_error,
        traceback_str=error_traceback,
        details={"task_context": task_context}
    )

    print(f"📡 [MCP BRIDGE ROUTED] Event #{bridge_event['id']}: {parsed_error} at {parsed_file}:{parsed_line or 'N/A'}")

    llm = get_resilient_llm()
    file_read = FileReadTool()
    file_write = FileWriterTool()

    context_str = f"\nTask Context: '{task_context}'" if task_context else ""
    target_str = f"\nTarget File: '{parsed_file or target_file or 'N/A'}' (Line: {parsed_line or 'N/A'})"

    # 3. Doctor Agent (Root Cause Diagnostician & Live Runtime Inspector)
    doctor = Agent(
        role="Lead Systems Debugger & Diagnostician",
        goal="Parse execution failures, inspect live variables, trigger IDE breakpoints if needed, and pinpoint root causes with mathematical precision.",
        backstory=(
            "You are the Lead Systems Debugger for MAK Enterprise AI Agency connected directly to the IDE "
            "workspace via Model Context Protocol (MCP) and debugpy. You excel at dissecting runtime tracebacks, "
            "inspecting variables using 'Inspect Variable Value', and triggering IDE breakpoints when needed."
        ),
        tools=[file_read, trigger_ide_breakpoint, inspect_variable_value],
        verbose=True,
        llm=llm
    )

    # 4. Surgeon Agent (Code Fixer with Human-in-the-Loop Safety)
    surgeon = Agent(
        role="Senior Software Engineer & System Healer",
        goal="Fix the root cause of crashes by patching source code with syntax validation and Human-in-the-Loop (HITL) approval.",
        backstory=(
            "You are the Senior Software Engineer & System Healer. When code breaks, you inspect the files, "
            "validate syntax with 'Python Syntax Checker', and apply fixes using 'HITL File Writer' so that "
            "all code patches are safely confirmed before saving to disk."
        ),
        tools=[file_read, hitl_file_writer, python_syntax_checker, inspect_variable_value, file_write],
        verbose=True,
        llm=llm
    )

    # 5. Tasks
    diagnosis_task = Task(
        description=(
            f"Analyze the following failure details and error logs:{context_str}{target_str}\n\n"
            f"MCP BRIDGE EVENT ID: #{bridge_event['id']}\n"
            f"ERROR TYPE: {parsed_error}\n"
            f"FAILURE LOG / ERROR TRACEBACK:\n```\n{error_traceback}\n```\n\n"
            "Identify: 1) The exact cause of the failure, 2) Target components or files involved, "
            "and 3) The required technical remediation. Use 'Inspect Variable Value' or 'Trigger IDE Breakpoint' if needed."
        ),
        expected_output="A structured diagnosis detailing root cause, failing components, and required solution.",
        agent=doctor
    )

    surgeon_task = Task(
        description=(
            "Based on the Doctor's diagnosis, execute the remediation. If a specific Python file is broken "
            "and needs modification, read it with FileReadTool, validate changes with 'Python Syntax Checker', "
            "and write the fix using 'HITL File Writer' (or provide clear diffs). "
            "If the issue is environment/tool-related, provide the complete, ready-to-run resolution report."
        ),
        expected_output="A comprehensive self-healing summary detailing the applied patch or actionable recovery solution.",
        agent=surgeon
    )

    # 6. Rescue Crew
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
        f"### 🛠️ Autonomous Self-Healing Report (MCP Debugger Bridge)\n\n"
        f"**Failure Detected**: `{task_context or 'System Operation'}`\n"
        f"**MCP Event**: `#{bridge_event['id']} ({parsed_error})` at `{parsed_file}:{parsed_line or 'N/A'}`\n\n"
        f"{result}\n"
    )
    return formatted_result

