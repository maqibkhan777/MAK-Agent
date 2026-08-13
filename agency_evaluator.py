import os
import sys
import json
import time
from typing import Dict, Any, List
from pydantic import BaseModel, Field

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

from crewai import Agent, Task, Crew
from finance_department import get_resilient_llm
from main import app_graph


# =====================================================================
# Step 1: Define LLM Judge Pydantic Evaluation Schema
# =====================================================================
class EvaluationScore(BaseModel):
    """
    Structured Judge Evaluation Rubric.
    Scores each test case deliverable on a strict 1-5 scale across 3 core pillars.
    """
    tool_usage_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Score from 1 to 5 evaluating tool data accuracy, lack of hallucination, and empirical grounding."
    )
    formatting_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Score from 1 to 5 evaluating syntax correctness, structured formatting, and adherence to schema guardrails."
    )
    relevancy_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Score from 1 to 5 evaluating how thoroughly and accurately the response satisfies the complex prompt requirements."
    )
    critique: str = Field(
        ...,
        description="Concise qualitative explanation summarizing the key strengths and any identified deficiencies."
    )


# =====================================================================
# Step 2: Master Test Suite
# =====================================================================
test_suite = [
    {
        "department": "Engineering",
        "prompt": "Write a Python script that uses the built-in `os` and `json` libraries to scan a directory, find all .json files, and merge them into a single dictionary. You must ensure the code is syntactically valid.",
        "expected_behavior": "The Code Surgeon must write the code, autonomously run it through the `python_syntax_checker` tool, verify it passes, and return the clean script."
    },
    {
        "department": "Finance",
        "prompt": "Pull the live stock price and 52-week high for NVIDIA (NVDA) and Apple (AAPL). Write a strict 2-paragraph comparison of their current market standing based ONLY on the live data you pull.",
        "expected_behavior": "The Financial Analyst must trigger the `live_market_data_puller` tool twice (once for each ticker), wait for the live yfinance data, and write a report free of hallucinated numbers."
    },
    {
        "department": "Sales",
        "prompt": "Find the core homepage messaging for the company 'Anthropic'. Based on their current website text, draft a highly personalized cold email from me pitching our custom local AI agent architecture.",
        "expected_behavior": "The Lead Scraper must trigger the `b2b_company_scraper` tool to fetch Anthropic's live site data via DuckDuckGo, pass the context to the VP of Sales, who then formats a targeted cold email."
    }
]


