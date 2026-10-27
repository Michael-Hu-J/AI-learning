from crewai import Agent, Task, Crew, Process

# 1. 创建三个 Agent
planner = Agent(
    role="测试计划专家",
    goal="制定全面的测试计划",
    backstory="你是经验丰富的测试计划专家"
)

designer = Agent(
    role="测试用例设计师",
    goal="根据测试计划设计详细的测试用例",
    backstory="你是专业的测试用例设计师"
)

executor = Agent(
    role="测试执行工程师",
    goal="执行测试用例并记录结果",
    backstory="你是执行力强的测试工程师"
)

# 2. 创建任务（按顺序依赖）
plan_task = Task(
    description="为登录功能制定测试计划",
    expected_output="包含测试范围、资源、时间的计划文档",
    agent=planner
)

design_task = Task(
    description="根据测试计划设计测试用例",
    expected_output="包含 20 条测试用例的详细文档",
    agent=designer,
    context=[plan_task]  # 依赖 plan_task 的输出
)

execute_task = Task(
    description="执行测试用例并记录结果",
    expected_output="测试结果报告",
    agent=executor,
    context=[design_task]  # 依赖 design_task 的输出
)

# 3. 创建 Crew（顺序执行）
crew = Crew(
    agents=[planner, designer, executor],
    tasks=[plan_task, design_task, execute_task],
    process=Process.sequential,  # 顺序执行
    verbose=True
)

# 4. 执行
result = crew.kickoff()
print(result)

from crewai import Agent, Task, Crew, Process

# 1. 创建三个 Agent（相同角色，不同任务）
api_tester = Agent(
    role="API 测试工程师",
    goal="执行 API 测试用例",
    backstory="你是专业的 API 测试工程师"
)

ui_tester = Agent(
    role="UI 测试工程师",
    goal="执行 UI 测试用例",
    backstory="你是专业的 UI 测试工程师"
)

perf_tester = Agent(
    role="性能测试工程师",
    goal="执行性能测试用例",
    backstory="你是专业的性能测试工程师"
)

# 2. 创建独立任务
api_task = Task(
    description="执行 API 测试用例（10 条）",
    expected_output="API 测试结果报告",
    agent=api_tester
)

ui_task = Task(
    description="执行 UI 测试用例（10 条）",
    expected_output="UI 测试结果报告",
    agent=ui_tester
)

perf_task = Task(
    description="执行性能测试用例（5 条）",
    expected_output="性能测试结果报告",
    agent=perf_tester
)

# 3. 创建 Crew（并行执行）
crew = Crew(
    agents=[api_tester, ui_tester, perf_tester],
    tasks=[api_task, ui_task, perf_task],
    process=Process.sequential,  # 注意：CrewAI 目前主要支持 sequential
    verbose=True
)

# 4. 执行
result = crew.kickoff()
print(result)

import asyncio
from concurrent.futures import ThreadPoolExecutor

# 方式 1：使用 asyncio 并发
async def run_agents_parallel():
    tasks = []
    
    # 创建多个独立的 Crew
    crew1 = Crew(agents=[api_tester], tasks=[api_task])
    crew2 = Crew(agents=[ui_tester], tasks=[ui_task])
    crew3 = Crew(agents=[perf_tester], tasks=[perf_task])
    
    # 并发执行
    with ThreadPoolExecutor(max_workers=3) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, crew1.kickoff),
            loop.run_in_executor(executor, crew2.kickoff),
            loop.run_in_executor(executor, crew3.kickoff)
        ]
        
        results = await asyncio.gather(*tasks)
    
    return results

# 执行
results = asyncio.run(run_agents_parallel())

from crewai import Agent, Task, Crew, Process

# 1. 创建管理 Agent
manager = Agent(
    role="测试经理 (Test Manager)",
    goal="协调测试团队，保证测试任务按时完成",
    backstory="""你是经验丰富的测试经理，擅长：
    1. 任务分配和协调
    2. 进度跟踪
    3. 风险管理
    4. 质量把控
    
    你有 15 年测试管理经验，带领过 20+ 人的测试团队。""",
    allow_delegation=True  # 允许委托任务
)

# 2. 创建执行 Agent
senior_tester = Agent(
    role="高级测试工程师",
    goal="完成分配的测试任务",
    backstory="你是高级测试工程师，有 8 年经验"
)

junior_tester = Agent(
    role="测试工程师",
    goal="完成分配的测试任务",
    backstory="你是测试工程师，有 3 年经验"
)

# 3. 创建任务
main_task = Task(
    description="完成秒杀系统的全面测试",
    expected_output="完整的测试报告",
    agent=manager  # 管理 Agent 负责任务
)

