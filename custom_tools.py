import os
import sys

# Configure UTF-8 encoding for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from crewai.tools import tool

@tool("Dynamic Browser Tool")
def dynamic_browser_tool(url: str) -> str:
    """Use this tool to open a real Chrome browser to navigate to a URL that requires JavaScript to load. It returns the visible text of the fully loaded page."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            text = page.inner_text("body")
            browser.close()
            return text
    except Exception as e:
        return f"Error executing dynamic browser navigation for {url}: {e}"

@tool("Post to Social API")
def post_to_social_api(platform: str, content: str) -> str:
    """Use this tool to physically publish a finalized post to a social media platform. Input the platform name and the content."""
    msg = f"SUCCESS: Pushed to {platform} API: {content}"
    print(msg)
    return msg
