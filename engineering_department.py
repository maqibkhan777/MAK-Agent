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

class EngineeringDepartment:
    """
    Enterprise Engineering Department Ecosystem (The Software House).
    Instantiates specialized software engineering agents equipped with Central Knowledge Base RAG tool
    to read company tech-stack preferences, bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: LLM = None, knowledge_tool = None):
        self.llm = llm if llm is not None else get_resilient_llm()
        self.knowledge_tool = knowledge_tool if knowledge_tool is not None else DirectoryReadTool(directory="company_knowledge_base")

    def create_cto(self) -> Agent:
        """Chief Technology Officer: Design scalable software architecture, framework selection & final code review."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Chief Technology Officer",
            goal="Design scalable software architecture, choose the best frameworks, and review the final codebase.",
            backstory="You are a visionary Chief Technology Officer (CTO) with extensive experience in enterprise system design, cloud-native infrastructure, software engineering best practices, and tech-stack selection. Always check the knowledge base for company tech-stack preferences and engineering standards.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_senior_developer(self) -> Agent:
        """Senior Software Engineer: Clean, highly efficient, well-commented code implementation."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Senior Software Engineer",
            goal="Write clean, highly efficient, and well-commented code based on the CTO's architecture.",
            backstory="You are an elite Senior Software Engineer master of software patterns, clean code design, optimal algorithm complexity, robust error handling, and maintainable software development. Always reference company tech-stack preferences when applicable.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_qa_engineer(self) -> Agent:
        """Lead QA Engineer: Code audit, syntax error checking, edge case testing & security vulnerability analysis."""
        tools = [self.knowledge_tool] if self.knowledge_tool else []
        return Agent(
            role="Lead QA Engineer",
            goal="Ruthlessly review the developer's code for syntax errors, edge cases, and security vulnerabilities, suggesting fixes before final deployment.",
            backstory="You are a meticulous Lead QA Engineer with a reputation for catching latent bugs, race conditions, memory leaks, input sanitization flaws, and security exploits. You audit all code thoroughly to ensure production stability.",
            tools=tools,
            verbose=True,
            memory=True,
            llm=self.llm
        )
