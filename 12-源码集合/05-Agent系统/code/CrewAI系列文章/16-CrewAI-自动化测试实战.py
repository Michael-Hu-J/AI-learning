# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# LLM 配置
LLM_CONFIG = {
    "model": "qwen-plus",
    "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}

# 被测系统配置
TARGET_CONFIG = {
    "base_url": os.getenv("TEST_BASE_URL", "http://http://localhost:8080"),
    "timeout": 30,
    "concurrent_users": 100,
}

# 测试配置
TEST_CONFIG = {
    "max_test_cases": 150,
    "priority_levels": ["P0", "P1", "P2"],
    "test_types": ["功能测试", "性能测试", "安全测试"],
}

# tools.py
from crewai.tools import BaseTool
import requests
from typing import Optional, Dict, Any
from datetime import datetime
import json
import random
import string


class APITestTool(BaseTool):
    """API 测试工具：发送 HTTP 请求并验证响应"""

    name: str = "api_test"
    description: str = (
        "发送 HTTP 请求并验证 API 响应。"
        "参数：url（请求地址）、method（请求方法）、"
        "headers（请求头）、body（请求体）、"
        "expected_status（期望状态码）、timeout（超时时间）"
    )

    def _run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        start_time = datetime.now()

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body,
                timeout=timeout,
            )

            end_time = datetime.now()
            response_time_ms = round(
                (end_time - start_time).total_seconds() * 1000, 2
            )

            return {
                "success": response.status_code == expected_status,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response_time_ms": response_time_ms,
                "response_body": response.text[:2000],
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat(),
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "请求超时",
                "timeout_seconds": timeout,
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"连接失败: {str(e)}",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
            }