# 4. 创建 Crew（层级管理）
crew = Crew(
    agents=[manager, senior_tester, junior_tester],
    tasks=[main_task],
    process=Process.sequential,
    manager_agent=manager,  # 指定管理 Agent
    verbose=True
)

# 5. 执行
result = crew.kickoff()
print(result)

# Task 2 依赖 Task 1 的输出
task1 = Task(
    description="编写测试计划",
    expected_output="测试计划文档",
    agent=planner
)

task2 = Task(
    description="根据测试计划设计测试用例",
    expected_output="测试用例文档",
    agent=designer,
    context=[task1]  # 依赖 task1
)

# Task 3 依赖 Task 1 和 Task 2
task3 = Task(
    description="综合测试计划和测试用例，生成测试执行方案",
    expected_output="测试执行方案",
    agent=executor,
    context=[task1, task2]  # 依赖多个任务
)

# 创建依赖链
# task1 -> task2 -> task3 -> task4

task1 = Task(description="需求分析", agent=analyst)
task2 = Task(description="测试计划", agent=planner, context=[task1])
task3 = Task(description="测试用例", agent=designer, context=[task2])
task4 = Task(description="测试执行", agent=executor, context=[task3])

# Task 1 的输出会自动传递给 Task 2
task1 = Task(
    description="分析需求文档",
    expected_output="需求分析报告"
)

task2 = Task(
    description="根据需求设计测试用例",
    expected_output="测试用例文档",
    context=[task1]  # task1 的输出会作为 task2 的输入
)

crew = Crew(
    agents=[agent1, agent2, agent3],
    tasks=[task1, task2, task3],
    memory=True,  # 启用记忆共享
    verbose=True
)

def task_callback(task_output):
    """任务完成回调"""
    print(f"任务完成：{task_output}")
    # 可以在这里处理中间结果，比如保存到文件

task = Task(
    description="执行测试",
    expected_output="测试结果",
    agent=executor,
    callback=task_callback  # 设置回调
)

from crewai import Agent, Task, Crew, Process

# 1. 测试经理
manager = Agent(
    role="测试经理",
    goal="协调测试团队，保证测试任务按时完成",
    backstory="你有 15 年测试管理经验",
    allow_delegation=True
)

# 2. 测试计划专家
planner = Agent(
    role="测试计划专家",
    goal="制定全面的测试计划",
    backstory="你是经验丰富的测试计划专家"
)

# 3. 测试用例设计师
designer = Agent(
    role="测试用例设计师",
    goal="设计高质量的测试用例",
    backstory="你是专业的测试用例设计师"
)

# 4. 测试执行工程师
executor = Agent(
    role="测试执行工程师",
    goal="准确执行测试用例",
    backstory="你是执行力强的测试工程师"
)

# 5. Bug 分析专家
bug_analyst = Agent(
    role="Bug 分析专家",
    goal="分析测试结果，定位根本原因",
    backstory="你是资深的 Bug 分析专家"
)

# 创建任务链
manager_task = Task(
    description="协调秒杀系统的全面测试",
    expected_output="完整的测试报告",
    agent=manager
)

plan_task = Task(
    description="制定秒杀系统测试计划",
    expected_output="测试计划文档",
    agent=planner,
    context=[manager_task]
)

design_task = Task(
    description="根据测试计划设计测试用例",
    expected_output="测试用例文档",
    agent=designer,
    context=[plan_task]
)

execute_task = Task(
    description="执行测试用例",
    expected_output="测试结果报告",
    agent=executor,
    context=[design_task]
)

analyze_task = Task(
    description="分析测试结果，定位问题",
    expected_output="Bug 分析报告",
    agent=bug_analyst,
    context=[execute_task]
)

# 创建 Crew
crew = Crew(
    agents=[manager, planner, designer, executor, bug_analyst],
    tasks=[manager_task, plan_task, design_task, execute_task, analyze_task],
    process=Process.sequential,
    verbose=True
)

# 执行
result = crew.kickoff()
print(result)

# 启用 verbose
crew = Crew(..., verbose=True)

# 查看每个 Task 的输出
result = crew.kickoff()
for i, task_output in enumerate(result.tasks_output):
    print(f"Task {i+1} 输出：{task_output.raw}")

# 在 Task 中设置中断条件
task = Task(
    description="执行测试",
    agent=executor,
    human_input=True  # 需要人工确认
)

# 添加重试机制
from tenacity import retry

@retry(max_attempts=3)
def execute_with_retry():
    return crew.kickoff()

result = execute_with_retry()
