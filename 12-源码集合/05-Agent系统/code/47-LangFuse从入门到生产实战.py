from langfuse import observe, get_client

@observe(name="hello-langfuse")
def answer_question(question: str) -> str:
    # 模拟 LLM 回答
    return f"关于「{question}」，我的回答是：测试通过。"

if __name__ == "__main__":
    answer_question("LangFuse 怎么用？")
    get_client().flush()   # 短脚本必须 flush，否则 Trace 可能丢
    print("Done — 去 LangFuse UI 的 Traces 页刷新查看")

from langfuse import observe

@observe(name="rag-pipeline")
def rag_answer(question: str) -> str:
    docs = retrieve(question)
    return generate(question, docs)

@observe(name="vector-search", as_type="retriever")
def retrieve(question: str) -> list:
    return ["doc1", "doc2"]

@observe(name="gpt-answer", as_type="generation")
def generate(question: str, docs: list) -> str:
    return "基于文档的回答..."

from langfuse import observe, get_client, propagate_attributes

@observe()
def handle_chat(session_id: str, user_id: str, message: str):
    with propagate_attributes(session_id=session_id, user_id=user_id):
        return do_rag(message)

from langfuse import observe, get_client

@observe(name="customer-service")
def customer_service(query: str, order_id: str | None = None) -> dict:
    intent = classify_intent(query)
    if intent == "order_status":
        data = query_order(order_id)
        reply = format_reply(data)
    else:
        reply = fallback_reply(query)
    return {"intent": intent, "reply": reply}

@observe(name="classify-intent", as_type="span")
def classify_intent(query: str) -> str:
    return "order_status"

@observe(name="query-order", as_type="tool")
def query_order(order_id: str) -> dict:
    return {"status": "已发货", "order_id": order_id}

@observe(name="format-reply", as_type="generation")
def format_reply(data: dict) -> str:
    return f"订单 {data['order_id']} 状态：{data['status']}"

from langfuse.openai import openai  #  drop-in 替换
from langfuse import get_client

client = openai.OpenAI()  # 环境变量 OPENAI_API_KEY 照旧

@observe(name="qa-with-openai")
def ask(question: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}],
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    print(ask("什么是 RAG？"))
    get_client().flush()

from langfuse import observe, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

@observe(name="langchain-rag-query")
def run_chain(user_input: str) -> str:
    with propagate_attributes(trace_name="langchain-demo", session_id="test-session-1"):
        handler = CallbackHandler()
        llm = ChatOpenAI(model="gpt-4o-mini")
        prompt = ChatPromptTemplate.from_template("简洁回答：{input}")
        chain = prompt | llm
        result = chain.invoke({"input": user_input}, config={"callbacks": [handler]})
        return result.content

from langfuse import get_client

langfuse = get_client()

with langfuse.start_as_current_observation(as_type="span", name="manual-step") as span:
    span.update(input={"query": "test"}, output={"answer": "ok"})

from langfuse import get_client

langfuse = get_client()
prompt = langfuse.get_prompt("customer-service-system", label="production")  # 或 version=2
compiled = prompt.compile(user_question="我的订单到哪了")
# compiled 可直接喂给 LLM

from langfuse import get_client

langfuse = get_client()
# trace_id 从 UI 或 observe 上下文获取
langfuse.create_score(
    trace_id="your-trace-id",
    name="answer-correct",
    value=1,           # 1=通过, 0=失败
    comment="检索文档正确，回答无幻觉",
)

@observe(name="auto-eval")
def auto_eval_trace(trace_id: str, question: str, answer: str, expected: str):
    score = 1 if expected.lower() in answer.lower() else 0
    get_client().create_score(
        trace_id=trace_id,
        name="keyword-match",
        value=score,
    )

# 伪代码：CI 门禁
def test_rag_eval_regression():
    result = run_langfuse_experiment(dataset="golden-set-v2", prompt_label="production")
    assert result.avg_score >= 0.85, f"Score dropped: {result.avg_score}"
    assert result.pass_rate >= 0.90

from langfuse import get_client

langfuse = get_client()
with langfuse.start_as_current_observation(as_type="generation", name="llm-call") as gen:
    gen.update(
        model="deepseek-v4-pro",
        usage={"input": 120, "output": 80, "total": 200},
        output={"text": "..."},
    )

import random
from langfuse import observe, get_client

SAMPLE_RATE = 0.1
ALWAYS_TRACE_ON_ERROR = True

def should_trace(success: bool) -> bool:
    if not success and ALWAYS_TRACE_ON_ERROR:
        return True
    return random.random() < SAMPLE_RATE

@observe(name="production-qa")
def production_qa(question: str) -> str:
    try:
        return real_pipeline(question)
    except Exception:
        # 失败请求 LangFuse 仍会记录（observe 捕获异常）
        raise

@observe(capture_input=False, capture_output=False, name="sensitive-qa")
def sensitive_qa(question: str) -> str:
    ...
