import sys
import os
import time
import json
import re

# =====================================================================
# Arize Phoenix Observability Instrumentation
# Top-level tracing for all downstream LLM calls and LangChain spans
# =====================================================================
try:
    import phoenix as px
    from openinference.instrumentation.langchain import LangChainInstrumentor

    # Launch local Phoenix server and register LangChain instrumentor
    px.launch_app()
    LangChainInstrumentor().instrument()
    print("[Arize Phoenix] Observability server active and LangChain instrumented.")
except Exception as _px_err:
    print(f"[Arize Phoenix] Instrumentation notice: {_px_err}")

import litellm
from typing import TypedDict, Annotated, List, Literal, Optional
from pydantic import BaseModel, Field

# UTF-8 stdout configuration for Windows console compatibility
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


from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import DirectoryReadTool
from langgraph.graph import StateGraph, START, END
from finance_department import FinanceDepartment, get_resilient_llm
from marketing_department import MarketingDepartment
from sales_department import SalesDepartment, get_sales_team, SalesEmail
from engineering_department import EngineeringDepartment, get_engineering_team, hitl_file_writer
from content_house_department import ContentHouseDepartment, get_content_team, OmnichannelDeliverable, ContentDeliverable

# Auto-create Central Company Brain Knowledge Base directory
KNOWLEDGE_BASE_DIR = os.path.join(os.getcwd(), "company_knowledge_base")
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

# Initialize RAG DirectoryReadTool pointed at Central Company Brain
knowledge_tool = DirectoryReadTool(directory="company_knowledge_base")

# Ensure local output persistence directory exists
os.makedirs("output", exist_ok=True)

# Load environment variables securely from .env
load_dotenv()

if not os.getenv("CHROMA_HUGGINGFACE_API_KEY"):
    os.environ["CHROMA_HUGGINGFACE_API_KEY"] = "dummy"

# Embedder configuration for local long-term memory without OpenAI API key dependency
EMBEDDER_CONFIG = {"provider": "huggingface", "config": {"model": "all-MiniLM-L6-v2"}}


# =====================================================================
# Pydantic Schemas for Triage & Inspector General QA
# =====================================================================
class RoutingDecision(BaseModel):
    reasoning: str = Field(
        description="Explain your step-by-step logic for choosing the departments based on the user's intent. Do this first."
    )
    departments: List[str] = Field(
        description="The final selected departments. Must be exact matches from the allowed list: ['cfo', 'corp_finance', 'risk', 'treasury', 'capital_structure', 'm_and_a', 'controller', 'portfolio', 'valuation', 'credit', 'inventory', 'planner', 'tutor', 'marketing', 'sales', 'engineering', 'content']."
    )


