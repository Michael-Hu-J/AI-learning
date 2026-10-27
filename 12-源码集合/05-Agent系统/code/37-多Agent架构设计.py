# Task 1：分析测试日志
analyze_task = Task(
    description="分析测试日志，提取失败用例和错误信息。如果日志中没有根因信息，明确标注'根因未知'。",
    agent=analyzer,
    expected_output="失败用例列表，每个用例包含：用例名、错误码、错误信息、根因分析（或'根因未知'）",
)

# Task 2：生成报告
report_task = Task(
    description="基于分析结果，生成结构化的Markdown测试报告。如果根因未知，在报告中注明'根因未知，需人工排查'。",
    agent=reporter,
    expected_output="完整的Markdown测试报告",
    context=[analyze_task],  # 依赖analyze_task的输出
)

# Task 3：审核报告
review_task = Task(
    description="审核报告质量。如果Analyzer明确标注'根因未知'，则接受该结论，不要死循环追问。",
    agent=reviewer,
    expected_output="审核意见：通过/不通过，以及修改建议",
    context=[report_task],  # 依赖report_task的输出
)

def execute_with_retry(agent, task, max_retries=3, backoff_factor=2):
    """带指数退避的重试函数"""
    import time
    for i in range(max_retries):
        try:
            result = agent.execute(task)
            return result
        except Exception as e:
            print(f"第{i+1}次执行失败: {e}")
            if i == max_retries - 1:
                # 最后一次重试失败，降级处理
                return {"status": "degraded", "message": "Agent不可用，使用默认值"}
            # 指数退避：第1次等1秒，第2次等2秒，第3次等4秒
            time.sleep(backoff_factor ** i)
    return None

import json
from datetime import datetime

def save_state_snapshot(crew, step_name):
    """保存状态快照"""
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "step": step_name,
        "agent_states": {
            agent.role: agent.state for agent in crew.agents
        },
        "task_states": {
            task.description: task.status for task in crew.tasks
        }
    }
    
    with open(f"snapshot_{step_name}.json", "w") as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"状态快照已保存: snapshot_{step_name}.json")

from crewai import Agent, Task, Crew, Process

# 定义Agent
analyzer = Agent(
    role="测试分析员",
    goal="从测试日志中提取失败用例和错误信息，给出初步根因分析",
    backstory="你有10年测试经验，擅长从海量日志中快速定位问题根因。",
    verbose=True,
    allow_delegation=False,
)

reporter = Agent(
    role="测试报告写手",
    goal="基于分析结果，生成结构化的Markdown测试报告",
    backstory="你擅长数据可视化和报告撰写，能把复杂的技术问题用通俗的语言表达。",
    verbose=True,
    allow_delegation=False,
)

reviewer = Agent(
    role="测试报告审核员",
    goal="审核报告质量，确保信息完整、准确、无遗漏",
    backstory="你有15年测试管理经验，对报告质量要求极其严格。",
    verbose=True,
    allow_delegation=False,
)

# 定义Task
analyze_task = Task(
    description="分析测试日志，提取失败用例和错误信息。",
    agent=analyzer,
    expected_output="失败用例列表，每个包含：用例名、错误码、错误信息、根因分析",
)

report_task = Task(
    description="基于分析结果，生成结构化的Markdown测试报告。",
    agent=reporter,
    expected_output="完整的Markdown测试报告",
    context=[analyze_task],
)

review_task = Task(
    description="审核报告质量。如果根因未知，接受该结论。",
    agent=reviewer,
    expected_output="审核意见：通过/不通过，以及修改建议",
    context=[report_task],
)

# 创建Crew
crew = Crew(
    agents=[analyzer, reporter, reviewer],
    tasks=[analyze_task, report_task, review_task],
    verbose=2,
    process=Process.sequential,  # 顺序执行
)

# 执行
result = crew.kickoff()
print(result)

from langgraph.graph import Graph, StateGraph

# 定义状态
class TestState:
    def __init__(self):
        self.test_results = []
        self.analysis = None
        self.report = None
        self.review_status = None

# 定义节点
def execute_tests(state):
    """执行测试"""
    state.test_results = run_api_tests()
    return state

def analyze_results(state):
    """分析结果"""
    if not state.test_results:
        return state  # 没有结果，跳过
    state.analysis = analyze(state.test_results)
    return state

def generate_report(state):
    """生成报告"""
    if not state.analysis:
        state.report = "测试未执行或分析失败"
        return state
    state.report = write_report(state.analysis)
    return state

def should_review(state):
    """判断是否需要审核"""
    if state.analysis and len(state.analysis.failures) > 10:
        return "review"  # 失败用例超过10个，需要审核
    return "done"        # 否则直接结束

# 构建图
workflow = StateGraph(TestState)
workflow.add_node("execute", execute_tests)
workflow.add_node("analyze", analyze_results)
workflow.add_node("report", generate_report)
workflow.add_node("review", review_report)

workflow.set_entry_point("execute")
workflow.add_edge("execute", "analyze")
workflow.add_edge("analyze", "report")
workflow.add_conditional_edges("report", should_review, {
    "review": "review",
    "done": "end"
})
workflow.add_edge("review", "end")

app = workflow.compile()
result = app.invoke(TestState())

import autogen

# 创建Agent
config_list = [{"model": "gpt-4", "api_key": "your-key"}]

llm_config = {
    "config_list": config_list,
    "temperature": 0.1,
    "max_tokens": 2000,
}

analyst = autogen.AssistantAgent(
    name="Analyst",
    llm_config=llm_config,
    system_message="你是测试分析员，负责分析测试日志中的失败用例。",
)

writer = autogen.AssistantAgent(
    name="Writer",
    llm_config=llm_config,
    system_message="你是报告写手，负责基于分析结果撰写测试报告。",
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
)

# 启动对话
user_proxy.initiate_chat(
    analyst,
    message="请分析以下测试日志中的失败用例，然后和Writer一起生成测试报告。",
)
