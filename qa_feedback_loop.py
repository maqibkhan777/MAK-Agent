import os
import sys
import time
import subprocess
import re

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

try:
    import pyperclip
except ImportError:
    pyperclip = None

from playwright.sync_api import sync_playwright


# =====================================================================
# Step 2: Execute the QA Run
# =====================================================================
def run_qa_test() -> str:
    """
    Executes agency_evaluator.py in a subprocess and captures the full console stdout.
    """
    print("\n" + "=" * 78)
    print(" 🚀 RUNNING AUTOMATED QA EVALUATOR VIA SUBPROCESS...")
    print("=" * 78 + "\n")

    cmd = [sys.executable, "agency_evaluator.py"]
    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    output = process.stdout
    if process.stderr:
        output += "\n--- STDERR ---\n" + process.stderr

    print(output)
    return output


def connect_to_live_browser():
    playwright = sync_playwright().start()
    # Connect to the live Chrome instance listening on port 9222
    try:
        browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
        # Grab the first open tab (default context)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        return page, browser, playwright
    except Exception as e:
        return f"CRITICAL ERROR: Could not connect to browser. Ensure Chrome is running with --remote-debugging-port=9222. Error: {e}"


# =====================================================================
# Step 3, 4 & 5: Analyze, Format, Clipboard & Launch Browser
# =====================================================================
def analyze_and_route(qa_output: str):
    """
    Parses the captured QA report:
    - If 100% PASS rate, prints a success message and exits.
    - If failures/warnings are detected, formats a master troubleshooting prompt,
      copies it to the clipboard, and connects to a live Chrome browser via CDP.
    """
    is_failing = False
    if "FAIL" in qa_output or "WARN" in qa_output or "Overall Agency Health    : 100" not in qa_output:
        is_failing = True

    if not is_failing and "100.0%" in qa_output:
        print("\n" + "=" * 78)
        print(" 🎉 QA TEST PASSED WITH 100% HEALTH SCORE! All departments operational.")
        print("=" * 78 + "\n")
        return

    print("\n" + "=" * 78)
    print(" ⚠️ QA TEST IDENTIFIED DEFICIENCIES OR FAILURES.")
    print(" Preparing troubleshooting payload for AI consultation...")
    print("=" * 78 + "\n")

    # Extract the structured report or fallback to saved file
    report_content = qa_output.strip()
    if "📊 AGENCY QA REPORT" in qa_output:
        report_content = qa_output[qa_output.find("📊 AGENCY QA REPORT"):]
    elif os.path.exists(os.path.join("output", "agency_health_report.txt")):
        try:
            with open(os.path.join("output", "agency_health_report.txt"), "r", encoding="utf-8") as f:
                report_content = f.read()
        except Exception:
            pass

    # Step 4: Format master troubleshooting prompt
    master_prompt = (
        "My LangGraph AI agency failed its QA test. Here is the exact console output and failure report:\n\n"
        f"{report_content}\n\n"
        "Based on these errors, provide the exact Python code fixes I need to give to my Antigravity IDE to repair the broken departments."
    )

    # Copy to system clipboard
    if pyperclip:
        try:
            pyperclip.copy(master_prompt)
            print("✔ Failure report & repair prompt successfully copied to system clipboard!")
        except Exception as e:
            print(f"Notice: Clipboard copy error: {e}")
    else:
        print("Notice: pyperclip is not available. Payload logged directly.")

    # Step 5: The Playwright Action Layer (Live Chrome CDP Connection)
    print("\n" + "=" * 78)
    print(" 🌐 CONNECTING TO LIVE CHROME BROWSER VIA CDP (port 9222)...")
    print("=" * 78 + "\n")

    browser_conn = connect_to_live_browser()
    if isinstance(browser_conn, str):
        print(f"\n{browser_conn}\n")
        print("The failure report is copied to your clipboard. You can paste it directly into your browser.")
        return

    page, browser, playwright = browser_conn
    try:
        print("Navigating live Chrome tab to https://gemini.google.com/ ...")
        page.goto("https://gemini.google.com/", timeout=60000)

        print("\n" + "*" * 78)
        print(" Live browser tab ready. The failure report is copied to your clipboard.")
        print(" Focus the Gemini chat box, hit Ctrl+V to paste, and let's fix the code.")
        print("*" * 78 + "\n")

        print("Press Enter in this terminal when you are finished consulting with the browser...")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
    except Exception as browser_err:
        print(f"Browser navigation notice: {browser_err}")
        print("\nThe failure report is copied to your clipboard. You can paste it directly into your browser.")
    finally:
        playwright.stop()
        print("[Disconnected] Live browser CDP session finished.")


if __name__ == "__main__":
    qa_results = run_qa_test()
    analyze_and_route(qa_results)
