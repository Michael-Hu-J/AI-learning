async def execute_crew_flow(
    task_id: str,
    requirement: str,
    base_url: str,
    enable_engineer: bool,
    enable_performance: bool,
    output_dir: str
):
    """执行 CrewAI 测试流程"""
    # 5 个 Agent 按顺序执行

# backend/app/api/execute.py 第 95-115 行

# ========== 阶段 1: 测试经理 ==========
# send_log(task_id, "agent_start", " 测试经理开始制定测试计划...")  # 异步调用示例

from app.agents.manager import run_manager_agent
# test_plan = await run_manager_agent(requirement, task_id)  # 异步调用示例

# 保存测试计划
plan_file = os.path.join(output_dir, "01_test_plan.md")
with open(plan_file, "w", encoding="utf-8") as f:
    f.write(test_plan)

# send_log(task_id, "agent_complete", " 测试经理完成测试计划", {...})  # 异步调用示例

def create_manager_agent():
    llm = LLM(
        model=settings.OPENAI_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL
    )
    
    return Agent(
        role="测试经理 (Test Manager)",
        goal="制定测试计划，分配测试任务，管理测试进度，保证测试质量",
        backstory="""你是拥有 15 年经验的测试经理，擅长：
        1. 根据需求评估测试范围和工作量
        2. 制定合理的测试计划和优先级
        3. 识别高风险区域并重点测试
        4. 协调资源，保证测试按时完成
        
        你的工作风格：
        - 结果导向，关注测试覆盖率
        - 风险推动，优先测试核心功能
        - 数据分析，用指标说话""",
        llm=llm,
        verbose=False,
        allow_delegation=False
    )

task = Task(
    description=f"""
作为测试经理，请根据以下需求文档制定测试计划：

{requirement}

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
""",
    expected_output="完整的测试计划文档，包含测试范围、优先级、类型、工作量评估和风险识别",
    agent=agent
# )

# backend/app/api/execute.py 第 103-135 行

# ========== 阶段 2: 测试设计师 ==========
# send_log(task_id, "agent_start", " 测试设计师开始设计测试用例...")  # 异步调用示例

from app.agents.designer import run_designer_agent
# test_cases = await run_designer_agent(test_plan, task_id)  # 异步调用示例

# 保存测试用例
cases_file = os.path.join(output_dir, "02_test_cases.md")
with open(cases_file, "w", encoding="utf-8") as f:
    f.write(test_cases)

# send_log(task_id, "agent_complete", " 测试设计师完成用例设计", {...})  # 异步调用示例

# test_plan 来自上一个 Agent 的输出
# test_cases = await run_designer_agent(test_plan, task_id)  # 异步调用示例

# backend/app/api/execute.py 第 138-165 行

# ========== 阶段 3: 测试工程师（可选）==========
test_results = ""
if enable_engineer:
    # send_log(task_id, "agent_start", " 测试工程师开始执行 API 测试...")  # 异步调用示例
    
    from app.agents.engineer import run_engineer_agent
    # test_results = await run_engineer_agent(
        # test_plan=test_plan,
        # test_cases=test_cases,
        # base_url=base_url,
        # client_id=task_id
    # )
    
    # 保存测试结果
    results_file = os.path.join(output_dir, "03_test_results.md")
    with open(results_file, "w", encoding="utf-8") as f:
        f.write(test_results)

# backend/app/agents/engineer.py
def create_engineer_agent():
    return Agent(
        role="测试工程师 (Test Engineer)",
        goal="执行测试用例，记录测试结果",
        backstory="你是执行力强的测试工程师，有 5 年自动化测试经验",
        tools=[APITestTool(), PerformanceTestTool()],  # 真实工具
        llm=llm,
        verbose=False,
        allow_delegation=False
    )

# backend/app/tools/api_test.py
def _run(self, url: str, method: str = "GET") -> dict:
    response = requests.request(method, url, timeout=timeout)
    return {
        "success": response.status_code == expected_status,
        "status_code": response.status_code,
        "response_time_ms": round(response_time, 2),
        "response_body": response.text[:2000]
    }

# ========== 阶段 4: 测试分析师 ==========
# send_log(task_id, "agent_start", " 测试分析师开始分析问题...")  # 异步调用示例

from app.agents.analyst import run_analyst_agent
# analysis_report = await run_analyst_agent(test_results, task_id)  # 异步调用示例

# 保存分析报告
analysis_file = os.path.join(output_dir, "04_analysis_report.md")
with open(analysis_file, "w", encoding="utf-8") as f:
    f.write(analysis_report)

# ========== 阶段 5: 测试报告专员 ==========
# send_log(task_id, "agent_start", " 测试报告专员开始生成最终报告...")  # 异步调用示例

from app.agents.reporter import run_reporter_agent
# final_report = await run_reporter_agent(
    # test_results=test_results,
    # analysis_report=analysis_report,
    # client_id=task_id
# )

# 保存最终报告
final_file = os.path.join(output_dir, "05_final_report.md")
with open(final_file, "w", encoding="utf-8") as f:
    f.write(final_report)

# backend/app/api/websocket.py

async def send_log(client_id: str, log_type: str, message: str, data: dict = None):
    """发送日志到指定客户端"""
    await manager.send_personal_message({
        "type": "log",
        "log_type": log_type,
        "message": message,
        "data": data or {}
    }, client_id)

async def execute_crew_flow(task_id, requirement, base_url):
    """执行 CrewAI 测试流程（180 行代码）"""
    
    # 1. 初始化
    task = execution_tasks[task_id]
    task["status"] = "running"
    await send_log(task_id, "info", " 测试流程启动")
    
    # 2. 阶段 1：测试经理
    await send_log(task_id, "agent_start", " 测试经理...")
    # test_plan = await run_manager_agent(requirement, task_id)  # 异步调用示例
    save_file("01_test_plan.md", test_plan)
    await send_log(task_id, "agent_complete", " 测试经理完成")
    
    # 3. 阶段 2：测试设计师
    await send_log(task_id, "agent_start", " 测试设计师...")
    # test_cases = await run_designer_agent(test_plan, task_id)  # 异步调用示例
    save_file("02_test_cases.md", test_cases)
    await send_log(task_id, "agent_complete", " 测试设计师完成")
    
    # 4. 阶段 3：测试工程师
    if enable_engineer:
        await send_log(task_id, "agent_start", " 测试工程师...")
        # test_results = await run_engineer_agent(..., base_url, ...)
        save_file("03_test_results.md", test_results)
        await send_log(task_id, "agent_complete", " 测试工程师完成")
    
    # 5. 阶段 4：测试分析师
    await send_log(task_id, "agent_start", " 测试分析师...")
    # analysis_report = await run_analyst_agent(test_results, task_id)  # 异步调用示例
    save_file("04_analysis_report.md", analysis_report)
    await send_log(task_id, "agent_complete", " 测试分析师完成")
    
    # 6. 阶段 5：测试报告专员
    await send_log(task_id, "agent_start", " 测试报告专员...")
    # final_report = await run_reporter_agent(test_results, analysis_report, ...)
    save_file("05_final_report.md", final_report)
    await send_log(task_id, "agent_complete", " 测试报告专员完成")
    
    # 7. 完成
    task["status"] = "completed"
    await send_log(task_id, "success", " 测试流程全部完成！")
