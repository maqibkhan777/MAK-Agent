"""
MCP Debugger Bridge Server for MAK-Agent.
Connects MAK-Agent runtime ecosystem to the IDE workspace via Model Context Protocol (FastMCP) and debugpy.

Exposes:
- FastMCP Server ('mak-debugger') with tools:
    * start_debug_listener
    * inspect_runtime_state
    * evaluate_expression_in_scope
    * get_debug_bridge_events
- LangChain / CrewAI diagnostic tools:
    * trigger_ide_breakpoint
    * inspect_variable_value
- Debug Bridge Event Store for routing error tracebacks, file paths, and line numbers.
"""

import sys
import os
import io
import time
import json
import inspect
import threading
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

# UTF-8 Encoding configuration for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Import debugpy & MCP FastMCP
import debugpy
from mcp.server.fastmcp import FastMCP
from crewai.tools import tool


# =====================================================================
# 1. Debug Bridge Telemetry & Event Store
# =====================================================================
class DebugBridgeStore:
    """
    Thread-safe in-memory store for tracking debug events, caught tracebacks,
    file locations, line numbers, and IDE breakpoint triggers across MAK-Agent.
    """
    _instance: Optional["DebugBridgeStore"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DebugBridgeStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DebugBridgeStore, cls).__new__(cls)
                cls._instance._events: List[Dict[str, Any]] = []
                cls._instance._listener_active: bool = False
                cls._instance._listener_host: str = "127.0.0.1"
                cls._instance._listener_port: int = 5678
            return cls._instance

    def record_event(
        self,
        event_type: str,
        file_path: str = "",
        line_number: Optional[int] = None,
        error_type: str = "",
        traceback_str: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Records a new debug/failure event into the store."""
        event = {
            "id": len(self._events) + 1,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "file_path": file_path,
            "line_number": line_number,
            "error_type": error_type,
            "traceback": traceback_str,
            "details": details or {},
            "process_id": os.getpid(),
            "thread_name": threading.current_thread().name
        }
        with self._lock:
            self._events.append(event)
            # Keep last 100 events
            if len(self._events) > 100:
                self._events.pop(0)
        return event

    def get_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent debug events."""
        with self._lock:
            return list(self._events[-limit:])

    def set_listener_status(self, active: bool, host: str = "127.0.0.1", port: int = 5678):
        with self._lock:
            self._listener_active = active
            self._listener_host = host
            self._listener_port = port

    def get_listener_status(self) -> Dict[str, Any]:
        with self._lock:
            connected = False
            try:
                connected = debugpy.is_client_connected()
            except Exception:
                connected = False
            return {
                "active": self._listener_active,
                "host": self._listener_host,
                "port": self._listener_port,
                "client_connected": connected,
                "pid": os.getpid()
            }


bridge_store = DebugBridgeStore()


def record_debug_event(
    event_type: str,
    file_path: str = "",
    line_number: Optional[int] = None,
    error_type: str = "",
    traceback_str: str = "",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper function to log debug events across modules."""
    return bridge_store.record_event(
        event_type=event_type,
        file_path=file_path,
        line_number=line_number,
        error_type=error_type,
        traceback_str=traceback_str,
        details=details
    )


# =====================================================================
# 2. FastMCP Server Initialization & Tools
# =====================================================================
mcp = FastMCP(
    name="mak-agent-debugger",
    instructions="MAK-Agent MCP Debugger Bridge for live IDE process attachment, runtime state inspection, and expression evaluation."
)


@mcp.tool()
def start_debug_listener(port: int = 5678, host: str = "127.0.0.1", wait_for_client: bool = False) -> str:
    """
    Binds debugpy to the specified host and port (default 127.0.0.1:5678) to enable live IDE process attachment.
    
    Args:
        port: Target TCP port to listen on (default: 5678).
        host: Host interface to bind (default: '127.0.0.1').
        wait_for_client: If True, blocks until an IDE debugger attaches (default: False).
    """
    try:
        debugpy.listen((host, port))
        bridge_store.set_listener_status(active=True, host=host, port=port)
        status_msg = f"✅ debugpy listener started on {host}:{port} (PID: {os.getpid()})."
    except RuntimeError as e:
        bridge_store.set_listener_status(active=True, host=host, port=port)
        status_msg = f"ℹ️ debugpy listener already running on {host}:{port} ({e})."
    except Exception as e:
        return f"❌ Failed to start debugpy listener on {host}:{port}: {e}"

    if wait_for_client:
        status_msg += "\n⏳ Paused execution, waiting for IDE debugger client to attach..."
        try:
            debugpy.wait_for_client()
            status_msg += "\n🔗 IDE Debugger client successfully attached!"
        except Exception as e:
            status_msg += f"\n⚠️ Error waiting for debugger client: {e}"

    client_connected = False
    try:
        client_connected = debugpy.is_client_connected()
    except Exception:
        pass

    status_msg += f"\n• Client Connected: {'YES' if client_connected else 'NO (Ready to attach in VS Code via port ' + str(port) + ')'}"
    return status_msg


@mcp.tool()
def inspect_runtime_state(thread_id: Optional[int] = None) -> str:
    """
    Inspects the live Python runtime state of the MAK-Agent process, including active threads,
    call stack frames, loaded modules, and debugpy status.
    
    Args:
        thread_id: Optional thread ident to filter stack frame inspection.
    """
    try:
        report_lines = [
            "============================================================",
            "🔍 MAK-AGENT RUNTIME STATE SNAPSHOT",
            "============================================================",
            f"• Process ID (PID): {os.getpid()}",
            f"• Python Executable: {sys.executable}",
            f"• Python Version: {sys.version.splitlines()[0]}",
            f"• Working Directory: {os.getcwd()}",
            f"• Active Threads: {threading.active_count()}"
        ]

        # Listener Status
        listener_info = bridge_store.get_listener_status()
        report_lines.append(
            f"• Debugpy Listener: {'ACTIVE on ' + listener_info['host'] + ':' + str(listener_info['port']) if listener_info['active'] else 'INACTIVE'}"
        )
        report_lines.append(f"• IDE Client Connected: {'YES' if listener_info['client_connected'] else 'NO'}")

        # Thread List
        report_lines.append("\n--- ACTIVE THREADS ---")
        for t in threading.enumerate():
            status = "Alive" if t.is_alive() else "Stopped"
            daemon_str = "Daemon" if t.daemon else "Non-Daemon"
            report_lines.append(f"  - [{t.ident}] '{t.name}' ({daemon_str}, {status})")

        # Current Frames
        report_lines.append("\n--- CALL STACK FRAMES ---")
        frames = sys._current_frames()
        for t_ident, frame in frames.items():
            if thread_id is not None and t_ident != thread_id:
                continue
            thread_name = "Unknown"
            for t in threading.enumerate():
                if t.ident == t_ident:
                    thread_name = t.name
                    break
            stack_summary = traceback.format_stack(frame)
            last_call = stack_summary[-1].strip() if stack_summary else "N/A"
            report_lines.append(f"  Thread {t_ident} ('{thread_name}'):")
            report_lines.append(f"    Top Frame: {last_call}")

        # Recent Bridge Events
        events = bridge_store.get_events(limit=5)
        if events:
            report_lines.append("\n--- RECENT DEBUG BRIDGE EVENTS ---")
            for ev in events:
                file_info = f"{ev.get('file_path', 'N/A')}:{ev.get('line_number', '?')}"
                report_lines.append(
                    f"  [{ev['timestamp']}] Event #{ev['id']} ({ev['event_type']}) - {ev.get('error_type', 'Error')} at {file_info}"
                )

        report_lines.append("============================================================")
        return "\n".join(report_lines)
    except Exception as e:
        return f"❌ Failed to inspect runtime state: {e}\n{traceback.format_exc()}"


@mcp.tool()
def evaluate_expression_in_scope(expression: str, scope: str = "global") -> str:
    """
    Evaluates a Python expression or variable query against the runtime environment safely.
    
    Args:
        expression: Python expression to evaluate (e.g. 'sys.version', 'os.getenv(\"RUNNING_IN_SERVER\")').
        scope: Scope context ('global', 'sys', or module name).
    """
    try:
        eval_globals = {
            "sys": sys,
            "os": os,
            "time": time,
            "json": json,
            "threading": threading,
            "bridge_store": bridge_store
        }

        # Inject agency modules if loaded
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("main") or mod_name.startswith("engineering_department") or mod_name.startswith("self_healing"):
                eval_globals[mod_name] = sys.modules[mod_name]

        result = eval(expression, eval_globals)
        return (
            f"✅ Expression Evaluation Result:\n"
            f"• Expression: {expression}\n"
            f"• Type: {type(result).__name__}\n"
            f"• Value: {repr(result)}"
        )
    except Exception as e:
        return (
            f"❌ Evaluation Error for '{expression}':\n"
            f"• Exception: {type(e).__name__}: {e}\n"
            f"• Traceback:\n{traceback.format_exc()}"
        )


@mcp.tool()
def get_debug_bridge_events(limit: int = 10) -> str:
    """
    Retrieves the list of recorded diagnostic error events, stack traces, and breakpoint triggers.
    
    Args:
        limit: Maximum number of events to return (default: 10).
    """
    events = bridge_store.get_events(limit=limit)
    if not events:
        return "ℹ️ No debug bridge events recorded yet."
    return json.dumps(events, indent=2, default=str)


# =====================================================================
# 3. LangChain / CrewAI Diagnostic Tools for Autonomous Agents
# =====================================================================
@tool("Trigger IDE Breakpoint")
def trigger_ide_breakpoint(file_path: str = "", line_number: Optional[int] = None, reason: str = "") -> str:
    """
    Diagnostic tool for autonomous agents to trigger an IDE breakpoint or bind debugpy
    for live step-debugging in the active IDE workspace.
    
    Args:
        file_path: Source file path where breakpoint or inspection is requested.
        line_number: Line number in the target file (optional).
        reason: Diagnostic reason or context for triggering the breakpoint.
    """
    print("\n" + "=" * 65)
    print(f"🐞 [IDE DEBUGGER BRIDGE] Breakpoint Triggered")
    print(f"   File: {file_path or 'N/A'}")
    print(f"   Line: {line_number if line_number is not None else 'N/A'}")
    print(f"   Reason: {reason or 'Agent Diagnostic Pause'}")
    print("=" * 65)

    # Ensure debugpy listener is active
    try:
        debugpy.listen(("127.0.0.1", 5678))
        bridge_store.set_listener_status(active=True, host="127.0.0.1", port=5678)
    except RuntimeError:
        bridge_store.set_listener_status(active=True, host="127.0.0.1", port=5678)
    except Exception as e:
        print(f"⚠️ [debugpy Notice]: {e}")

    # Record event in bridge store
    ev = record_debug_event(
        event_type="IDE_BREAKPOINT_TRIGGERED",
        file_path=file_path,
        line_number=line_number,
        error_type="AGENT_REQUESTED_BREAKPOINT",
        traceback_str=reason,
        details={"reason": reason}
    )

    client_connected = False
    try:
        client_connected = debugpy.is_client_connected()
    except Exception:
        pass

    if client_connected:
        print("🔗 IDE Debugger connected! Triggering debugpy.breakpoint()...")
        try:
            debugpy.breakpoint()
            return f"SUCCESS: Breakpoint triggered at {file_path}:{line_number}. IDE Debugger attached and paused execution."
        except Exception as bp_err:
            return f"NOTICE: Debugger attached, but breakpoint invocation returned: {bp_err}"
    else:
        return (
            f"SUCCESS: Debugger listener is active at 127.0.0.1:5678 (PID: {os.getpid()}). "
            f"Event #{ev['id']} recorded. "
            f"To step-debug interactively, attach VS Code using Run & Debug -> 'Python: Attach to MAK-Agent'."
        )


@tool("Inspect Variable Value")
def inspect_variable_value(variable_name: str, scope: str = "global") -> str:
    """
    Diagnostic tool for autonomous agents to inspect runtime variables, module attributes,
    or execution context values during failure analysis.
    
    Args:
        variable_name: Variable name or attribute path (e.g. 'os.environ.get(\"RUNNING_IN_SERVER\")').
        scope: Scope to inspect ('global', 'sys', or module name).
    """
    return evaluate_expression_in_scope(expression=variable_name, scope=scope)


__all__ = [
    "mcp",
    "bridge_store",
    "record_debug_event",
    "start_debug_listener",
    "inspect_runtime_state",
    "evaluate_expression_in_scope",
    "get_debug_bridge_events",
    "trigger_ide_breakpoint",
    "inspect_variable_value"
]


# =====================================================================
# 4. Main Entrypoint (FastMCP Server stdio Runner)
# =====================================================================
if __name__ == "__main__":
    # Start debugpy listener on port 5678 by default
    try:
        debugpy.listen(("127.0.0.1", 5678))
        bridge_store.set_listener_status(active=True, host="127.0.0.1", port=5678)
        sys.stderr.write("[mak-debugger] debugpy listening on 127.0.0.1:5678\n")
    except Exception as e:
        sys.stderr.write(f"[mak-debugger] debugpy notice: {e}\n")

    # Run FastMCP stdio server
    mcp.run(transport="stdio")
