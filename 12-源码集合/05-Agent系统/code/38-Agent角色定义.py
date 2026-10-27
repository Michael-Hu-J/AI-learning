agent = Agent(
    role="API 测试工程师",
    goal="发现 API 中的缺陷",
    backstory="擅长 pytest、Postman、性能测试",
    allow_delegation=False,  # 不允许委派
    verbose=True,
)

# Backstory V1：简单
backstory_v1 = "你有测试经验。"

# Backstory V2：具体
backstory_v2 = """你有5年Web系统测试经验，熟悉功能测试、安全测试、性能测试。
你曾负责某电商平台的测试工作，发现过多个高危漏洞。"""

# Backstory V3：故事化
backstory_v3 = """你曾在某头部电商公司担任安全测试负责人，负责核心交易系统的测试。
你擅长黑盒测试和灰盒测试，熟悉OWASP Top 10漏洞。
你曾发现过一个严重的SQL注入漏洞，避免了公司数百万损失。
你对密码安全、Session管理、权限绕过有深入研究。"""

constraints = [
    "只关注安全测试，不关注UI和功能",  # 范围约束
    "每个漏洞必须给出复现步骤",  # 输出格式约束
    "按照严重程度排序输出",  # 输出顺序约束
    "不要使用Markdown表格，使用列表格式",  # 格式约束
    "如果不确定，请明确说明'不确定'，不要编造",  # 真实性约束
]

def test_agent_role(agent, test_tasks):
    """
    验证角色定义是否有效：
    1. Agent是否理解自己的角色
    2. Agent是否按角色预期行事
    """
    results = []
    
    for task in test_tasks:
        response = agent.execute(task)
        
        checks = {
            "角色一致性": "测试" in response or "缺陷" in response,
            "专业度": "建议" in response or "风险" in response,
            "格式规范": len(response.split('\n')) > 3,
            "无幻觉": "不确定" in response or len(response) > 50,
        }
        
        passed = sum(checks.values()) >= 3
        
        results.append({
            "task": task,
            "checks": checks,
            "passed": passed
        })
    
    pass_rate = sum(1 for r in results if r["passed"]) / len(results)
    
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "pass_rate": pass_rate,
        "details": results
    }

# 测试用例
test_tasks = [
    "请为登录功能生成安全测试用例",
    "分析以下测试日志中的失败原因：[日志内容]",
    "审核这份测试报告的质量",
]

result = test_agent_role(test_agent, test_tasks)
print(f"角色定义通过率: {result['pass_rate']:.2%}")

from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage

llm = ChatOpenAI(temperature=0, model="gpt-4")

# 角色定义通过SystemMessage注入
system_message = SystemMessage(
    content="""你是一名有5年经验的Web安全测试工程师。
你曾在某电商公司负责安全测试，发现过多个高危漏洞。
你熟悉OWASP Top 10，擅长SQL注入、XSS、CSRF等漏洞的发现和修复。
你的任务是根据需求文档生成全面的安全测试用例。
每个用例必须包含：用例名称、前置条件、测试步骤、预期结果、风险等级。
按照风险等级从高到低排序输出。"""
)

# 初始化Agent
agent = initialize_agent(
    tools=[],
    llm=llm,
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    system_message=system_message,
)

# 执行任务
result = agent.run("请为用户登录功能生成安全测试用例")
print(result)

from crewai import Agent, Task, Crew, Process

# 定义角色
security_tester = Agent(
    role='Web安全测试工程师',
    goal='发现系统中的所有安全漏洞',
    backstory="""你曾在某头部电商公司担任安全测试负责人，
负责核心交易系统的测试。你擅长黑盒测试和灰盒测试，
熟悉OWASP Top 10漏洞。你曾发现过一个严重的SQL注入漏洞，
避免了公司数百万损失。""",
    allow_delegation=False,
    verbose=True,
)

reviewer = Agent(
    role='测试质量评审专家',
    goal='确保测试用例的完整性和专业性',
    backstory="""你有10年测试质量保障经验，
曾评审过上千份测试报告。你擅长发现测试用例中的遗漏和缺陷。""",
    allow_delegation=False,
    verbose=True,
)

# 定义任务
generate_task = Task(
    description='为登录功能生成安全测试用例',
    expected_output='一份完整的安全测试用例列表',
    agent=security_tester,
)

review_task = Task(
    description='评审安全测试用例的完整性和专业性',
    expected_output='评审报告，指出遗漏和不足',
    agent=reviewer,
)

# 创建Crew
crew = Crew(
    agents=[security_tester, reviewer],
    tasks=[generate_task, review_task],
    process=Process.sequential,
)

# 执行
result = crew.kickoff()

import autogen

# 角色配置
security_tester_config = {
    "seed": 42,
    "llm_config": {"model": "gpt-4", "temperature": 0},
    "system_message": """你是一名Web安全测试工程师。
你的任务是发现系统中的安全漏洞。
每个漏洞必须给出复现步骤和修复建议。""",
}

reviewer_config = {
    "seed": 42,
    "llm_config": {"model": "gpt-4", "temperature": 0},
    "system_message": """你是一名测试质量评审专家。
你的任务是评审安全测试的结果，指出遗漏和不足。
不要自己生成测试用例，只评审已有的结果。""",
}

# 创建Agent
security_tester = autogen.AssistantAgent(
    name="SecurityTester",
    **security_tester_config,
)

reviewer = autogen.AssistantAgent(
    name="Reviewer",
    **reviewer_config,
)

user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
)

# 启动对话
user_proxy.initiate_chat(
    security_tester,
    message="请为登录功能生成安全测试用例",
)

import openai

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": """你是一名有5年经验的Web安全测试工程师。
你曾在某电商公司负责安全测试，发现过多个高危漏洞。
你熟悉OWASP Top 10，擅长SQL注入、XSS、CSRF等漏洞的发现和修复。
你的任务是根据需求文档生成全面的安全测试用例。
每个用例必须包含：用例名称、前置条件、测试步骤、预期结果、风险等级。
按照风险等级从高到低排序输出。
如果不确定某个漏洞是否存在，请明确说明"不确定"，不要编造。"""
        },
        {
            "role": "user",
            "content": "请为登录功能生成安全测试用例"
        }
    ],
    temperature=0,
)

print(response.choices[0].message.content)

def ab_test_roles(role_a, role_b, test_tasks, num_runs=5):
    """
    对两个角色定义版本做A/B测试
    """
    results_a = []
    results_b = []
    
    for _ in range(num_runs):
        for task in test_tasks:
            # 测试角色A
            response_a = run_agent(role_a, task)
            score_a = evaluate_response(response_a, task)
            results_a.append(score_a)
            
            # 测试角色B
            response_b = run_agent(role_b, task)
            score_b = evaluate_response(response_b, task)
            results_b.append(score_b)
    
    avg_a = sum(results_a) / len(results_a)
    avg_b = sum(results_b) / len(results_b)
    
    print(f"角色A平均分: {avg_a:.2f}")
    print(f"角色B平均分: {avg_b:.2f}")
    print(f"提升: {((avg_b - avg_a) / avg_a * 100):.1f}%" if avg_b > avg_a else "角色A更优")
    
    return {"a": avg_a, "b": avg_b}

# 使用示例
role_v1 = "你是一名测试工程师"
role_v2 = """你是一名有5年经验的Web安全测试工程师，
擅长SQL注入、XSS、CSRF等漏洞的发现和修复"""

ab_test_roles(role_v1, role_v2, test_tasks=["生成登录功能测试用例"])
