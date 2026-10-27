"""
04-工具调用：封装测试工具
对应文章：工具调用
"""

from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
import requests


class APITestTool(BaseTool):
    """API 测试工具"""
    name: str = "API 测试工具"
    description: str = "测试 HTTP 接口的功能"

    def _run(self, url: str, method: str = "GET", expected_status: int = 200) -> dict:
        try:
            response = requests.request(method, url, timeout=10)
            passed = response.status_code == expected_status
            return {
                "url": url,
                "method": method,
                "actual_status": response.status_code,
                "expected_status": expected_status,
                "passed": passed,
                "response_time": f"{response.elapsed.total_seconds():.3f}s",
                "content_length": len(response.text),
            }
        except Exception as e:
            return {"url": url, "method": method, "passed": False, "error": str(e)}


class PerformanceTestTool(BaseTool):
    """性能测试工具"""
    name: str = "性能测试工具"
    description: str = "对接口进行简单压力测试"

    def _run(self, url: str, concurrency: int = 5, total_requests: int = 20) -> dict:
        import time
        from concurrent.futures import ThreadPoolExecutor

        results = {"success": 0, "failed": 0, "times": []}

        def make_request():
            try:
                start = time.time()
                response = requests.get(url, timeout=10)
                elapsed = time.time() - start
                results["times"].append(elapsed)
                if response.status_code == 200:
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception:
                results["failed"] += 1

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            for _ in range(total_requests):
                executor.submit(make_request)

        avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
        return {
            "url": url,
            "concurrency": concurrency,
            "total_requests": total_requests,
            "success": results["success"],
            "failed": results["failed"],
            "avg_response_time": f"{avg_time:.3f}s",
            "tps": f"{total_requests / sum(results['times']):.1f}" if results["times"] else "0",
        }


def main():
    # 创建测试工程师 Agent
    tester = Agent(
        role="自动化测试工程师",
        goal="使用测试工具验证系统功能",
        backstory="5 年自动化测试经验",
        tools=[APITestTool(), PerformanceTestTool()],
        verbose=True,
    )

    # 创建测试任务
    task = Task(
        description="测试 https://httpbin.org/get 的功能和性能",
        expected_output="功能测试结果 + 性能测试报告",
        agent=tester,
    )

    crew = Crew(agents=[tester], tasks=[task])
    result = crew.kickoff()

    print("\n=== 测试结果 ===")
    print(result)


if __name__ == "__main__":
    main()
