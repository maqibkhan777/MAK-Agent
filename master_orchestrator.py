import os
import sys
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Core dynamic tool engine imports
from dynamic_tool_loader import load_dynamic_tools, reload_dynamic_tools, list_dynamic_tools_catalog, get_dynamic_tool
from surgeon_agent import synthesize_dynamic_tool, SANDBOX_DIR, restricted_file_writer, sandbox_test_runner
from main import run_agency, app_graph, AgencyState


class ToolProposalPayload(BaseModel):
    """Structured HITL Interrupt Payload returned to Node/React frontend for user approval."""
    status: str = Field(default="AWAITING_APPROVAL", description="Approval status: AWAITING_APPROVAL, APPROVED, or REJECTED")
    tool_name: str = Field(..., description="Name of the proposed new dynamic tool")
    file_name: str = Field(..., description="Filename created in dynamic_tools/")
    file_path: str = Field(..., description="Absolute path inside sandbox")
    code_content: str = Field(..., description="Python source code of the tool")
    surgeon_report: str = Field(..., description="Subprocess sandbox test output and validation notes")


# =====================================================================
# HITL Tool Expansion Orchestrator Pipeline
# =====================================================================
def propose_and_sandbox_tool(tool_name: str, requirement: str) -> Dict[str, Any]:
    """
    Step 1 & 2: Runs the Surgeon Agent to build & test code in the sandbox.
    Pauses with an HITL Interrupt Payload before dynamic loading is allowed.
    """
    print(f"\n[Master Orchestrator] Invoking Surgeon Agent for Tool: '{tool_name}'...")
    proposal = synthesize_dynamic_tool(tool_name=tool_name, requirement_prompt=requirement)

    payload = ToolProposalPayload(
        status="AWAITING_APPROVAL",
        tool_name=proposal["tool_name"],
        file_name=proposal["file_name"],
        file_path=proposal["file_path"],
        code_content=proposal["code_content"],
        surgeon_report=proposal["surgeon_report"]
    )

    print(f"\n" + "=" * 70)
    print(f"🔒 [HITL INTERRUPT] Dynamic Tool Generated: '{proposal['tool_name']}'")
    print(f"File Location : {proposal['file_path']}")
    print(f"Execution Gate: Awaiting Human Authorization to Ingest Script into Registry.")
    print("=" * 70 + "\n")

    return payload.model_dump()


def approve_and_deploy_tool(tool_name: str, approved: bool = True) -> Dict[str, Any]:
    """
    Step 3: Human-in-the-Loop Resolution Gate.
    If approved, executes dynamic importlib loading to ingest tool into active registry.
    If rejected, removes the unverified file from dynamic_tools/.
    """
    safe_name = tool_name.replace(".py", "")
    target_path = os.path.join(SANDBOX_DIR, f"{safe_name}.py")

    if not approved:
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass
        return {
            "status": "REJECTED",
            "message": f"Tool '{tool_name}' proposal was rejected by human operator. Sandbox file removed.",
            "active_tools": [t["name"] for t in list_dynamic_tools_catalog()]
        }

    # Ingest and reload into runtime tool registry
    active_tools = reload_dynamic_tools()
    deployed_names = [getattr(t, "name", str(t)) for t in active_tools]

    return {
        "status": "DEPLOYED",
        "message": f"Tool '{tool_name}' approved by human operator and successfully registered into active tool registry.",
        "deployed_tool": safe_name,
        "total_active_tools": len(active_tools),
        "active_tools": deployed_names
    }


# =====================================================================
# Standalone CLI Demo
# =====================================================================
if __name__ == "__main__":
    print("=== MAK Master Orchestrator — Self-Expanding Tool Architecture Demo ===")
    
    # 1. Propose & test in sandbox
    test_requirement = "Create a function named `calculate_compound_interest(principal, rate, years, compounds_per_year=1)` that returns total accrued amount."
    proposal = propose_and_sandbox_tool("compound_interest_calculator", test_requirement)
    
    print("\n--- Generated Tool Payload ---")
    print(f"Tool: {proposal['tool_name']}")
    print(f"Code Length: {len(proposal['code_content'])} chars")
    
    # 2. Simulate HITL Approval
    print("\n[Simulating HITL User Approval] Deploying to active registry...")
    deployment = approve_and_deploy_tool(proposal["tool_name"], approved=True)
    print("Deployment Result:", deployment)
