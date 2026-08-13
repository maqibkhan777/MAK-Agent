import sys
import os

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from crewai import Agent, Task, Crew
from crewai_tools import FileReadTool, FileWriterTool
from finance_department import get_resilient_llm

def trigger_rescue_mission(error_traceback: str) -> str:
    """
    Autonomous debugging workflow triggered upon runtime exception.
    Doctor analyzes the stack trace -> Surgeon fixes the bug.
    Safely handles non-interactive environments (e.g. Streamlit) to avoid EOF input crashes.
    """
    llm = get_resilient_llm()
    file_read = FileReadTool()
    file_write = FileWriterTool()

    # Safe TTY check: Only request terminal human input if attached to an interactive shell
    is_interactive_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty()

    # 1. Doctor Agent (Diagnostician)
    doctor = Agent(
        role="Lead Systems Debugger",
        goal="Read Python traceback errors and explain exactly what broke in plain English without jargon.",
        backstory="You are Lead Systems Debugger, an expert AI diagnostician specializing in parsing stack traces, identifying root causes of exceptions, and explaining runtime failures in clear, concise language.",
        tools=[file_read],
        verbose=True,
        llm=llm
    )

    # 2. Surgeon Agent (Code Fixer)
    surgeon = Agent(
        role="Senior Software Engineer",
        goal="Read the faulty .py file, fix the exact line causing the crash, and rewrite the file securely.",
        backstory="You are Senior Software Engineer, a master Python developer who inspects buggy source code, writes robust code patches, and rewrites broken files securely.",
        tools=[file_read, file_write],
        verbose=True,
        llm=llm
    )

    # 3. Tasks
    diagnosis_task = Task(
        description=f"Analyze the following Python error traceback:\n\n{error_traceback}\n\nIdentify the exact file path, line number, and root cause of the crash. Explain what broke in clear, plain English.",
        expected_output="A clear diagnosis detailing the root cause of the crash, target file path, line number, and proposed fix.",
        agent=doctor
    )

    surgeon_task = Task(
        description=f"Based on the Doctor's diagnosis, read the target file causing the failure, apply the exact code fix required to resolve the exception, and rewrite the file safely.",
        expected_output="A summary of the precise code modifications applied to fix the bug.",
        agent=surgeon,
        human_input=is_interactive_tty
    )

    # 4. Rescue Crew
    rescue_crew = Crew(
        agents=[doctor, surgeon],
        tasks=[diagnosis_task, surgeon_task],
        memory=True,
        embedder={"provider": "huggingface", "config": {"model": "all-MiniLM-L6-v2"}},
        verbose=True
    )

    result = rescue_crew.kickoff()
    return str(result)
