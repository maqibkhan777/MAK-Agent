"""
Automated Verification Suite for MCP Debugger Bridge & HITL Integration.
"""

import os
import sys
import json
import traceback

# Configure UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

print("============================================================")
print("🧪 RUNNING MCP DEBUGGER BRIDGE VERIFICATION TESTS")
print("============================================================")

# Test 1: MCP Debug Server & Tool Registry
print("\n[TEST 1] Testing FastMCP Server & Exposed Tools...")
import mcp_debug_server
from mcp_debug_server import (
    mcp,
    bridge_store,
    record_debug_event,
    start_debug_listener,
    inspect_runtime_state,
    evaluate_expression_in_scope,
    get_debug_bridge_events,
    trigger_ide_breakpoint,
    inspect_variable_value
)

tools = [t.name for t in mcp._tool_manager.list_tools()]
print(f"Registered FastMCP Tools: {tools}")
assert "start_debug_listener" in tools, "Missing start_debug_listener tool"
assert "inspect_runtime_state" in tools, "Missing inspect_runtime_state tool"
assert "evaluate_expression_in_scope" in tools, "Missing evaluate_expression_in_scope tool"
assert "get_debug_bridge_events" in tools, "Missing get_debug_bridge_events tool"
print("✅ Test 1 Passed: FastMCP server properly configured with all tools.")

# Test 2: Debugpy Listener & Runtime State
print("\n[TEST 2] Testing debugpy listener & runtime state inspection...")
listener_res = start_debug_listener(port=5678, host="127.0.0.1", wait_for_client=False)
print("Listener Response:\n", listener_res)
assert "debugpy listener" in listener_res.lower(), "debugpy listener failed to start"

runtime_snapshot = inspect_runtime_state()
print("Runtime Snapshot Summary:\n", "\n".join(runtime_snapshot.splitlines()[:10]))
assert "MAK-AGENT RUNTIME STATE SNAPSHOT" in runtime_snapshot, "Runtime snapshot format error"
assert "PID" in runtime_snapshot, "PID missing from snapshot"
print("✅ Test 2 Passed: debugpy listener active and runtime state inspection functional.")

# Test 3: Expression Evaluation in Scope
print("\n[TEST 3] Testing evaluate_expression_in_scope...")
eval_res = evaluate_expression_in_scope("2 + 2")
print("Evaluation Result (2+2):\n", eval_res)
assert "4" in eval_res, "Evaluation failed for 2+2"

eval_sys = evaluate_expression_in_scope("sys.version_info.major")
print("Evaluation Result (Python Major):\n", eval_sys)
assert "3" in eval_sys, "Evaluation failed for sys.version_info.major"
print("✅ Test 3 Passed: Expression evaluation tool working properly.")

# Test 4: Agent Breakpoint & Variable Inspection Tools
print("\n[TEST 4] Testing trigger_ide_breakpoint & inspect_variable_value...")
bp_res = trigger_ide_breakpoint.func(
    file_path="d:/MAK-agent/test_script.py",
    line_number=42,
    reason="AssertionError in calculation"
)
print("Breakpoint Tool Output:\n", bp_res)
assert "127.0.0.1:5678" in bp_res or "SUCCESS" in bp_res, "Breakpoint tool returned unexpected output"

var_res = inspect_variable_value.func(
    variable_name="os.name",
    scope="global"
)
print("Variable Inspection Tool Output:\n", var_res)
assert "nt" in var_res or "posix" in var_res, "Variable inspection failed"
print("✅ Test 4 Passed: Diagnostic agent tools functioning.")

# Test 5: Engineering Department Agent Tool Binding
print("\n[TEST 5] Verifying Engineering Department agents have debugger tools bound...")
import engineering_department
from engineering_department import EngineeringDepartment

dept = EngineeringDepartment()
surgeon = dept.create_code_surgeon()
qa = dept.create_qa_tester()

surgeon_tool_names = [t.name for t in surgeon.tools]
qa_tool_names = [t.name for t in qa.tools]

print(f"Code Surgeon Tools: {surgeon_tool_names}")
print(f"QA Tester Tools: {qa_tool_names}")

