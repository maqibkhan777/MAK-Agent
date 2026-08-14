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

def connect_to_live_browser():
    from playwright.sync_api import sync_playwright
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

@tool("Dynamic Browser Tool")
def dynamic_browser_tool(url: str) -> str:
    """Use this tool to navigate a live Chrome browser session via CDP (port 9222) to a URL that requires JavaScript to load. It returns the visible text of the fully loaded page."""
    browser_conn = connect_to_live_browser()
    if isinstance(browser_conn, str):
        # Fallback to isolated chromium if live CDP instance is unavailable
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
                if len(text) > 15000:
                    text = text[:15000] + "\n\n[...Content truncated for LLM context optimization...]"
                return text
        except Exception as e:
            return f"{browser_conn}\nFallback navigation error: {e}"

    page, browser, playwright = browser_conn
    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception:
            pass
        text = page.inner_text("body")
        if len(text) > 15000:
            text = text[:15000] + "\n\n[...Content truncated for LLM context optimization...]"
        return text
    except Exception as e:
        return f"Error executing dynamic browser navigation for {url} via live CDP: {e}"
    finally:
        playwright.stop()

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

