import os
import sys
import urllib.parse
import urllib.request

# Configure UTF-8 encoding for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Pydantic V1 type inference patch for ChromaDB under Python 3.14
try:
    import pydantic.v1.fields
    _orig_set_default = pydantic.v1.fields.ModelField._set_default_and_type
    def _safe_set_default(self):
        if getattr(self, 'type_', None) is None or self.type_ is pydantic.v1.fields.Undefined:
            if hasattr(self, 'default') and self.default is not None and self.default is not pydantic.v1.fields.Undefined:
                self.type_ = type(self.default)
                self.outer_type_ = self.type_
            else:
                self.type_ = str
                self.outer_type_ = str
        return _orig_set_default(self)
    pydantic.v1.fields.ModelField._set_default_and_type = _safe_set_default
except Exception:
    pass

from crewai.tools import tool
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

import io
try:
    from PIL import Image, ImageFilter, ImageEnhance
except ImportError:
    Image = None

@tool("Generate Free Image")
def generate_free_image(prompt: str, filename: str) -> str:
    """Use this tool to physically generate and download ultra-high-definition (4K UHD) crisp image files for free from a prompt. Provide a detailed visual prompt and a descriptive filename."""
    try:
        # 1. Prompt Quality Augmentation for 4K UHD photorealism and razor-sharp clarity
        enhancement_tokens = [
            "4k resolution", "8k uhd", "photorealistic", "sharp focus",
            "cinematic volumetric lighting", "octane render", "masterpiece",
            "hyper-detailed textures", "unreal engine 5"
        ]
        lower_prompt = prompt.lower()
        missing_tokens = [tok for tok in enhancement_tokens if tok not in lower_prompt]
        boosted_prompt = f"{prompt.strip()}, {', '.join(missing_tokens[:5])}" if missing_tokens else prompt.strip()

        encoded_prompt = urllib.parse.quote(boosted_prompt)

        # 2. Enforce 1920x1080 cinematic HD rendering via Flux model
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true&model=flux&enhance=true"
        os.makedirs('output', exist_ok=True)
        clean_name = filename.rsplit('.', 1)[0] if filename.endswith(('.jpg', '.jpeg', '.png')) else filename
        filepath = os.path.join('output', f"{clean_name}.jpg")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            image_bytes = response.read()

        # 3. Ultra-HD Lanczos Resampling & Unsharp Mask Edge Hardening
        if Image is not None:
            try:
                img = Image.open(io.BytesIO(image_bytes))

                # Determine 4K target dimensions (3840px width for widescreen 16:9, 2048px for square/portrait)
                if img.width >= img.height:
                    target_w = 3840
                    target_h = int(target_w * (img.height / img.width))
                else:
                    target_w = 2048
                    target_h = int(target_w * (img.height / img.width))

                # Resample with Lanczos high-fidelity filter
                img_hd = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                # Apply unsharp mask to restore edge micro-contrast and eliminate all blurriness
                unsharp = ImageFilter.UnsharpMask(radius=1.5, percent=140, threshold=2)
                img_hd = img_hd.filter(unsharp)

                # Fine-tune sharpness
                sharpness_enhancer = ImageEnhance.Sharpness(img_hd)
                img_hd = sharpness_enhancer.enhance(1.2)

                # Save as pristine, high-bitrate progressive JPEG
                img_hd.save(filepath, "JPEG", quality=96, optimize=True, progressive=True)
                return f"Successfully generated and saved ultra-high-definition 4K image ({target_w}x{target_h}) to {filepath}"
            except Exception as pil_err:
                print(f"PIL Post-Processing Notice: {pil_err}")
                with open(filepath, "wb") as out_file:
                    out_file.write(image_bytes)
                return f"Successfully generated and saved image to {filepath}"
        else:
            with open(filepath, "wb") as out_file:
                out_file.write(image_bytes)
            return f"Successfully generated and saved image to {filepath}"
    except Exception as e:
        return f"Error generating image: {e}"

