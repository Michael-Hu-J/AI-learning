from crewai import Agent

def create_manager_agent(llm):
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
        - 数据分析，用指标说话
        - 注重效率，合理分配资源
        
        你曾经在多个大型电商系统负责测试管理，对秒杀系统、订单系统、支付系统
        的测试有丰富经验。你深知测试的价值不在于找 bug，而在于降低业务风险。""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        human_input=False
    )

from crewai import Agent

def create_designer_agent(llm):
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
        你特别擅长发现容易被忽略的边界场景，你的测试用例曾经帮助团队
        在生产问题发生前发现多个严重 bug。
        
        你相信好的测试用例设计是测试成功的关键。""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        human_input=False
    )

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
        - 及时报告阻塞性问题
        
        你有 5 年自动化测试经验，熟悉 API 测试、性能测试、UI 测试。
        你使用过多种测试工具，包括 Postman、JMeter、Selenium 等。
        
        你相信细节决定成败，每一个测试结果都可能揭示重要的问题。""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        human_input=False,
        tools=[APITestTool(), PerformanceTestTool()]
    )

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
        - 给出具体修复步骤
        
        你有 8 年缺陷分析经验，曾经分析过上千个生产问题。
        你擅长从表面现象找到深层原因，你的分析报告帮助开发团队
        迅速定位并修复了无数 bug。
        
        你相信每个问题背后都有原因，找到根因才能彻底解决。""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        human_input=False
    )

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
        - 适合向管理层汇报
        
        你有 6 年测试报告撰写经验，曾经为多个大型项目编写测试报告。
        你的报告以清晰、准确、可操作著称，深受管理层信任。
        
        你相信好的报告能够帮助团队做出正确的决策。""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        human_input=False
    )

from crewai.tools import BaseTool
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime


class APITestTool(BaseTool):
    """API 测试工具类"""
    
    name: str = "api_test"
    description: str = """发送 HTTP 请求并验证 API 响应，用于测试后端接口。
    参数包括：url(接口地址), method(HTTP 方法), headers(请求头), body(请求体), 
    expected_status(期望状态码), timeout(超时时间)"""
    
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
        start_time = datetime.now()
        
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body,
                timeout=timeout
            )
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result = {
                "success": response.status_code == expected_status,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response_time_ms": round(response_time, 2),
                "response_body": response.text[:2000],  # 截断避免过长
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat()
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
                "timeout_seconds": timeout,
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat()
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"连接错误：{str(e)}",
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"未知错误：{str(e)}",
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat()
            }

from crewai.tools import BaseTool
import requests
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
from datetime import datetime
import threading


class PerformanceTestTool(BaseTool):
    """性能测试工具类"""
    
    name: str = "performance_test"
    description: str = """执行接口性能测试，支持并发请求和压力测试。
    参数包括：url(接口地址), method(HTTP 方法), concurrent_users(并发用户数), 
    iterations(总请求次数), body(请求体)"""
    
    def _run(
        self,
        url: str,
        method: str = "GET",
        concurrent_users: int = 10,
        iterations: int = 100,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """执行性能测试"""
        start_time = datetime.now()
        
        response_times: List[float] = []
        success_count = 0
        error_count = 0
        status_codes: Dict[int, int] = {}
        lock = threading.Lock()
        
        def send_request():
            nonlocal success_count, error_count
            try:
                req_start = time.time()
                response = requests.request(
                    method=method.upper(), 
                    url=url, 
                    json=body,
                    headers=headers or {},
                    timeout=60
                )
                req_end = time.time()
                response_time = (req_end - req_start) * 1000
                
                with lock:
                    response_times.append(response_time)
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1
                    
                    status_codes[response.status_code] = status_codes.get(response.status_code, 0) + 1
                    
            except Exception as e:
                with lock:
                    error_count += 1
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(send_request) for _ in range(iterations)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    with lock:
                        error_count += 1
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # 计算统计指标
        if response_times:
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            
            result = {
                "test_summary": "性能测试完成",
                "total_requests": iterations,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": f"{success_count/iterations*100:.2f}%",
                "total_time_seconds": round(total_time, 2),
                "avg_response_time_ms": round(statistics.mean(response_times), 2),
                "min_response_time_ms": round(min(response_times), 2),
                "max_response_time_ms": round(max(response_times), 2),
                "median_response_time_ms": round(statistics.median(response_times), 2),
                "p95_response_time_ms": round(sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1], 2),
                "p99_response_time_ms": round(sorted_times[p99_index] if p99_index < len(sorted_times) else sorted_times[-1], 2),
                "qps": round(iterations / total_time if total_time > 0 else 0, 2),
                "concurrent_users": concurrent_users,
                "status_code_distribution": status_codes,
            }
        else:
            result = {
                "test_summary": "性能测试失败 - 所有请求失败",
                "total_requests": iterations,
                "success_count": 0,
                "error_count": error_count,
                "error": "所有请求失败，请检查接口可用性",
            }
        
        return result