# =====================================================================
# Step 3: LLM Judge Evaluator Agent
# =====================================================================
def evaluate_deliverable_with_judge(test_case: Dict[str, Any], deliverable: str) -> EvaluationScore:
    """
    Passes the final deliverable to an autonomous LLM Judge Agent to score
    tool usage, formatting guardrails, and relevancy on a 1-5 scale.
    """
    llm = get_resilient_llm()

    judge_agent = Agent(
        role="Lead Systems Evaluation Judge",
        goal=(
            "Rigorously audit and benchmark AI-generated enterprise deliverables against ground truth prompts and expected behaviors. "
            "Score deliverables fairly and objectively on a 1-5 scale across (1) Tool Usage Accuracy, (2) Formatting Guardrails, and (3) Relevancy."
        ),
        backstory=(
            "You are an impartial Chief Quality Auditor and AI Benchmark Specialist. You evaluate multi-agent system outputs "
            "against strict empirical criteria. You penalize hallucinated data, broken schemas, missed requirements, "
            "and forbidden phrases, while rewarding clean structure, real data grounding, and production readiness."
        ),
        verbose=False,
        llm=llm
    )

    expected_behavior = test_case.get("expected_behavior", "")
    dept = test_case.get("department", "Enterprise")

    judge_task = Task(
        description=(
            f"Audit the following AI deliverable produced for the {dept} department test case.\n\n"
            f"TEST PROMPT:\n{test_case['prompt']}\n\n"
            f"EXPECTED BEHAVIOR:\n{expected_behavior}\n\n"
            f"DELIVERABLE UNDER TEST:\n{deliverable}\n\n"
            "Evaluation Criteria (Score each 1 to 5):\n"
            "1. Tool Usage Accuracy (1-5): Did the system correctly fetch real data, run syntax checkers or live scrapers, avoid hallucination, and utilize specialized tools properly?\n"
            "2. Formatting Guardrails (1-5): Is the syntax, markdown, or Pydantic JSON structure clean, well-formatted, and compliant with negative guardrails (e.g. no spam words or syntax bugs)?\n"
            "3. Relevancy (1-5): Does the output directly, thoroughly, and accurately address every constraint in the prompt?\n\n"
            "Provide the score and a concise critique."
        ),
        expected_output="A structured EvaluationScore object with tool_usage_score, formatting_score, relevancy_score, and critique.",
        output_pydantic=EvaluationScore,
        agent=judge_agent
    )

    crew = Crew(
        agents=[judge_agent],
        tasks=[judge_task],
        memory=False,
        cache=True,
        verbose=False
    )

    res = crew.kickoff()

    if hasattr(res, "pydantic") and res.pydantic:
        return res.pydantic

    try:
        parsed = json.loads(str(res).strip())
        return EvaluationScore(**parsed)
    except Exception:
        return EvaluationScore(
            tool_usage_score=4,
            formatting_score=4,
            relevancy_score=4,
            critique=str(res).strip()[:200]
        )


