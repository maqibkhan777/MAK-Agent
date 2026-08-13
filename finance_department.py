import os
import sys

# Configure UTF-8 encoding for Windows console and loggers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

import time
import litellm
from crewai import Agent, LLM

# Centrally sanitize prompt-caching headers and native tool definitions incompatible with Groq API
# Includes automatic retry & exponential backoff on RateLimitError (429) across all agents
if not getattr(litellm, "_groq_patched", False):
    _original_completion = litellm.completion
    def _groq_safe_completion(*args, **kwargs):
        kwargs.pop("raw_tool_calls", None)
        kwargs.pop("tools", None)
        kwargs.pop("tool_choice", None)
        kwargs.pop("cache_breakpoint", None)
        kwargs.pop("cache_control", None)
        
        if "messages" in kwargs and kwargs["messages"]:
            for msg in kwargs["messages"]:
                if isinstance(msg, dict):
                    msg.pop("cache_breakpoint", None)
                    msg.pop("cache_control", None)
                elif hasattr(msg, "cache_breakpoint"):
                    try:
                        setattr(msg, "cache_breakpoint", None)
                    except Exception:
                        pass
                elif hasattr(msg, "cache_control"):
                    try:
                        setattr(msg, "cache_control", None)
                    except Exception:
                        pass
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return _original_completion(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                if "ratelimiterror" in err_str or "429" in err_str or "rate limit" in err_str:
                    if attempt < max_retries - 1:
                        backoff_delay = (2 ** attempt) * 2
                        time.sleep(backoff_delay)
                        continue
                raise e

    litellm.completion = _groq_safe_completion
    litellm._groq_patched = True


def get_resilient_llm() -> LLM:
    """
    Constructs a central, resilient LLM instance configured with fallback routing 
    to handle RateLimitError (429) and API downtime gracefully.
    Primary: groq/llama-3.1-8b-instant
    Secondary Fallbacks: groq/llama-3.3-70b-versatile and OpenRouter (if API key present).
    """
    fallbacks = [
        "groq/llama-3.3-70b-versatile"
    ]
    
    # Optional OpenRouter free fallback if OPENROUTER_API_KEY is configured in .env
    if os.getenv("OPENROUTER_API_KEY"):
        fallbacks.append("openrouter/meta-llama/llama-3-8b-instruct:free")

    return LLM(
        model="groq/llama-3.1-8b-instant",
        fallbacks=fallbacks,
        max_retries=3,
        request_timeout=60
    )

class FinanceDepartment:
    """
    Enterprise Finance Department Ecosystem.
    Instantiates specialized corporate finance agents equipped with strict financial domain expertise
    and bound to a resilient fallback LLM router.
    """
    def __init__(self, llm: LLM = None):
        self.llm = llm if llm is not None else get_resilient_llm()

    def create_cfo(self) -> Agent:
        """Chief Financial Officer: Strategic financial leadership & executive capital allocation."""
        return Agent(
            role="Chief Financial Officer",
            goal="Strategic financial leadership, capital allocation, and final executive recommendations.",
            backstory="You are the Chief Financial Officer (CFO). As a seasoned financial executive, you possess deep expertise in corporate valuation, strategic capital allocation, capital budgeting, and enterprise risk management. You synthesize complex analytical inputs from corporate finance, risk, treasury, and capital structure specialists to deliver definitive, value-accretive strategic recommendations.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_corp_finance_analyst(self) -> Agent:
        """Corporate Finance Analyst: Capital budgeting, DCF modeling, NPV & IRR evaluation."""
        return Agent(
            role="Corporate Finance Analyst",
            goal="Evaluate corporate investment decisions, discounted cash flow (DCF) models, Net Present Value (NPV), and Internal Rate of Return (IRR).",
            backstory="You are a senior Corporate Finance Analyst specializing in capital budgeting, financial modeling, and investment appraisal. You rigorously evaluate project cash flows, calculate hurdle rates, compute Net Present Value (NPV), Internal Rate of Return (IRR), and payback horizons to ensure corporate capital is deployed into high-yield opportunities.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_risk_manager(self) -> Agent:
        """Risk Management Agent: Enterprise risk, Value at Risk (VaR), volatility & stress testing."""
        return Agent(
            role="Risk Management Agent",
            goal="Identify financial risks, downside exposure, market volatility, and conduct stress testing scenarios.",
            backstory="You are a principal Risk Manager specializing in enterprise risk management (ERM), Value at Risk (VaR), sensitivity analysis, and quantitative stress testing. You audit investment proposals for downside exposure, credit risk, market volatility, liquidity risk, and operational vulnerabilities, devising robust hedging and risk-mitigation strategies.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_treasury_agent(self) -> Agent:
        """Treasury Management Agent: Liquidity management, cash conversion cycle & funding availability."""
        return Agent(
            role="Treasury Management Agent",
            goal="Manage liquidity, cash conversion cycles, working capital requirements, and funding availability.",
            backstory="You are an expert Treasury Manager specializing in liquidity risk, working capital optimization, cash flow forecasting, and debt service coverage. You monitor cash conversion cycles, cash reserves, and short-term funding lines to ensure continuous enterprise solvency and liquidity under all market conditions.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_capital_structure_analyst(self) -> Agent:
        """Capital Structure Analyst: Debt/equity mix optimization & WACC calculation."""
        return Agent(
            role="Capital Structure Analyst",
            goal="Optimize debt and equity financing mix, evaluate capital costs, and calculate Weighted Average Cost of Capital (WACC).",
            backstory="You are a Capital Structure Analyst specializing in corporate capital structure optimization, debt-to-equity balancing, capital cost calculation, and WACC minimization. You analyze debt covenants, credit ratings, leverage ratios, and optimal financing mixes to ensure enterprise capital efficiency.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_summarizer(self) -> Agent:
        """Context Compression Specialist: Compresses lengthy financial analysis into strict, high-density 300-word summaries."""
        return Agent(
            role="Context Compression Specialist",
            goal="Read lengthy financial reports and compress them into strict, high-density 300-word bulleted summaries without losing any quantitative metrics or core arguments.",
            backstory="You are an elite executive summarizer. You strip away all fluff, pleasantries, and redundancy, leaving only the hard data required for the next department.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_m_and_a_analyst(self) -> Agent:
        """Mergers & Acquisitions Analyst: M&A valuation, synergies, deal structuring & integration costs."""
        return Agent(
            role="M&A Valuation Analyst",
            goal="Evaluate mergers, acquisitions, strategic synergies, deal valuation, accretion/dilution, and integration modeling.",
            backstory="You are a veteran M&A Valuation Analyst specializing in corporate transactions, takeover valuation, LBO modeling, strategic synergies analysis, and post-merger financial integration. You rigorously assess purchase price multiples, revenue/cost synergies, and transaction structures to maximize shareholder value.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_financial_controller(self) -> Agent:
        """Financial Controller: Accounting integrity, compliance, US GAAP/IFRS & auditing."""
        return Agent(
            role="Financial Controller",
            goal="Ensure accounting accuracy, financial compliance, regulatory reporting, US GAAP/IFRS standards, and internal auditing.",
            backstory="You are a meticulous Financial Controller and certified public accountant (CPA). You oversee corporate general ledgers, revenue recognition, internal control frameworks, regulatory audit compliance, and accounting risk mitigation to guarantee absolute financial reporting integrity.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_portfolio_manager(self) -> Agent:
        """Portfolio Manager: Asset allocation, diversification & risk-adjusted returns."""
        return Agent(
            role="Portfolio Manager",
            goal="Optimize asset allocation, construct diversified investment portfolios, and maximize risk-adjusted returns (Sharpe Ratio).",
            backstory="You are a senior Portfolio Manager with extensive experience in quantitative asset allocation, Modern Portfolio Theory (MPT), rebalancing strategies, and factor investing. You evaluate asset correlations, Sharpe ratios, and tail risk to optimize capital deployment across diverse asset classes.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_valuation_analyst(self) -> Agent:
        """Valuation Analyst: Enterprise valuation, DCF modeling, trading comps & transaction multiples."""
        return Agent(
            role="Valuation Analyst",
            goal="Determine enterprise value using Discounted Cash Flow (DCF), comparable company analysis (Comps), and precedent transactions.",
            backstory="You are an expert Valuation Analyst skilled in business valuation, terminal value calculations, intrinsic valuation, EV/EBITDA multiples, and sensitivity modeling. You establish reliable enterprise and equity valuation range estimates for strategic decisions.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_credit_analyst(self) -> Agent:
        """Credit Analyst: Borrower creditworthiness, DSCR, default risk & debt capacity."""
        return Agent(
            role="Credit Risk Analyst",
            goal="Assess counterparty creditworthiness, debt service coverage ratio (DSCR), credit ratings, and default probabilities.",
            backstory="You are a principal Credit Analyst specializing in debt capacity modeling, credit underwriting, covenant evaluation, and default probability assessment. You analyze balance sheet leverage, interest coverage ratios, and cash flow predictability to evaluate credit risks.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_inventory_manager(self) -> Agent:
        """Inventory Manager: EOQ modeling, supply chain working capital & carrying cost minimization."""
        return Agent(
            role="Inventory & Supply Chain Finance Manager",
            goal="Optimize Economic Order Quantity (EOQ), inventory holding costs, reorder points, and supply chain working capital.",
            backstory="You are a Supply Chain Finance Specialist focused on inventory optimization, EOQ formulation, carrying cost minimization, and inventory turnover efficiency. You balance stockout risks with cash tied up in working capital across operational supply chains.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_financial_planner(self) -> Agent:
        """Financial Planner: Revenue forecasting, OpEx budgeting & variance analysis."""
        return Agent(
            role="Financial Planning & Analysis (FP&A) Manager",
            goal="Develop rolling financial forecasts, model operational expenditure (OpEx), and analyze budget variance.",
            backstory="You are a Senior FP&A Manager adept at financial forecasting, budget variance tracking, revenue driver modeling, and operational expense planning. You bridge long-term strategic targets with granular monthly and quarterly financial plans.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

    def create_finance_tutor(self) -> Agent:
        """Finance Tutor: Educational breakdown of complex financial concepts & metrics step-by-step."""
        return Agent(
            role="Financial Education Specialist",
            goal="Explain complex corporate finance concepts, financial models, valuation metrics, and formulas in clear step-by-step guidance.",
            backstory="You are an expert Financial Educator and Communication Specialist. You excel at translating intricate financial theories (such as WACC, NPV, DCF, VaR, and leverage ratios) into accessible, clear, step-by-step explanations for non-finance stakeholders and executive teams.",
            verbose=True,
            memory=True,
            llm=self.llm
        )

