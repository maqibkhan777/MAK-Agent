import sys
import os
import time
import json
import re
import litellm
from typing import TypedDict, Annotated

# UTF-8 stdout configuration for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import DirectoryReadTool
from langgraph.graph import StateGraph, START, END
from finance_department import FinanceDepartment, get_resilient_llm
from marketing_department import MarketingDepartment
from sales_department import SalesDepartment
from engineering_department import EngineeringDepartment

# Auto-create Central Company Brain Knowledge Base directory
KNOWLEDGE_BASE_DIR = os.path.join(os.getcwd(), "company_knowledge_base")
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

# Initialize RAG DirectoryReadTool pointed at Central Company Brain
knowledge_tool = DirectoryReadTool(directory="company_knowledge_base")

# Ensure local output persistence directory exists
os.makedirs("output", exist_ok=True)

# Load environment variables securely from .env
load_dotenv()

# =====================================================================
# State Reducer for Dynamic Parallel Execution
# =====================================================================
def merge_dict(a: dict, b: dict) -> dict:
    """Merges dictionary outputs from parallel department nodes into shared state."""
    res = (a or {}).copy()
    res.update(b or {})
    return res

# =====================================================================
# 1. LangGraph Shared State Definition
# =====================================================================
class AgencyState(TypedDict):
    user_request: str
    triage_output: str
    selected_departments: list[str]
    raw_department_reports: Annotated[dict[str, str], merge_dict]
    department_summaries: dict[str, str]
    final_response: str
    final_cfo_decision: str


# =====================================================================
# Helper: Token Compression Function
# =====================================================================
def _compress_report(raw_report: str, department_name: str, summarizer: Agent) -> str:
    """Uses Context Compression Specialist to compress raw report into a high-density <=300 word summary."""
    summary_task = Task(
        description=f"Compress the following raw report from {department_name} into a strict, high-density 300-word bulleted summary. Retain all quantitative metrics, financial figures, and core technical arguments. Remove all fluff and pleasantries.\n\nRAW REPORT:\n{raw_report}",
        expected_output="A high-density bulleted summary under 300 words preserving all quantitative metrics and core findings.",
        agent=summarizer
    )
    crew = Crew(agents=[summarizer], tasks=[summary_task], cache=True, verbose=True)
    res = crew.kickoff()
    return str(res)


# =====================================================================
# 2. LangGraph Node Definitions (Stateful Execution Pipeline)
# =====================================================================

