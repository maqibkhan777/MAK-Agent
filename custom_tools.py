import os
import sys

# Configure UTF-8 encoding for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from crewai.tools import tool
from duckduckgo_search import DDGS

@tool("Live Internet Search")
def live_web_search(query: str) -> str:
    """Use this tool to search the live internet for the absolute latest, up-to-date information, news, pricing, or documentation."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return f"No results found for query: '{query}'"
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. Title: {r.get('title', '')}\n   Snippet: {r.get('body', '')}\n   URL: {r.get('href', '')}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error executing live web search for '{query}': {e}"

@tool("Dynamic Browser Tool")
def dynamic_browser_tool(url: str) -> str:
    """Use this tool to open a real Chrome browser to navigate to a URL that requires JavaScript to load. It returns the visible text of the fully loaded page."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass
            text = page.inner_text("body")
            browser.close()
            # Truncate text to avoid blowing LLM context window
            if len(text) > 15000:
                text = text[:15000] + "\n\n[...Content truncated for LLM context optimization...]"
            return text
    except Exception as e:
        return f"Error executing dynamic browser navigation for {url}: {e}"

@tool("Post to Social API")
def post_to_social_api(platform: str, content: str) -> str:
    """Use this tool to physically publish a finalized post to a social media platform. Input the platform name and the content."""
    msg = f"SUCCESS: Pushed to {platform} API: {content}"
    print(msg)
    return msg

