from crewai import Agent, Task, Crew, LLM
from app.core.config import settings
from app.tools.api_test import APITestTool
from app.tools.performance_test import PerformanceTestTool
import asyncio


def create_engineer_agent():
    """创建测试工程师 Agent"""
    llm = LLM(
        model=settings.OPENAI_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL
    )
    
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
        verbose=False,
        allow_delegation=False,
        tools=[APITestTool(), PerformanceTestTool()]  # 挂载真实工具
    )


async def run_engineer_agent(
    test_plan: str,
    test_cases: str,
    base_url: str,
    client_id: str
) -> str:
    """
    运行测试工程师 Agent
    
    Args:
        test_plan: 测试计划
        test_cases: 测试用例
        base_url: 被测系统基础 URL
        client_id: WebSocket 客户端 ID
        
    Returns:
        测试结果报告
    """
    agent = create_engineer_agent()
    
    task = Task(
        description=f"""
作为测试工程师，请执行以下测试用例：

测试计划：
{test_plan}

测试用例：
{test_cases}

## 测试环境
基础 URL: {base_url}

## 执行要求

1. **执行顺序**
   - 按优先级顺序执行 (P0 → P1 → P2)
   - 先执行功能测试，再执行性能测试

2. **记录内容**
   - 每个用例的实际结果
   - 通过/失败状态
   - 接口响应时间
   - 失败用例的详细错误信息

3. **工具使用**
   - 使用 APITestTool 执行 API 测试
   - 使用 PerformanceTestTool 执行性能测试
   - 记录每次调用的详细结果

4. **问题处理**
   - 遇到阻塞性问题立即记录
   - 尝试复现失败的场景
   - 记录复现步骤

## 输出格式

使用 Markdown 表格格式：

| 用例 ID | 状态 | 实际结果 | 响应时间 (ms) | 错误信息 | 备注 |
|---------|------|----------|---------------|----------|------|
| TC001   |  通过 | ...      | 120           | -        | -    |
| TC002   |  失败 | ...      | 350           | 详细错误 | 需复现 |

状态标记： 通过 /  失败 /  阻塞 / ⏭ 跳过
""",
        expected_output="测试执行结果表格，包含每个用例的状态、实际结果、响应时间和错误信息",
        agent=agent
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=False
    )
    
    result = await asyncio.to_thread(crew.kickoff)
    return str(result)

from crewai.tools import BaseTool
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class APITestTool(BaseTool):
    """API 测试工具类"""
    
    name: str = "api_test"
    description: str = """发送 HTTP 请求并验证 API 响应，用于测试后端接口。"""
    
    def _run(
        self, 
        url: str, 
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """执行 API 测试"""
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
            
            return {
                "success": response.status_code == expected_status,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response_time_ms": round(response_time, 2),
                "response_body": response.text[:2000],
                "url": url,
                "method": method.upper(),
                "timestamp": start_time.isoformat()
            }
            
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

# Agent 通过 Tool 调用
result = tool._run(
    url="http://your-server:port/api/seckill/activities",
    method="GET",
    expected_status=200
)

# 返回结果
{
    "success": True,
    "status_code": 200,
    "response_time_ms": 125,
    "response_body": "[{\"id\": 1, \"name\": \"双 11 秒杀大促\"}]",
    "url": "http://your-server:port/api/seckill/activities",
    "method": "GET"
}

# 阶段 3：测试工程师（可选）
test_results = ""
if enable_engineer:
    # send_log(task_id, "agent_start", " 测试工程师开始执行 API 测试...")  # 异步调用示例
    
    from app.agents.engineer import run_engineer_agent
    # test_results = await run_engineer_agent(
        # test_plan=test_plan,
        # test_cases=test_cases,
#        base_url=base_url,  # http://your-server:port
        # client_id=task_id
    # )
    
    # 保存测试结果
    results_file = os.path.join(output_dir, "03_test_results.md")
    with open(results_file, "w", encoding="utf-8") as f:
        f.write(test_results)
    
    # send_log(task_id, "agent_complete", " 测试工程师完成 API 测试", {
#        "output_file": "03_test_results.md",
#        "word_count": len(test_results)
    # })
else:
    test_results = "# 测试执行已跳过\n\n用户选择不执行真实 API 测试。"

# 场景 1：有测试环境
ExecuteRequest(
    requirement="...",
    base_url="http://test-server:5000",
    enable_engineer=True  # 执行真实测试
)

# 场景 2：仅生成文档
ExecuteRequest(
    requirement="...",
    enable_engineer=False  # 跳过执行
)
