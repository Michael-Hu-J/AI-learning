from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall

# dataset 需含 question, answer, contexts, ground_truth
result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall])

from deepeval import evaluate
from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase

case = LLMTestCase(input="...", actual_output="...", context=[...])
evaluate([case], [HallucinationMetric(threshold=0.5)])

import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = "my-agent"
# 之后 LangChain 调用自动上报
