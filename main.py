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
    from openinference.instrumentation.langchain import LangChainInstrumentor
    LangChainInstrumentor().instrument()
    if os.getenv("ENABLE_PHOENIX_UI", "false").lower() in ("true", "1"):
        import phoenix as px
        px.launch_app(host=os.getenv("PHOENIX_HOST", "0.0.0.0"), port=int(os.getenv("PHOENIX_PORT", 6060)))
        print("[Arize Phoenix] Observability server active and LangChain instrumented.")
except Exception as _px_err:
    print(f"[Arize Phoenix] Instrumentation notice: {_px_err}")

import litellm
from typing import TypedDict, Annotated, List, Literal, Optional, Dict, Any
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
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from finance_department import FinanceDepartment, get_resilient_llm
from marketing_department import MarketingDepartment
from sales_department import SalesDepartment, get_sales_team, SalesEmail
from engineering_department import EngineeringDepartment, get_engineering_team, hitl_file_writer
from content_house_department import ContentHouseDepartment, get_content_team, OmnichannelDeliverable, ContentDeliverable
from research_department import ResearchDepartment, get_research_team, arxiv_academic_scraper
from custom_tools import dynamic_browser_tool, live_web_search, browser_tool, search_tool
from pc_control_tools import pc_tools, run_application, close_application, search_local_file
from self_healing import trigger_rescue_mission
from key_vault import vault
from memory_engine import memory

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
        description="The final selected departments. Must be exact matches from the allowed list: ['cfo', 'corp_finance', 'risk', 'treasury', 'capital_structure', 'm_and_a', 'controller', 'portfolio', 'valuation', 'credit', 'inventory', 'planner', 'tutor', 'marketing', 'sales', 'engineering', 'content', 'research', 'general_ops']."
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


def merge_str(a: str, b: str) -> str:
    """Merges string updates. Prioritizes latest non-empty string revision."""
    if b and b.strip():
        return b.strip()
    return (a or "").strip()


# =====================================================================
# 1. LangGraph Shared State Definition
# =====================================================================
class AgencyState(TypedDict):
    user_request: str
    session_id: str
    cognitive_memory: str
    triage_output: str
    triage_action: str
    selected_departments: list[str]
    collaborating_departments: list[str]
    raw_department_reports: Annotated[dict[str, str], merge_dict]
    department_summaries: dict[str, str]
    final_response: Annotated[str, merge_str]
    final_cfo_decision: str
    retry_count: int
    inspector_feedback: str
    last_active_department: Annotated[str, merge_str]
    inspector_decision: dict
    messages: Annotated[list[BaseMessage], add_messages]


import concurrent.futures