def node_triage(state: AgencyState) -> dict:
    """Chief of Staff (Triage): Searches Knowledge Base SOPs, analyzes user request, and outputs strict raw JSON list of departments to activate."""
    llm = get_resilient_llm()
    triage_agent = Agent(
        role="Chief of Staff (Triage)",
        goal="You are the Chief of Staff. Search the knowledge base for any company rules, pricing, or SOPs, then output a valid JSON list of required departments.",
        backstory=(
            "You are the Chief of Staff for the Enterprise Agency. Before routing the task, search the knowledge base "
            "for any company rules, pricing, or SOPs relevant to the user's request. Pass this context along.\n"
            "Your ONLY job is to read the user's prompt and output a valid JSON list of required departments following strict decision rules:\n"
            "The Education Rule: If the user asks to 'explain', 'learn', 'what is', or mentions being a 'beginner', "
            "this is purely an educational request. You MUST output exactly [\"tutor\"] and absolutely nothing else. "
            "Do not activate any analytical, marketing, or sales departments.\n"
            "The Marketing Rule: If the user asks to write content, generate ads, find keywords, build a marketing strategy, or plan a campaign, "
            "output exactly [\"marketing\"].\n"
            "The Sales Rule: If the user asks to write cold emails, handle objections, score leads, or build a sales process, "
            "output strictly [\"sales\"].\n"
            "The Engineering Rule: If the user asks to write code, build an app, debug a script, or design software architecture, "
            "output strictly [\"engineering\"].\n"
            "The Analysis Rule: Only activate finance departments like cfo, corp_finance, or valuation if the user explicitly "
            "asks you to analyze a business, run numbers, calculate ROI, or evaluate an acquisition."
        ),
        tools=[knowledge_tool],
        verbose=True,
        llm=llm
    )

    triage_task = Task(
        description=(
            f"Analyze the user request:\n'{state['user_request']}'\n\n"
            "Before routing the task, search the knowledge base for any company rules, pricing, or SOPs relevant to the user's request. "
            "You are the Chief of Staff. Your ONLY job is to read the user's prompt and output a valid JSON list of required departments. "
            "You must follow these strict routing rules:\n\n"
            "The Education Rule: If the user asks to \"explain\", \"learn\", \"what is\", or mentions being a \"beginner\", "
            "this is purely an educational request. You MUST output exactly [\"tutor\"] and absolutely nothing else.\n\n"
            "The Marketing Rule: If the user asks to write content, generate ads, find keywords, build a marketing strategy, or plan a campaign, "
            "output exactly [\"marketing\"].\n\n"
            "The Sales Rule: If the user asks to write cold emails, handle objections, score leads, or build a sales process, "
            "output strictly [\"sales\"].\n\n"
            "The Engineering Rule: If the user asks to write code, build an app, debug a script, or design software architecture, "
            "output strictly [\"engineering\"].\n\n"
            "The Analysis Rule: Only activate finance departments like cfo, corp_finance, or valuation if the user explicitly asks you to "
            "analyze a business, run numbers, calculate ROI, or evaluate an acquisition.\n\n"
            "Available departments: [\"cfo\", \"corp_finance\", \"risk\", \"treasury\", \"capital_structure\", \"m_and_a\", \"controller\", \"portfolio\", \"valuation\", \"credit\", \"inventory\", \"planner\", \"tutor\", \"marketing\", \"sales\", \"engineering\"].\n\n"
            "Format: Output ONLY the raw JSON array. Example: [\"engineering\"] or [\"sales\"] or [\"marketing\"] or [\"tutor\"] or [\"m_and_a\", \"risk\"]."
        ),
        expected_output='ONLY the raw JSON array. Example: ["engineering"].',
        agent=triage_agent
    )

    crew = Crew(agents=[triage_agent], tasks=[triage_task], cache=True, verbose=True)
    raw_output = str(crew.kickoff()).strip()
    return {"triage_output": raw_output}


def node_tutor(state: AgencyState) -> dict:
    """Finance Tutor Node: Explains complex financial concepts step-by-step for educational requests."""
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    tutor = dept.create_finance_tutor()

    task = Task(
        description=f"Provide a clear, beginner-friendly, step-by-step educational breakdown explaining key financial concepts and formulas for: '{state['user_request']}'.",
        expected_output="Clear step-by-step educational tutorial explaining financial concepts with practical examples.",
        agent=tutor
    )
    crew = Crew(agents=[tutor], tasks=[task], cache=True, verbose=True)
    res = str(crew.kickoff())
    return {"final_response": res}


