from crewai import Agent, Task, Crew, LLM
from app.core.config import settings
import asyncio


def create_designer_agent():
    """创建测试设计师 Agent"""
    llm = LLM(
        model=settings.OPENAI_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL
    )
    
    return Agent(
        role="测试设计师 (Test Designer)",
        goal="根据需求和接口定义，设计全面的测试用例，覆盖正常流程、边界条件和异常场景",
        backstory="""你是资深测试设计师，擅长：
        1. 等价类划分和边界值分析
        2. 状态迁移图和判定表
        3. 场景法和错误推测法
        4. 覆盖正常流程、边界条件、异常场景
        
        你的设计原则：
        - 每个功能点至少 3 个测试用例（正常/边界/异常）
        - 优先覆盖核心业务流程
        - 考虑并发和竞态条件
        - 输出结构化的测试用例表格
        
        你有 10 年测试设计经验，曾经为多个电商平台设计过测试用例库。
        你特别擅长发现容易被忽略的边界场景。
        
        你相信好的测试用例设计是测试成功的关键。""",
        llm=llm,
        verbose=False,
        allow_delegation=False
    )


async def run_designer_agent(test_plan: str, client_id: str) -> str:
    """
    运行测试设计师 Agent
    
    Args:
        test_plan: 测试计划（来自上一个 Agent）
        client_id: WebSocket 客户端 ID
        
    Returns:
        生成的测试用例
    """
    agent = create_designer_agent()
    
    task = Task(
        description=f"""
作为测试设计师，请根据以下测试计划设计测试用例：

{test_plan}

## 设计要求

1. **用例覆盖**
   - 每个 P0 功能至少设计 5 个测试用例
   - 每个 P1 功能至少设计 3 个测试用例
   - P2 功能至少设计 2 个测试用例

2. **场景覆盖**
   - 正常流程场景
   - 边界条件场景
   - 异常场景
   - 并发场景（如适用）

3. **用例要素**
   - 用例 ID（唯一标识）
   - 功能模块
   - 优先级
   - 测试类型
   - 前置条件
   - 测试步骤（详细、可执行）
   - 预期结果
   - 自动化可行性（可自动化/需手工）

## 输出格式

使用 Markdown 表格格式：

| 用例 ID | 功能模块 | 优先级 | 测试类型 | 前置条件 | 测试步骤 | 预期结果 | 自动化 |
|---------|----------|--------|----------|----------|----------|----------|--------|
| TC001   | ...      | P0     | 功能测试 | ...      | 1.xxx 2.xxx | ...    | 是     |

保证测试用例清晰、可执行，便于测试工程师执行。
""",
        expected_output="结构化的测试用例集，用 Markdown 表格呈现，包含所有 required 字段",
        agent=agent
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=False
    )
    
    result = await asyncio.to_thread(crew.kickoff)
    return str(result)

# 阶段 2：测试设计师
# send_log(task_id, "agent_start", " 测试设计师开始设计测试用例...")  # 异步调用示例

from app.agents.designer import run_designer_agent
# test_cases = await run_designer_agent(test_plan, task_id)

# 保存测试用例
cases_file = os.path.join(output_dir, "02_test_cases.md")
with open(cases_file, "w", encoding="utf-8") as f:
    f.write(test_cases)

# send_log(task_id, "agent_complete", " 测试设计师完成用例设计", {
    # "output_file": "02_test_cases.md",
    # "word_count": len(test_cases)
# })

# test_plan 来自上一个 Agent（测试经理）的输出
# test_cases = await run_designer_agent(test_plan, task_id)