# =====================================================================
# Helper: Thread-Safe Crew Kickoff Function (Async Event Loop Protection)
# =====================================================================
def _safe_kickoff(crew: Crew) -> str:
    """Executes crew kickoff cleanly in an isolated thread to prevent event loop collision with LangGraph."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(crew.kickoff)
            return str(future.result())
    except Exception as e:
        print(f"[Crew Execution Notice]: {e}")
        return str(crew.kickoff())


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
    res = _safe_kickoff(crew)
    return str(res)


# =====================================================================
# 2. LangGraph Node Definitions (Stateful Execution Pipeline)
# =====================================================================

TRIAGE_SYSTEM_PROMPT = (
    "You are the executive Chief of Staff of MAK Enterprise AI Agency.\n"
    "Your mission is to understand user intent dynamically and dispatch tasks to the most qualified specialized department.\n\n"
    "DYNAMIC INTENT DECOMPOSITION & CAPABILITY MATCHING:\n"
    "1. Target Deliverable & Capability Identification:\n"
    "   - Source Code / Scripts / Syntax Testing -> 'engineering' (Code Surgeon + QA Tester with AST syntax validation)\n"
    "   - Live Stock Metrics / Ticker Comparisons / DCF Valuation / Equity Models -> 'valuation' or 'corp_finance' (Valuation Analyst with live_market_data_puller)\n"
    "   - B2B Company Research / Lead Dossiers / Personalized Cold Outreach -> 'sales' (Lead Scraper + VP Sales with b2b_company_scraper)\n"
    "   - SEO Keyword Strategies / Growth Campaigns / Ad Copy -> 'marketing' (Marketing Strategist)\n"
    "   - Omnichannel Media / Video Scripts / Viral Hooks -> 'content' (Content Studio)\n"
    "   - Academic Research / Peer-Reviewed Literature (ArXiv) -> 'research' (Research Fellow)\n"
    "   - Conceptual Lessons / Tutorials / Financial Explanations -> 'tutor' (Educational Instructor)\n"
    "   - PC Desktop Control (Run/Close App) / Local File Search / General Web Browsing -> 'general_ops'\n"
    "   - Multi-department Corporate Board Governance -> 'cfo'\n\n"
    "2. Information Completeness & Action Decision:\n"
    "   - COMPLETE & ACTIONABLE DIRECTIVES:\n"
    "     * If the prompt provides the target subject/entity AND the desired outcome:\n"
    "       (e.g., 'write python code to scan and merge json files', 'pull live stock price for NVDA and AAPL and compare them', 'find homepage messaging for Anthropic and draft cold email pitching AI agents')\n"
    "     -> The prompt is 100% self-contained. Set 'action': 'ROUTE'.\n"
    "     -> Select the single best-matching 'primary_department'. Keep 'collaborating_departments': [].\n\n"
    "   - UNDERSPECIFIED / AMBIGUOUS DIRECTIVES (CLARIFICATION ONLY):\n"
    "     * ONLY engage clarification if the user prompt is an empty greeting (e.g., 'hi', 'hello'), conversational greeting ('who are you'), or fundamentally lacks targets/parameters (e.g., 'launch' without app name, 'write code' without specifications, 'search' without query).\n"
    "     -> Set 'action': 'CLARIFY' and ask 2-3 focused consultative questions or options (A/B).\n\n"
    "3. Multi-Turn Context Continuity:\n"
    "   - When previous conversation history is present, interpret follow-up answers (e.g., 'Option A', 'now write python code for it', 'proceed') against the preceding turns and route to the appropriate department.\n\n"
    "OUTPUT FORMAT (STRICT JSON ONLY):\n"
    "{\n"
    '  "action": "CLARIFY" | "ROUTE",\n'
    '  "target_artifact": "Identified deliverable type (e.g., Python Script, Valuation Model, Cold Email, Web Data)",\n'
    '  "reasoning": "Step-by-step intent reasoning and capability matching",\n'
    '  "primary_department": "department_name",\n'
    '  "collaborating_departments": [],\n'
    '  "clarification_response": "Consultative questions if action is CLARIFY, otherwise empty string"\n'
    "}"
)


def node_triage(state: AgencyState) -> dict:
    """Chief of Staff (Triage & Clarification Engine): Analyzes prompt, engages in consultative dialogue if underspecified, or routes to specialists."""
    user_request = state.get("user_request", "").strip()
    cognitive_memory = state.get("cognitive_memory", "")
    api_key = vault.get_active_key("groq") or os.getenv("GROQ_API_KEY")

    # Fast direct evaluation using resilient ChatGroq with JSON mode
    try:
        chat_llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            groq_api_key=api_key,
            temperature=0.1,
            max_retries=2,
            response_format={"type": "json_object"}
        )
        sys_prompt = TRIAGE_SYSTEM_PROMPT
        if cognitive_memory:
            sys_prompt += f"\n\n{cognitive_memory}"
        
        messages: List[BaseMessage] = [SystemMessage(content=sys_prompt)]
        
        # Inject preceding multi-turn dialogue history from state into triage prompt
        state_msgs = state.get("messages") or []
        if len(state_msgs) > 1:
            for m in state_msgs[:-1][-6:]:
                messages.append(m)
        
        messages.append(HumanMessage(content=f"User Request: {user_request}"))

        try:
            res = chat_llm.invoke(messages)
        except Exception as groq_70b_err:
            if any(w in str(groq_70b_err).lower() for w in ["ratelimit", "429", "limit reached", "tpd", "tpm", "quota"]):
                rotated_key = vault.rotate_key("groq", failed_key=api_key, reason="Triage Rate Limit")
                chat_llm_8b = ChatGroq(
                    model_name="llama-3.1-8b-instant",
                    groq_api_key=rotated_key,
                    temperature=0.1,
                    max_retries=2,
                    response_format={"type": "json_object"}
                )
                res = chat_llm_8b.invoke(messages)
            else:
                raise groq_70b_err

        raw_output = str(res.content).strip()
        parsed = json.loads(raw_output)
    except Exception as e:
        print(f"[Triage Direct LLM Notice]: {e}")
        # Intelligent fallback for conversational, ambiguous, or underspecified prompts
        lower_req = user_request.lower().strip()
        word_count = len(lower_req.split())

        if any(g in lower_req for g in ["hi", "hello", "hey", "who are you", "what can you do", "help me"]) or word_count <= 2:
            parsed = {
                "action": "CLARIFY",
                "clarification_response": (
                    f"Hello! I am your Chief of Staff at MAK Enterprise AI Agency.\n\n"
                    "To ensure we give you the most precise deliverable, could you please clarify:\n"
                    "1. **Primary Goal**: What specific task or outcome would you like us to achieve?\n"
                    "2. **Target Details**: If this involves an application, codebase, research topic, or market, which one?\n"
                    "3. **Format/Parameters**: Any specific constraints or preferred format for the result?"
                ),
                "reasoning": "Greeting, ambiguous, or underspecified prompt requiring conversational clarification.",
                "primary_department": "general_ops",
                "collaborating_departments": []
            }
        elif any(k in lower_req for k in ["search", "google", "browse", "visit", "scrape", "lookup", "online", "open app", "close app", "find file", "search file", "launch", "run"]):
            parsed = {
                "action": "ROUTE",
                "clarification_response": "",
                "reasoning": "User requested live web search, browsing, or Windows PC automation.",
                "primary_department": "general_ops",
                "collaborating_departments": []
            }
        else:
            parsed = {
                "action": "ROUTE",
                "clarification_response": "",
                "reasoning": "Standard agency directive.",
                "primary_department": "cfo",
                "collaborating_departments": []
            }
        raw_output = json.dumps(parsed)

    action = parsed.get("action", "ROUTE").upper()
    clarification = parsed.get("clarification_response", "")
    reasoning = parsed.get("reasoning", "")
    primary_dept = parsed.get("primary_department", "").strip().lower()
    collab_depts = parsed.get("collaborating_departments", [])

    print(f"\n[Chief of Staff Triage Decision]: Action={action} | Primary Dept='{primary_dept}' | Reasoning='{reasoning}'\n")

    if action == "CLARIFY" and clarification:
        return {
            "triage_output": raw_output,
            "triage_action": "CLARIFY",
            "selected_departments": [],
            "collaborating_departments": [],
            "final_response": clarification,
            "last_active_department": "Chief of Staff"
        }

    selected = [primary_dept] if primary_dept in ALL_DEPARTMENTS else ["general_ops"]
    # Only include collaborating departments for corporate finance analytical suites or when explicitly valid
    CORP_NODES_SET = set(["corp_finance", "risk", "treasury", "capital_structure", "m_and_a", "controller", "portfolio", "valuation", "credit", "inventory", "planner"])
    if primary_dept in CORP_NODES_SET:
        for d in collab_depts:
            d_clean = str(d).strip().lower()
            if d_clean in CORP_NODES_SET and d_clean not in selected:
                selected.append(d_clean)

    return {
        "triage_output": raw_output,
        "triage_action": "ROUTE",
        "selected_departments": selected,
        "collaborating_departments": [d for d in selected if d != primary_dept],
        "last_active_department": primary_dept
    }

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
        description=(
            f"Identify target companies, prospective B2B accounts, decision-makers, and key intelligence for: '{user_request}'. "
            "You MUST execute the `b2b_company_scraper` tool to scrape the target company's official homepage messaging, "
            "value propositions, and positioning before passing the prospect dossier to the VP of Sales."
        ),
        expected_output="Structured B2B lead generation dossier detailing target accounts, scraped homepage messaging, and pain points.",
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
            "You MUST run the `python_syntax_checker` tool to verify AST syntax validity and ensure the code compiles without error. "
            "Present the final clean, production-ready Python script and the syntax validation status."
        ),
        expected_output="Final QA-verified production-ready Python code deliverable and syntax audit report.",
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

    try:
        raw_code_output = str(engineering_crew.kickoff())
        if "syntaxerror" in raw_code_output.lower() or "traceback (most recent call last)" in raw_code_output.lower():
            rescue_report = trigger_rescue_mission(error_traceback=raw_code_output, task_context=user_request)
            raw_code_output = f"{raw_code_output}\n\n{rescue_report}"
    except Exception as eng_err:
        import traceback
        tb = traceback.format_exc()
        raw_code_output = trigger_rescue_mission(error_traceback=tb, task_context=user_request)

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

    # Task 4: Graphic Designer creates text-to-image prompt and physically generates the image
    task4_visuals = Task(
        description=(
            f"Design a highly detailed, photorealistic text-to-image prompt for the banner/thumbnail for: '{user_request}'. "
            "Specify lighting, subject composition, artistic style, camera lens, and aspect ratio. "
            "You MUST invoke the generate_free_image tool with your detailed prompt and a descriptive filename to physically create and save the image asset."
        ),
        expected_output="Production-grade text-to-image prompt and confirmation of image file generation.",
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


def research_node(state: AgencyState) -> dict:
    """
    Research Department Node: Executes an Academic Research workflow equipped with ArXiv scraper & knowledge base.
    """
    user_request = state.get("user_request", "")
    llm = get_resilient_llm()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    research_agents = get_research_team(llm=llm, knowledge_tool=knowledge_tool)
    academic_researcher = research_agents[0]

    research_task = Task(
        description=(
            f"Conduct rigorous scientific and academic literature review using ArXiv academic papers for: '{user_request}'. "
            "Extract relevant theoretical findings, empirical results, citations, and structure a high-density academic briefing."
            f"{feedback_prompt}"
        ),
        expected_output="Comprehensive academic literature review and scientific briefing grounded in ArXiv research.",
        agent=academic_researcher
    )

    research_crew = Crew(
        agents=[academic_researcher],
        tasks=[research_task],
        process=Process.sequential,
        memory=True,
        embedder=EMBEDDER_CONFIG,
        cache=True,
        verbose=True
    )

    raw_research_output = str(research_crew.kickoff())
    return {
        "raw_department_reports": {"research": raw_research_output},
        "final_response": raw_research_output,
        "last_active_department": "research"
    }


# Backwards compatibility alias
node_research = research_node


def general_ops_node(state: AgencyState) -> dict:
    """
    General Operations Node: Executes generic web browsing, online chores, and native Windows PC Control operations.
    Equipped with browser_tool, search_tool, run_application, close_application, and search_local_file.
    """
    user_request = state.get("user_request", "")
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    ops_system_prompt = (
        "You are an executive General Operations & Windows PC Controller agent.\n"
        "You have access to tools for live internet searching, browser navigation, opening desktop applications, closing processes, and searching local files on the Windows host machine.\n"
        "Analyze the user's directive and invoke the appropriate tool:\n"
        "- run_application: To launch desktop software or Windows system apps (e.g., notepad, calc, code).\n"
        "- close_application: To terminate running software by process name (e.g., notepad.exe, spotify.exe).\n"
        "- search_local_file: To search for specific files on disk.\n"
        "- search_tool / browser_tool: For live internet searching and web page navigation.\n"
        "Execute the necessary tool to satisfy the prompt and return a clear, structured summary of the action taken."
    )

    # Initialize messages conversation history
    messages = list(state.get("messages") or [])
    if not messages:
        messages = [
            SystemMessage(content=ops_system_prompt),
            HumanMessage(content=f"{user_request}{feedback_prompt}")
        ]

    # Map available tools
    available_tools = [browser_tool, search_tool] + pc_tools
    tool_map = {t.name: t for t in available_tools}

    api_key = vault.get_active_key("groq") or os.getenv("GROQ_API_KEY")
    chat_llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key, max_retries=2)
    chat_with_tools = chat_llm.bind_tools(available_tools)

    try:
        response = chat_with_tools.invoke(messages)
    except Exception as e:
        # Fallback parser for Groq tool-call format or heuristic matching
        err_str = str(e)
        tool_call_match = re.search(r'<function=(\w+)[>:]?\s*({.*?})', err_str)
        if tool_call_match:
            fn_name = tool_call_match.group(1)
            try:
                fn_args = json.loads(tool_call_match.group(2))
            except Exception:
                fn_args = {"query": user_request}
            response = AIMessage(
                content="",
                tool_calls=[{
                    "name": fn_name,
                    "args": fn_args,
                    "id": f"call_{int(time.time()*1000)}"
                }]
            )
        else:
            response = AIMessage(content="", tool_calls=[])

    # Check for direct heuristic tool routing if LLM didn't emit a tool call
    lower_req = user_request.lower()
    tool_calls_to_run = getattr(response, "tool_calls", None) or []

    if not tool_calls_to_run:
        app_launch_match = re.search(r'^(?:please\s+)?(?:open|launch|run|start)\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\.\s]+)$', lower_req.strip())
        if app_launch_match:
            app_target = app_launch_match.group(1).strip()
            if app_target not in ["a", "an", "the", "file", "url", "link", "browser", "website"]:
                tool_calls_to_run = [{"name": "run_application", "args": {"app_name": app_target}, "id": "direct_1"}]
        elif any(k in lower_req for k in ["close app", "kill app", "close notepad", "terminate", "kill notepad", "close application", "stop app"]):
            app_target = re.sub(r'^(please\s+)?(close|kill|terminate|stop|quit|exit)\s+(the\s+)?(app\s+|application\s+)?', '', lower_req).strip()
            tool_calls_to_run = [{"name": "close_application", "args": {"app_name": app_target or "notepad.exe"}, "id": "direct_2"}]
        elif any(k in lower_req for k in ["search file", "find file", "locate file", "search for file", "find the file"]):
            file_target = re.sub(r'^(please\s+)?(search\s+for\s+file|search\s+file|find\s+file|locate\s+file|find\s+the\s+file)\s+', '', lower_req).strip()
            # Extract directory if specified
            search_dir = "." if ("current directory" in lower_req or "this directory" in lower_req) else ""
            clean_file = file_target.replace("in the current directory", "").replace("in this directory", "").strip()
            tool_calls_to_run = [{"name": "search_local_file", "args": {"file_name": clean_file or "requirements.txt", "search_directory": search_dir}, "id": "direct_3"}]
        elif "http" in user_request or "www." in user_request:
            url_m = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', user_request)
            t_url = url_m[0] if url_m else "https://www.google.com"
            if not t_url.startswith("http"):
                t_url = "https://" + t_url
            tool_calls_to_run = [{"name": "browser_tool", "args": {"url": t_url}, "id": "direct_4"}]

    # Execute tool calls if present
    if tool_calls_to_run:
        results = []
        for call in tool_calls_to_run:
            t_name = call.get("name")
            t_args = call.get("args") or {}
            target_tool = tool_map.get(t_name)
            if target_tool:
                try:
                    tool_res = target_tool.invoke(t_args)
                    results.append(str(tool_res))
                except Exception as t_err:
                    results.append(f"Error executing {t_name}: {t_err}")
            else:
                results.append(f"Tool {t_name} is not recognized.")
        raw_tool_output = "\n\n".join(results)
        
        # Structure deliverable cleanly for Inspector General QA and user UI
        if any(c.get("name") in ["run_application", "close_application", "search_local_file"] for c in tool_calls_to_run):
            has_error = any(w in raw_tool_output.lower() for w in ["failed", "error", "could not find", "could not close"])
            if has_error:
                rescue_report = trigger_rescue_mission(error_traceback=raw_tool_output, task_context=user_request)
                content_str = (
                    f"### Action & Findings\n"
                    f"{raw_tool_output}\n\n"
                    f"{rescue_report}\n\n"
                    f"### System Status\n"
                    f"* **Task Target**: `{user_request}`\n"
                    f"* **Execution Mode**: Native Windows OS Process / File Subsystem (Autonomous Self-Healer Active)\n"
                    f"* **Operation**: Self-Healer Diagnosed & Formulated Remediation."
                )
            else:
                content_str = (
                    f"### Action & Findings\n"
                    f"{raw_tool_output}\n\n"
                    f"### System Status\n"
                    f"* **Task Target**: `{user_request}`\n"
                    f"* **Execution Mode**: Native Windows OS Process / File Subsystem\n"
                    f"* **Operation**: Successfully executed."
                )
        else:
            has_error = any(w in raw_tool_output.lower() for w in ["failed", "error", "could not"])
            if has_error:
                rescue_report = trigger_rescue_mission(error_traceback=raw_tool_output, task_context=user_request)
                content_str = f"{raw_tool_output}\n\n{rescue_report}"
            else:
                content_str = raw_tool_output
    else:
        content_str = response.content if isinstance(response.content, str) else str(response.content)

    return {
        "messages": [response],
        "final_response": content_str,
        "raw_department_reports": {"general_ops": content_str},
        "last_active_department": "general_ops"
    }


# Backwards compatibility alias
node_general_ops = general_ops_node


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
        description=(
            f"Deliver the financial valuation, live market metrics, or stock comparison requested for: '{state['user_request']}'.\n"
            "If company tickers are provided (e.g. NVDA, AAPL, MSFT), you MUST invoke the live_market_data_puller tool to pull real-time pricing and 52-week metrics, "
            "and format your comparative analysis strictly conforming to the requested length and structure."
        ),
        expected_output="Direct, accurate enterprise valuation or comparative stock analysis grounded in live tool data and conforming strictly to prompt constraints.",
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
    raw_reports = state.get("raw_department_reports", {})
    dept_summaries = state.get("department_summaries", {})

    # If only one specialized corporate department was activated, deliver its direct report
    if len(raw_reports) == 1:
        dept_name, report = next(iter(raw_reports.items()))
        return {
            "final_cfo_decision": report,
            "final_response": report,
            "last_active_department": dept_name
        }

    llm = get_resilient_llm()
    dept = FinanceDepartment(llm)
    cfo = dept.create_cfo()
    feedback = state.get("inspector_feedback", "")
    feedback_prompt = f"\n\n[INSPECTOR GENERAL FEEDBACK TO ADDRESS IN REWRITE]:\n{feedback}" if feedback else ""

    if not dept_summaries:
        summaries_text = f"Direct Analysis for: {state['user_request']}"
    else:
        summaries_text = "\n\n".join(
            [f"=== {name} Report ===\n{summary}" for name, summary in dept_summaries.items()]
        )

    task = Task(
        description=(
            f"Formulate definitive executive synthesis and strategic recommendations for: '{state['user_request']}'.\n\n"
            f"Synthesize the compressed departmental reports from activated departments:\n\n{summaries_text}"
            f"{feedback_prompt}"
        ),
        expected_output="Definitive executive deliverable synthesizing the specialized departmental analyses into a cohesive, structured strategic outcome.",
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

    res = _safe_kickoff(inspector_crew)
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
    res = _safe_kickoff(crew)
    return {"raw_department_reports": {"corp_finance": str(res)}, "last_active_department": "corp_finance"}


# =====================================================================
# 3. Dynamic Conditional Routing & Graph Topology
# =====================================================================
ALL_DEPARTMENTS = [
    "cfo", "corp_finance", "risk", "treasury", "capital_structure", "m_and_a",
    "controller", "portfolio", "valuation", "credit", "inventory", "planner", "tutor", "marketing", "sales", "engineering", "content", "research", "general_ops"
]

def route_from_triage(state: AgencyState) -> list[str]:
    """
    Parses validated Chief of Staff Triage decision:
    - If action is 'CLARIFY', routes directly to END without firing department crews.
    - If action is 'ROUTE', routes to the primary and collaborating departments.
    """
    triage_action = state.get("triage_action", "ROUTE").upper()
    if triage_action == "CLARIFY":
        print("\n[Route From Triage] Triage Action is CLARIFY. Returning directly to user with consultative questions.\n")
        return [END]

    selected_depts = state.get("selected_departments", [])
    if not selected_depts:
        user_req = state.get("user_request", "").strip().lower()
        if any(k in user_req for k in ["search", "browse", "google", "website", "online", "scrape"]):
            return ["general_ops"]
        return ["cfo"]

    valid_depts = [d for d in selected_depts if d in ALL_DEPARTMENTS]
    if not valid_depts:
        return ["general_ops"]

    print(f"\n[Route From Triage] Mobilizing Departments: {valid_depts}\n")
    return valid_depts


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
        "research": "research",
        "general_ops": "general_ops",
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
workflow.add_node("research", research_node)
workflow.add_node("general_ops", general_ops_node)
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

# Step 3 & 4: Define and add ToolNode for live browser tool execution
tools_node = ToolNode([browser_tool, search_tool])
workflow.add_node("tools", tools_node)

# Entry Point -> Triage
workflow.add_edge(START, "triage")

# Dynamic Conditional Edges from Triage (Explicit Dict Mapping)
TRIAGE_ROUTING_MAP = {d: d for d in ALL_DEPARTMENTS}
TRIAGE_ROUTING_MAP[END] = END
TRIAGE_ROUTING_MAP["__end__"] = END
workflow.add_conditional_edges("triage", route_from_triage, TRIAGE_ROUTING_MAP)

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

# 6. Academic Research Path: research agent routes to inspector
workflow.add_edge("research", "inspector")

# 7. General Operations Path: general_ops routes to inspector
workflow.add_edge("general_ops", "inspector")

# 8. Direct CFO Path: cfo routes to inspector
workflow.add_edge("cfo", "inspector")

# 9. Corporate Path: Analytical department nodes run in parallel -> Summarizer -> CFO Synthesis -> inspector
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
    ["tutor", "marketing", "sales", "engineering", "content", "research", "general_ops", "cfo_synthesis", "cfo", END]
)

app_graph = workflow.compile()


# =====================================================================
# 4. Main Entry Point for Streamlit & Standalone Execution
# =====================================================================
def run_agency(
    user_request: str,
    session_id: str = "default",
    chat_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Invokes the Chief of Staff Triage, Dynamic Parallel Execution, and Inspector General QA workflow.
    - Preserves and propagates multi-turn conversational history across all LLM/LangGraph state nodes.
    - Uses CognitiveMemoryEngine to inject user profile & conversational memory.
    - Educational queries route: triage -> tutor -> inspector -> END.
    - Marketing queries route: triage -> marketing mini-crew -> inspector -> END.
    - Sales queries route: triage -> sales mini-crew -> inspector -> END.
    - Engineering queries route: triage -> engineering mini-crew -> inspector -> END.
    - Content House queries route: triage -> content mini-crew -> inspector -> END.
    - Research queries route: triage -> academic researcher -> inspector -> END.
    - General Operations queries route: triage -> executive assistant -> inspector -> END.
    - Corporate queries route: triage -> parallel depts -> summarizer -> CFO -> inspector -> END.
    """
    cognitive_memory = memory.get_cognitive_context(session_id=session_id)

    # Reconstruct multi-turn LangGraph BaseMessage stream from client chat history
    msg_list: List[BaseMessage] = []
    if chat_history:
        for item in chat_history[-10:]:
            role = item.get("role", "").lower()
            content = item.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                msg_list.append(HumanMessage(content=content))
            elif role in ("assistant", "agent"):
                msg_list.append(AIMessage(content=content))

    # Append current user prompt as the latest HumanMessage
    msg_list.append(HumanMessage(content=user_request))

    initial_state = {
        "user_request": user_request,
        "session_id": session_id,
        "cognitive_memory": cognitive_memory,
        "triage_output": "",
        "triage_action": "",
        "selected_departments": [],
        "collaborating_departments": [],
        "raw_department_reports": {},
        "department_summaries": {},
        "final_response": "",
        "final_cfo_decision": "",
        "retry_count": 0,
        "inspector_feedback": "",
        "last_active_department": "",
        "inspector_decision": {},
        "messages": msg_list
    }

    try:
        final_state = app_graph.invoke(initial_state)
        result = final_state.get("final_response") or final_state.get("final_cfo_decision", "")
        dept = final_state.get("last_active_department") or "general_ops"
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"\n[Agency Execution Exception Caught] Activating Self-Healer...\n{tb}")
        rescue_report = trigger_rescue_mission(error_traceback=tb, task_context=user_request)
        result = rescue_report
        dept = "self_healing"

    # Persist turn into SQLite memory database and update user cognitive impression
    try:
        memory.record_turn(
            session_id=session_id,
            user_prompt=user_request,
            agent_response=result,
            department_used=dept
        )
    except Exception as e:
        print(f"[Memory Record Notice]: {e}")

    return result


if __name__ == "__main__":
    test_prompt = "Conduct a discounted cash flow valuation for a project with $5M initial outlay and $1.5M annual cash flows for 5 years at 10% discount rate."
    print(f"\n--- Running Master LangGraph Pipeline ---")
    print(f"Prompt: {test_prompt}\n")
    final_deliverable = run_agency(test_prompt)
    print("\n--- Final Master Deliverable ---")
    print(final_deliverable)
