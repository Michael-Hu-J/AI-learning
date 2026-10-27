from crewai import Agent, Task, Crew

# 1. 定义 Agent
agent = Agent(
    role="助手",
    goal="帮助用户完成任务",
    backstory="你是一个友好的 AI 助手，擅长解答各种问题。",
    verbose=True,
    allow_delegation=False
)

# 2. 定义 Task
task = Task(
    description="请用 3 句话介绍人工智能的发展历史",
    expected_output="一段关于 AI 发展历史的简介",
    agent=agent
)

# 3. 创建 Crew
crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

# 4. 执行
print(" 开始执行...\n")
result = crew.kickoff()

print("\n 执行完成！")
print(f"结果：{result}")

# 导入必要的类
from crewai import Agent, Task, Crew

# 1. 定义 Agent
# ================
agent = Agent(
    # role: Agent 的角色，决定了它的行为方式
    role="助手",
    
    # goal: Agent 的目标，它要完成什么
    goal="帮助用户完成任务",
    
    # backstory: Agent 的背景故事，让它更"真实"
    backstory="你是一个友好的 AI 助手，擅长解答各种问题。",
    
    # verbose: 是否输出详细日志
    verbose=True,
    
    # allow_delegation: 是否允许委派任务给其他 Agent
    allow_delegation=False
)

# 2. 定义 Task
# ============
task = Task(
    # description: 任务描述，告诉 Agent 要做什么
    description="请用 3 句话介绍人工智能的发展历史",
    
    # expected_output: 期望的输出格式
    expected_output="一段关于 AI 发展历史的简介",
    
    # agent: 负责执行这个任务的 Agent
    agent=agent
)

# 3. 创建 Crew
# ============
crew = Crew(
    # agents: Agent 列表，可以有多个
    agents=[agent],
    
    # tasks: Task 列表，按顺序执行
    tasks=[task],
    
    # verbose: 输出详细日志
    verbose=True
)

# 4. 执行
# =======
result = crew.kickoff()

# 版本 1：友好助手
backstory="你是一个友好的 AI 助手，擅长解答各种问题。"

# 版本 2：资深专家
backstory="你是拥有 20 年经验的 AI 专家，曾在谷歌、微软等公司工作，发表过 100+ 篇论文。"

# 版本 3：幽默风格
backstory="你是个幽默的 AI，喜欢用段子和比喻来解释复杂概念。"

from crewai import Agent

agent = Agent(
    # ========== 必填参数 ==========
    role="测试经理",                    # 角色
    goal="制定测试计划",                # 目标
    backstory="你是拥有 15 年经验的...", # 背景故事
    
    # ========== 可选参数 ==========
    llm=None,                           # LLM 配置（默认使用环境变量）
    tools=[],                           # 工具列表
    verbose=True,                       # 详细日志
    allow_delegation=False,             # 允许委派
    allow_code_execution=False,         # 允许执行代码
    max_iter=15,                        # 最大迭代次数
    max_rpm=None,                       # 每分钟最大请求数
    max_execution_time=None,            # 最大执行时间
    step_callback=None,                 # 每步回调
    function_calling_llm=None,          # 函数调用 LLM
    human_input=False,                  # 是否需要人工输入
    cache=True,                         # 启用缓存
    memory=True,                        # 启用记忆
    config=None,                        # 配置文件
    **kwargs
)

#  不好的角色定义
role="助手"  # 太模糊

#  好的角色定义
role="测试经理 (Test Manager)"  # 明确、专业
role="资深测试设计师 (Senior Test Designer)"  # 包含经验级别

# 测试 1：模糊角色
agent1 = Agent(
    role="助手",
    goal="写测试计划",
    backstory="你帮助写测试文档"
)

# 测试 2：明确角色
agent2 = Agent(
    role="测试经理 (Test Manager)",
    goal="制定测试计划，分配测试任务，管理测试进度",
    backstory="你是拥有 15 年经验的测试经理，擅长风险评估和资源分配"
)

# 输出质量：agent2 >> agent1

#  模糊的目标
goal="做好测试"  # 不可衡量

