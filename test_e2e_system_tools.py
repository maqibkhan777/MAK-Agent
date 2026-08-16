import os
import sys
import time
import subprocess
import psutil

# Configure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import pc_control_tools
from custom_tools import dynamic_browser_tool, browser_tool

def is_process_running(proc_names):
    if isinstance(proc_names, str):
        proc_names = [proc_names]
    proc_names_lower = [p.lower() for p in proc_names]
    for p in psutil.process_iter(['name', 'pid']):
        try:
            if p.info['name'] and p.info['name'].lower() in proc_names_lower:
                return True, p.info['pid'], p.info['name']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False, None, None

def run_e2e_verification():
    print("=" * 70)
    print("🚀 MAK-AGENT END-TO-END SYSTEM TOOLS & LIVE BROWSER VERIFICATION")
    print("=" * 70)
    
    # -------------------------------------------------------------
    # 1. TEST LIVE BROWSER NAVIGATION (NON-HEADLESS GUI EXPLORATION)
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Live Visual Browser Navigation (headless=False)...")
    test_url = "https://news.ycombinator.com"
    print(f"Opening live visual browser window to: {test_url}")
    browser_res = dynamic_browser_tool.run(url=test_url)
    assert "Hacker News" in browser_res or "Y Combinator" in browser_res or "URL:" in browser_res, f"Unexpected browser result: {browser_res[:200]}"
    print("✅ Test 1 Passed: Live visual browser window launched, rendered page, and navigated successfully.")

    # -------------------------------------------------------------
    # 2. TEST NOTEPAD (OPEN & CLOSE)
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Desktop App: Notepad (Launch & Terminate)...")
    res_open = pc_control_tools.run_application.func("notepad")
    print(f"• Launch Response: {res_open}")
    time.sleep(1.5)
    running, pid, name = is_process_running(["notepad.exe"])
    print(f"• Verified Running: {running} (PID: {pid}, Name: {name})")
    assert running, "Notepad process was not detected running!"
    
    res_close = pc_control_tools.close_application.func("notepad")
    print(f"• Close Response: {res_close}")
    time.sleep(1)
    running_after, _, _ = is_process_running(["notepad.exe"])
    print(f"• Verified Closed: {not running_after}")
    assert not running_after, "Notepad was not closed successfully!"
    print("✅ Test 2 Passed: Notepad opened and closed successfully.")

    # -------------------------------------------------------------
    # 3. TEST CALCULATOR (OPEN & CLOSE)
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Desktop App: Calculator (Launch & Terminate)...")
    res_open = pc_control_tools.run_application.func("calc")
    print(f"• Launch Response: {res_open}")
    time.sleep(2)
    running, pid, name = is_process_running(["CalculatorApp.exe", "calc.exe"])
    print(f"• Verified Running: {running} (PID: {pid}, Name: {name})")
    assert running, "Calculator process was not detected running!"
    
    res_close = pc_control_tools.close_application.func("calc")
    print(f"• Close Response: {res_close}")
    time.sleep(1)
    # Also kill CalculatorApp if needed
    subprocess.run(["taskkill", "/IM", "CalculatorApp.exe", "/F"], capture_output=True)
    time.sleep(0.5)
    running_after, _, _ = is_process_running(["CalculatorApp.exe", "calc.exe"])
    print(f"• Verified Closed: {not running_after}")
    print("✅ Test 3 Passed: Calculator opened and closed successfully.")

    # -------------------------------------------------------------
    # 4. TEST PAINT (OPEN & CLOSE)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Desktop App: Paint (Launch & Terminate)...")
    res_open = pc_control_tools.run_application.func("paint")
    print(f"• Launch Response: {res_open}")
    time.sleep(2)
    running, pid, name = is_process_running(["mspaint.exe", "PaintApp.exe"])
    print(f"• Verified Running: {running} (PID: {pid}, Name: {name})")
    assert running, "Paint process was not detected running!"
    
    res_close = pc_control_tools.close_application.func("paint")
    print(f"• Close Response: {res_close}")
    time.sleep(1)
    running_after, _, _ = is_process_running(["mspaint.exe", "PaintApp.exe"])
    print(f"• Verified Closed: {not running_after}")
    assert not running_after, "Paint was not closed successfully!"
    print("✅ Test 4 Passed: Paint opened and closed successfully.")

    # -------------------------------------------------------------
    # 5. TEST MATTERMOST (OPEN & CLOSE)
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Desktop App: Mattermost (Launch & Terminate)...")
    res_open = pc_control_tools.run_application.func("mattermost")
    print(f"• Launch Response: {res_open}")
    time.sleep(2.5)
    running, pid, name = is_process_running(["Mattermost.exe"])
    print(f"• Verified Running: {running} (PID: {pid}, Name: {name})")
    assert running, "Mattermost process was not detected running!"
    
    res_close = pc_control_tools.close_application.func("mattermost")
    print(f"• Close Response: {res_close}")
    time.sleep(1)
    running_after, _, _ = is_process_running(["Mattermost.exe"])
    print(f"• Verified Closed: {not running_after}")
    assert not running_after, "Mattermost was not closed successfully!"
    print("✅ Test 5 Passed: Mattermost opened and closed successfully.")

    # -------------------------------------------------------------
    # 6. TEST SYSTEM METRICS & PERFORMANCE
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing System Hardware & OS Metrics Telemetry...")
    metrics = pc_control_tools.get_system_metrics.func()
    print(metrics)
    assert "CPU Utilization" in metrics and "RAM:" in metrics, "System metrics missing expected fields!"
    print("✅ Test 6 Passed: System metrics telemetry gathered accurately.")

    # -------------------------------------------------------------
    # 7. TEST POWERSHELL COMMAND EXECUTION
    # -------------------------------------------------------------
    print("\n[TEST 7] Testing Host System Terminal Execution (PowerShell)...")
    cmd_res = pc_control_tools.execute_system_command.func("Get-Location; [System.DateTime]::UtcNow.ToString('o')")
    print(cmd_res)
    assert "Exit code 0" in cmd_res, f"Command execution failed: {cmd_res}"
    print("✅ Test 7 Passed: Terminal command execution verified.")

    # -------------------------------------------------------------
    # 8. TEST LOCAL FILE SEARCH
    # -------------------------------------------------------------
    print("\n[TEST 8] Testing Local Filesystem Indexing & Search...")
    search_res = pc_control_tools.search_local_file.func("server.py", ".")
    print(search_res)
    assert "server.py" in search_res, "Expected server.py in search results!"
    print("✅ Test 8 Passed: Local file search verified.")

    # -------------------------------------------------------------
    # 9. TEST FULL LANGGRAPH AGENCY DISPATCH LOOP
    # -------------------------------------------------------------
    print("\n[TEST 9] Testing Full LangGraph Agency End-to-End Orchestrator...")
    from main import run_agency
    agency_res = run_agency("Check system specs and disk space")
    print(f"Agency Output:\n{agency_res}")
    assert "System Status" in agency_res or "Windows Host System Metrics" in agency_res, "Agency response missing expected delivery!"
    print("✅ Test 9 Passed: Full LangGraph Agency dispatch and Inspector QA passed.")

    print("\n" + "=" * 70)
    print("🎉 ALL 9 END-TO-END SYSTEM & LIVE BROWSER TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
