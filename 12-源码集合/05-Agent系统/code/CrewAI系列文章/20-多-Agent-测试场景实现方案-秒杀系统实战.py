# tools/api_test_tool.py
from crewai.tools import BaseTool
import requests
import json
from typing import Optional, Dict, Any

class APITestTool(BaseTool):
    name = "api_test"
    description = "发送 HTTP 请求并验证 API 响应，用于测试后端接口"
    
    def _run(
        self, 
        url: str, 
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        执行 API 测试
        
        Args:
            url: 接口 URL
            method: HTTP 方法 (GET/POST/PUT/DELETE)
            headers: 请求头
            body: 请求体
            expected_status: 期望的状态码
            timeout: 超时时间 (秒)
            
        Returns:
            测试结果字典
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                json=body,
                timeout=timeout
            )
            
            result = {
                "success": response.status_code == expected_status,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "response_body": response.text[:1000],  # 截断避免过长
                "url": url,
                "method": method
            }
            
            # 尝试解析 JSON
            try:
                result["response_json"] = response.json()
            except:
                result["response_json"] = None
                
            return result
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "请求超时",
                "timeout_seconds": timeout
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }

# tools/performance_test_tool.py
from crewai.tools import BaseTool
import requests
import time
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

class PerformanceTestTool(BaseTool):
    name = "performance_test"
    description = "执行接口性能测试，支持并发请求和压力测试"
    
    def _run(
        self,
        url: str,
        method: str = "GET",
        concurrent_users: int = 10,
        iterations: int = 100,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行性能测试
        
        Args:
            url: 接口 URL
            method: HTTP 方法
            concurrent_users: 并发用户数
            iterations: 总请求次数
            body: 请求体
            
        Returns:
            性能测试结果
        """
        response_times: List[float] = []
        success_count = 0
        error_count = 0
        
        def send_request():
            try:
                start = time.time()
                response = requests.request(method, url, json=body, timeout=30)
                end = time.time()
                response_times.append((end - start) * 1000)
                if response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1
            except:
                error_count += 1
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(send_request) for _ in range(iterations)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    error_count += 1
        
        # 计算统计指标
        if response_times:
            result = {
                "total_requests": iterations,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": f"{success_count/iterations*100:.2f}%",
                "avg_response_time_ms": round(statistics.mean(response_times), 2),
                "min_response_time_ms": round(min(response_times), 2),
                "max_response_time_ms": round(max(response_times), 2),
                "p95_response_time_ms": round(statistics.quantiles(response_times, n=20)[18], 2),
                "p99_response_time_ms": round(statistics.quantiles(response_times, n=100)[98], 2),
                "qps": round(iterations / (max(response_times)/1000), 2)
            }
        else:
            result = {
                "total_requests": iterations,
                "success_count": 0,
                "error_count": error_count,
                "error": "所有请求失败"
            }
        
        return result

# agents/manager.py
from crewai import Agent

def create_manager_agent(llm):
    return Agent(
        role="测试经理 (Test Manager)",
        goal="制定测试计划，分配测试任务，管理测试进度",
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
        verbose=True,
        allow_delegation=False
    )

# agents/designer.py
from crewai import Agent

def create_designer_agent(llm):
    return Agent(
        role="测试设计师 (Test Designer)",
        goal="根据需求和接口定义，设计全面的测试用例",
        backstory="""你是资深测试设计师，擅长：
        1. 等价类划分和边界值分析
        2. 状态迁移图和判定表
        3. 场景法和错误推测法
        4. 覆盖正常流程、边界条件、异常场景
        
        你的设计原则：
        - 每个功能点至少 3 个测试用例（正常/边界/异常）
        - 优先覆盖核心业务流程
        - 考虑并发和竞态条件
        - 输出结构化的测试用例表格""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

# agents/engineer.py
from crewai import Agent
from tools.api_test_tool import APITestTool
from tools.performance_test_tool import PerformanceTestTool

def create_engineer_agent(llm):
    return Agent(
        role="测试工程师 (Test Engineer)",
        goal="执行测试用例，记录测试结果，报告发现的问题",
        backstory="""你是执行力强的测试工程师，擅长：
        1. 准确执行测试用例
        2. 详细记录测试步骤和结果
        3. 发现并复现问题
        4. 使用各种测试工具
        
        你的工作习惯：
        - 严格按照测试用例执行
        - 详细记录每一步操作
        - 遇到问题先尝试复现
        - 及时报告阻塞性问题""",
        llm=llm,
        verbose=True,
        tools=[APITestTool(), PerformanceTestTool()],
        allow_delegation=False
    )

# agents/analyst.py
from crewai import Agent

def create_analyst_agent(llm):
    return Agent(
        role="测试分析师 (Test Analyst)",
        goal="分析测试结果，定位问题根因，给出修复建议",
        backstory="""你是问题分析专家，擅长：
        1. 从日志和错误信息中定位问题
        2. 区分是代码 bug、配置问题还是环境问题
        3. 评估问题的严重程度和影响范围
        4. 给出可操作的修复建议
        
        你的分析方法：
        - 5 Why 分析法找到根因
        - 鱼骨图分析影响因素
        - 优先级排序 (P0-P3)
        - 给出具体修复步骤""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

# agents/reporter.py
from crewai import Agent

def create_reporter_agent(llm):
    return Agent(
        role="测试报告专员 (Report Specialist)",
        goal="汇总测试结果，生成专业的测试报告",
        backstory="""你是专业的测试报告撰写专家，擅长：
        1. 整理和汇总测试数据
        2. 生成清晰的测试报告
        3. 用图表展示测试结果
        4. 给出质量评估和改进建议
        
        你的报告特点：
        - 结构清晰，层次分明
        - 数据准确，图表直观
        - 结论明确，建议可行
        - 适合向管理层汇报""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

# tasks/planning.py
from crewai import Task

def create_planning_task(manager_agent, requirement_doc: str):
    return Task(
        description=f"""
作为测试经理，请根据以下需求文档制定测试计划：

{requirement_doc}

请输出：
1. 测试范围：哪些功能需要测试，哪些不需要
2. 测试优先级：P0(核心)/P1(重要)/P2(一般)/P3(可选)
3. 测试类型：功能测试/性能测试/安全测试/兼容性测试
4. 工作量评估：预计需要多少人天
5. 风险识别：哪些地方容易出问题

输出格式：Markdown 表格
""",
        expected_output="完整的测试计划，包含测试范围、优先级、类型、工作量评估和风险识别",
        agent=manager_agent
    )

# tasks/design.py
def create_design_task(designer_agent, test_plan: str):
    return Task(
        description=f"""
作为测试设计师，请根据测试计划设计测试用例：

{test_plan}

要求：
1. 每个 P0/P1功能至少设计 5 个测试用例
2. 覆盖正常流程、边界条件、异常场景
3. 包含前置条件、测试步骤、预期结果
4. 标注自动化可行性 (可自动化/需手工)

输出格式：Markdown 表格，包含列：
| 用例 ID | 功能模块 | 优先级 | 测试类型 | 前置条件 | 测试步骤 | 预期结果 | 自动化 |
""",
        expected_output="结构化的测试用例集，用 Markdown 表格呈现",
        agent=designer_agent
    )

# tasks/execution.py
def create_execution_task(engineer_agent, test_cases: str, base_url: str):
    return Task(
        description=f"""
作为测试工程师，请执行以下测试用例：

{test_cases}

基础 URL: {base_url}

执行要求：
1. 按优先级顺序执行 (P0 → P1 → P2)
2. 记录每个用例的实际结果
3. 标记通过/失败状态
4. 失败的用例记录详细错误信息
5. 记录接口响应时间

使用提供的工具执行 API 测试和性能测试。

输出格式：Markdown 表格
| 用例 ID | 状态 | 实际结果 | 响应时间 | 错误信息 |
""",
        expected_output="测试执行结果，包含每个用例的状态和详细信息",
        agent=engineer_agent
    )

# tasks/analysis.py
def create_analysis_task(analyst_agent, test_results: str):
    return Task(
        description=f"""
作为测试分析师，请分析以下测试结果：

{test_results}

分析要求：
1. 统计通过率、失败率
2. 对每个失败用例进行根因分析
3. 评估问题严重程度 (P0-P3)
4. 给出修复建议和优先级
5. 识别需要回归测试的范围

输出格式：
## 测试概览
- 总用例数：X
- 通过：X (X%)
- 失败：X (X%)

## 问题分析
### 问题 1: [问题标题]
- 严重程度：P0/P1/P2/P3
- 根因分析：...
- 修复建议：...
- 影响范围：...
""",
        expected_output="详细的问题分析报告，包含根因分析和修复建议",
        agent=analyst_agent
    )

# tasks/reporting.py
def create_reporting_task(reporter_agent, test_results: str, analysis_report: str):
    return Task(
        description=f"""
作为测试报告专员，请汇总以下信息生成最终测试报告：

测试结果:
{test_results}

分析报告:
{analysis_report}

报告要求：
1. 执行摘要：给管理层看的简短总结
2. 测试范围：测了什么，没测什么
3. 测试结果：通过率、失败率统计
4. 问题分析：主要问题和风险
5. 质量评估：是否可以发布
6. 后续建议：下一步行动

输出格式：完整的测试报告文档
""",
        expected_output="专业的测试报告文档",
        agent=reporter_agent
    )

# crew.py
from crewai import Crew, Process
from agents.manager import create_manager_agent
from agents.designer import create_designer_agent
from agents.engineer import create_engineer_agent
from agents.analyst import create_analyst_agent
from agents.reporter import create_reporter_agent
from tasks.planning import create_planning_task
from tasks.design import create_design_task
from tasks.execution import create_execution_task
from tasks.analysis import create_analysis_task
from tasks.reporting import create_reporting_task

def create_test_crew(llm, requirement_doc: str, base_url: str):
    """创建测试 Crew"""
    
    # 创建 Agent
    manager = create_manager_agent(llm)
    designer = create_designer_agent(llm)
    engineer = create_engineer_agent(llm)
    analyst = create_analyst_agent(llm)
    reporter = create_reporter_agent(llm)
    
    # 创建 Task
    planning_task = create_planning_task(manager, requirement_doc)
    design_task = create_design_task(designer, planning_task.output)
    execution_task = create_execution_task(engineer, design_task.output, base_url)
    analysis_task = create_analysis_task(analyst, execution_task.output)
    reporting_task = create_reporting_task(reporter, execution_task.output, analysis_task.output)
    
    # 创建 Crew
    crew = Crew(
        agents=[manager, designer, engineer, analyst, reporter],
        tasks=[planning_task, design_task, execution_task, analysis_task, reporting_task],
        process=Process.sequential,  # 顺序执行
        verbose=True
    )
    
    return crew

# main.py
import os
from crew import create_test_crew
from crewai import LLM

# 配置 LLM (阿里巴巴 DashScope)
llm = LLM(
    model="qwen/qwen-2.5-72b-instruct",  # 或你使用的模型
    api_key=os.getenv("ALIBABA_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 需求文档示例
requirement_doc = """
秒杀系统需求：
1. 用户可以在指定时间参与秒杀
2. 库存有限，先到先得
3. 每人限购 1 件
4. 秒杀成功后生成订单
5. 支持订单查询和取消
"""

# 创建并执行 Crew
crew = create_test_crew(llm, requirement_doc, "http://your-server:port")
result = crew.kickoff()

print("=== 测试报告 ===")
print(result)

# 针对秒杀核心接口的多 Agent 测试流程

# 1. Manager 分析测试范围
测试范围 = """
P0 核心功能:
- 秒杀开始时间校验
- 库存扣减逻辑
- 订单创建

P1 重要功能:
- 限购规则校验
- 秒杀结束处理
- 库存回滚

P2 边界场景:
- 并发秒杀
- 库存为 0 时下单
- 重复提交
"""

# 2. Designer 设计测试用例
测试用例 = """
| ID | 场景 | 步骤 | 预期 |
|----|------|------|------|
| TC001 | 正常秒杀 | 在开始时间后请求秒杀接口 | 返回成功，库存 -1 |
| TC002 | 提前秒杀 | 在开始时间前请求 | 返回"活动未开始" |
| TC003 | 库存耗尽 | 最后 1 件时请求 | 返回成功 |
| TC004 | 超卖测试 | 库存为 0 时请求 | 返回"已售罄" |
| TC005 | 重复提交 | 同一用户重复请求 | 第二次返回"已购买" |
"""

# 3. Engineer 执行测试
# 使用 APITestTool 执行每个用例

# 4. Analyst 分析结果
# 识别超卖、并发等问题

# 5. Reporter 生成报告

# 性能测试场景配置
性能测试配置 = {
    "场景 1_秒杀开始瞬间": {
        "url": "http://your-server:port/api/seckill/buy",
        "concurrent_users": 1000,  # 1000 人同时抢
        "iterations": 10000,        # 总共 10000 次请求
        "expected_qps": "> 5000"
    },
    "场景 2_库存查询": {
        "url": "http://your-server:port/api/seckill/stock",
        "concurrent_users": 500,
        "iterations": 5000,
        "expected_response_time": "< 100ms"
    },
    "场景 3_订单创建": {
        "url": "http://your-server:port/api/order/create",
        "concurrent_users": 200,
        "iterations": 2000,
        "expected_success_rate": "> 99.9%"
    }
}

# 代码变更后的回归测试流程

# 1. Manager 评估影响范围
影响分析 = """
本次变更：修改了库存扣减逻辑
影响模块:
- 秒杀购买接口 (P0)
- 订单创建接口 (P0)
- 库存查询接口 (P1)
- 退款接口 (P2)
"""

# 2. Designer 选择回归用例
回归用例集 = """
从历史用例库中选择：
- 所有 P0 用例 (100% 执行)
- 相关 P1 用例 (80% 执行)
- 抽样 P2 用例 (30% 执行)
"""

# 3. Engineer 执行回归
# 4. Analyst 对比历史结果
# 5. Reporter 生成回归报告

# 1. 增加输出格式约束
Task(
    description="...",
    expected_output="请用以下 JSON 格式输出：{...}",
    output_json=OutputModel  # Pydantic 模型
)

# 2. 使用 Guardrail 验证输出
from crewai.tasks.llm_guardrail import LLMGuardrail

Task(
    description="...",
    guardrails=[
        LLMGuardrail(
            description="输出必须包含测试用例 ID、步骤、预期结果",
            llm=llm
        )
    ]
)

# 3. 添加重试机制
Task(
    description="...",
    max_retry=3  # 失败后重试 3 次
)

# 4. 使用 Knowledge 增强
from crewai.knowledge.knowledge import Knowledge

agent.knowledge = Knowledge(
    sources=[test_case_source, defect_db_source]
)
