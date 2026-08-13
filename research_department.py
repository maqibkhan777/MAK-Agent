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
    import arxiv
except ImportError:
    arxiv = None

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
# Step 2: Define ArXiv Academic Scraper Tool
# =====================================================================
@tool("ArXiv Academic Scraper")
def arxiv_academic_scraper(query: str) -> str:
    """
    Searches the ArXiv scientific repository for peer-reviewed academic papers and scientific preprints.
    Retrieves the top 3 papers sorted by relevance, including title, authors, publication date, abstract/summary, and paper URL.

    Args:
        query: The scientific or academic search query (e.g. 'transformer architecture attention', 'quantum computing error correction').
    """
    if arxiv is None:
        return f"Notice: arxiv library is not available. Unable to search academic papers for '{query}'."

    try:
        clean_query = query.strip()
        search_query = arxiv.Search(
            query=clean_query,
            max_results=3,
            sort_by=arxiv.SortCriterion.Relevance
        )

        # Support both modern Client API and legacy Search API
        try:
            client = arxiv.Client()
            results = list(client.results(search_query))
        except (AttributeError, TypeError):
            results = list(search_query.results())

        if not results:
            return f"No academic papers found on ArXiv for query: '{clean_query}'"

        papers_output = []
        for i, paper in enumerate(results, 1):
            title = paper.title.strip().replace("\n", " ")
            authors = ", ".join([a.name for a in paper.authors]) if paper.authors else "Unknown Authors"
            pub_date = paper.published.strftime("%Y-%m-%d") if hasattr(paper.published, "strftime") else str(paper.published)
            summary = paper.summary.strip().replace("\n", " ")
            url = paper.entry_id if hasattr(paper, "entry_id") else (paper.pdf_url if hasattr(paper, "pdf_url") else "N/A")

            papers_output.append(
                f"=== Paper {i}: {title} ===\n"
                f"• Authors: {authors}\n"
                f"• Published Date: {pub_date}\n"
                f"• Paper URL: {url}\n"
                f"• Abstract / Summary:\n{summary}"
            )

        return f"Top ArXiv Peer-Reviewed Scientific Papers for '{clean_query}':\n\n" + "\n\n".join(papers_output)
    except Exception as e:
        return f"Error executing ArXiv academic search for '{query}': {e}"


# =====================================================================
# Step 3: Agent & Department Definitions
# =====================================================================
class ResearchDepartment:
    """
    Enterprise Research Department Ecosystem.
    Instantiates specialized academic research agents equipped with real-time ArXiv scientific paper scraping,
    live web intelligence, central company knowledge base RAG tool, and bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: Optional[LLM] = None, knowledge_tool: Any = None):
        self.llm = llm if llm is not None else get_resilient_llm()
        self.knowledge_tool = knowledge_tool if knowledge_tool is not None else DirectoryReadTool(directory="company_knowledge_base")

    def create_academic_researcher(self) -> Agent:
        """
        Academic Researcher: Conducts rigorous scientific literature reviews using peer-reviewed papers from ArXiv.
        Strictly mandated to verify scientific claims against empirical ArXiv papers.
        """
        tools = (
            [arxiv_academic_scraper, self.knowledge_tool, live_web_search]
            if self.knowledge_tool
            else [arxiv_academic_scraper, live_web_search]
        )
        return Agent(
            role="Academic Researcher",
            goal=(
                "Conduct rigorous scientific and academic literature reviews using real peer-reviewed scientific papers. "
                "You MUST run the arxiv_academic_scraper tool to pull real, peer-reviewed scientific papers "
                "BEFORE drafting any research summaries, educational guides, or factual reports. Do not hallucinate science."
            ),
            backstory=(
                "You are a distinguished Academic Researcher and Senior Research Fellow with deep expertise in scientific inquiry, "
                "empirical verification, and academic citation standards. You rigorously investigate scientific domains using the ArXiv repository. "
                "You MUST run the arxiv_academic_scraper tool to pull real, peer-reviewed scientific papers "
                "BEFORE drafting any research summaries, educational guides, or factual reports. Do not hallucinate science. "
                "You translate complex theoretical publications into accurate, structured, and factual research intelligence."
            ),
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def get_research_team(self) -> List[Agent]:
        """Returns the research department team."""
        return [self.create_academic_researcher()]


def get_research_team(llm: Optional[LLM] = None, knowledge_tool: Any = None) -> List[Agent]:
    """
    Module-level factory function returning the Research Team:
    1. Academic Researcher (Equipped with ArXiv Academic Scraper for empirical scientific research)
    """
    dept = ResearchDepartment(llm=llm, knowledge_tool=knowledge_tool)
    return dept.get_research_team()


__all__ = [
    "arxiv_academic_scraper",
    "ResearchDepartment",
    "get_research_team",
]
