class CodeReviewState(TypedDict):
    # 输入
    code: str; language: str; reviewer_id: str
    # 中间状态
    security_issues: List[str]; performance_issues: List[str]; style_issues: List[str]
    # 合并结果
    merged_issues: List[str]; severity_score: float
    # 控制流
    review_round: int; max_rounds: int; status: ReviewStatus
    # 输出
    final_report: Optional[str]; manual_review_required: bool

from langgraph.graph import StateGraph, END

workflow = StateGraph(CodeReviewState)
workflow.add_node("security_review", security_review_agent)
workflow.add_node("performance_review", performance_review_agent)
workflow.add_node("style_review", style_review_agent)
workflow.add_node("merge_results", merge_agent)
workflow.add_node("generate_report", report_agent)
workflow.set_entry_point("security_review")

# 并行边：security完成后，performance和style同时执行
workflow.add_edge("security_review", "performance_review")
workflow.add_edge("security_review", "style_review")
workflow.add_edge("performance_review", "merge_results")
workflow.add_edge("style_review", "merge_results")

# 条件边：根据审查结果决定下一步
def route_after_merge(state):
    if state["severity_score"] > 8.0 and state["review_round"] < state["max_rounds"]:
        return "revise"
    elif state["merged_issues"]:
        return "generate_report"
    return "pass"

workflow.add_conditional_edges("merge_results", route_after_merge,
    {"revise": "security_review", "generate_report": "generate_report", "pass": END})
workflow.add_edge("generate_report", END)
app = workflow.compile()

def security_review_agent(state):
    try:
        # 执行安全审查
        issues = analyze_security(state["code"])
        state["security_issues"] = issues
        state["status"] = ReviewStatus.COMPLETED
    except Exception as e:
        state["status"] = ReviewStatus.FAILED
        state["error_message"] = str(e)
        # 不抛出异常，让工作流继续，但标记失败
        print(f"安全审查失败：{e}")
    
    return state

import signal

class TimeoutException(Exception):
    pass

signal.signal(signal.SIGALRM, lambda s, f: (_ for None).throw(TimeoutException("超时")))
signal.alarm(300)  # 5分钟超时

try:
    result = app.invoke(initial_state)
except TimeoutException:
    result = {"status": "timeout", "partial_result": get_partial_state()}
finally:
    signal.alarm(0)

def route_after_merge(state):
    if state["severity_score"] > 8.0:
        if state["review_round"] < state["max_rounds"]:
            state["review_round"] += 1
            return "revise"
        else:
            state["manual_review_required"] = True
            return "generate_report"
    elif state["merged_issues"]:
        return "generate_report"
    return "pass"

def test_workflow_paths(workflow_app, test_cases):
    path_coverage = set()
    for case in test_cases:
        result = workflow_app.invoke(case["input"])
        path = "→".join(result.get("executed_nodes", []))
        path_coverage.add(path)
        passed = result.get("output") == case.get("expected_output")
        print(f"{'✅' if passed else '❌'} {case['name']}: {path}")
    return {"paths": len(path_coverage), "coverage": path_coverage}

test_cases = [
    {"name": "正常通过", "input": {"code": "def add(a,b): return a+b", "max_rounds": 3}, "expected_output": "pass"},
    {"name": "严重漏洞-循环", "input": {"code": "eval(user_input)", "max_rounds": 3}, "expected_output": "report"},
    {"name": "循环超限-需人工", "input": {"code": "vulnerable_code", "max_rounds": 2}, "expected_output": "manual_review"},
]

class DocumentState(TypedDict):
    document_path: str; document_type: str
    extracted_text: str; ocr_confidence: float
    entities: dict; risk_items: List[dict]; overall_risk_score: float
    summary: str; key_points: List[str]
    status: str; error_message: Optional[str]

from langgraph.graph import StateGraph, END

# 状态定义——所有节点共享的数据结构
class ReviewState(TypedDict):
    code: str
    security_issues: List[str]
    merged_issues: List[str]
    severity_score: float
    review_round: int
    max_rounds: int
    final_report: Optional[str]

# 节点函数——每个Agent对应一个函数
def security_node(state):
    state["security_issues"] = analyze_security(state["code"])
    return state

def merge_node(state):
    state["merged_issues"] = state["security_issues"]
    state["severity_score"] = calculate_severity(state["merged_issues"])
    return state

def report_node(state):
    state["final_report"] = generate_report(state["merged_issues"])
    return state

# 构建图
graph = StateGraph(ReviewState)
graph.add_node("security", security_node)
graph.add_node("merge", merge_node)
graph.add_node("report", report_node)
graph.set_entry_point("security")
graph.add_edge("security", "merge")
graph.add_edge("merge", "report")
graph.add_edge("report", END)

app = graph.compile()

from crewai import Agent, Task, Crew, Process

security_agent = Agent(
    role="安全审查专家",
    goal="发现代码中的安全漏洞",
    backstory="你有10年安全审计经验"
)

merge_task = Task(
    description="合并所有审查结果",
    agent=merge_agent,
    context=[security_task, performance_task, style_task],
)

crew = Crew(agents=[...], tasks=[...], process=Process.sequential)
result = crew.kickoff(inputs={"code": "..."})