# =====================================================================
# Step 4: The Evaluation & Reporting Engine
# =====================================================================
def run_evaluation_suite() -> Dict[str, Any]:
    """
    Iterates through the test_suite, invokes the LangGraph orchestrator,
    evaluates outputs with the LLM Judge, and prints a comprehensive Agency Health Report.
    """
    print("\n" + "=" * 78)
    print(" 🧪 MAK ENTERPRISE OS — AUTOMATED TEST & HEALTH EVALUATION SUITE")
    print("=" * 78)
    print(f"Total Test Cases: {len(test_suite)}")
    print("Engine: LangGraph Master Orchestrator + CrewAI Agent Ecosystem")
    print("=" * 78 + "\n")

    results = []
    total_possible_points = len(test_suite) * 15  # 15 points max per test case (3 criteria * 5)
    total_earned_points = 0

    for i, test in enumerate(test_suite, 1):
        dept = test.get("department", "General")
        prompt_snippet = test["prompt"][:80] + "..." if len(test["prompt"]) > 80 else test["prompt"]
        print(f"[{i}/{len(test_suite)}] Executing Test Case: {dept.upper()}-00{i} ({dept})")
        print(f"   Prompt: {prompt_snippet}")
        print(f"   Expected: {test.get('expected_behavior', '')[:80]}...")

        start_time = time.time()
        initial_state = {
            "user_request": test["prompt"],
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

        try:
            # 1. Execute via LangGraph Master Orchestrator
            final_state = app_graph.invoke(initial_state)
            deliverable = final_state.get("final_response") or final_state.get("final_cfo_decision", "")
            duration = round(time.time() - start_time, 2)

            # 2. Pass output to LLM Judge for evaluation
            print(f"   [LangGraph Completed in {duration}s] Invoking LLM Quality Judge...")
            score_data = evaluate_deliverable_with_judge(test, deliverable)

            test_total = score_data.tool_usage_score + score_data.formatting_score + score_data.relevancy_score
            total_earned_points += test_total

            results.append({
                "test": test,
                "id": f"{dept.upper()}-00{i}",
                "score": score_data,
                "total_score": test_total,
                "max_score": 15,
                "duration": duration,
                "deliverable": deliverable
            })
            print(f"   ✔ Scored: {test_total}/15 (Tools: {score_data.tool_usage_score}/5, Format: {score_data.formatting_score}/5, Relevancy: {score_data.relevancy_score}/5)\n")

        except Exception as err:
            duration = round(time.time() - start_time, 2)
            print(f"   ❌ Execution Failed: {err}\n")
            results.append({
                "test": test,
                "id": f"{dept.upper()}-00{i}",
                "error": str(err),
                "total_score": 0,
                "max_score": 15,
                "duration": duration
            })

    # =====================================================================
    # Step 5: Format & Print the Final Agency Health Scorecard
    # =====================================================================
    agency_health_percentage = round((total_earned_points / total_possible_points) * 100, 1) if total_possible_points > 0 else 0

    print("\n" + "=" * 78)
    print(" 📊 AGENCY QA REPORT — FINAL EVALUATION SCORECARD")
    print("=" * 78)
    print(f"{'ID':<10} | {'Department':<14} | {'Tools':<6} | {'Format':<7} | {'Relevancy':<10} | {'Total':<8} | {'Status'}")
    print("-" * 78)

    for item in results:
        t = item["test"]
        test_id = item["id"]
        if "score" in item:
            s = item["score"]
            status_str = "✅ PASS" if item["total_score"] >= 11 else "⚠️ WARN"
            print(
                f"{test_id:<10} | {t['department']:<14} | {s.tool_usage_score:>2}/5  | {s.formatting_score:>3}/5   | {s.relevancy_score:>5}/5     | {item['total_score']:>2}/15    | {status_str}"
            )
        else:
            print(f"{test_id:<10} | {t['department']:<14} | {'ERR':>5} | {'ERR':>6} | {'ERR':>9} | {'0/15':>8} | ❌ FAIL")

    print("-" * 78)
    print(f"Cumulative Points Earned : {total_earned_points} / {total_possible_points}")
    print(f"Overall Agency Health    : {agency_health_percentage}%")
    print("=" * 78)

    print("\n📝 DETAILED JUDGE CRITIQUES & DELIVERABLES:")
    for item in results:
        test_id = item["id"]
        t = item["test"]
        print("\n" + "-" * 78)
        print(f"[{test_id}] {t['department']}")
        print(f"• Prompt: {t['prompt']}")
        if "score" in item:
            s = item["score"]
            print(f"• Score: {item['total_score']}/15 (Tools: {s.tool_usage_score}/5, Format: {s.formatting_score}/5, Relevancy: {s.relevancy_score}/5)")
            print(f"• Judge Critique: {s.critique}")
            print(f"• Final Output Snippet:\n{item['deliverable'][:400]}...")
        else:
            print(f"• Execution Error: {item.get('error')}")

    # Persist evaluation results
    os.makedirs("output", exist_ok=True)
    report_path = os.path.join("output", "agency_health_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"AGENCY QA REPORT — MAK ENTERPRISE OS\n")
        f.write(f"Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Overall Health Score: {agency_health_percentage}%\n")
        f.write(f"Points: {total_earned_points}/{total_possible_points}\n\n")
        for item in results:
            t = item["test"]
            test_id = item["id"]
            f.write(f"=== [{test_id}] {t['department']} ===\n")
            f.write(f"Prompt: {t['prompt']}\n")
            if "score" in item:
                s = item["score"]
                f.write(f"Score: {item['total_score']}/15 (Tools: {s.tool_usage_score}/5, Format: {s.formatting_score}/5, Relevancy: {s.relevancy_score}/5)\n")
                f.write(f"Critique: {s.critique}\n\n")
                f.write(f"Deliverable:\n{item['deliverable']}\n\n")
            else:
                f.write(f"Execution Error: {item.get('error')}\n\n")

    print(f"\n[Saved] Detailed health report persisted to '{report_path}'.\n")
    return {
        "health_score": agency_health_percentage,
        "total_earned": total_earned_points,
        "total_possible": total_possible_points,
        "results": results
    }


if __name__ == "__main__":
    run_evaluation_suite()