class TestDataGeneratorTool(BaseTool):
    """测试数据生成工具：生成符合业务规则的测试数据"""

    name: str = "test_data_generator"
    description: str = (
        "生成测试数据。"
        "参数：data_type（数据类型）、count（数量）、"
        "rules（生成规则）"
    )

    def _generate_user(self) -> Dict[str, str]:
        user_id = "".join(random.choices(string.digits, k=10))
        return {
            "user_id": user_id,
            "username": f"user_{user_id}",
            "phone": f"1{random.randint(30, 99)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}",
            "token": f"token_{''.join(random.choices(string.ascii_lowercase, k=16))}",
        }

    def _generate_product(self) -> Dict[str, Any]:
        product_id = "".join(random.choices(string.digits, k=8))
        return {
            "product_id": product_id,
            "name": f"秒杀商品_{product_id}",
            "price": round(random.uniform(1, 9999), 2),
            "original_price": round(random.uniform(100, 19999), 2),
            "stock": random.randint(1, 1000),
            "limit_per_user": 1,
        }

    def _generate_order(self, user: Dict, product: Dict) -> Dict[str, Any]:
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
        return {
            "order_id": order_id,
            "user_id": user["user_id"],
            "product_id": product["product_id"],
            "quantity": 1,
            "total_price": product["price"],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

    def _run(
        self,
        data_type: str = "seckill_scenario",
        count: int = 10,
        rules: Optional[str] = None,
    ) -> str:
        if data_type == "seckill_scenario":
            users = [self._generate_user() for _ in range(count)]
            products = [self._generate_product() for _ in range(count)]
            scenarios = []

            for i in range(count):
                scenario = {
                    "scenario_id": f"SCENARIO_{i + 1:03d}",
                    "user": users[i],
                    "product": products[i],
                    "order": self._generate_order(users[i], products[i]),
                }
                scenarios.append(scenario)

            return json.dumps(scenarios, ensure_ascii=False, indent=2)

        elif data_type == "users":
            users = [self._generate_user() for _ in range(count)]
            return json.dumps(users, ensure_ascii=False, indent=2)

        elif data_type == "products":
            products = [self._generate_product() for _ in range(count)]
            return json.dumps(products, ensure_ascii=False, indent=2)

        else:
            return json.dumps({"error": f"不支持的数据类型: {data_type}"})


class ResultValidatorTool(BaseTool):
    """结果验证工具：验证测试结果的合理性和一致性"""

    name: str = "result_validator"
    description: str = (
        "验证测试结果。"
        "参数：test_results（测试结果列表）、validation_rules（验证规则）"
    )

    def _run(
        self,
        test_results: str,
        validation_rules: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            results = json.loads(test_results) if isinstance(test_results, str) else test_results
        except (json.JSONDecodeError, TypeError):
            return {"valid": False, "error": "测试结果格式无效"}

        total = len(results)
        passed = sum(1 for r in results if r.get("success"))
        failed = sum(1 for r in results if not r.get("success"))
        blocked = sum(1 for r in results if r.get("blocked"))

        response_times = [
            r.get("response_time_ms", 0)
            for r in results
            if r.get("response_time_ms") is not None
        ]
        avg_response_time = (
            round(sum(response_times) / len(response_times), 2)
            if response_times
            else 0
        )
        max_response_time = max(response_times) if response_times else 0

        issues = []
        for r in results:
            if r.get("response_time_ms", 0) > 5000:
                issues.append(
                    f"响应时间过长: {r.get('url', 'unknown')} "
                    f"耗时 {r['response_time_ms']}ms"
                )
            if r.get("status_code") == 500:
                issues.append(
                    f"服务端错误: {r.get('url', 'unknown')} "
                    f"返回 500"
                )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "avg_response_time_ms": avg_response_time,
            "max_response_time_ms": max_response_time,
            "issues": issues,
            "overall_status": "通过" if failed == 0 and blocked == 0 else "不通过",
        }

# agents.py
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from tools import APITestTool, TestDataGeneratorTool, ResultValidatorTool
from config import LLM_CONFIG


def _create_llm():
    return LLM(
        model=LLM_CONFIG["model"],
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
    )


def create_test_planner_agent() -> Agent:
    """测试计划 Agent：分析需求，制定测试策略"""
    return Agent(
        role="测试计划经理",
        goal="分析需求文档，制定测试范围和优先级，输出测试计划",
        backstory="""你是拥有 15 年经验的测试经理，擅长电商系统的测试规划。
你曾经负责过多个大型电商项目的测试管理，包括秒杀系统、订单系统、支付系统。
你的工作风格是风险推动，优先保障核心业务流程的正确性。
你善于识别高风险区域，并合理分配测试资源。
你相信测试计划的价值在于降低业务风险，而不是追求形式上的完整。""",
        llm=_create_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_test_designer_agent() -> Agent:
    """用例设计 Agent：根据测试计划生成详细测试用例"""
    return Agent(
        role="测试用例设计师",
        goal="根据测试计划生成覆盖全面的测试用例，包含正常场景和异常场景",
        backstory="""你是拥有 10 年经验的测试设计师，擅长编写高质量的测试用例。
你精通等价类划分、边界值分析、错误推测等多种用例设计方法。
你编写的测试用例结构清晰、步骤明确、预期结果准确。
你特别关注边界条件和异常场景，因为真实环境中的问题往往出现在这些地方。
你认为好的测试用例应该让任何人拿到都能执行，不需要额外的解释。""",
        llm=_create_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_test_executor_agent() -> Agent:
    """测试执行 Agent：调用工具执行测试，记录结果"""
    return Agent(
        role="测试执行工程师",
        goal="严格按照测试用例执行测试，准确记录每一步的执行结果",
        backstory="""你是执行力强的测试工程师，擅长自动化测试执行。
你有 5 年 API 测试和性能测试经验，熟悉各种测试工具的使用。
你的工作习惯是严格按照用例执行，不跳过任何步骤，不遗漏任何验证点。
遇到问题时，你会先尝试复现，然后详细记录复现步骤和错误信息。
你相信测试执行的价值在于发现真实问题，而不是走过场。""",
        llm=_create_llm(),
        verbose=True,
        allow_delegation=False,
        tools=[APITestTool(), TestDataGeneratorTool()],
    )


def create_bug_analyst_agent() -> Agent:
    """Bug 分析 Agent：分析失败用例，生成 Bug 报告"""
    return Agent(
        role="Bug 分析专家",
        goal="分析测试失败的原因，生成结构化的 Bug 报告和改进建议",
        backstory="""你是拥有 12 年经验的测试分析专家，擅长根因分析和问题定位。
你曾经在一个电商团队工作，通过系统化的 Bug 分析帮助团队将线上故障率降低了 60%。
你的分析方法是：先分类，再定位，最后提出改进建议。
你善于从失败的测试结果中提炼出共性问题，而不是孤立地看待每个 Bug。
你认为 Bug 报告的价值不仅在于记录问题，更在于帮助团队改进流程。""",
        llm=_create_llm(),
        verbose=True,
        allow_delegation=False,
        tools=[ResultValidatorTool()],
    )

# main.py
from crewai import Task, Crew, Process
from agents import (
    create_test_planner_agent,
    create_test_designer_agent,
    create_test_executor_agent,
    create_bug_analyst_agent,
)
from config import TARGET_CONFIG
import os


def run_seckill_test_flow(requirement_doc: str, base_url: str) -> dict:
    """
    运行完整的秒杀系统测试流程

    Args:
        requirement_doc: 需求文档内容
        base_url: 被测系统地址

    Returns:
        包含各阶段输出的字典
    """
    # 创建四个 Agent
    planner = create_test_planner_agent()
    designer = create_test_designer_agent()
    executor = create_test_executor_agent()
    analyst = create_bug_analyst_agent()

    # 任务 1：生成测试计划
    plan_task = Task(
        description=f"""
请根据以下需求文档制定测试计划：

{requirement_doc}

请输出以下内容：

## 1. 测试范围
列出需要测试的功能模块，标注哪些需要测试、哪些不需要测试及原因。

## 2. 测试优先级
按 P0（核心）/P1（重要）/P2（一般）分级，说明分级理由。

## 3. 测试类型
标注每个功能需要的测试类型：功能测试、性能测试、安全测试。

## 4. 工作量评估
预计需要多少测试用例。

## 5. 风险识别
列出哪些地方容易出问题，需要重点测试。

输出格式要求：使用 Markdown 格式，结构清晰。
""",
        expected_output="完整的测试计划文档",
        agent=planner,
        output_file="reports/01_test_plan.md",
        create_directory=True,
    )

    # 任务 2：生成测试用例
    case_task = Task(
        description="""
根据以下测试计划，生成详细的测试用例。

{plan_output}

要求：
1. 每个用例包含：用例编号、标题、前置条件、测试步骤、预期结果、优先级
2. 覆盖正常场景和异常场景
3. P0 用例必须覆盖所有核心业务流程
4. 包含边界值测试和异常输入测试
5. 预计生成 100 到 150 条用例

输出格式：Markdown 表格
""",
        expected_output="完整的测试用例集",
        agent=designer,
        context=[plan_task],
        output_file="reports/02_test_cases.md",
    )

    # 任务 3：执行测试
    exec_task = Task(
        description=f"""
作为测试执行工程师，请执行以下测试用例。

测试用例：
{case_task.output}

测试环境信息：
- 基础地址：{base_url}
- 超时时间：30 秒

执行要求：
1. 按优先级顺序执行（P0 优先）
2. 使用 api_test 工具发送真实 HTTP 请求
3. 使用 test_data_generator 工具生成测试数据
4. 记录每个用例的执行结果：通过、失败或阻塞
5. 记录响应时间和错误信息

输出格式：Markdown 表格，包含用例编号、状态、响应时间、错误信息。
""",
        expected_output="测试执行结果报告",
        agent=executor,
        context=[case_task],
        output_file="reports/03_test_results.md",
    )

    # 任务 4：分析 Bug
    report_task = Task(
        description="""
作为 Bug 分析专家，请分析以下测试结果，生成 Bug 报告。

测试结果：
{exec_task.output}

请使用 result_validator 工具验证结果，然后输出：

## 1. 测试概览
- 用例总数、通过数、失败数、阻塞数、通过率

## 2. 发现的问题
按严重程度分级（P0/P1/P2），每个问题包含：
- 问题描述
- 复现步骤
- 影响范围
- 严重程度

## 3. 改进建议
针对发现的问题，提出具体的改进建议。

## 4. 发布建议
基于测试结果，给出是否建议发布的结论。
""",
        expected_output="完整的 Bug 分析报告",
        agent=analyst,
        context=[exec_task],
        output_file="reports/04_bug_report.md",
    )

    # 创建 Crew，顺序执行
    crew = Crew(
        agents=[planner, designer, executor, analyst],
        tasks=[plan_task, case_task, exec_task, report_task],
        process=Process.sequential,
        verbose=True,
    )

    # 执行
    result = crew.kickoff()

    return {
        "test_plan": plan_task.output,
        "test_cases": case_task.output,
        "test_results": exec_task.output,
        "bug_report": report_task.output,
        "final_result": result,
    }


if __name__ == "__main__":
    # 需求文档示例
    requirement = """
秒杀系统需求概述：

1. 用户可以在指定时间参与秒杀活动
2. 每个活动有固定的库存数量和活动时间窗口
3. 每个用户每个活动限购一件商品
4. 秒杀成功后生成订单，用户需在 15 分钟内完成支付
5. 超时未支付的订单自动取消，库存恢复
6. 系统需要支持至少 1000 QPS 的并发请求
7. 库存扣减需要保证一致性，不能超卖
"""

    base_url = TARGET_CONFIG["base_url"]

    print("=" * 60)
    print("开始执行秒杀系统自动化测试流程")
    print(f"目标地址：{base_url}")
    print("=" * 60)

    results = run_seckill_test_flow(requirement, base_url)

    print("\n测试流程执行完毕！")
    print(f"测试计划已保存至：reports/01_test_plan.md")
    print(f"测试用例已保存至：reports/02_test_cases.md")
    print(f"测试结果已保存至：reports/03_test_results.md")
    print(f"Bug 报告已保存至：reports/04_bug_report.md")

# # case_task 依赖 plan_task
# case_task = Task(
#     context=[plan_task],  # 声明依赖
#     # 省略参数
# 
# # exec_task 依赖 case_task
# exec_task = Task(
#     context=[case_task],  # 声明依赖
#     # 省略参数
# 

# 两个独立的测试任务可以并行
api_test_task = Task(description="测试 API 接口", agent=executor)
ui_test_task = Task(description="测试 UI 界面", agent=ui_agent)

crew = Crew(
    agents=[executor, ui_agent],
    tasks=[api_test_task, ui_test_task],
    process=Process.hierarchical,  # 支持并行
)

def calculate_coverage(test_results, total_requirements):
    """
    计算测试覆盖率

    Args:
        test_results: 测试结果列表
        total_requirements: 需求条目总数

    Returns:
        覆盖率百分比
    """
    covered_requirements = set()
    for result in test_results:
        if result.get("success"):
            req_id = result.get("requirement_id")
            if req_id:
                covered_requirements.add(req_id)

    coverage = len(covered_requirements) / total_requirements * 100
    return round(coverage, 1)

# # 按优先级分批执行
# for priority in ["P0", "P1", "P2"]:
#     batch_cases = [c for c in all_cases if c.priority == priority]
#     task = Task(
#         description=f"执行以下 {priority} 级测试用例：{batch_cases}", pass  # 省略参数
# 

# Agent 生成的并发测试脚本示例
import asyncio
import aiohttp

async def concurrent_seckill(session, url, headers, count=100):
    """并发发送秒杀请求"""
    tasks = []
    for _ in range(count):
        tasks.append(session.post(url, headers=headers, json={"action": "buy"}))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

def run_with_retry(tool, url, method="GET", max_retries=3):
    for attempt in range(max_retries):
        result = tool._run(url=url, method=method)
        if result.get("success"):
            return result
        if "超时" in result.get("error", ""):
            continue  # 超时时重试
        return result  # 其他错误不重试
    return result  # 返回最后一次结果