def node_marketing(state: AgencyState) -> dict:
    """Marketing Department Node: Executes a sequential mini-Crew (SEO Analyst -> Copywriter -> Social Manager -> CMO) equipped with Central Knowledge Base."""
    llm = get_resilient_llm()
    dept = MarketingDepartment(llm=llm, knowledge_tool=knowledge_tool)

    cmo = dept.create_cmo()
    seo_analyst = dept.create_seo_analyst()
    copywriter = dept.create_copywriter()
    social_manager = dept.create_social_manager()

    task1_seo = Task(
        description=f"Conduct SEO and trend research for: '{state['user_request']}'. Identify high-volume target keywords, search intent, competitor strategies, and content gaps.",
        expected_output="Comprehensive SEO keyword research report with target keywords, search intent analysis, and content strategy recommendations.",
        agent=seo_analyst
    )

    task2_copy = Task(
        description=f"Draft a high-converting landing page and ad copy framework for: '{state['user_request']}'. Always search the central knowledge base for Brand Guidelines, Tone of Voice, and Pricing SOPs before writing copy.",
        expected_output="High-converting marketing copy framework aligned with corporate Brand Guidelines, including headline, value proposition, landing page copy, and CTA.",
        agent=copywriter
    )

    task3_social = Task(
        description=f"Repurpose the landing page copy into platform-specific social posts for LinkedIn, Twitter/X, and Instagram.",
        expected_output="Platform-specific social media posts optimized for LinkedIn, Twitter/X, and Instagram with engaging hooks and relevant hashtags.",
        agent=social_manager
    )

    task4_cmo = Task(
        description=f"Review, refine, and orchestrate all campaign deliverables (SEO, Copy, Social Posts) for: '{state['user_request']}'. Always search the central knowledge base for Brand Guidelines and Tone of Voice to ensure strict executive alignment.",
        expected_output="Final CMO-approved strategic marketing campaign aligned with corporate Brand Guidelines and ready for launch.",
        agent=cmo
    )

    marketing_crew = Crew(
        agents=[seo_analyst, copywriter, social_manager, cmo],
        tasks=[task1_seo, task2_copy, task3_social, task4_cmo],
        process=Process.sequential,
        cache=True,
        verbose=True
    )

    raw_campaign = str(marketing_crew.kickoff())
    return {"final_response": raw_campaign}


def node_sales(state: AgencyState) -> dict:
    """Sales Department Node: Executes a sequential mini-Crew (Senior SDR -> Solutions Architect -> VP of Sales) equipped with Central Knowledge Base."""
    llm = get_resilient_llm()
    dept = SalesDepartment(llm=llm, knowledge_tool=knowledge_tool)

    vp_sales = dept.create_vp_sales()
    sdr = dept.create_sdr()
    solutions_architect = dept.create_solutions_architect()

    task1_sdr = Task(
        description=f"Draft highly personalized cold outreach emails, LinkedIn DM sequences, and define lead-scoring criteria for: '{state['user_request']}'. Always search the central knowledge base for brand voice, tone, and pricing SOPs.",
        expected_output="Personalized cold email templates, LinkedIn DM sequences, and lead-scoring criteria matrix.",
        agent=sdr
    )

    task2_sa = Task(
        description=f"Anticipate key prospect objections (pricing, competition, implementation timeline, ROI) for: '{state['user_request']}' and write tactical objection-handling scripts using knowledge base SOPs.",
        expected_output="Tactical objection-handling battlecard and competitive displacement scripts.",
        agent=solutions_architect
    )

    task3_vp = Task(
        description=f"Review, refine, and optimize the complete sales playbook (outreach sequences & objection handling) for: '{state['user_request']}'. Ensure brand alignment, high conversion potential, and deliver the final approved sales playbook.",
        expected_output="Final VP of Sales-approved enterprise sales playbook ready for team execution.",
        agent=vp_sales
    )

    sales_crew = Crew(
        agents=[sdr, solutions_architect, vp_sales],
        tasks=[task1_sdr, task2_sa, task3_vp],
        process=Process.sequential,
        cache=True,
        verbose=True
    )

    raw_playbook = str(sales_crew.kickoff())
    return {"final_response": raw_playbook}