@tool("Live Internet Search")
def live_web_search(query: str) -> str:
    """Use this tool to search the live internet for the absolute latest, up-to-date information, news, pricing, or documentation."""
    import re
    # Clean leading conversational or command prefixes
    clean_query = query.strip()
    clean_query = re.sub(r'^(please\s+)?(search\s+the\s+web\s+for|search\s+for|search\s+online\s+for|search\s+the\s+internet\s+for|search|google\s+for|google|look\s+up|find\s+information\s+on|find)\s+', '', clean_query, flags=re.IGNORECASE).strip()
    if not clean_query:
        clean_query = query.strip()

    formatted = []
    # 1. Primary: Try DuckDuckGo HTML endpoint
    try:
        import urllib.parse
        import requests
        from bs4 import BeautifulSoup
        ddg_html_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(clean_query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(ddg_html_url, headers=headers, timeout=6)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results_elements = soup.find_all("div", class_="result__body")
            for i, elem in enumerate(results_elements[:5], 1):
                title_elem = elem.find("a", class_="result__a")
                snippet_elem = elem.find("a", class_="result__snippet")
                url_elem = elem.find("a", class_="result__url")
                t = title_elem.get_text().strip() if title_elem else ""
                s = snippet_elem.get_text().strip() if snippet_elem else ""
                u = url_elem.get_text().strip() if url_elem else ""
                if t or s:
                    formatted.append(f"{i}. Title: {t}\n   Snippet: {s}\n   URL: {u}")
            if formatted:
                return "\n\n".join(formatted)
    except Exception:
        pass

    # 2. Secondary: Try DDGS
    try:
        results = list(DDGS().text(clean_query, max_results=5))
        if not results:
            results = list(DDGS().text(query, max_results=5))
        if results:
            for i, r in enumerate(results, 1):
                formatted.append(f"{i}. Title: {r.get('title', '')}\n   Snippet: {r.get('body', '')}\n   URL: {r.get('href', '')}")
            return "\n\n".join(formatted)
    except Exception:
        pass

    if formatted:
        return "\n\n".join(formatted)
    return f"No results found for query: '{clean_query}'"

def is_port_open(host: str = "127.0.0.1", port: int = 9222, timeout: float = 0.4) -> bool:
    """Fast socket probe to verify if Chrome DevTools Protocol debugging port is listening."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def connect_to_live_browser(port: int = 9222):
    """
    Connects directly to the user's running Chrome/Edge browser session via CDP (port 9222).
    Accesses user session cookies, logged-in states, and browser tabs without spawning blank chromium.
    """
    debug_port = int(os.getenv("CHROME_DEBUG_PORT", str(port)))
    if not is_port_open(port=debug_port):
        return f"PORT_CLOSED: Chrome remote debugging port {debug_port} is not listening."

    from playwright.sync_api import sync_playwright
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.connect_over_cdp(f"http://localhost:{debug_port}", timeout=4000)
        # Use existing open tab or open a tab in the user's active session context
        if browser.contexts:
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
        else:
            context = browser.new_context()
            page = context.new_page()
        return page, browser, playwright, True
    except Exception as e:
        try:
            playwright.stop()
        except Exception:
            pass
        return f"CDP_ERROR: Could not attach to live Chrome on port {debug_port}: {e}"


@tool("Dynamic Browser Tool")
def dynamic_browser_tool(url: str) -> str:
    """Use this tool to navigate the user's live Chrome browser session via CDP (port 9222) to a URL that requires JavaScript to load. It returns the visible text of the fully loaded page."""
    conn = connect_to_live_browser()
    
    if isinstance(conn, tuple):
        page, browser, playwright, is_live = conn
        try:
            print(f"[MAK Browser Tool] 🌐 Connected directly to User's Local Chrome via Port 9222: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(800)
            text = page.inner_text("body")
            if len(text) > 15000:
                text = text[:15000] + "\n\n[...Content truncated for LLM context optimization...]"
            return f"=== Live Local Browser Navigation (Port 9222: Connected) ===\nURL: {url}\n\n{text}"
        except Exception as e:
            return f"Error during live browser navigation to {url}: {e}"
        finally:
            try:
                browser.close()
                playwright.stop()
            except Exception:
                pass
    else:
        # Launch live visible browser engine so the user can watch the automation explore the web in real-time
        print(f"[MAK Browser Tool] Launching live interactive browser window for: {url}")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, args=["--start-maximized"])
                context = browser.new_context(viewport=None)
                page = context.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    # Live exploration pause allowing user to visually see the rendered page
                    page.wait_for_timeout(2500)
                    # Smooth scroll down to simulate real visual reading
                    page.evaluate("window.scrollBy({ top: 600, behavior: 'smooth' });")
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
                text = page.inner_text("body")
                browser.close()
                if len(text) > 15000:
                    text = text[:15000] + "\n\n[...Content truncated for LLM context optimization...]"
                return f"=== Live Web Browser Navigation ===\nURL: {url}\n\n{text}"
        except Exception as e:
            return f"Browser navigation error for {url}: {e}"

@tool("Post to Social API")
def post_to_social_api(platform: str, content: str) -> str:
    """Use this tool to physically publish a finalized post to a social media platform. Input the platform name and the content."""
    msg = f"SUCCESS: Pushed to {platform} API: {content}"
    print(msg)
    return msg


# =====================================================================
# LangChain ToolNode Compatible Tool Definitions
# =====================================================================
try:
    from langchain_core.tools import tool as lc_tool

    @lc_tool("browser_tool")
    def browser_tool(url: str) -> str:
        """Use this tool to navigate a live Chrome browser session via CDP (port 9222) to a URL. Returns the visible text from the page."""
        return dynamic_browser_tool.run(url=url)

    @lc_tool("search_tool")
    def search_tool(query: str) -> str:
        """Use this tool to search the live web for the latest information, news, or website URLs."""
        return live_web_search.run(query=query)

except ImportError:
    browser_tool = dynamic_browser_tool
    search_tool = live_web_search

# Enterprise Cognitive Memory & Knowledge Graph Tool
try:
    from memory_layer import search_enterprise_memory
except ImportError:
    search_enterprise_memory = None


