import sys
import os
import litellm

# UTF-8 stdout configuration for Windows console compatibility
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, FileReadTool

# Sanitize prompt-caching headers and native tool definitions incompatible with Groq API
_original_completion = litellm.completion
def _groq_safe_completion(*args, **kwargs):
    kwargs.pop("raw_tool_calls", None)
    kwargs.pop("tools", None)  # Bypasses Groq native tool syntax error to enable standard ReAct tool execution
    kwargs.pop("tool_choice", None)  # Prevents tool_choice mismatches during memory extraction
    if "messages" in kwargs:
        for msg in kwargs["messages"]:
            if isinstance(msg, dict):
                msg.pop("cache_breakpoint", None)
                msg.pop("cache_control", None)
    return _original_completion(*args, **kwargs)
litellm.completion = _groq_safe_completion

# Ensure local output persistence directory exists
os.makedirs("output", exist_ok=True)

# Load environment variables securely from .env
load_dotenv()

def run_agency(user_request: str) -> str:
    """
    Executes the MAK AI Business Agency multi-agent workflow for a given user request.
    Features 4 specialized agents: Business Analyst, Data Analyst, Financial Assessor, and MAK (Chief of Operations).
    Returns the final executive report string synthesized by MAK.
    """
    # 1. Initialize LLM with Groq model (llama-3.3-70b-versatile)
    llm = LLM(model="groq/llama-3.3-70b-versatile")

    # 2. Initialize Tools
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()
    file_tool = FileReadTool()

    # 3. Create Agents
    ba = Agent(
        role="Business Analyst",
        goal="Analyze market trends, business strategy, competitive landscape, and commercial opportunities.",
        backstory="You are an expert Business Analyst specializing in market intelligence, deep website analysis, and strategic positioning.",
        tools=[search_tool, scrape_tool],
        verbose=True,
        llm=llm
    )

    da = Agent(
        role="Data Analyst",
        goal="Gather, parse, and analyze quantitative data, local datasets, performance metrics, and statistical benchmarks.",
        backstory="You are a skilled Data Analyst specializing in quantitative research, reading local documents/datasets, and statistical validation.",
        tools=[file_tool],
        verbose=True,
        llm=llm
    )

    assessor = Agent(
        role="Financial Risk & Feasibility Assessor",
        goal="Evaluate the financial viability, ROI, and risk of proposed business strategies.",
        backstory="You are a ruthless financial auditor. You do not care about hype; you only care about margins, costs, and feasible profit.",
        tools=[search_tool],
        verbose=True,
        llm=llm
    )

    mak = Agent(
        role="Chief of Operations",
        goal="Oversee agency operations, coordinate specialists, and deliver executive-level business summaries.",
        backstory="You are MAK, the Chief of Operations for the AI Business Agency. You supervise the Business Analyst, Data Analyst, and Financial Assessor, synthesizing their insights into clear, actionable executive strategy.",
        verbose=True,
        llm=llm
    )

    # 4. Create Tasks dynamically based on user_request
    ba_task = Task(
        description=f"Analyze the strategic and business aspects of the request: '{user_request}'. Search the web and scrape relevant competitor/industry websites to uncover trends and strategic positioning.",
        expected_output="A comprehensive business strategy report detailing market trends, competitor insights, and strategic positioning.",
        agent=ba
    )

    da_task = Task(
        description=f"Conduct a quantitative and data-driven analysis for the request: '{user_request}'. Parse local files or data sources where available, analyzing numbers, metrics, and quantitative benchmarks.",
        expected_output="A detailed quantitative data report summarizing statistics, data points, and performance benchmarks.",
        agent=da
    )

    assessor_task = Task(
        description=f"Critically audit the financial feasibility, estimated ROI, cost structures, and risk factors for the request: '{user_request}', evaluating the findings of the Business and Data Analysts.",
        expected_output="A rigorous financial risk and ROI assessment highlighting margins, projected costs, risks, and commercial viability.",
        agent=assessor
    )

    summary_task = Task(
        description=f"Review the strategic findings from the Business Analyst, quantitative metrics from the Data Analyst, and financial audit from the Financial Assessor regarding '{user_request}'. Synthesize these 3 expert perspectives into an executive-level summary for the user.",
        expected_output="An executive-ready business report incorporating strategic market analysis, quantitative metrics, financial risk assessment, and clear recommendations.",
        agent=mak,
        output_file="output/agency_report.txt"
    )

    # 5. Instantiate Crew with 4 Agents and Sequential Process
    crew = Crew(
        agents=[ba, da, assessor, mak],
        tasks=[ba_task, da_task, assessor_task, summary_task],
        process=Process.sequential,
        memory=True,
        verbose=True
    )

    # 6. Run agency workflow and return final string result
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    test_request = "Analyze the growth potential, unit economics, and risk factors for launching an open-source AI agent SaaS in 2026."
    print("Testing expanded 4-agent MAK AI Business Agency Engine standalone...")
    output = run_agency(test_request)
    print("\n" + "=" * 50)
    print("STANDALONE TEST OUTPUT:")
    print("=" * 50)
    print(output)
