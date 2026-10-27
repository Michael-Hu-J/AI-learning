# Tool 有 Bug：超时处理错误
def _run(self, url: str, timeout: int = 30):
    response = requests.get(url)  # 没有 timeout 参数
    return {"status": response.status_code}

def test_timeout():
    result = tool._run(url="...", timeout=1)
    assert result["error"] == "请求超时"

# test_api_test_tool.py
import pytest
from app.tools.api_test import APITestTool


class TestAPITestTool:
    """APITestTool 测试类"""
    
    @pytest.fixture
    def tool(self):
        """创建测试工具实例"""
        return APITestTool()
    
    def test_successful_request(self, tool):
        """测试成功的请求"""
        result = tool._run(
            url="https://httpbin.org/get",
            method="GET",
            expected_status=200
        )
        
        assert result["success"] is True
        assert result["status_code"] == 200
        assert "response_time_ms" in result
        assert result["response_time_ms"] > 0
    
    def test_timeout(self, tool):
        """测试超时"""
        result = tool._run(
            url="https://httpbin.org/delay/10",
            timeout=1  # 1 秒超时
        )
        
        assert result["success"] is False
        assert result["error"] == "请求超时"
        assert "timeout_seconds" in result
    
    def test_invalid_url(self, tool):
        """测试无效 URL"""
        result = tool._run(
            url="http://invalid-url-12345.com"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_post_request(self, tool):
        """测试 POST 请求"""
        result = tool._run(
            url="https://httpbin.org/post",
            method="POST",
            body={"key": "value"},
            expected_status=200
        )
        
        assert result["success"] is True
        assert result["status_code"] == 200
        assert "response_json" in result
    
    def test_custom_headers(self, tool):
        """测试自定义请求头"""
        result = tool._run(
            url="https://httpbin.org/headers",
            headers={"X-Custom-Header": "test-value"}
        )
        
        assert result["success"] is True
        assert "X-Custom-Header" in result["response_body"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# test_performance_test_tool.py
import pytest
from app.tools.performance_test import PerformanceTestTool


class TestPerformanceTestTool:
    """PerformanceTestTool 测试类"""
    
    @pytest.fixture
    def tool(self):
        return PerformanceTestTool()
    
    def test_basic_performance_test(self, tool):
        """测试基本性能测试"""
        result = tool._run(
            url="https://httpbin.org/get",
            concurrent_users=5,
            iterations=10
        )
        
        assert result["test_summary"] == "性能测试完成"
        assert result["total_requests"] == 10
        assert result["success_count"] >= 8  # 允许少量失败
        assert "avg_response_time_ms" in result
        assert "qps" in result
    
    def test_concurrent_requests(self, tool):
        """测试并发请求"""
        result = tool._run(
            url="https://httpbin.org/get",
            concurrent_users=10,
            iterations=50
        )
        
        assert result["concurrent_users"] == 10
        assert result["total_requests"] == 50
        assert "p95_response_time_ms" in result
        assert "p99_response_time_ms" in result
    
    def test_all_requests_fail(self, tool):
        """测试所有请求失败"""
        result = tool._run(
            url="http://invalid-url-12345.com",
            iterations=5
        )
        
        assert result["success_count"] == 0
        assert result["error_count"] == 5
        assert "所有请求失败" in result["test_summary"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# test_agent_integration.py
import pytest
from crewai import Agent, Task, Crew
from app.tools.api_test import APITestTool


class TestAgentIntegration:
    """Agent + Tool 集成测试"""
    
    def test_engineer_with_api_tool(self):
        """测试工程师 Agent 使用 API 测试工具"""
        # 创建 Agent
        engineer = Agent(
            role="测试工程师",
            goal="执行 API 测试",
            backstory="你有 5 年测试经验",
            tools=[APITestTool()],
            verbose=False
        )
        
        # 创建 Task
        task = Task(
            description="请测试 https://httpbin.org/get 接口",
            expected_output="测试报告",
            agent=engineer
        )
        
        # 执行
        crew = Crew(agents=[engineer], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        # 验证
        assert result is not None
        assert "httpbin.org" in str(result)
        assert "测试" in str(result) or "test" in str(result).lower()

def test_1():  # 看不出测试什么
    pass

def test_api():  # 太模糊
    pass

def test_successful_request():  # 测试成功请求
    pass

def test_timeout_handling():  # 测试超时处理
    pass

def test_invalid_url():  # 测试无效 URL
    pass

def test_1():
    global_data = {"count": 0}  # 依赖全局变量
    global_data["count"] += 1

def test_2():
    assert global_data["count"] == 1  # 依赖 test_1

def test_1():
    local_data = {"count": 0}  # 使用局部变量
    local_data["count"] += 1
    assert local_data["count"] == 1

def test_2():
    local_data = {"count": 0}  # 独立
    local_data["count"] += 1
    assert local_data["count"] == 1

def test_1():
    tool = APITestTool()  # 每个测试都创建
    ...

def test_2():
    tool = APITestTool()  # 重复代码
    ...

@pytest.fixture
def tool():
    """共享的 tool 实例"""
    return APITestTool()

def test_1(tool):  # 使用 fixture
    ...

def test_2(tool):  # 复用
    ...
