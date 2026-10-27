"""
01-CrewAI 入门示例：第一个测试 Agent
对应文章：CrewAI 入门指南 - 14 年测试老兵的 AI Agent 初体验
"""

import os
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import Field


class APITestTool(BaseTool):
    """API 测试工具"""
    name: str = "API 测试工具"
    description: str = "发送 HTTP 请求并返回响应状态码和内容长度"

    def _run(self, url: str, method: str = "GET") -> str:
        import requests
        try:
            response = requests.request(method, url, timeout=10)
            return (
                f"状态码: {response.status_code}\n"
                f"响应长度: {len(response.text)} 字符\n"
                f"响应时间: {response.elapsed.total_seconds():.2f}s"
            )
        except Exception as e:
            return f"请求失败: {str(e)}"


def create_test_agent():
    """创建测试专家 Agent"""
    return Agent(
        role="测试专家",
        goal="设计并执行测试用例，保证软件质量",
        backstory=(
            "你是一名有 10 年经验的测试工程师，擅长功能测试、"
            "边界值分析和异常场景测试。你注重细节，善于发现潜在问题。"
        ),
        tools=[APITestTool()],
        verbose=True,
    )


def main():
    # 创建 Agent
    tester = create_test_agent()

    # 创建 Task
    task = Task(
        description="测试 https://httpbin.org/get 接口的功能是否正常",
        expected_output="包含状态码、响应长度、响应时间的测试报告",
        agent=tester,
    )

    # 创建 Crew 并执行
    crew = Crew(agents=[tester], tasks=[task])
    result = crew.kickoff()

    print("\n=== 测试结果 ===")
    print(result)


if __name__ == "__main__":
    main()