#  明确的目标
goal="制定测试计划，识别高风险区域，保证测试覆盖率≥95%"  # 可衡量

# 完整的 backstory 包含：
# 1. 经验年限
# 2. 专业领域
# 3. 工作风格
# 4. 价值观

backstory="""你是拥有 15 年经验的测试经理，擅长：
1. 根据需求评估测试范围和工作量
2. 制定合理的测试计划和优先级
3. 识别高风险区域并重点测试
4. 协调资源，保证测试按时完成

你的工作风格：
- 结果导向，关注测试覆盖率
- 风险推动，优先测试核心功能
- 数据分析，用指标说话

你曾经在多个大型电商系统负责测试管理，对秒杀系统、订单系统、支付系统
的测试有丰富经验。你深知测试的价值不在于找 bug，而在于降低业务风险。"""

# 代码中不需要配置
agent = Agent(
    role="测试经理",
    goal="制定测试计划"
    # 自动使用环境变量中的配置
)

from crewai import LLM, Agent

llm = LLM(
    model="qwen-plus",
    api_key="YOUR_DASHSCOPE_API_KEY",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

agent = Agent(
    role="测试经理",
    goal="制定测试计划",
    llm=llm  # 显式传入
)

from crewai import Task

task = Task(
    # ========== 必填参数 ==========
    description="任务描述",          # 要做什么
    expected_output="期望输出",      # 输出什么
    
    # ========== 可选参数 ==========
    agent=None,                      # 负责的 Agent
    tools=[],                        # 可用工具
    async_execution=False,           # 异步执行
    context=None,                    # 上下文（其他 Task 的输出）
    config=None,                     # 配置文件
    output_json=None,                # JSON 输出格式
    output_pydantic=None,            # Pydantic 模型
    output_file="output.md",         # 输出文件
    callback=None,                   # 完成回调
    human_input=False,               # 需要人工输入
    create_directory=False,          # 创建输出目录
    **kwargs
)

task = Task(
    description="写测试计划",  # 太模糊
    expected_output="测试计划"
)

task = Task(
    description="""
作为测试经理，请根据以下需求文档制定测试计划：

{requirement_doc}

请输出以下内容：

## 1. 测试范围
列出需要测试的功能模块，标注哪些需要测试、哪些不需要测试及原因。

## 2. 测试优先级
按 P0(核心)/P1(重要)/P2(一般)/P3(可选) 分级，说明分级理由。

## 3. 测试类型
标注每个功能需要的测试类型：功能测试/性能测试/安全测试/兼容性测试。

## 4. 工作量评估
预计需要多少人天完成测试。

## 5. 风险识别
列出哪些地方容易出问题，需要重点测试。

## 输出格式要求
使用 Markdown 格式，结构清晰，便于后续任务使用。
""",
    expected_output="完整的测试计划文档，包含测试范围、优先级、类型、工作量评估和风险识别"
)

requirement_doc = """
秒杀系统需求：
1. 用户可以在指定时间参与秒杀
2. 库存有限，先到先得
3. 每人限购 1 件
"""

task = Task(
    description=f"""
作为测试经理，请根据以下需求文档制定测试计划：

{requirement_doc}

...（后续内容）
"""
)

task = Task(
    description="制定测试计划",
    expected_output="测试计划文档",
    output_file="reports/01_test_plan.md",  # 输出文件路径
    create_directory=True  # 自动创建目录
)

from crewai import Agent, Task, Crew

agent = Agent(role="助手", goal="回答问题", backstory="...")
task = Task(description="什么是 AI？", expected_output="简介", agent=agent)

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()

from crewai import Agent, Task, Crew, Process

agent = Agent(role="作家", goal="写文章", backstory="...")

task1 = Task(description="写大纲", expected_output="大纲", agent=agent)
task2 = Task(description="写正文", expected_output="文章", agent=agent)
task3 = Task(description="写标题", expected_output="10 个标题", agent=agent)

crew = Crew(
    agents=[agent],
    tasks=[task1, task2, task3],
    process=Process.sequential  # 顺序执行
)

result = crew.kickoff()

from crewai import Agent, Task, Crew, Process

# 创建 2 个 Agent
writer = Agent(role="作家", goal="写文章", backstory="...")
editor = Agent(role="编辑", goal="审核文章", backstory="...")

# 创建 Task
write_task = Task(description="写文章", expected_output="初稿", agent=writer)
edit_task = Task(description="审核并修改", expected_output="终稿", agent=editor)

# Crew 编排
crew = Crew(
    agents=[writer, editor],
    tasks=[write_task, edit_task],
    process=Process.sequential,  # 先写后编辑
    verbose=True
)

result = crew.kickoff()

# Task 2 依赖 Task 1 的输出
task1 = Task(
    description="写大纲",
    expected_output="文章大纲",
    agent=writer
)

task2 = Task(
    description=f"""
根据以下大纲写正文：
{{task1_output}}
""",
    expected_output="文章正文",
    agent=writer,
    context=[task1]  # 依赖 task1 的输出
)

crew = Crew(agents=[writer], tasks=[task1, task2])

from crewai.tools import BaseTool
import requests

class APITestTool(BaseTool):
    name: str = "api_test"
    description: str = "发送 HTTP 请求并验证 API 响应"
    
    def _run(self, url: str, method: str = "GET") -> dict:
        response = requests.request(method, url)
        return {
            "status_code": response.status_code,
            "body": response.text[:500]
        }

# 使用 Tool
agent = Agent(
    role="测试工程师",
    goal="执行 API 测试",
    backstory="...",
    tools=[APITestTool()]  # 挂载工具
)

agent = Agent(role="测试工程师", goal="测试 API", backstory="...")
# Agent 只能"想象"测试结果，无法真实调用

agent = Agent(
    role="测试工程师",
    goal="测试 API",
    backstory="...",
    tools=[APITestTool()]
)
# Agent 可以真实调用 API，获取真实响应

crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True  # 启用详细日志
)