def node_engineering(state: AgencyState) -> dict:
    """Engineering Department Node: Executes a sequential mini-Crew (CTO -> Senior Developer -> Lead QA Engineer -> CTO) equipped with Central Knowledge Base."""
    llm = get_resilient_llm()
    dept = EngineeringDepartment(llm=llm, knowledge_tool=knowledge_tool)

    cto = dept.create_cto()
    senior_dev = dept.create_senior_developer()
    qa_engineer = dept.create_qa_engineer()

    task1_cto = Task(
        description=f"Design a scalable software architecture, select optimal tech-stack frameworks, and design system components for: '{state['user_request']}'. Always search the central knowledge base for company tech-stack preferences and engineering SOPs.",
        expected_output="Comprehensive software architecture design document specifying framework selection, data flow, component breakdown, and technical requirements.",
        agent=cto
    )

    task2_dev = Task(
        description=f"Based strictly on the CTO's software architecture design, write clean, highly efficient, and well-commented code for: '{state['user_request']}'. Ensure modular structure and robust implementation.",
        expected_output="Complete, production-ready, clean, and well-commented source code implementing the CTO's architecture.",
        agent=senior_dev
    )

    task3_qa = Task(
        description=f"Ruthlessly review the Senior Software Engineer's code for syntax errors, edge cases, performance bottlenecks, and security vulnerabilities. Provide detailed audit findings and suggested fixes.",
        expected_output="Lead QA Engineer code audit report detailing syntax checks, security vulnerabilities, edge case tests, and code fixes.",
        agent=qa_engineer
    )

    task4_cto_review = Task(
        description=f"Perform final executive code and architecture review for: '{state['user_request']}'. Synthesize the developer's implementation and QA audit fixes into the final, polished production deliverable.",
        expected_output="Final CTO-approved software architecture and production-ready code deliverable.",
        agent=cto
    )

    engineering_crew = Crew(
        agents=[cto, senior_dev, qa_engineer, cto],
        tasks=[task1_cto, task2_dev, task3_qa, task4_cto_review],
        process=Process.sequential,
        cache=True,
        verbose=True
    )

    raw_code_output = str(engineering_crew.kickoff())
    return {"final_response": raw_code_output}


def node_corp_finance(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_corp_finance_analyst()

    task = Task(
        description=f"Evaluate capital investment viability, projected cash flows, Net Present Value (NPV), Internal Rate of Return (IRR), and hurdle rate for: '{state['user_request']}'.",
        expected_output="Detailed corporate finance valuation report with DCF, NPV, IRR, and payback horizons.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Corporate Finance": raw_output}}


def node_risk(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_risk_manager()

    task = Task(
        description=f"Conduct quantitative risk assessment for: '{state['user_request']}'. Analyze downside risk, market volatility, liquidity risk, Value at Risk (VaR), and stress testing scenarios.",
        expected_output="Comprehensive risk management report with stress tests, downside risks, and mitigation strategies.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Risk Management": raw_output}}


def node_treasury(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_treasury_agent()

    task = Task(
        description=f"Analyze liquidity requirements and cash conversion cycles for: '{state['user_request']}'. Evaluate working capital impact, liquidity risk, and short-term funding availability.",
        expected_output="Treasury liquidity assessment detailing working capital needs, cash reserves, and funding availability.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Treasury Management": raw_output}}


def node_capital_structure(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_capital_structure_analyst()

    task = Task(
        description=f"Determine optimal debt/equity financing mix and WACC impact for: '{state['user_request']}'. Calculate cost of capital, interest coverage, leverage ratios, and optimal financing allocation.",
        expected_output="Capital structure optimization analysis detailing debt/equity mix, leverage ratios, and WACC impact.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Capital Structure": raw_output}}


