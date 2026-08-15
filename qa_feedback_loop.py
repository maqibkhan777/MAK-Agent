import os
import sys
import time
import subprocess
from typing import Optional, Tuple, Any

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

from playwright.sync_api import sync_playwright, Browser, Page, Playwright


# =====================================================================
# Step 1: CDP Connection to User's Live Chrome
# =====================================================================
def connect_to_live_browser(cdp_url: str = "http://localhost:9222") -> Tuple[Optional[Page], Optional[Browser], Optional[Playwright], Optional[str]]:
    """
    Connects directly to the user's live running Google Chrome instance via CDP (port 9222).
    Controls the user's actual authenticated Chrome session instead of launching sandbox Chromium.
    """
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(cdp_url, timeout=5000)
        
        # Grab active session context or create one
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        # Open a new tab in the active Chrome window
        page = context.new_page()
        return page, browser, playwright, None
    except Exception as e:
        return None, None, None, (
            f"⚠️ Could not connect to live Chrome at {cdp_url}.\n"
            f"Please ensure Chrome is running with: chrome.exe --remote-debugging-port=9222\n"
            f"Details: {e}"
        )


# =====================================================================
# Step 2: Automated Gemini QA Report Injection via CDP
# =====================================================================
def paste_qa_report_to_gemini(page: Page, master_prompt: str) -> bool:
    """
    Navigates live Chrome to Gemini and automatically injects the QA failure report into the chatbox.
    """
    try:
        print("\n[CDP Action] Navigating live Chrome tab to https://gemini.google.com/app ...")
        page.goto("https://gemini.google.com/app", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Gemini input box selectors: rich-textarea, contenteditable div, role=textbox, or standard textarea
        selectors = [
            "div[role='textbox']",
            "rich-textarea",
            "div.ql-editor",
            "textarea",
            "p[data-placeholder]"
        ]

        target_element = None
        for sel in selectors:
            try:
                elem = page.wait_for_selector(sel, timeout=4000)
                if elem and elem.is_visible():
                    target_element = elem
                    break
            except Exception:
                continue

        if target_element:
            target_element.click()
            page.wait_for_timeout(300)
            
            # Use insert_text to simulate natural pasting across contenteditable / rich-text editors
            page.keyboard.insert_text(master_prompt)
            print("✔ QA Failure Report automatically pasted into Gemini chat box in your visible Chrome browser!")
            return True
        else:
            print("Notice: Could not locate Gemini input selector automatically. Failure report is copied to clipboard.")
            return False

    except Exception as err:
        print(f"Notice during Gemini injection: {err}")
        return False


# =====================================================================
# Step 3: Run QA Test & Trigger Automated Handoff
# =====================================================================
def run_qa_test() -> str:
    """Executes agency_evaluator.py and returns console output."""
    print("\n" + "=" * 78)
    print(" 🚀 RUNNING AGENCY QA EVALUATOR IN BACKGROUND...")
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


def analyze_and_route(qa_output: str):
    """
    Evaluates QA report:
    - If 100% PASS, displays congratulations.
    - If errors/warnings are present, connects via CDP to live Chrome,
      opens Gemini in a visible tab, and drops the QA failure report directly in the prompt box.
    """
    is_failing = False
    if "FAIL" in qa_output or "WARN" in qa_output or "ERR" in qa_output or "100.0%" not in qa_output:
        is_failing = True

    if not is_failing:
        print("\n" + "=" * 78)
        print(" 🎉 QA TEST PASSED WITH 100% HEALTH SCORE! All departments operational.")
        print("=" * 78 + "\n")
        return

    print("\n" + "=" * 78)
    print(" ⚠️ QA TEST IDENTIFIED DEFICIENCIES OR FAILURES.")
    print(" 🌐 INITIATING CDP LIVE CHROME HANDOFF TO GEMINI...")
    print("=" * 78 + "\n")

    # Extract clean report
    report_content = qa_output.strip()
    if "📊 AGENCY QA REPORT" in qa_output:
        report_content = qa_output[qa_output.find("📊 AGENCY QA REPORT"):]
    elif os.path.exists(os.path.join("output", "agency_health_report.txt")):
        try:
            with open(os.path.join("output", "agency_health_report.txt"), "r", encoding="utf-8") as f:
                report_content = f.read()
        except Exception:
            pass

    master_prompt = (
        "My LangGraph AI agency failed its QA test. Here is the exact console output and failure report:\n\n"
        f"{report_content}\n\n"
        "Based on these errors, provide the exact Python code fixes I need to give to my Antigravity IDE to repair the broken departments."
    )

    # Clipboard fallback
    if pyperclip:
        try:
            pyperclip.copy(master_prompt)
            print("✔ Failure report copied to system clipboard.")
        except Exception:
            pass

    # CDP Connection
    page, browser, playwright, err = connect_to_live_browser()
    if err:
        print(err)
        print("\nThe failure report is copied to your clipboard. You can paste it directly into your browser.")
        return

    try:
        pasted = paste_qa_report_to_gemini(page, master_prompt)
        print("\n" + "*" * 78)
        print(" 🎯 LIVE CHROME TAB READY: Check your visible Chrome window!")
        if pasted:
            print(" The prompt is loaded in Gemini. Hit Enter or review suggestions.")
        else:
            print(" The failure report is in your clipboard. Press Ctrl+V in Gemini.")
        print("*" * 78 + "\n")
    except Exception as e:
        print(f"Browser interaction note: {e}")
    finally:
        # Keep connection open briefly so user sees the tab
        time.sleep(2)
        try:
            playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    qa_results = run_qa_test()
    analyze_and_route(qa_results)
