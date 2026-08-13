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

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field, field_validator
from crewai import Agent, LLM
from crewai.tools import tool
from crewai_tools import DirectoryReadTool
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

from finance_department import get_resilient_llm
from custom_tools import live_web_search


# =====================================================================
# Step 2: Define Guardrails (Structured Output)
# =====================================================================
class SalesEmail(BaseModel):
    """
    Structured Guardrail Model for B2B Sales Outreach.

    Strict Constraints & Guidelines:
    - Maintain a polished, professional, executive B2B tone of voice at all times.
    - Deliver clear, consultative value propositions addressing prospect pain points.
    - FORBIDDEN PHRASES: Never use spammy, misleading, or overpromising expressions 
      such as "100% free", "guarantee", "risk-free guarantee", or hyperbolic claims.
    """
    subject: str = Field(
        ...,
        description="Subject line for the sales email. Must be compelling, concise, and professional. Strictly prohibited from containing spam triggers or phrases like '100% free' or 'guarantee'."
    )
    body: str = Field(
        ...,
        description="Body content of the sales email. Must maintain an executive, consultative tone with clear value articulation and call-to-action. Must strictly never use phrases like '100% free' or 'guarantee'."
    )

    @field_validator("subject", "body")
    @classmethod
    def validate_guardrail_phrases(cls, value: str) -> str:
        prohibited_phrases = ["100% free", "guarantee"]
        lower_value = value.lower()
        for phrase in prohibited_phrases:
            if phrase in lower_value:
                raise ValueError(
                    f"Forbidden phrase '{phrase}' detected in sales output. "
                    "Sales outreach must maintain strict professional tone and avoid prohibited promotional language."
                )
        return value


# =====================================================================
# Step 2: Define B2B Lead Scraping Tool
# =====================================================================
@tool("B2B Company Scraper")
def b2b_company_scraper(query: str) -> str:
    """
    Scrapes the homepage of a target B2B company or organization to extract core product positioning, value proposition, and messaging.
    Searches DuckDuckGo for the official URL, fetches page HTML, parses visible paragraph text, and truncates to 1,500 characters.

    Args:
        query: The target company name (e.g., 'Snowflake', 'Stripe', 'Datadog') or industry keyword.
    """
    try:
        clean_query = query.strip()
        # 1. Use DDGS().text(query, max_results=1) to find the top URL for the target company
        results = list(DDGS().text(clean_query, max_results=1))
        if not results or not results[0].get("href"):
            return f"No company URL found for query: '{clean_query}'"

        target_url = results[0].get("href")
        title = results[0].get("title", clean_query)

        # 2. Use requests.get(url, timeout=10) to fetch the page HTML
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()

        # 3. Use BeautifulSoup to extract visible paragraph (<p>) text from the homepage
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]

        if not paragraphs:
            page_text = " ".join(soup.stripped_strings)
        else:
            page_text = "\n".join(paragraphs)

        # 4. Truncate the extracted text to the first 1,500 characters
        truncated_text = page_text[:1500].strip()

        output = (
            f"=== B2B Company Intelligence for {title} ===\n"
            f"Official Website: {target_url}\n\n"
            f"Core Homepage Messaging:\n{truncated_text}\n"
        )
        return output
    except Exception as e:
        return f"Error scraping company intelligence for '{query}': {e}"


# =====================================================================
# Step 3 & 4: Agent & Department Definitions
# =====================================================================
class SalesDepartment:
    """
    Enterprise Sales Department Ecosystem.
    Instantiates specialized sales agents equipped with Central Company Knowledge Base RAG tool,
    live DuckDuckGo & BeautifulSoup B2B scrapers, web intelligence, and bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: Optional[LLM] = None, knowledge_tool: Any = None):
        self.llm = llm if llm is not None else get_resilient_llm()
        self.knowledge_tool = knowledge_tool if knowledge_tool is not None else DirectoryReadTool(directory="company_knowledge_base")

    def create_lead_gen_specialist(self) -> Agent:
        """Lead Generation Specialist: Tasked with scraping target company websites and formatting structured prospect dossiers."""
        tools = (
            [b2b_company_scraper, self.knowledge_tool, live_web_search]
            if self.knowledge_tool
            else [b2b_company_scraper, live_web_search]
        )
        return Agent(
            role="Lead Generation Specialist",
            goal=(
                "Identify high-value B2B target accounts, prospective companies, key decision-makers, and format structured lead intelligence dossiers. "
                "You MUST run the b2b_company_scraper tool to find and read the target company's website BEFORE passing the lead dossier to the VP of Sales."
            ),
            backstory=(
                "You are an elite B2B Lead Generation Specialist with comprehensive expertise in ICP (Ideal Customer Profile) "
                "qualification, account-based prospecting, industry vertical analysis, and decision-maker discovery. "
                "You MUST run the b2b_company_scraper tool to find and read the target company's website BEFORE passing the lead dossier to the VP of Sales. "
                "You gather verified company pain points, business context, and recent market developments using search tools "
                "and format them into crisp, actionable prospect profiles."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_vp_sales(self) -> Agent:
        """VP of Sales: Tasked with taking Lead Gen output and drafting highly targeted cold emails adhering strictly to SalesEmail guardrails."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="VP of Sales",
            goal=(
                "Transform structured B2B lead generation data into highly targeted, consultative cold emails conforming strictly to the "
                "SalesEmail Pydantic schema. Enforce an executive tone, clear value proposition, and ensure zero forbidden phrases "
                "('100% free' or 'guarantee') are present."
            ),
            backstory=(
                "You are a seasoned VP of Sales with a proven track record of architecting high-converting outbound sales engines. "
                "You write hyper-personalized, value-driven executive outreach while strictly enforcing corporate compliance, brand voice, "
                "and communication guardrails. You ensure every email adheres to the SalesEmail schema without spammy claims."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_sdr(self) -> Agent:
        """Senior SDR (Lead Generation & Outreach): Maintained for backwards compatibility with main.py pipeline."""
        return self.create_lead_gen_specialist()

    def create_solutions_architect(self) -> Agent:
        """Solutions Architect: Objection handling, technical positioning & competitive differentiation (main.py compatibility)."""
        tools = [self.knowledge_tool, live_web_search] if self.knowledge_tool else [live_web_search]
        return Agent(
            role="Solutions Architect",
            goal="Anticipate prospect objections (pricing, competitors, implementation time) and write tactical scripts to overcome them using company SOPs. Always search the live web for the most recent data before making conclusions.",
            backstory="You are a senior Solutions Architect expert in technical sales, objection neutralization, value engineering, and competitive displacement strategies. Always consult the knowledge base for technical SOPs and pricing details.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def get_sales_team(self) -> List[Agent]:
        """Returns the core two-agent sales team: Lead Generation Specialist (with B2B scraper) and VP of Sales."""
        return [self.create_lead_gen_specialist(), self.create_vp_sales()]


def get_sales_team(llm: Optional[LLM] = None, knowledge_tool: Any = None) -> List[Agent]:
    """
    Module-level factory function returning the core two-agent Sales Team:
    1. Lead Generation Specialist (Equipped with DuckDuckGo + BeautifulSoup b2b_company_scraper tool)
    2. VP of Sales (Targeted outreach drafting adhering strictly to SalesEmail guardrails)
    """
    dept = SalesDepartment(llm=llm, knowledge_tool=knowledge_tool)
    return dept.get_sales_team()


__all__ = [
    "SalesEmail",
    "b2b_company_scraper",
    "SalesDepartment",
    "get_sales_team",
]