def node_m_and_a(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_m_and_a_analyst()

    task = Task(
        description=f"Evaluate mergers, acquisitions, takeovers, deal valuation, and strategic synergies for: '{state['user_request']}'. Assess accretion/dilution, deal structuring, and post-merger integration costs.",
        expected_output="M&A valuation report detailing takeover pricing, synergy analysis, accretion/dilution, and transaction structuring.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"M&A Valuation": raw_output}}


def node_controller(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_financial_controller()

    task = Task(
        description=f"Evaluate accounting accuracy, internal controls, regulatory audit compliance, and US GAAP/IFRS standards for: '{state['user_request']}'. Audit financial statements and reporting risks.",
        expected_output="Financial Controller audit report detailing compliance, internal controls, GAAP/IFRS accounting, and risk controls.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Financial Controller": raw_output}}


def node_portfolio(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_portfolio_manager()

    task = Task(
        description=f"Analyze asset allocation, diversification strategies, and risk-adjusted return optimization (Sharpe Ratio) for: '{state['user_request']}'. Conduct Modern Portfolio Theory (MPT) evaluation.",
        expected_output="Portfolio management report detailing asset allocation, diversification, Sharpe ratio, and risk-adjusted return expectations.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Portfolio Management": raw_output}}


def node_valuation(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_valuation_analyst()

    task = Task(
        description=f"Perform enterprise valuation for: '{state['user_request']}' using Discounted Cash Flow (DCF), comparable company analysis (Trading Comps), and precedent transactions.",
        expected_output="Comprehensive enterprise valuation report with DCF sensitivity, trading multiples, and fair value range.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Enterprise Valuation": raw_output}}


def node_credit(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_credit_analyst()

    task = Task(
        description=f"Assess borrower creditworthiness, Debt Service Coverage Ratio (DSCR), default risk, and credit ratings for: '{state['user_request']}'. Evaluate balance sheet leverage and debt capacity.",
        expected_output="Credit risk assessment report detailing DSCR, default risk, covenant terms, and credit rating recommendation.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Credit Risk Analysis": raw_output}}


def node_inventory(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_inventory_manager()

    task = Task(
        description=f"Evaluate Economic Order Quantity (EOQ), inventory carrying cost minimization, and supply chain working capital efficiency for: '{state['user_request']}'.",
        expected_output="Inventory management report detailing EOQ formulation, holding cost minimization, and supply chain working capital strategy.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Inventory Management": raw_output}}


def node_planner(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_financial_planner()

    task = Task(
        description=f"Analyze revenue forecasting, budget variance, and operational expense (OpEx) budgeting for: '{state['user_request']}'. Develop rolling forecasts and budget variance models.",
        expected_output="FP&A report detailing revenue drivers, OpEx projections, budget variance analysis, and rolling forecast targets.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Financial Planning & Analysis": raw_output}}


def node_cfo_direct(state: AgencyState) -> dict:
    """Direct CFO Node: Executes when CFO is directly requested without intermediate department nodes."""
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    cfo = dept.create_cfo()

    task = Task(
        description=f"Formulate definitive executive capital allocation strategy and recommendations for: '{state['user_request']}'.",
        expected_output="Definitive CFO executive strategy report detailing capital allocation decisions, risk mitigation, and board recommendations.",
        agent=cfo,
        output_file="output/agency_report.txt"
    )
    crew = Crew(agents=[cfo], tasks=[task], cache=True, verbose=True)
    res = str(crew.kickoff())
    return {"final_cfo_decision": res, "final_response": res}


def node_summarizer(state: AgencyState) -> dict:
    """Summarizer Node: Compresses raw corporate department reports into high-density <=300 word summaries."""
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    summarizer = dept.create_summarizer()

    raw_reports = state.get("raw_department_reports", {})
    compressed_summaries = {}

    for dept_name, raw_text in raw_reports.items():
        compressed = _compress_report(raw_text, dept_name, summarizer)
        compressed_summaries[dept_name] = compressed

    return {"department_summaries": compressed_summaries}


def node_cfo(state: AgencyState) -> dict:
    """CFO Node: Executive synthesis of all activated departmental summaries."""
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    cfo = dept.create_cfo()

    dept_summaries = state.get("department_summaries", {})
    if not dept_summaries:
        summaries_text = f"Direct Analysis for: {state['user_request']}"
    else:
        summaries_text = "\n\n".join(
            [f"=== {name} Report ===\n{summary}" for name, summary in dept_summaries.items()]
        )

    task = Task(
        description=(
            f"Formulate definitive board capital allocation decision and strategic recommendations for: '{state['user_request']}'.\n\n"
            f"Synthesize the compressed departmental reports from activated departments:\n\n{summaries_text}"
        ),
        expected_output="Definitive CFO executive strategy report detailing capital allocation decisions, risk mitigation, valuation/WACC optimization, and board recommendations.",
        agent=cfo,
        output_file="output/agency_report.txt"
    )
    crew = Crew(agents=[cfo], tasks=[task], cache=True, verbose=True)
    res = str(crew.kickoff())
    return {"final_cfo_decision": res, "final_response": res}


# =====================================================================
# 3. Dynamic Conditional Routing & Graph Topology
# =====================================================================
ALL_DEPARTMENTS = [
    "cfo", "corp_finance", "risk", "treasury", "capital_structure", "m_and_a",
    "controller", "portfolio", "valuation", "credit", "inventory", "planner", "tutor", "marketing", "sales", "engineering"
]

def route_from_triage(state: AgencyState) -> list[str]:
    r"""
    Safely extracts and parses the JSON array from Triage node's output string using multi-stage RegEx.
    1. Uses re.search(r'\[.*?\]', text, re.DOTALL) to locate the JSON array.
    2. Uses json.loads() direct parsing.
    3. Uses keyword extraction fallback if JSON array is absent (e.g. 'engineering', 'sales', 'marketing', 'tutor').
    4. Defaults to ["cfo"] only if all extraction methods fail.
    """
    text = state.get("triage_output", "").strip()

    try:
        # Stage 1: RegEx extraction for JSON array pattern [ ... ]
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            parsed = json.loads(json_str)

            if isinstance(parsed, list):
                valid_depts = [d for d in parsed if isinstance(d, str) and d in ALL_DEPARTMENTS]
                if valid_depts:
                    if "engineering" in valid_depts:
                        print(f"\n[Route From Triage] Engineering request detected. Enforcing single engineering path: ['engineering']\n")
                        return ["engineering"]
                    if "tutor" in valid_depts:
                        print(f"\n[Route From Triage] Educational 'tutor' requested. Enforcing single tutor path: ['tutor']\n")
                        return ["tutor"]
                    if "sales" in valid_depts:
                        print(f"\n[Route From Triage] Sales request detected. Enforcing single sales path: ['sales']\n")
                        return ["sales"]
                    if "marketing" in valid_depts:
                        print(f"\n[Route From Triage] Marketing request detected. Enforcing single marketing path: ['marketing']\n")
                        return ["marketing"]
                    print(f"\n[Route From Triage] Successfully extracted departments via RegEx: {valid_depts}\n")
                    return valid_depts

        # Stage 2: Direct json.loads fallback if regex pattern matched non-array or raw JSON
        parsed = json.loads(text)
        if isinstance(parsed, list):
            valid_depts = [d for d in parsed if isinstance(d, str) and d in ALL_DEPARTMENTS]
            if valid_depts:
                if "engineering" in valid_depts:
                    print(f"\n[Route From Triage] Engineering request detected. Enforcing single engineering path: ['engineering']\n")
                    return ["engineering"]
                if "tutor" in valid_depts:
                    print(f"\n[Route From Triage] Educational 'tutor' requested. Enforcing single tutor path: ['tutor']\n")
                    return ["tutor"]
                if "sales" in valid_depts:
                    print(f"\n[Route From Triage] Sales request detected. Enforcing single sales path: ['sales']\n")
                    return ["sales"]
                if "marketing" in valid_depts:
                    print(f"\n[Route From Triage] Marketing request detected. Enforcing single marketing path: ['marketing']\n")
                    return ["marketing"]
                print(f"\n[Route From Triage] Successfully parsed departments directly: {valid_depts}\n")
                return valid_depts

    except Exception as e:
        print(f"\n[Triage Routing Notice] JSON parsing notice on output: '{text}'. Falling back to keyword scanner. Error: {e}\n")

    # Stage 3: Robust Keyword Fallback Scanner (prevents unparsed conversational output from defaulting to CFO)
    lower_text = text.lower()
    if "engineering" in lower_text or "code" in lower_text or "app" in lower_text or "developer" in lower_text or "software" in lower_text:
        print(f"\n[Route From Triage Keyword Fallback] Extracted 'engineering' from output text. Enforcing ['engineering']\n")
        return ["engineering"]
    if "tutor" in lower_text or "education" in lower_text:
        print(f"\n[Route From Triage Keyword Fallback] Extracted 'tutor' from output text. Enforcing ['tutor']\n")
        return ["tutor"]
    if "sales" in lower_text or "sdr" in lower_text or "outreach" in lower_text:
        print(f"\n[Route From Triage Keyword Fallback] Extracted 'sales' from output text. Enforcing ['sales']\n")
        return ["sales"]
    if "marketing" in lower_text or "cmo" in lower_text or "copywriter" in lower_text:
        print(f"\n[Route From Triage Keyword Fallback] Extracted 'marketing' from output text. Enforcing ['marketing']\n")
        return ["marketing"]

    print(f"\n[Triage Routing Warning] Could not extract valid departments from output: '{text}'. Defaulting to ['cfo'].\n")
    return ["cfo"]


workflow = StateGraph(AgencyState)

# Add Triage Node
workflow.add_node("triage", node_triage)

# Add Department Nodes
workflow.add_node("tutor", node_tutor)
workflow.add_node("marketing", node_marketing)
workflow.add_node("sales", node_sales)
workflow.add_node("engineering", node_engineering)
workflow.add_node("cfo", node_cfo_direct)
workflow.add_node("corp_finance", node_corp_finance)
workflow.add_node("risk", node_risk)
workflow.add_node("treasury", node_treasury)
workflow.add_node("capital_structure", node_capital_structure)
workflow.add_node("m_and_a", node_m_and_a)
workflow.add_node("controller", node_controller)
workflow.add_node("portfolio", node_portfolio)
workflow.add_node("valuation", node_valuation)
workflow.add_node("credit", node_credit)
workflow.add_node("inventory", node_inventory)
workflow.add_node("planner", node_planner)

# Add Summarizer & CFO Synthesis Nodes
workflow.add_node("summarizer", node_summarizer)
workflow.add_node("cfo_synthesis", node_cfo)

# Entry Point -> Triage
workflow.add_edge(START, "triage")

# Dynamic Conditional Edges from Triage
workflow.add_conditional_edges("triage", route_from_triage, ALL_DEPARTMENTS)

# 1. Educational Path: tutor routes directly to END (bypasses summarizer and CFO)
workflow.add_edge("tutor", END)

# 2. Marketing Path: marketing mini-crew routes directly to END
workflow.add_edge("marketing", END)

# 3. Sales Path: sales mini-crew routes directly to END
workflow.add_edge("sales", END)

# 4. Engineering Path: engineering mini-crew routes directly to END
workflow.add_edge("engineering", END)

# 5. Direct CFO Path: cfo routes directly to END
workflow.add_edge("cfo", END)

# 5. Corporate Path: Analytical department nodes run in parallel -> Summarizer -> CFO Synthesis -> END
CORP_NODES = [
    "corp_finance", "risk", "treasury", "capital_structure", "m_and_a",
    "controller", "portfolio", "valuation", "credit", "inventory", "planner"
]
for dept_key in CORP_NODES:
    workflow.add_edge(dept_key, "summarizer")

workflow.add_edge("summarizer", "cfo_synthesis")
workflow.add_edge("cfo_synthesis", END)

app_graph = workflow.compile()


# =====================================================================
# 4. Main Entry Point for Streamlit & Standalone Execution
# =====================================================================
def run_agency(user_request: str) -> str:
    """
    Invokes the Chief of Staff Triage & Dynamic Parallel Execution workflow with Central Knowledge Base RAG.
    - Educational queries route: triage -> tutor -> END.
    - Marketing queries route: triage -> marketing mini-crew -> END.
    - Sales queries route: triage -> sales mini-crew -> END.
    - Corporate queries route: triage -> parallel depts -> summarizer -> CFO -> END.
    """
    initial_state = {
        "user_request": user_request,
        "triage_output": "",
        "selected_departments": [],
        "raw_department_reports": {},
        "department_summaries": {},
        "final_response": "",
        "final_cfo_decision": ""
    }

    final_state = app_graph.invoke(initial_state)
    return final_state.get("final_response") or final_state.get("final_cfo_decision", "")


if __name__ == "__main__":
    print("Testing LangGraph Multi-Department Enterprise Architecture with Engineering Department...")

    eng_test = "Design a scalable software architecture and write clean Python FastAPI code for a microservice that handles user authentication and JWT token verification."
    print("\n--- TEST: ENGINEERING DEPARTMENT REQUEST ---")
    out = run_agency(eng_test)
    print("\n" + "=" * 50)
    print("ENGINEERING OUTPUT:")
    print("=" * 50)
    print(out)