assert "Trigger IDE Breakpoint" in surgeon_tool_names, "Code Surgeon missing Trigger IDE Breakpoint"
assert "Inspect Variable Value" in surgeon_tool_names, "Code Surgeon missing Inspect Variable Value"
assert "HITL File Writer" in surgeon_tool_names, "Code Surgeon missing HITL File Writer"
assert "Python Syntax Checker" in surgeon_tool_names, "Code Surgeon missing Python Syntax Checker"

assert "Trigger IDE Breakpoint" in qa_tool_names, "QA Tester missing Trigger IDE Breakpoint"
assert "Inspect Variable Value" in qa_tool_names, "QA Tester missing Inspect Variable Value"
print("✅ Test 5 Passed: Engineering department agents successfully equipped with debugger & HITL tools.")

# Test 6: Self-Healing Traceback Parsing & Event Routing
print("\n[TEST 6] Testing self-healing traceback parsing and bridge routing...")
simulated_tb = """
Traceback (most recent call last):
  File "d:\\MAK-agent\\dynamic_tools\\sample_tool.py", line 87, in compute_rate
    return numerator / denominator
ZeroDivisionError: division by zero
"""

ev = record_debug_event(
    event_type="SIMULATED_TEST_ROUTED",
    file_path="d:\\MAK-agent\\dynamic_tools\\sample_tool.py",
    line_number=87,
    error_type="ZeroDivisionError",
    traceback_str=simulated_tb
)
assert ev["id"] > 0, "Event recording failed"
assert ev["file_path"] == "d:\\MAK-agent\\dynamic_tools\\sample_tool.py"
assert ev["line_number"] == 87

events_json = get_debug_bridge_events(limit=5)
print("Bridge Events JSON (tail):\n", events_json)
assert "ZeroDivisionError" in events_json, "Event missing from bridge events store"
print("✅ Test 6 Passed: Debug bridge event routing verified.")

# Test 7: IDE Configuration Files & Antigravity MCP Workspace
print("\n[TEST 7] Verifying IDE Configuration Files (.antigravity/mcp.json, .vscode/launch.json, .vscode/mcp.json, mcp.json)...")
assert os.path.exists(".antigravity/mcp.json"), ".antigravity/mcp.json does not exist"
assert os.path.exists(".vscode/launch.json"), ".vscode/launch.json does not exist"
assert os.path.exists(".vscode/mcp.json"), ".vscode/mcp.json does not exist"
assert os.path.exists("mcp.json"), "mcp.json does not exist"

with open(".antigravity/mcp.json", "r", encoding="utf-8") as f:
    antigravity_mcp = json.load(f)
    assert "mak-agent-debugger" in antigravity_mcp.get("mcpServers", {}), "mak-agent-debugger missing in .antigravity/mcp.json"

with open(".vscode/launch.json", "r", encoding="utf-8") as f:
    launch_data = json.load(f)
    config_names = [c.get("name") for c in launch_data.get("configurations", [])]
    assert "Attach AI Agent Debugger" in config_names, "'Attach AI Agent Debugger' missing in launch.json"
    assert any(c.get("port") == 5678 or c.get("connect", {}).get("port") == 5678 for c in launch_data.get("configurations", [])), "debugpy port 5678 missing in launch.json"

with open(".vscode/mcp.json", "r", encoding="utf-8") as f:
    mcp_data = json.load(f)
    assert "mak-agent-debugger" in mcp_data.get("mcpServers", {}), "mak-agent-debugger missing in .vscode/mcp.json"

with open("mcp.json", "r", encoding="utf-8") as f:
    mcp_root_data = json.load(f)
    assert "mak-agent-debugger" in mcp_root_data.get("mcpServers", {}), "mak-agent-debugger missing in mcp.json"

# Verify server.py and autonomous_worker.py startup DAP init
import server
assert hasattr(server, "init_debugpy_listener"), "server.py missing init_debugpy_listener"
import autonomous_worker
assert hasattr(autonomous_worker, "init_debugpy_listener"), "autonomous_worker.py missing init_debugpy_listener"
assert hasattr(autonomous_worker, "verify_hitl_code_safety_gate"), "autonomous_worker.py missing verify_hitl_code_safety_gate"

print("✅ Test 7 Passed: IDE launch & MCP configurations validated with full DAP + HITL gates.")

print("\n" + "=" * 60)
print("🎉 ALL 7 VERIFICATION TESTS PASSED SUCCESSFULLY!")
print("============================================================")