class InspectorDecision(BaseModel):
    status: Literal["PASS", "FAIL"] = Field(
        description="Must be 'PASS' if the deliverable satisfies the prompt, contains zero formatting/syntax errors, and has no hallucinated tool data. Otherwise 'FAIL'."
    )
    feedback: Optional[str] = Field(
        default="",
        description="If status is 'FAIL', provide specific, actionable feedback on what must be corrected or rewritten. Empty if 'PASS'."
    )


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
    retry_count: int
    inspector_feedback: str
    last_active_department: str
    inspector_decision: dict


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
    crew = Crew(agents=[summarizer], tasks=[summary_task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
    res = crew.kickoff()
    return str(res)


# =====================================================================
# 2. LangGraph Node Definitions (Stateful Execution Pipeline)
# =====================================================================

def node_triage(state: AgencyState) -> dict:
    """Chief of Staff (Triage): Searches Knowledge Base SOPs, analyzes user request, and outputs structured RoutingDecision with reasoning and departments."""
    llm = get_resilient_llm()
    triage_agent = Agent(
        role="Chief of Staff (Triage)",
        goal="Analyze user request intent step-by-step, consult Knowledge Base company guidelines, and select appropriate department routing.",
        backstory=(
            "You are the executive Chief of Staff. You analyze user inquiries using strict step-by-step reasoning. "
            "You consult the Central Company Knowledge Base to understand company structure and SOPs. "
            "You categorize requests and assign them to the exact right departments.\n\n"
            "Routing Rules:\n"
            "- Educational Rule: If the user asks for explanations, tutorials, or to learn financial concepts (e.g. 'what is WACC?', 'explain NPV', 'how does DCF work?'), select strictly ['tutor'].\n"
            "- Marketing Rule: If the user asks for marketing campaigns, SEO research, landing page copy, social media posts, competitor website scraping, or brand promotion, select strictly ['marketing'].\n"
            "- Sales Rule: If the user asks for lead generation, finding target companies, B2B outreach, cold emails, or prospect qualification, select strictly ['sales'].\n"
            "- Engineering Rule: If the user asks for writing Python scripts, debugging code, building software, checking code syntax, or modifying local files, select strictly ['engineering'].\n"
            "- Content House Rule: If the user asks for blog posts, YouTube video scripts, viral hooks, B-roll instructions, or banner/thumbnail image prompts, select strictly ['content'].\n"
            "- Corporate Finance Rule: If the user asks for numerical, analytical, valuation, risk, M&A, treasury, or investment analysis, select the relevant corporate finance departments.\n"
            "- Direct CFO Rule: If the user asks for high-level board strategy or CFO advice without needing detailed department models, select ['cfo']."
        ),
        tools=[knowledge_tool],
        verbose=True,
        memory=True,
        llm=llm
    )

    triage_task = Task(
        description=(
            f"User Request: '{state['user_request']}'\n\n"
            "First, search the company knowledge base for relevant SOPs, brand guidelines, or routing policies.\n"
            "Then, write your step-by-step reasoning explaining why specific departments are required.\n"
            "Finally, output your decision as a strict, valid JSON object with 'reasoning' and 'departments':\n"
            '```json\n{\n  "reasoning": "step-by-step reasoning...",\n  "departments": ["department_name"]\n}\n```\n\n'
            "Example 1: User asks 'Explain WACC step-by-step'. Reasoning: The user is asking an educational question to learn a concept. Departments: [\"tutor\"].\n"
            "Example 2: User asks to tweet about a new product. Reasoning: The user wants social media promotion. Departments: [\"marketing\"].\n"
            "Example 3: User asks for B2B target companies and cold outreach emails. Reasoning: The user wants lead generation and outbound sales. Departments: [\"sales\"].\n"
            "Example 4: User asks for a blog post, YouTube video script, or banner image prompt. Reasoning: The user wants content house media production. Departments: [\"content\"].\n"
            "Example 5: User asks to write a Python script or debug code. Reasoning: The user wants software engineering and code implementation. Departments: [\"engineering\"].\n\n"
            "Available departments: [\"cfo\", \"corp_finance\", \"risk\", \"treasury\", \"capital_structure\", \"m_and_a\", \"controller\", \"portfolio\", \"valuation\", \"credit\", \"inventory\", \"planner\", \"tutor\", \"marketing\", \"sales\", \"engineering\", \"content\"]."
        ),
        expected_output="A strict JSON object containing 'reasoning' (string) and 'departments' (list of strings).",
        agent=triage_agent
    )

    crew = Crew(agents=[triage_agent], tasks=[triage_task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
    res = crew.kickoff()
    raw_output = str(res).strip()
    return {"triage_output": raw_output}


def node_tutor(state: AgencyState) -> dict:
    """Finance Tutor Node: Explains complex financial concepts step-by-step for educational requests."""
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    tutor = dept.create_finance_tutor()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    task = Task(
        description=f"Provide a clear, beginner-friendly, step-by-step educational breakdown explaining key financial concepts and formulas for: '{state['user_request']}'.{feedback_prompt}",
        expected_output="Clear step-by-step educational tutorial explaining financial concepts with practical examples.",
        agent=tutor
    )
    crew = Crew(agents=[tutor], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
    res = str(crew.kickoff())
    return {"final_response": res, "last_active_department": "tutor"}


def node_marketing(state: AgencyState) -> dict:
    """Marketing Department Node: Executes a sequential mini-Crew (SEO Analyst -> Copywriter -> Social Manager -> CMO) equipped with Central Knowledge Base."""
    llm = get_resilient_llm()
    dept = MarketingDepartment(llm=llm, knowledge_tool=knowledge_tool)
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

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
        description=f"Review, refine, and orchestrate all campaign deliverables (SEO, Copy, Social Posts) for: '{state['user_request']}'. Always search the central knowledge base for Brand Guidelines and Tone of Voice to ensure strict executive alignment.{feedback_prompt}",
        expected_output="Final CMO-approved strategic marketing campaign aligned with corporate Brand Guidelines and ready for launch.",
        agent=cmo
    )

    marketing_crew = Crew(
        agents=[seo_analyst, copywriter, social_manager, cmo],
        tasks=[task1_seo, task2_copy, task3_social, task4_cmo],
        process=Process.sequential,
        memory=True,
        embedder=EMBEDDER_CONFIG,
        cache=True,
        verbose=True
    )

    raw_campaign = str(marketing_crew.kickoff())
    return {"final_response": raw_campaign, "last_active_department": "marketing"}


def sales_node(state: AgencyState) -> dict:
    """Sales Department Node: Executes a sequential sales workflow (Lead Scraper -> VP of Sales) initialized via get_sales_team()."""
    user_request = state.get("user_request", "")
    llm = get_resilient_llm()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    # Initialize the Sales agents via get_sales_team()
    sales_agents = get_sales_team(llm=llm, knowledge_tool=knowledge_tool)
    lead_scraper = sales_agents[0]
    vp_sales = sales_agents[1]

    # Task 1: Pass request to the Lead Scraper (Lead Generation Specialist)
    task1_lead_gen = Task(
        description=f"Identify target companies, prospective B2B accounts, decision-makers, and key intelligence for: '{user_request}'. Gather pain points, company context, and format a structured lead dossier.",
        expected_output="Structured B2B lead generation dossier detailing target accounts, pain points, and decision-maker profiles.",
        agent=lead_scraper
    )

    # Task 2: Pass output to the VP of Sales to draft structured cold email adhering to SalesEmail schema
    task2_vp_sales = Task(
        description=(
            f"Using the lead intelligence provided by the Lead Generation Specialist for: '{user_request}', "
            "craft a high-converting, consultative B2B cold outreach email. "
            "Output your email as a strict JSON object matching this schema:\n"
            '```json\n{\n  "subject": "Compelling subject line",\n  "body": "Executive consultative body"\n}\n```\n'
            "Strictly ensure zero spam triggers or prohibited phrases like '100% free' or 'guarantee'."
            f"{feedback_prompt}"
        ),
        expected_output="A strict JSON object with 'subject' and 'body'.",
        agent=vp_sales
    )

    sales_crew = Crew(
        agents=[lead_scraper, vp_sales],
        tasks=[task1_lead_gen, task2_vp_sales],
        process=Process.sequential,
        memory=True,
        embedder=EMBEDDER_CONFIG,
        cache=True,
        verbose=True
    )

    res = sales_crew.kickoff()
    raw_res = str(res).strip()
    if "```json" in raw_res:
        clean_json = raw_res.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_res:
        clean_json = raw_res.split("```")[1].split("```")[0].strip()
    else:
        clean_json = raw_res

    try:
        validated = SalesEmail.model_validate_json(clean_json)
        email_output = validated.model_dump_json(indent=2)
    except Exception:
        email_output = clean_json

    return {
        "raw_department_reports": {"sales": email_output},
        "final_response": email_output,
        "last_active_department": "sales"
    }


# Backwards compatibility alias
node_sales = sales_node


def engineering_node(state: AgencyState) -> dict:
    """
    Engineering Department Node: Executes a sequential 2-agent engineering workflow
    (Code Surgeon [with HITL File Writer] -> QA Tester) initialized via get_engineering_team().
    """
    user_request = state.get("user_request", "")
    llm = get_resilient_llm()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    # Initialize the Engineering agents via get_engineering_team()
    engineering_agents = get_engineering_team(llm=llm, knowledge_tool=knowledge_tool)
    code_surgeon = engineering_agents[0]
    qa_tester = engineering_agents[1]

    # Task 1: Pass request to Code Surgeon (equipped with hitl_file_writer tool)
    task1_code = Task(
        description=(
            f"Design and write clean, modular, and self-documenting Python code for: '{user_request}'. "
            "If file modifications or new files are needed, use the 'HITL File Writer' tool to propose changes, "
            "noting that changes require manual terminal approval from the user."
            f"{feedback_prompt}"
        ),
        expected_output="Clean, modular, production-ready Python source code implementation and file write status.",
        agent=code_surgeon
    )

    # Task 2: Pass output to QA Tester for rigorous review
    task2_qa = Task(
        description=(
            f"Rigorously review the Code Surgeon's proposed code and implementation for: '{user_request}'. "
            "Audit for syntax correctness, edge case resilience, and verify it will not break existing LangGraph orchestrator architecture. "
            "Provide the final code and verification report."
        ),
        expected_output="Final QA-verified production-ready Python code deliverable and audit report.",
        agent=qa_tester
    )

    engineering_crew = Crew(
        agents=[code_surgeon, qa_tester],
        tasks=[task1_code, task2_qa],
        process=Process.sequential,
        memory=True,
        embedder=EMBEDDER_CONFIG,
        cache=True,
        verbose=True
    )

    raw_code_output = str(engineering_crew.kickoff())
    return {
        "raw_department_reports": {"engineering": raw_code_output},
        "final_response": raw_code_output,
        "last_active_department": "engineering"
    }


# Backwards compatibility alias
node_engineering = engineering_node


def content_node(state: AgencyState) -> dict:
    """
    Content House Department Node: Executes a sequential 5-agent omnichannel production studio
    (Creative Director -> Scriptwriter -> Hook Specialist -> Graphic Designer -> Video Producer)
    initialized via get_content_team(). Enforces strict structured output conforming to OmnichannelDeliverable.
    """
    user_request = state.get("user_request", "")
    llm = get_resilient_llm()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    # Initialize the 5 Content House agents via get_content_team()
    content_agents = get_content_team(llm=llm, knowledge_tool=knowledge_tool)
    creative_director = content_agents[0]
    scriptwriter = content_agents[1]
    hook_specialist = content_agents[2]
    graphic_designer = content_agents[3]
    video_producer = content_agents[4]

    # Task 1: Creative Director architects narrative & strategy
    task1_strategy = Task(
        description=f"Analyze trending angles and architect the narrative arc, thematic vision, and distribution brief for: '{user_request}'.",
        expected_output="Strategic creative direction brief detailing narrative arc, tone, target audience, and key messaging pillars.",
        agent=creative_director
    )

    # Task 2: Scriptwriter drafts long-form video script and written post
    task2_writing = Task(
        description=f"Based on the creative direction, write a high-value long-form video script and an engaging written post for LinkedIn/Twitter/Blog for: '{user_request}'.",
        expected_output="Complete written post copy and core video script draft.",
        agent=scriptwriter
    )

    # Task 3: Hook Specialist frames viral opening hooks
    task3_hook = Task(
        description=f"Formulate high-retention viral opening hooks, pattern interrupts, and curiosity triggers for the video and written post for: '{user_request}'.",
        expected_output="Punchy viral hooks and opening lines optimized to stop the scroll.",
        agent=hook_specialist
    )

    # Task 4: Graphic Designer creates Midjourney / DALL-E prompt
    task4_visuals = Task(
        description=f"Design a highly detailed, photorealistic Midjourney/DALL-E 3 text-to-image prompt for the banner/thumbnail for: '{user_request}'. Specify lighting, subject composition, artistic style, camera lens, and aspect ratio.",
        expected_output="Production-grade text-to-image prompt for high-CTR thumbnail and header banner.",
        agent=graphic_designer
    )

    # Task 5: Video Producer structures final video, B-roll cues, and enforces OmnichannelDeliverable schema
    task5_production = Task(
        description=(
            f"Synthesize all assets for '{user_request}' into a unified omnichannel deliverable. "
            "Output your final result as a strict, valid JSON object matching the OmnichannelDeliverable schema:\n"
            "```json\n{\n"
            '  "written_post": "Complete written post for LinkedIn/Twitter/Blog...",\n'
            '  "video_script": "Full video script with exact spoken dialogue and text-on-screen cues...",\n'
            '  "b_roll_instructions": "Cinematic visual directions and B-roll cues mapped to timeline...",\n'
            '  "image_generation_prompt": "Highly detailed Midjourney/DALL-E prompt for banner/thumbnail..."\n'
            "}\n```\n"
            f"{feedback_prompt}"
        ),
        expected_output="A strict JSON object containing written_post, video_script, b_roll_instructions, and image_generation_prompt.",
        agent=video_producer
    )

    content_crew = Crew(
        agents=[creative_director, scriptwriter, hook_specialist, graphic_designer, video_producer],
        tasks=[task1_strategy, task2_writing, task3_hook, task4_visuals, task5_production],
        process=Process.sequential,
        memory=True,
        embedder=EMBEDDER_CONFIG,
        cache=True,
        verbose=True
    )

    res = content_crew.kickoff()
    raw_res = str(res).strip()
    if "```json" in raw_res:
        clean_json = raw_res.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_res:
        clean_json = raw_res.split("```")[1].split("```")[0].strip()
    else:
        clean_json = raw_res

    try:
        validated = OmnichannelDeliverable.model_validate_json(clean_json)
        content_output = validated.model_dump_json(indent=2)
    except Exception:
        content_output = clean_json

    return {
        "raw_department_reports": {"content": content_output},
        "final_response": content_output,
        "last_active_department": "content"
    }


# Backwards compatibility alias
node_content = content_node


def node_corp_finance(state: AgencyState) -> dict:
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    analyst = dept.create_corp_finance_analyst()

    task = Task(
        description=f"Evaluate capital investment viability, projected cash flows, Net Present Value (NPV), Internal Rate of Return (IRR), and hurdle rate for: '{state['user_request']}'.",
        expected_output="Detailed corporate finance valuation report with DCF, NPV, IRR, and payback horizons.",
        agent=analyst
    )
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
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
    crew = Crew(agents=[analyst], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
    raw_output = str(crew.kickoff())
    return {"raw_department_reports": {"Financial Planning & Analysis": raw_output}}


def node_cfo_direct(state: AgencyState) -> dict:
    """Direct CFO Node: Executes when CFO is directly requested without intermediate department nodes."""
    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    cfo = dept.create_cfo()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    task = Task(
        description=f"Formulate definitive executive capital allocation strategy and recommendations for: '{state['user_request']}'.{feedback_prompt}",
        expected_output="Definitive CFO executive strategy report detailing capital allocation decisions, risk mitigation, and board recommendations.",
        agent=cfo,
        output_file="output/agency_report.txt"
    )
    crew = Crew(agents=[cfo], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
    res = str(crew.kickoff())
    return {"final_cfo_decision": res, "final_response": res, "last_active_department": "cfo"}


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
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

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
            f"{feedback_prompt}"
        ),
        expected_output="Definitive CFO executive strategy report detailing capital allocation decisions, risk mitigation, valuation/WACC optimization, and board recommendations.",
        agent=cfo,
        output_file="output/agency_report.txt"
    )
    crew = Crew(agents=[cfo], tasks=[task], memory=True, embedder=EMBEDDER_CONFIG, cache=True, verbose=True)
    res = str(crew.kickoff())
    return {"final_cfo_decision": res, "final_response": res, "last_active_department": "cfo_synthesis"}


# =====================================================================
# Step 1: Inspector General QA Node Definition
# =====================================================================
def inspector_node(state: AgencyState) -> dict:
    """
    Inspector General QA Node:
    Evaluates state['final_response'] against state['user_request'] to verify:
    1. Fully answers the prompt
    2. Contains no formatting errors
    3. Has no hallucinated tool data
    Outputs strict JSON: {"status": "PASS"} or {"status": "FAIL", "feedback": "exact reason for failure"}.
    """
    user_req = state.get("user_request", "")
    final_resp = state.get("final_response") or state.get("final_cfo_decision", "")
    retry_count = state.get("retry_count", 0)

    # Hard circuit-breaker for max 2 retries to prevent infinite loops
    if retry_count >= 2:
        print(f"\n[Inspector General] Max retries reached ({retry_count}/2). Forcing PASS approval to prevent loop.\n")
        return {
            "inspector_decision": {"status": "PASS", "feedback": "Max retry limit reached; accepted deliverable."},
            "inspector_feedback": ""
        }

    llm = get_resilient_llm()
    inspector_agent = Agent(
        role="Inspector General (Enterprise QA Auditor)",
        goal=(
            "Rigorously evaluate the final deliverable against the user request to guarantee absolute quality control. "
            "Verify that the deliverable thoroughly answers the prompt, contains zero formatting/syntax defects, and has no hallucinated tool data."
        ),
        backstory=(
            "You are the Inspector General of the enterprise. You enforce strict quality assurance, adherence to user prompts, "
            "clean markdown/code formatting, and factually grounded tool outputs. If a deliverable fails any quality criteria, "
            "you fail it with precise, constructive feedback for a rewrite. If it meets high standards, you pass it."
        ),
        verbose=True,
        llm=llm
    )

    inspector_task = Task(
        description=(
            f"Perform a comprehensive quality assurance audit on the following deliverable.\n\n"
            f"USER REQUEST:\n{user_req}\n\n"
            f"FINAL DELIVERABLE TO AUDIT:\n{final_resp}\n\n"
            "Audit Checklist:\n"
            "1. Completeness: Does the deliverable fully answer all aspects of the user's prompt?\n"
            "2. Formatting: Is the formatting clean, structured, and free of syntax/schema errors?\n"
            "3. Factuality: Is there zero hallucinated tool data or fabricated information?\n\n"
            "Output your audit decision strictly as a valid JSON object matching this schema:\n"
            '```json\n{\n  "status": "PASS",\n  "feedback": ""\n}\n```\n'
            'or if defective:\n'
            '```json\n{\n  "status": "FAIL",\n  "feedback": "exact actionable reason for failure"\n}\n```'
        ),
        expected_output="A strict JSON object containing 'status' (PASS or FAIL) and 'feedback' (string).",
        agent=inspector_agent
    )

    inspector_crew = Crew(
        agents=[inspector_agent],
        tasks=[inspector_task],
        memory=False,
        cache=True,
        verbose=True
    )

    res = inspector_crew.kickoff()
    decision_data = {"status": "PASS", "feedback": ""}

    if hasattr(res, "pydantic") and res.pydantic:
        decision_data = res.pydantic.model_dump() if hasattr(res.pydantic, "model_dump") else res.pydantic.dict()
    else:
        try:
            parsed = json.loads(str(res).strip())
            if isinstance(parsed, dict) and "status" in parsed:
                decision_data = parsed
        except Exception:
            raw_text = str(res).strip().upper()
            if "FAIL" in raw_text:
                decision_data = {"status": "FAIL", "feedback": str(res).strip()}
            else:
                decision_data = {"status": "PASS", "feedback": ""}

    status = decision_data.get("status", "PASS").upper()
    feedback = decision_data.get("feedback", "")
    new_retry_count = retry_count + 1 if status == "FAIL" else retry_count

    print(f"\n[Inspector General QA Audit]: Status={status}, Retries={new_retry_count}/2, Feedback='{feedback}'\n")

    return {
        "inspector_decision": {"status": status, "feedback": feedback},
        "inspector_feedback": feedback if status == "FAIL" else "",
        "retry_count": new_retry_count
    }


# =====================================================================
# 3. Dynamic Conditional Routing & Graph Topology
# =====================================================================
ALL_DEPARTMENTS = [
    "cfo", "corp_finance", "risk", "treasury", "capital_structure", "m_and_a",
    "controller", "portfolio", "valuation", "credit", "inventory", "planner", "tutor", "marketing", "sales", "engineering", "content"
]

def route_from_triage(state: AgencyState) -> list[str]:
    """
    Parses the validated RoutingDecision output from Chief of Staff to extract selected departments.
    CrewAI handles Pydantic validation, so output is a validated RoutingDecision object or JSON string.
    """
    text = state.get("triage_output", "").strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            reasoning = parsed.get("reasoning", "")
            if reasoning:
                print(f"\n[Chief of Staff Triage Reasoning]: {reasoning}\n")
            depts = parsed.get("departments", [])
        elif isinstance(parsed, list):
            depts = parsed
        else:
            depts = []

        valid_depts = [d for d in depts if isinstance(d, str) and d in ALL_DEPARTMENTS]
        if valid_depts:
            if "content" in valid_depts:
                print(f"\n[Route From Triage] Content House request detected: ['content']\n")
                return ["content"]
            if "engineering" in valid_depts:
                print(f"\n[Route From Triage] Engineering request detected: ['engineering']\n")
                return ["engineering"]
            if "tutor" in valid_depts:
                print(f"\n[Route From Triage] Educational request detected: ['tutor']\n")
                return ["tutor"]
            if "sales" in valid_depts:
                print(f"\n[Route From Triage] Sales request detected: ['sales']\n")
                return ["sales"]
            if "marketing" in valid_depts:
                print(f"\n[Route From Triage] Marketing request detected: ['marketing']\n")
                return ["marketing"]
            print(f"\n[Route From Triage] Selected departments: {valid_depts}\n")
            return valid_depts

    except Exception as e:
        print(f"\n[Triage Routing Notice] Exception parsing RoutingDecision JSON: '{text}'. Error: {e}\n")

    print(f"\n[Triage Routing Warning] Could not extract valid departments from output. Defaulting to ['cfo'].\n")
    return ["cfo"]


def route_from_inspector(state: AgencyState) -> str:
    """
    Conditional routing from Inspector General QA node:
    - If status is 'PASS' or retry_count >= 2: routes to END.
    - If status is 'FAIL': routes back to the specific department node that generated it to force a rewrite.
    """
    decision = state.get("inspector_decision", {})
    status = decision.get("status", "PASS").upper()
    retry_count = state.get("retry_count", 0)
    last_dept = state.get("last_active_department", "cfo")

    if status == "PASS" or retry_count >= 2:
        print(f"\n[Route From Inspector] Deliverable QA Approved. Routing to END.\n")
        return END

    dept_to_node_map = {
        "tutor": "tutor",
        "marketing": "marketing",
        "sales": "sales",
        "engineering": "engineering",
        "content": "content",
        "cfo_synthesis": "cfo_synthesis",
        "cfo": "cfo"
    }

    target_node = dept_to_node_map.get(last_dept, "cfo_synthesis")
    print(f"\n[Route From Inspector] QA Failed. Routing back to '{target_node}' for self-correction (Attempt #{retry_count}/2).\n")
    return target_node


workflow = StateGraph(AgencyState)
graph = workflow

# Add Triage Node
workflow.add_node("triage", node_triage)

# Add Department Nodes
workflow.add_node("tutor", node_tutor)
workflow.add_node("marketing", node_marketing)
workflow.add_node("sales", sales_node)
workflow.add_node("engineering", engineering_node)
workflow.add_node("content", content_node)
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

# Add Summarizer, CFO Synthesis, and Inspector Nodes
workflow.add_node("summarizer", node_summarizer)
workflow.add_node("cfo_synthesis", node_cfo)
workflow.add_node("inspector", inspector_node)

# Entry Point -> Triage
workflow.add_edge(START, "triage")

# Dynamic Conditional Edges from Triage
workflow.add_conditional_edges("triage", route_from_triage, ALL_DEPARTMENTS)

# 1. Educational Path: tutor routes to inspector
workflow.add_edge("tutor", "inspector")

# 2. Marketing Path: marketing mini-crew routes to inspector
workflow.add_edge("marketing", "inspector")

# 3. Sales Path: sales mini-crew routes to inspector
workflow.add_edge("sales", "inspector")

# 4. Engineering Path: engineering mini-crew routes to inspector
workflow.add_edge("engineering", "inspector")

# 5. Content House Path: omnichannel content mini-crew routes to inspector
workflow.add_edge("content", "inspector")

# 6. Direct CFO Path: cfo routes to inspector
workflow.add_edge("cfo", "inspector")

# 7. Corporate Path: Analytical department nodes run in parallel -> Summarizer -> CFO Synthesis -> inspector
CORP_NODES = [
    "corp_finance", "risk", "treasury", "capital_structure", "m_and_a",
    "controller", "portfolio", "valuation", "credit", "inventory", "planner"
]
for dept_key in CORP_NODES:
    workflow.add_edge(dept_key, "summarizer")

workflow.add_edge("summarizer", "cfo_synthesis")
workflow.add_edge("cfo_synthesis", "inspector")

# Conditional Edge from Inspector Node (PASS -> END, FAIL -> last active department)
workflow.add_conditional_edges(
    "inspector",
    route_from_inspector,
    ["tutor", "marketing", "sales", "engineering", "content", "cfo_synthesis", "cfo", END]
)

app_graph = workflow.compile()


# =====================================================================
# 4. Main Entry Point for Streamlit & Standalone Execution
# =====================================================================
def run_agency(user_request: str) -> str:
    """
    Invokes the Chief of Staff Triage, Dynamic Parallel Execution, and Inspector General QA workflow.
    - Educational queries route: triage -> tutor -> inspector -> END.
    - Marketing queries route: triage -> marketing mini-crew -> inspector -> END.
    - Sales queries route: triage -> sales mini-crew -> inspector -> END.
    - Engineering queries route: triage -> engineering mini-crew -> inspector -> END.
    - Content House queries route: triage -> content mini-crew -> inspector -> END.
    - Corporate queries route: triage -> parallel depts -> summarizer -> CFO -> inspector -> END.
    """
    initial_state = {
        "user_request": user_request,
        "triage_output": "",
        "selected_departments": [],
        "raw_department_reports": {},
        "department_summaries": {},
        "final_response": "",
        "final_cfo_decision": "",
        "retry_count": 0,
        "inspector_feedback": "",
        "last_active_department": "",
        "inspector_decision": {}
    }

    final_state = app_graph.invoke(initial_state)
    return final_state.get("final_response") or final_state.get("final_cfo_decision", "")


if __name__ == "__main__":
    test_prompt = "Conduct a discounted cash flow valuation for a project with $5M initial outlay and $1.5M annual cash flows for 5 years at 10% discount rate."
    print(f"\n--- Running Master LangGraph Pipeline ---")
    print(f"Prompt: {test_prompt}\n")
    final_deliverable = run_agency(test_prompt)
    print("\n--- Final Master Deliverable ---")
    print(final_deliverable)