agent = Agent(
    role="测试经理",
    goal="制定测试计划",
    backstory="...",
    verbose=True,  # 输出思考过程
    max_iter=15    # 最大迭代次数
)

# 1. 更明确的描述
task = Task(
    description="""
请输出以下内容（必须包含这 5 个部分）：
1. 测试范围
2. 测试优先级
3. 测试类型
4. 工作量评估
5. 风险识别
""",
    expected_output="包含 5 个部分的测试计划"
)

# 2. 提供示例
task = Task(
    description="""
参考以下格式：

## 1. 测试范围
| 功能模块 | 是否测试 | 原因 |
|----------|----------|------|
| 登录     | 是       | 核心功能 |

请按照上述格式输出...
"""
)

# 3. 增加约束
task = Task(
    description="...",
    expected_output="测试计划（不少于 1000 字）"
)

agent = Agent(
    role="测试经理",
    goal="制定测试计划",
    max_execution_time=300,  # 最大执行时间（秒）
    max_rpm=10               # 每分钟最大请求数
)

# 在文件开头添加
# -*- coding: utf-8 -*-

# 或者在输出时指定编码
with open("output.md", "w", encoding="utf-8") as f:
    f.write(result)

task = Task(
    description="...",
    expected_output="详细的测试计划（不少于 2000 字）"  # 明确字数要求
)

agent = Agent(
    ...,
    max_iter=20  # 增加迭代次数
)

task = Task(
    description="写测试计划",
    expected_output="测试计划文档",
    output_file="reports/test_plan.md",  # 输出文件
    create_directory=True  # 自动创建目录
)

# 1. 启用详细日志
crew = Crew(..., verbose=True)

# 2. 捕获异常
try:
    result = crew.kickoff()
except Exception as e:
    print(f"错误：{e}")
    print(f"错误类型：{type(e)}")

# 3. 检查 Agent 配置
print(agent.role)
print(agent.goal)
print(task.description)

# 第 2 篇会详细讲解这段代码
manager = Agent(
    role="测试经理 (Test Manager)",
    goal="制定测试计划，分配测试任务，管理测试进度",
    backstory="""你是拥有 15 年经验的测试经理..."""
)
