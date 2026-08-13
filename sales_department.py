import os
import sys

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from crewai import Agent, LLM
from crewai_tools import DirectoryReadTool
from finance_department import get_resilient_llm

class SalesDepartment:
    """
    Enterprise Sales Department Ecosystem.
    Instantiates specialized sales agents equipped with Central Company Knowledge Base RAG tool,
    bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: LLM = None, knowledge_tool = None):
        self.llm = llm if llm is not None else get_resilient_llm()
        self.knowledge_tool = knowledge_tool if knowledge_tool is not None else DirectoryReadTool(directory="company_knowledge_base")

    def create_vp_sales(self) -> Agent:
        """VP of Sales: Outreach strategy review, objection handling approval & conversion optimization."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="VP of Sales",
            goal="Review all outreach sequences and objection-handling scripts to ensure high conversion rates, brand alignment, and revenue optimization.",
            backstory="You are a seasoned VP of Sales with a track record of building high-velocity revenue engines. Always search the knowledge base for company pricing, SOPs, and Brand Voice guidelines before approving sales playbooks.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_sdr(self) -> Agent:
        """Senior SDR: Cold outreach, lead scoring & LinkedIn/email prospecting."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Senior SDR",
            goal="Write highly personalized cold emails, LinkedIn DMs, and design lead-scoring criteria based on company SOPs and brand positioning.",
            backstory="You are a top-performing Senior Sales Development Representative (SDR) master of cold outreach, email personalization, and qualification frameworks. Always check the knowledge base for tone of voice, SOPs, and pricing tiers before writing cold outreach.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_solutions_architect(self) -> Agent:
        """Solutions Architect: Objection handling, technical positioning & competitive differentiation."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Solutions Architect",
            goal="Anticipate prospect objections (pricing, competitors, implementation time) and write tactical scripts to overcome them using company SOPs.",
            backstory="You are a senior Solutions Architect expert in technical sales, objection neutralization, value engineering, and competitive displacement strategies. Always consult the knowledge base for technical SOPs and pricing details.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )
