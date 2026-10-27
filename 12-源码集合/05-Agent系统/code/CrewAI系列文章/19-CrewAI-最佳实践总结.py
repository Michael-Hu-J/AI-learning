#  错误 - 一个 Agent 做太多事
agent = Agent(
    role="测试全能手",
    goal="做所有测试相关的事情",
    backstory="你会写计划、设计用例、执行测试、分析 Bug..."
)

#  正确 - 每个 Agent 专注一件事
planner = Agent(role="测试计划专家", goal="制定测试计划")
designer = Agent(role="测试用例设计师", goal="设计测试用例")
executor = Agent(role="测试执行工程师", goal="执行测试用例")
analyst = Agent(role="Bug 分析专家", goal="分析 Bug 原因")

#  错误 - 目标模糊
agent = Agent(
    role="测试助手",
    goal="帮助测试"
)

#  正确 - 目标具体可衡量
agent = Agent(
    role="测试用例设计师",
    goal="根据需求文档设计 20 条以上覆盖全面的测试用例"
)

#  错误 - backstory 太简单
agent = Agent(
    role="测试专家",
    backstory="你有测试经验"
)

#  正确 - backstory 详细具体
agent = Agent(
    role="高级测试工程师",
    backstory="""你是拥有 10 年经验的测试专家，擅长：
    1. 测试用例设计（等价类、边界值、场景法）
    2. 测试自动化（Selenium、Appium、Pytest）
    3. 性能测试（LoadRunner、JMeter）
    
    你的工作风格：
    - 结果导向
    - 风险推动
    - 注重细节
    
    你相信：好的测试用例是测试成功的一半。"""
)

# 开发调试：verbose=True
agent = Agent(..., verbose=True)  # 查看详细执行过程

# 生产环境：verbose=False
agent = Agent(..., verbose=False)  # 只输出结果

# 设计时可测试的 Agent
agent = Agent(
    role="测试执行工程师",
    goal="执行测试用例并记录结果",
    backstory="...",
    max_iter=10,  # 限制迭代次数，防止无限循环
    max_rpm=60,   # 限制请求频率，防止 API 限流
    cache=True    # 启用缓存，提高重复执行速度
)

#  错误 - 描述模糊
task = Task(
    description="测试一下系统"
)

#  正确 - 描述具体
task = Task(
    description="""请为以下功能设计测试用例：

功能：用户登录
输入：用户名、密码
输出：登录成功/失败

要求：
1. 至少 10 条测试用例
2. 覆盖正常场景和异常场景
3. 包含边界值测试"""
)

#  错误 - 输出不明确
task = Task(
    description="分析测试结果",
    expected_output="分析报告"
)

#  正确 - 输出格式明确
task = Task(
    description="分析测试结果",
    expected_output="""JSON 格式报告，包含：
- summary: 测试总结
- passed: 通过数量
- failed: 失败数量
- bugs: Bug 列表（每个 Bug 包含标题、严重级别、复现步骤）"""
)

# Task 依赖链
plan_task = Task(description="制定测试计划", agent=planner)

design_task = Task(
    description="设计测试用例",
    agent=designer,
    context=[plan_task]  # 依赖测试计划
)

execute_task = Task(
    description="执行测试用例",
    agent=executor,
    context=[design_task]  # 依赖测试用例
)

task = Task(
    description="执行测试",
    agent=executor,
    human_input=True,  # 关键任务需要人工确认
    callback=lambda result: log_result(result)  # 回调处理结果
)

# 小型任务：1-2 个 Agent
crew = Crew(agents=[agent1], tasks=[task1])

# 中型任务：3-5 个 Agent
crew = Crew(
    agents=[planner, designer, executor, analyst],
    tasks=[plan_task, design_task, execute_task, analyze_task]
)

# 大型任务：拆分成多个 Crew
crew1 = Crew(agents=..., tasks=...)  # 测试计划
crew2 = Crew(agents=..., tasks=...)  # 测试执行
crew3 = Crew(agents=..., tasks=...)  # Bug 分析

# 顺序执行（默认）
crew = Crew(
    agents=[...],
    tasks=[...],
    process=Process.sequential  # 按顺序执行
)

# 并行执行（需要自己实现）
# 创建多个独立 Crew，使用 asyncio 并发执行

crew = Crew(
    agents=[...],
    tasks=[...],
    verbose=True,  # 启用日志
    memory=True    # 启用记忆（跨 Task 共享上下文）
)

#  错误
task = Task(
    description="写测试用例"
)

#  正确
task = Task(
    description="""请为登录功能设计测试用例

要求：
1. 至少 10 条测试用例
2. 覆盖以下场景：
   - 正常登录（用户名密码正确）
   - 异常登录（密码错误、用户不存在、账户锁定）
   - 边界值（用户名长度、密码长度）
3. 使用表格格式输出

输出格式：
| 编号 | 测试场景 | 输入数据 | 预期结果 |""")

#  错误
task = Task(
    description="生成测试数据"
)

#  正确
task = Task(
    description="""生成测试用户数据

示例：
{
  "username": "test_user_001",
  "email": "user001@example.com",
  "password": "Test@123456",
  "status": "active"
}

请生成 100 条类似数据。""")

#  错误 - 提示词是英文，期望中文输出
task = Task(
    description="Generate test cases for login feature",
    expected_output="测试用例列表"
)

#  正确 - 提示词和期望输出都用中文
task = Task(
    description="为登录功能设计测试用例",
    expected_output="测试用例列表"
)

#  错误 - 没有限制迭代次数
agent = Agent(
    role="测试分析师",
    goal="分析测试结果"
)

#  正确 - 限制最大迭代次数
agent = Agent(
    role="测试分析师",
    goal="分析测试结果",
    max_iter=10  # 最多迭代 10 次
)

#  错误 - 没有限流
crew = Crew(agents=[...], tasks=[...])

#  正确 - 限制请求频率
crew = Crew(
    agents=[...],
    tasks=[...],
    max_rpm=60  # 每分钟最多 60 次请求
)

#  错误 - 没有清理缓存
for i in range(100):
    result = crew.kickoff()

#  正确 - 定期清理
crew = Crew(..., cache=True)

for i in range(100):
    result = crew.kickoff()
    if i % 10 == 0:
        crew.cache.clear()  # 定期清理缓存

#  错误 - API Key 硬编码
llm = LLM(
    model="qwen-plus",
    api_key="sk-1234567890"  # 泄露风险！
)

#  正确 - 从环境变量读取
import os
llm = LLM(
    model="qwen-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY")
)

#  错误 - 没有日志
agent = Agent(..., verbose=False)
crew = Crew(..., verbose=False)

#  正确 - 生产环境也要有日志
agent = Agent(..., verbose=False)
crew = Crew(..., verbose=False)

# 使用 logging 记录关键信息
import logging
logger = logging.getLogger('crewai')
logger.info("Agent 执行开始")

#  错误 - 没有错误处理
result = crew.kickoff()

#  正确 - 添加错误处理
from tenacity import retry

@retry(max_attempts=3)
def execute_with_retry():
    return crew.kickoff()

try:
    result = execute_with_retry()
except Exception as e:
    logger.error(f"执行失败：{e}")
    raise

task = Task(
    description="""请按以下步骤分析：

步骤 1：理解需求
- 识别功能点
- 识别输入输出

步骤 2：设计测试场景
- 正常场景
- 异常场景
- 边界场景

步骤 3：编写测试用例
- 每个场景至少 3 条用例

步骤 4：评审测试用例
- 检查覆盖度
- 检查可执行性"""
)

task = Task(
    description="""请按以下模板输出：

## 测试计划

### 测试范围
...

### 测试资源
...

### 测试时间
...

## 测试用例

| 编号 | 场景 | 输入 | 预期 |
|------|------|------|------|
| 001  | ...  | ...  | ...  |"""
)

agent = Agent(
    role="资深测试专家（20 年经验）",
    backstory="""你是测试领域的权威专家，
    曾在谷歌、微软、阿里担任测试负责人，
    发表过 50+ 篇测试论文，
    出版过 3 本测试专著。
    
    你的建议总是被业界广泛采用。"""
)

# 启用缓存
crew = Crew(..., cache=True)

# 相同任务不会重复执行
result1 = crew.kickoff()  # 执行
result2 = crew.kickoff()  # 从缓存读取

#  错误 - 单个执行
for case in test_cases:
    result = execute_single(case)

#  正确 - 批量执行
results = execute_batch(test_cases)

import asyncio

async def execute_parallel():
    crew1 = Crew(...)
    crew2 = Crew(...)
    crew3 = Crew(...)
    
    # 并发执行
    results = await asyncio.gather(
        crew1.kickoff_async(),
        crew2.kickoff_async(),
        crew3.kickoff_async()
    )
    
    return results

def evaluate_agent_output(output: str, criteria: Dict) -> Dict:
    """评估 Agent 输出质量"""
    
    result = {
        "score": 0,
        "details": {}
    }
    
    # 准确性
    if "accuracy_check" in criteria:
        is_accurate = criteria["accuracy_check"](output)
        result["details"]["accuracy"] = is_accurate
        result["score"] += 1 if is_accurate else 0
    
    # 完整性
    if "completeness_check" in criteria:
        is_complete = criteria["completeness_check"](output)
        result["details"]["completeness"] = is_complete
        result["score"] += 1 if is_complete else 0
    
    # 一致性
    if "consistency_check" in criteria:
        is_consistent = criteria["consistency_check"](output)
        result["details"]["consistency"] = is_consistent
        result["score"] += 1 if is_consistent else 0
    
    return result
