import os
import sys

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from crewai import Agent, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, DirectoryReadTool
from finance_department import get_resilient_llm
from custom_tools import dynamic_browser_tool, post_to_social_api

class MarketingDepartment:
    """
    Enterprise Marketing Department Ecosystem.
    Instantiates specialized marketing agents equipped with web tools, Chrome controller, social action API, and central knowledge base RAG tool,
    bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: LLM = None, knowledge_tool = None):
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
        """SEO & Trend Analyst: Keyword research, search intent & content gap identification."""
        return Agent(
            role="SEO & Trend Analyst",
            goal="Use search and web scraping tools to identify trending keywords, search intent, competitor strategies, and profitable content gaps.",
            backstory="You are an expert SEO & Trend Analyst specializing in search engine optimization, market trend identification, keyword intent clustering, and organic growth strategies.",
            tools=[self.search_tool, self.scrape_tool, dynamic_browser_tool],
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
