import os
import sys
from typing import Optional, List, Any

# Configure UTF-8 encoding for Windows console and loggers
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

try:
    from googlesearch import search
except ImportError:
    search = None

from crewai import Agent, LLM
from crewai.tools import tool
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, DirectoryReadTool
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

from finance_department import get_resilient_llm
from custom_tools import dynamic_browser_tool, post_to_social_api, live_web_search


# =====================================================================
# Step 2: Define SEO Scraper Tool
# =====================================================================
@tool("Live SEO Scraper")
def live_seo_scraper(query: str) -> str:
    """
    Fetches real-time organic Google search engine results for target keywords and competitor domains.
    Extracts top ranking URLs, meta titles, and descriptions/snippets to inform SEO keyword clustering and competitor analysis.

    Args:
        query: The search query, target keyword, or topic to research.
    """
    if search is None:
        return f"Notice: googlesearch-python is not installed. Unable to execute live Google search for '{query}'."

    try:
        results_output = []
        try:
            # Attempt advanced search to extract structured titles, URLs, and descriptions
            raw_results = list(search(query, num_results=10, advanced=True))
            if raw_results and hasattr(raw_results[0], "url"):
                for i, r in enumerate(raw_results[:10], 1):
                    title = getattr(r, "title", "N/A")
                    url = getattr(r, "url", "N/A")
                    desc = getattr(r, "description", "")
                    results_output.append(f"{i}. Title: {title}\n   URL: {url}\n   Snippet: {desc}")
            else:
                for i, r in enumerate(raw_results[:10], 1):
                    results_output.append(f"{i}. URL: {r}")
        except TypeError:
            # Fallback for standard search signature (num=10, stop=10, pause=2.0)
            raw_results = list(search(query, num=10, stop=10, pause=2.0))
            for i, r in enumerate(raw_results[:10], 1):
                results_output.append(f"{i}. URL: {r}")

        if not results_output:
            return f"No ranking Google search results found for query: '{query}'"

        return f"Top Google Ranking Results for '{query}':\n\n" + "\n\n".join(results_output)
    except Exception as e:
        return f"Error executing live SEO scraper for '{query}': {e}"


# =====================================================================
# Step 3: Agent & Department Definitions
# =====================================================================
class MarketingDepartment:
    """
    Enterprise Marketing Department Ecosystem.
    Instantiates specialized marketing agents equipped with live Google SEO scraper, web tools,
    Chrome controller, social action API, and central company knowledge base RAG tool,
    bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: Optional[LLM] = None, knowledge_tool: Any = None):
        self.llm = llm if llm is not None else get_resilient_llm()
        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()
        self.knowledge_tool = knowledge_tool if knowledge_tool is not None else DirectoryReadTool(directory="company_knowledge_base")

    def create_cmo(self) -> Agent:
        """Chief Marketing Officer: Brand strategy, copy review & executive campaign alignment."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Chief Marketing Officer",
            goal="Orchestrate overall brand strategy, review all copy, and ensure the final marketing campaign aligns with executive vision, market positioning, and corporate SOPs.",
            backstory="You are a visionary Chief Marketing Officer (CMO) with a proven track record of scaling high-growth brands. Always search the knowledge base for Brand Guidelines and Tone of Voice before writing or approving any content. Ensure final campaigns align with corporate SOPs.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_seo_analyst(self) -> Agent:
        """SEO & Trend Analyst: Keyword research, SERP analysis & competitor content gap identification."""
        tools = [live_seo_scraper, self.search_tool, self.scrape_tool, dynamic_browser_tool, live_web_search]
        return Agent(
            role="SEO & Trend Analyst",
            goal=(
                "Use the live_seo_scraper tool to analyze current ranking competitors, uncover high-volume target keywords, "
                "evaluate search intent, and identify profitable content gaps. "
                "You MUST run the live_seo_scraper tool to analyze current ranking competitors BEFORE drafting any SEO strategy or keyword recommendations."
            ),
            backstory=(
                "You are an expert SEO & Trend Analyst specializing in search engine optimization, competitor SERP intelligence, "
                "keyword intent clustering, and organic growth strategies. "
                "You MUST run the live_seo_scraper tool to analyze current ranking competitors BEFORE drafting any SEO strategy or keyword recommendations."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_copywriter(self) -> Agent:
        """Lead Copywriter: High-converting landing pages, ad copy & campaign messaging."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Lead Copywriter",
            goal="Draft high-converting landing pages and campaigns based strictly on the SEO Analyst's data, keyword research, and company brand guidelines.",
            backstory="You are an elite Lead Copywriter master of persuasive writing, direct response marketing, and compelling storytelling. Always search the knowledge base for Brand Guidelines and Tone of Voice before writing or approving any content. Convert technical features into irresistible value propositions.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_social_manager(self) -> Agent:
        """Social Media Manager: Platform-specific post optimization & content repurposing."""
        return Agent(
            role="Social Media Manager",
            goal="Draft the posts and then USE the post_to_social_api tool to actually publish them to the simulated web.",
            backstory="You are a dynamic Social Media Manager expert in viral engagement, platform nuances, formatting techniques, and community growth across major social networks.",
            tools=[post_to_social_api],
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def get_marketing_team(self) -> List[Agent]:
        """Returns the complete marketing department team."""
        return [
            self.create_cmo(),
            self.create_seo_analyst(),
            self.create_copywriter(),
            self.create_social_manager()
        ]


def get_marketing_team(llm: Optional[LLM] = None, knowledge_tool: Any = None) -> List[Agent]:
    """
    Module-level factory function returning the Marketing Team:
    1. CMO (Brand strategy & executive alignment)
    2. SEO & Trend Analyst (Equipped with live_seo_scraper tool)
    3. Lead Copywriter (Landing page & copy framework)
    4. Social Media Manager (Social optimization & API publisher)
    """
    dept = MarketingDepartment(llm=llm, knowledge_tool=knowledge_tool)
    return dept.get_marketing_team()


__all__ = [
    "live_seo_scraper",
    "MarketingDepartment",
    "get_marketing_team",
]
