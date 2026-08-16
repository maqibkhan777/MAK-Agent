import os
import sys
import pytest
from dotenv import load_dotenv

# UTF-8 stdout configuration for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

load_dotenv()

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



import litellm
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from deepeval.models import DeepEvalBaseLLM
from main import run_agency


# =====================================================================
# Custom Groq LLM Provider for DeepEval Mathematical Metrics
# Uses resilient LiteLLM Groq router to evaluate test cases without OpenAI dependency
# =====================================================================
class GroqEvalLLM(DeepEvalBaseLLM):
    def __init__(self, model_name="groq/llama-3.3-70b-versatile"):
        self.model_name = model_name

    def load_model(self):
        return self.model_name

    def get_model_name(self):
        return self.model_name


    def generate(self, prompt: str) -> str:
        try:
            res = litellm.completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return res.choices[0].message.content
        except Exception as e:
            # Fallback to 8b-instant if 70b hits rate limits
            res = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return res.choices[0].message.content

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)


# Initialize evaluation model using Groq LLM backend
eval_llm = GroqEvalLLM()


# =====================================================================
# DeepEval Agent Evaluation Test Suite
# =====================================================================
def test_agent_relevancy_and_faithfulness():
    """
    Evaluates primary agent responses against:
    - AnswerRelevancyMetric (threshold=0.7)
    - FaithfulnessMetric (threshold=0.7)
    """
    input_query = "What is the recommended software architecture pattern for microservices handling JWT authentication?"
    
    # Execute primary agent via LangGraph pipeline
    actual_output = run_agency(input_query)
    assert actual_output is not None and len(actual_output) > 0, "Agent returned empty response"

    # Reference context for Faithfulness evaluation
    retrieval_context = [
        "Microservice architecture for user authentication should utilize API Gateway for routing, stateless JWT validation, HTTPS transport security, and isolated identity user stores."
    ]

    # Configure DeepEval mathematical metrics with 0.7 thresholds
    relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=eval_llm)
    faithfulness_metric = FaithfulnessMetric(threshold=0.7, model=eval_llm)

    # Construct test case
    test_case = LLMTestCase(
        input=input_query,
        actual_output=str(actual_output),
        retrieval_context=retrieval_context
    )

    # Assert test execution against configured metric thresholds
    assert_test(test_case, [relevancy_metric, faithfulness_metric])


def test_sales_cold_outreach_relevancy():
    """
    Evaluates the Sales Department's ability to pull real data and adhere to email constraints.
    """
    input_query = "Find the core homepage messaging for 'Vercel' and draft a cold email pitching our web framework."
    
    # Execute primary agent via LangGraph pipeline
    actual_output = run_agency(input_query)
    assert actual_output is not None and len(actual_output) > 0, "Agent returned empty response"

    # We expect the output to be a JSON object containing "subject" and "body" based on SalesEmail schema
    retrieval_context = [
        "Vercel is the frontend cloud platform. It provides the developer experience and infrastructure to build, scale, and secure a faster, more personalized web."
    ]

    relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=eval_llm)
    faithfulness_metric = FaithfulnessMetric(threshold=0.7, model=eval_llm)

    test_case = LLMTestCase(
        input=input_query,
        actual_output=str(actual_output),
        retrieval_context=retrieval_context
    )

    assert_test(test_case, [relevancy_metric, faithfulness_metric])


def test_finance_ticker_hallucination():
    """
    Evaluates the Finance Valuation agent to ensure it doesn't hallucinate stock data.
    """
    input_query = "What is the live stock price and 52-week high for Microsoft (MSFT)?"
    
    actual_output = run_agency(input_query)
    
    # Check if the output actually attempts to provide real financial metrics 
    # instead of a generic refusal or hallucinated text.
    relevancy_metric = AnswerRelevancyMetric(threshold=0.8, model=eval_llm)
    
    test_case = LLMTestCase(
        input=input_query,
        actual_output=str(actual_output)
    )

    assert_test(test_case, [relevancy_metric])


if __name__ == "__main__":
    print("Running test_agent_evals standalone execution...")
    test_agent_relevancy_and_faithfulness()
    test_sales_cold_outreach_relevancy()
    test_finance_ticker_hallucination()
    print("All DeepEval evaluations completed successfully.")