# tasks/planning.py
def create_planning_task(manager_agent, requirement_doc):
    return Task(
        description=f"""
作为测试经理，请根据以下需求文档制定测试计划：
{requirement_doc}

请输出以下内容：
## 1. 测试范围
## 2. 测试优先级
## 3. 测试类型
## 4. 工作量评估
## 5. 风险识别
""",
        expected_output="完整的测试计划文档",
        agent=manager_agent,
        output_file="reports/01_test_plan.md"
    )

# tasks/design.py
def create_design_task(designer_agent, test_plan):
    return Task(
        description=f"""
作为测试设计师，请根据以下测试计划设计测试用例：
{test_plan}

要求：
1. 每个 P0 功能至少设计 5 个测试用例
2. 覆盖正常流程、边界条件、异常场景
3. 输出 Markdown 表格格式
""",
        expected_output="结构化的测试用例集",
        agent=designer_agent,
        output_file="reports/02_test_cases.md"
    )

# tasks/execution.py
def create_execution_task(engineer_agent, test_cases, base_url):
    return Task(
        description=f"""
作为测试工程师，请执行以下测试用例：
{test_cases}

基础 URL: {base_url}

执行要求：
1. 按优先级顺序执行 (P0 → P1 → P2)
2. 记录每个用例的实际结果
3. 标记通过/失败状态
4. 使用 APITestTool 和 PerformanceTestTool
""",
        expected_output="测试执行结果表格",
        agent=engineer_agent,
        output_file="reports/03_test_results.md"
    )

# tasks/analysis.py
def create_analysis_task(analyst_agent, test_results):
    return Task(
        description=f"""
作为测试分析师，请分析以下测试结果：
{test_results}

分析要求：
1. 统计通过率、失败率
2. 对每个失败用例进行根因分析（5 Why）
3. 评估问题严重程度 (P0-P3)
4. 给出修复建议和优先级
""",
        expected_output="详细的问题分析报告",
        agent=analyst_agent,
        output_file="reports/04_analysis_report.md"
    )

# tasks/reporting.py
def create_reporting_task(reporter_agent, test_results, analysis_report):
    return Task(
        description=f"""
作为测试报告专员，请汇总以下信息生成最终测试报告：

测试结果:
{test_results}

分析报告:
{analysis_report}

报告要求：
1. 执行摘要（给管理层看）
2. 测试范围和结果统计
3. 主要问题和风险
4. 质量评估和发布建议
""",
        expected_output="专业的测试报告文档",
        agent=reporter_agent,
        output_file="reports/05_final_report.md"
    )

from crewai import Crew, Process

def create_test_crew(llm, requirement_doc, base_url):
    # 创建 Agent
    manager = create_manager_agent(llm)
    designer = create_designer_agent(llm)
    engineer = create_engineer_agent(llm)
    analyst = create_analyst_agent(llm)
    reporter = create_reporter_agent(llm)
    
    # 创建 Task
    planning_task = create_planning_task(manager, requirement_doc)
    design_task = create_design_task(designer, "{test_plan}")
    execution_task = create_execution_task(engineer, "{test_cases}", base_url)
    analysis_task = create_analysis_task(analyst, "{test_results}")
    reporting_task = create_reporting_task(reporter, "{test_results}", "{analysis_report}")
    
    # 创建 Crew
    crew = Crew(
        agents=[manager, designer, engineer, analyst, reporter],
        tasks=[planning_task, design_task, execution_task, analysis_task, reporting_task],
        process=Process.sequential,  # 顺序执行
        verbose=True,
        memory=True,  # 启用记忆
        cache=True    # 启用缓存
    )
    
    return crew

# 查询秒杀活动
GET http://your-server:port/api/seckill/activities
响应：HTTP 200
[
  {
    "id": 1,
    "name": "双 11 秒杀大促",
    "start_time": "2026-04-10T21:15:28",
    "end_time": "2026-04-11T21:15:28",
    "status": "ACTIVE"
  }
]

# 参与秒杀（模拟）
POST http://your-server:port/api/seckill/1/buy
请求体：{"user_id": "test_user_001"}
响应：HTTP 200
{"order_id": "ORD-20231205-001", "status": "success"}

# 查询订单
GET http://your-server:port/api/orders/ORD-20231205-001
响应：HTTP 200
{"order_id": "ORD-20231205-001", "status": "PENDING_PAYMENT"}

# 没有 backstory
Agent(role="测试经理", goal="制定测试计划")
# 输出：通用的测试计划，缺乏深度

# 有 backstory
Agent(
    role="测试经理",
    goal="制定测试计划",
    backstory="15 年经验，风险推动，数据分析..."
)
# 输出：包含风险识别、工作量评估、应对措施的专业计划

#  好的做法
class APITestTool(BaseTool):
    name: str = "api_test"  # 类型注解
    description: str = "..."  # 完整描述
    
    def _run(self, url: str, method: str = "GET") -> Dict[str, Any]:
        """完整的 docstring"""
        try:
            pass  # 业务逻辑
        except Exception as e:
            return {"success": False, "error": str(e)}

#  不好的做法
class APITestTool(BaseTool):
    name = "api_test"  # 缺少类型注解
    description = "..."  # 描述不完整
    
    def _run(self, url, method="GET"):  # 缺少类型注解
        # 没有 docstring
        response = requests.get(url)  # 没有异常处理
        return response.json()
