import os
import sys
import subprocess
from typing import Dict, Any, Optional
from crewai import Agent, Task, Crew
from crewai.tools import tool

from finance_department import get_resilient_llm

# Enforce strict sandbox root path
SANDBOX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dynamic_tools"))
os.makedirs(SANDBOX_DIR, exist_ok=True)


# =====================================================================
# 1. Restricted Sandbox File Writer Tool
# =====================================================================
@tool("Restricted File Writer")
def restricted_file_writer(file_name: str, code_content: str) -> str:
    """
    Security-Enforced Sandbox File Writer Tool.
    Strictly verifies destination file paths to ensure new Python tools can ONLY
    be written inside the isolated 'dynamic_tools/' sandbox directory.

    Args:
        file_name: Target filename (must end in .py, e.g. 'currency_converter.py').
        code_content: Complete, self-contained Python source code implementation.
    """
    try:
        raw_name = file_name.strip()
        if ".." in raw_name or raw_name.startswith("/") or raw_name.startswith("\\") or (len(raw_name) > 1 and raw_name[1] == ":"):
            target_path = os.path.abspath(os.path.join(SANDBOX_DIR, raw_name))
            common_path = os.path.commonpath([SANDBOX_DIR, target_path])
            if common_path != SANDBOX_DIR:
                return (
                    f"SECURITY VIOLATION: Access Denied. Target path '{target_path}' "
                    f"escapes the dynamic tools sandbox root '{SANDBOX_DIR}'."
                )

        base_name = os.path.basename(raw_name)
        if not base_name.endswith(".py"):
            base_name += ".py"

        target_path = os.path.abspath(os.path.join(SANDBOX_DIR, base_name))
        common_path = os.path.commonpath([SANDBOX_DIR, target_path])
        if common_path != SANDBOX_DIR:
            return (
                f"SECURITY VIOLATION: Access Denied. Target path '{target_path}' "
                f"escapes the dynamic tools sandbox root '{SANDBOX_DIR}'."
            )

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code_content)

        return (
            f"SUCCESS: File successfully written to sandbox: {target_path}\n"
            f"Bytes Written: {len(code_content)} chars. Ready for Sandbox Test."
        )
    except Exception as e:
        return f"ERROR: Failed writing file to sandbox: {e}"


# =====================================================================
# 2. Subprocess Sandbox Test Tool
# =====================================================================
@tool("Sandbox Test Runner")
def sandbox_test_runner(file_name: str) -> str:
    """
    Isolated Subprocess Testing Tool.
    Executes a newly written script inside an isolated Python subprocess,
    verifying AST compilation, syntax correctness, and runtime stability.
    Captures full stdout/stderr streams.

    Args:
        file_name: Name of the .py file in dynamic_tools/ to test (e.g. 'currency_converter.py').
    """
    try:
        base_name = os.path.basename(file_name.strip())
        target_path = os.path.abspath(os.path.join(SANDBOX_DIR, base_name))

        if not os.path.exists(target_path):
            return f"ERROR: Target file does not exist in sandbox: {target_path}"

        # 1. AST Syntax Verification Check (py_compile)
        compile_res = subprocess.run(
            [sys.executable, "-m", "py_compile", target_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if compile_res.returncode != 0:
            return (
                f"SYNTAX ERROR DETECTED in {base_name}:\n"
                f"{compile_res.stderr}\n"
                "Please rewrite the code to fix these syntax errors."
            )

        # 2. Dry-Run Subprocess Smoke Execution (with stdin disabled to prevent blocking input() calls)
        exec_res = subprocess.run(
            [sys.executable, target_path],
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
            cwd=SANDBOX_DIR
        )

        status = "PASSED" if exec_res.returncode == 0 else f"FAILED (Exit Code {exec_res.returncode})"
        output_report = (
            f"=== Sandbox Test Report for '{base_name}' ===\n"
            f"• Syntax Check: PASSED (AST Valid)\n"
            f"• Execution Status: {status}\n"
            f"• Standard Output:\n{exec_res.stdout if exec_res.stdout.strip() else '(No output)'}\n"
            f"• Standard Error:\n{exec_res.stderr if exec_res.stderr.strip() else '(None)'}\n"
        )
        return output_report
    except subprocess.TimeoutExpired:
        return f"ERROR: Script execution timed out (exceeded 10 seconds limit)."
    except Exception as e:
        return f"ERROR running sandbox test: {e}"


# =====================================================================
# 3. Surgeon Agent Definition
# =====================================================================
def create_surgeon_agent(llm: Optional[Any] = None) -> Agent:
    """
    Constructs the Autonomous Tool Surgeon Agent.
    Equipped with RestrictedFileWriteTool and SandboxTestTool to design,
    implement, test, and package self-expanding tool modules.
    """
    active_llm = llm if llm is not None else get_resilient_llm()

    return Agent(
        role="Autonomous Tool Surgeon",
        goal=(
            "Design, write, and verify self-contained, production-ready Python tool modules. "
            "You MUST write files using the 'Restricted File Writer' tool (strictly in dynamic_tools/) "
            "and verify them using the 'Sandbox Test Runner' tool before finalizing. "
            "Never write blocking terminal input() statements; design clean callable API functions."
        ),
        backstory=(
            "You are an elite AI Systems & Metaprogramming Specialist. You expand the agency's cognitive toolset "
            "by dynamically generating clean, modular Python tools. Each tool module must provide standard callable "
            "functions with type annotations, docstrings, and an automated self-test block. "
            "You strictly enforce sandbox containment and verify zero syntax errors via subprocess testing."
        ),
        tools=[restricted_file_writer, sandbox_test_runner],
        verbose=True,
        memory=False,
        llm=active_llm
    )


def synthesize_dynamic_tool(tool_name: str, requirement_prompt: str) -> Dict[str, Any]:
    """
    Executes the Surgeon Agent pipeline to generate, write, and test a new dynamic tool.
    Returns a structured payload ready for HITL approval.
    """
    surgeon = create_surgeon_agent()

    safe_filename = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in tool_name.lower().strip())
    if not safe_filename.endswith(".py"):
        safe_filename += ".py"

    task_design = Task(
        description=(
            f"Design and implement a robust Python tool module named '{safe_filename}' satisfying this requirement:\n"
            f"'{requirement_prompt}'\n\n"
            "Requirements for the code:\n"
            "1. Write clean, self-contained Python code with full type hints and comprehensive docstrings.\n"
            "2. Define the main capability as a standalone function decorated with @tool if applicable, or a clean top-level callable.\n"
            "3. Include an `if __name__ == '__main__':` block that demonstrates and self-tests the function.\n"
            "4. Step 1: Use 'Restricted File Writer' to save the code to dynamic_tools/.\n"
            "5. Step 2: Use 'Sandbox Test Runner' to verify syntax validity and run the self-test.\n"
            "6. Step 3: Present the final verified script and test report."
        ),
        expected_output="Final synthesis containing file_name, full verified python code, and sandbox test confirmation.",
        agent=surgeon
    )

    crew = Crew(
        agents=[surgeon],
        tasks=[task_design],
        verbose=True,
        memory=False
    )

    result_text = str(crew.kickoff())
    file_path = os.path.join(SANDBOX_DIR, safe_filename)

    code_content = ""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()

    return {
        "status": "PROPOSED",
        "tool_name": safe_filename.replace(".py", ""),
        "file_name": safe_filename,
        "file_path": file_path,
        "code_content": code_content,
        "surgeon_report": result_text
    }
