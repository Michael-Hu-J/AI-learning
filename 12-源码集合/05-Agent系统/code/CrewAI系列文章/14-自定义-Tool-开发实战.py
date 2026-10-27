from crewai_tools import BaseTool

class CustomTool(BaseTool):
    name: str = "工具名称"
    description: str = "工具描述"
    
    def _run(self, *args, **kwargs):
        # 实现工具逻辑
        pass

from crewai_tools import BaseTool
import sqlite3

class DatabaseQueryTool(BaseTool):
    name: str = "数据库查询工具"
    description: str = "查询测试数据库"
    
    def __init__(self, db_url: str):
        super().__init__()
        self.db_url = db_url
    
    def _run(self, query: str) -> str:
        """执行 SQL 查询"""
        conn = sqlite3.connect(self.db_url)
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return str(results)
        except Exception as e:
            return f"查询失败：{e}"
        finally:
            conn.close()

# 使用
db_tool = DatabaseQueryTool("test.db")

agent = Agent(
    role="数据分析师",
    goal="分析测试数据",
    tools=[db_tool]
)

from crewai_tools import BaseTool
import requests

class APITestTool(BaseTool):
    name: str = "API 测试工具"
    description: str = "执行 API 测试请求"
    
    def _run(self, method: str, url: str, data: dict = None) -> str:
        """执行 API 请求"""
        
        try:
            if method.upper() == "GET":
                response = requests.get(url)
            elif method.upper() == "POST":
                response = requests.post(url, json=data)
            
            return f"状态码：{response.status_code}\n响应：{response.text}"
        except Exception as e:
            return f"请求失败：{e}"

# 使用
api_tool = APITestTool()

agent = Agent(
    role="API 测试工程师",
    goal="执行 API 测试",
    tools=[api_tool]
)

# 创建多个 Tool
tools = [
    DatabaseQueryTool("test.db"),
    APITestTool(),
    FileReadTool(),
    FileWriteTool()
]

# 创建 Agent 并挂载 Tool
agent = Agent(
    role="测试工程师",
    goal="执行各种测试任务",
    backstory="你有 10 年测试经验",
    tools=tools
)

# 创建 Task
task = Task(
    description="查询数据库，分析测试结果",
    agent=agent
)

# 执行
crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()

from crewai_tools import BaseTool
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import requests

class APITestParams(BaseModel):
    """API 测试参数模型"""
    url: str = Field(..., description="API 地址", min_length=1)
    method: str = Field(default="GET", description="HTTP 方法")
    headers: Optional[dict] = Field(default=None, description="请求头")
    body: Optional[dict] = Field(default=None, description="请求体")
    timeout: int = Field(default=30, description="超时时间(秒)", ge=1, le=300)
    
    @validator('method')
    def validate_method(cls, v):
        allowed = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if v.upper() not in allowed:
            raise ValueError(f"不支持的 HTTP 方法: {v}")
        return v.upper()
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL 必须以 http:// 或 https:// 开头")
        return v

class AdvancedAPITestTool(BaseTool):
    name: str = "高级 API 测试工具"
    description: str = """执行完整的 API 测试，支持参数验证、响应断言、性能统计。
    输入参数：url, method, headers, body, timeout"""
    
    def _run(self, url: str, method: str = "GET", 
             headers: dict = None, body: dict = None, 
             timeout: int = 30) -> str:
        """执行 API 测试请求"""
        # 参数验证
        try:
            params = APITestParams(
                url=url, method=method, 
                headers=headers, body=body, timeout=timeout
            )
        except ValueError as e:
            return f"参数验证失败：{e}"
        
        import time
        start_time = time.time()
        
        try:
            response = requests.request(
                method=params.method,
                url=params.url,
                headers=params.headers,
                json=params.body,
                timeout=params.timeout
            )
            
            elapsed = time.time() - start_time
            
            # 构建详细测试报告
            report = f"""API 测试报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请求信息:
  URL:    {params.url}
  方法:   {params.method}
  超时:   {params.timeout}s

响应信息:
  状态码: {response.status_code}
  响应时间: {elapsed*1000:.0f}ms
  响应大小: {len(response.text)} bytes
  内容类型: {response.headers.get('Content-Type', 'N/A')}

响应体:
{response.text[:500]}{'...' if len(response.text) > 500 else ''}

性能评估:
  {'✅ 响应迅速 (< 500ms)' if elapsed < 0.5 else '⚠️ 响应较慢 (> 500ms)'}
  {'✅ 状态码正常' if 200 <= response.status_code < 300 else f'❌ 状态码异常: {response.status_code}'}"""
            
            return report
            
        except requests.exceptions.Timeout:
            return f"请求超时：{params.url} (超时设置: {params.timeout}s)"
        except requests.exceptions.ConnectionError:
            return f"连接失败：无法连接到 {params.url}"
        except Exception as e:
            return f"请求异常：{type(e).__name__} - {e}"

from crewai_tools import BaseTool
import asyncio
import aiohttp
from typing import List

class AsyncBatchAPITestTool(BaseTool):
    name: str = "异步批量 API 测试工具"
    description: str = "并发测试多个 API 接口，返回汇总报告"
    
    def _run(self, urls: List[str]) -> str:
        """执行批量异步 API 测试"""
        return asyncio.run(self._async_test(urls))
    
    async def _async_test(self, urls: List[str]) -> str:
        """异步执行批量测试"""
        results = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._test_single(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 生成汇总报告
        success_count = sum(1 for r in results if isinstance(r, dict))
        fail_count = len(results) - success_count
        
        report = f"""批量 API 测试报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计: {len(urls)} 个接口
成功: {success_count}
失败: {fail_count}

详细结果:
"""
        for url, result in zip(urls, results):
            if isinstance(result, dict):
                report += f"✅ {url} - {result['status']} ({result['time']:.0f}ms)\n"
            else:
                report += f"❌ {url} - {str(result)}\n"
        
        return report
    
    async def _test_single(self, session, url: str) -> dict:
        """测试单个 API"""
        import time
        start = time.time()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            elapsed = time.time() - start
            return {
                "status": resp.status,
                "time": elapsed * 1000
            }

# 使用示例
batch_tool = AsyncBatchAPITestTool()

agent = Agent(
    role="性能测试工程师",
    goal="批量测试 API 接口性能",
    tools=[batch_tool],
    backstory="你擅长并发测试和性能分析"
)

from crewai_tools import BaseTool
import hashlib
import json
import time
from typing import Optional, Dict

class CachedTool(BaseTool):
    """带缓存功能的 Tool 基类"""
    
    def __init__(self, cache_ttl: int = 300):
        super().__init__()
        self.cache_ttl = cache_ttl  # 缓存有效期（秒）
        self._cache: Dict[str, dict] = {}
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        cache_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """从缓存获取结果"""
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['time'] < self.cache_ttl:
                return cached['result']
            else:
                del self._cache[cache_key]
        return None
    
    def _save_to_cache(self, cache_key: str, result: str):
        """保存结果到缓存"""
        self._cache[cache_key] = {
            'result': result,
            'time': time.time()
        }
    
    def _run(self, *args, **kwargs) -> str:
        """带缓存的执行逻辑"""
        cache_key = self._get_cache_key(*args, **kwargs)
        
        # 尝试从缓存获取
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return f"[缓存结果]\n{cached_result}"
        
        # 执行实际逻辑（由子类实现）
        result = self._execute(*args, **kwargs)
        self._save_to_cache(cache_key, result)
        return result
    
    def _execute(self, *args, **kwargs) -> str:
        """子类实现具体的执行逻辑"""
        raise NotImplementedError


class CachedDatabaseQueryTool(CachedTool):
    name: str = "缓存数据库查询工具"
    description: str = "查询数据库（带 5 分钟缓存）"
    
    def __init__(self, db_url: str, cache_ttl: int = 300):
        super().__init__(cache_ttl=cache_ttl)
        self.db_url = db_url
    
    def _execute(self, query: str) -> str:
        """执行数据库查询"""
        import sqlite3
        conn = sqlite3.connect(self.db_url)
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return str(results)
        except Exception as e:
            return f"查询失败：{e}"
        finally:
            conn.close()

from crewai_tools import BaseTool
from typing import List

class TestSuiteRunnerTool(BaseTool):
    name: str = "测试套件执行工具"
    description: str = """组合多个测试工具，执行完整的测试套件。
    包括：环境检查 → API 测试 → 数据库验证 → 生成报告"""
    
    def __init__(self, api_tool, db_tool, env_checker):
        super().__init__()
        self.api_tool = api_tool
        self.db_tool = db_tool
        self.env_checker = env_checker
    
    def _run(self, test_config: dict) -> str:
        """执行完整测试套件"""
        report_parts = []
        
        # 步骤 1：环境检查
        report_parts.append("## 步骤 1：环境检查")
        env_result = self.env_checker._run()
        report_parts.append(env_result)
        
        if "失败" in env_result:
            return "测试套件中止：环境检查未通过\n\n" + "\n".join(report_parts)
        
        # 步骤 2：API 测试
        report_parts.append("## 步骤 2：API 测试")
        for api in test_config.get("apis", []):
            api_result = self.api_tool._run(**api)
            report_parts.append(f"### {api.get('url', 'N/A')}")
            report_parts.append(api_result)
        
        # 步骤 3：数据库验证
        report_parts.append("## 步骤 3：数据库验证")
        for query in test_config.get("queries", []):
            db_result = self.db_tool._run(query)
            report_parts.append(f"### SQL: {query[:50]}...")
            report_parts.append(db_result)
        
        # 生成汇总
        total = len(report_parts) - 1
        passed = sum(1 for p in report_parts[1:] if "失败" not in p and "异常" not in p)
        
        summary = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
测试套件执行完成
总计: {total} 项检查
通过: {passed}
失败: {total - passed}
通过率: {passed/total*100:.1f}%"""
        
        report_parts.append(summary)
        return "\n".join(report_parts)

from crewai_tools import BaseTool
import re
from typing import Optional

class SecureDatabaseQueryTool(BaseTool):
    name: str = "安全数据库查询工具"
    description: str = "安全地查询数据库（防止 SQL 注入）"
    
    # 只允许 SELECT 查询
    ALLOWED_PATTERNS = [
        r'^\s*SELECT\b',
    ]
    
    # 禁止的操作
    FORBIDDEN_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
        'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE',
        '--', ';', '/*', '*/'
    ]
    
    def __init__(self, db_url: str, max_rows: int = 1000):
        super().__init__()
        self.db_url = db_url
        self.max_rows = max_rows
    
    def _run(self, query: str) -> str:
        """安全执行查询"""
        # 1. 检查是否包含禁止的关键字
        query_upper = query.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in query_upper:
                return f"❌ 查询被拒绝：包含禁止的操作 '{keyword}'"
        
        # 2. 检查是否以 SELECT 开头
        if not re.match(self.ALLOWED_PATTERNS[0], query, re.IGNORECASE):
            return "❌ 查询被拒绝：只允许 SELECT 查询"
        
        # 3. 限制返回行数
        if 'LIMIT' not in query_upper:
            query += f" LIMIT {self.max_rows}"
        
        # 4. 执行查询
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # 格式化输出
            output = f"查询结果（共 {len(results)} 行）：\n"
            output += " | ".join(columns) + "\n"
            output += "-" * 80 + "\n"
            for row in results[:100]:  # 最多显示 100 行
                output += " | ".join(str(v) for v in row) + "\n"
            
            if len(results) > 100:
                output += f"\n... 还有 {len(results) - 100} 行未显示"
            
            return output
        except Exception as e:
            return f"查询失败：{e}"
        finally:
            conn.close()

import unittest
from unittest.mock import patch, MagicMock

class TestAPITestTool(unittest.TestCase):
    """API 测试工具单元测试"""
    
    def setUp(self):
        self.tool = APITestTool()
    
    @patch('requests.get')
    def test_get_request_success(self, mock_get):
        """测试 GET 请求成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'
        mock_get.return_value = mock_response
        
        result = self.tool._run(method="GET", url="https://api.example.com/test")
        
        self.assertIn("状态码：200", result)
        self.assertIn("ok", result)
        mock_get.assert_called_once_with("https://api.example.com/test")
    
    @patch('requests.post')
    def test_post_request_with_data(self, mock_post):
        """测试 POST 请求带数据"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 123}'
        mock_post.return_value = mock_response
        
        result = self.tool._run(
            method="POST",
            url="https://api.example.com/users",
            data={"name": "test"}
        )
        
        self.assertIn("状态码：201", result)
        mock_post.assert_called_once_with(
            "https://api.example.com/users",
            json={"name": "test"}
        )
    
    @patch('requests.get')
    def test_connection_error(self, mock_get):
        """测试连接失败"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        result = self.tool._run(method="GET", url="https://invalid.example.com")
        
        self.assertIn("请求失败", result)
        self.assertIn("ConnectionError", result)
    
    def test_parameter_validation(self):
        """测试参数验证"""
        tool = AdvancedAPITestTool()
        
        # 无效 URL
        result = tool._run(url="invalid-url")
        self.assertIn("参数验证失败", result)
        
        # 无效方法
        result = tool._run(url="https://example.com", method="INVALID")
        self.assertIn("参数验证失败", result)


class TestCachedTool(unittest.TestCase):
    """缓存工具单元测试"""
    
    def test_cache_hit(self):
        """测试缓存命中"""
        tool = CachedDatabaseQueryTool("test.db", cache_ttl=60)
        
        # 第一次调用
        with patch.object(tool, '_execute', return_value="result1") as mock_exec:
            result1 = tool._run("SELECT * FROM users")
            mock_exec.assert_called_once()
        
        # 第二次调用（应该命中缓存）
        with patch.object(tool, '_execute', return_value="result2") as mock_exec:
            result2 = tool._run("SELECT * FROM users")
            mock_exec.assert_not_called()  # 不应该执行
            self.assertEqual(result2, "[缓存结果]\nresult1")
    
    def test_cache_expiry(self):
        """测试缓存过期"""
        tool = CachedDatabaseQueryTool("test.db", cache_ttl=0.1)
        
        with patch.object(tool, '_execute', return_value="result1"):
            tool._run("SELECT * FROM users")
        
        import time
        time.sleep(0.2)  # 等待缓存过期
        
        with patch.object(tool, '_execute', return_value="result2") as mock_exec:
            result = tool._run("SELECT * FROM users")
            mock_exec.assert_called_once()  # 应该重新执行
            self.assertIn("result2", result)


if __name__ == '__main__':
    unittest.main()

from crewai_tools import BaseTool
from typing import List, Dict, Optional
import json
import time
import sqlite3
from datetime import datetime

# ──────────────────────────────────────────────
# 工具 1：测试环境健康检查
# ──────────────────────────────────────────────
class EnvironmentHealthCheckTool(BaseTool):
    name: str = "环境健康检查工具"
    description: str = "检查测试环境的各项服务是否正常运行"
    
    def _run(self, services: List[str] = None) -> str:
        """检查指定服务的健康状态"""
        if services is None:
            services = ["database", "redis", "api_gateway", "message_queue"]
        
        results = {}
        for service in services:
            # 模拟健康检查逻辑
            results[service] = self._check_service(service)
        
        # 生成报告
        healthy = sum(1 for v in results.values() if v['status'] == 'healthy')
        total = len(results)
        
        report = f"""环境健康检查报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
服务总数: {total}
健康服务: {healthy}
异常服务: {total - healthy}

详细状态:
"""
        for service, info in results.items():
            icon = "✅" if info['status'] == 'healthy' else "❌"
            report += f"  {icon} {service}: {info['message']}\n"
        
        if total - healthy > 0:
            report += "\n⚠️ 建议：修复异常服务后再执行测试"
        
        return report
    
    def _check_service(self, service: str) -> dict:
        """检查单个服务"""
        checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            "api_gateway": self._check_api_gateway,
            "message_queue": self._check_message_queue,
        }
        return checks.get(service, lambda: {"status": "unknown", "message": "未知服务"})()
    
    def _check_database(self) -> dict:
        """检查数据库连接"""
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("SELECT 1")
            conn.close()
            return {"status": "healthy", "message": "连接正常，响应时间 < 10ms"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"连接失败: {e}"}
    
    def _check_redis(self) -> dict:
        return {"status": "healthy", "message": "Redis 连接正常"}
    
    def _check_api_gateway(self) -> dict:
        return {"status": "healthy", "message": "API 网关响应正常"}
    
    def _check_message_queue(self) -> dict:
        return {"status": "healthy", "message": "消息队列运行正常"}


# ──────────────────────────────────────────────
# 工具 2：测试数据生成器
# ──────────────────────────────────────────────
class TestDataGeneratorTool(BaseTool):
    name: str = "测试数据生成工具"
    description: str = "生成各种类型的测试数据（用户、订单、商品等）"
    
    def _run(self, data_type: str, count: int = 10) -> str:
        """生成测试数据"""
        generators = {
            "user": self._generate_users,
            "order": self._generate_orders,
            "product": self._generate_products,
        }
        
        generator = generators.get(data_type)
        if not generator:
            return f"不支持的数据类型: {data_type}。可选: {list(generators.keys())}"
        
        data = generator(count)
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _generate_users(self, count: int) -> List[dict]:
        """生成用户测试数据"""
        import random
        users = []
        domains = ["example.com", "test.com", "demo.com"]
        for i in range(count):
            users.append({
                "id": i + 1,
                "username": f"test_user_{i+1}",
                "email": f"user{i+1}@{random.choice(domains)}",
                "phone": f"138{random.randint(10000000, 99999999)}",
                "status": random.choice(["active", "inactive", "pending"]),
                "created_at": f"2026-01-{random.randint(1,28):02d}"
            })
        return users
    
    def _generate_orders(self, count: int) -> List[dict]:
        """生成订单测试数据"""
        import random
        orders = []
        statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
        for i in range(count):
            orders.append({
                "order_id": f"ORD{datetime.now().strftime('%Y%m%d')}{i+1:04d}",
                "user_id": random.randint(1, 100),
                "amount": round(random.uniform(10, 9999), 2),
                "status": random.choice(statuses),
                "created_at": f"2026-06-{random.randint(1,7):02d} {random.randint(0,23):02d}:{random.randint(0,59):02d}"
            })
        return orders
    
    def _generate_products(self, count: int) -> List[dict]:
        """生成商品测试数据"""
        import random
        categories = ["电子产品", "服装", "食品", "图书", "家居"]
        products = []
        for i in range(count):
            products.append({
                "product_id": f"PROD{i+1:04d}",
                "name": f"测试商品{i+1}",
                "category": random.choice(categories),
                "price": round(random.uniform(9.9, 9999.9), 2),
                "stock": random.randint(0, 10000),
                "rating": round(random.uniform(3.0, 5.0), 1)
            })
        return products


# ──────────────────────────────────────────────
# 工具 3：测试报告生成器
# ──────────────────────────────────────────────
class TestReportGeneratorTool(BaseTool):
    name: str = "测试报告生成工具"
    description: str = "根据测试结果生成专业的测试报告"
    
    def _run(self, test_results: List[dict], report_type: str = "summary") -> str:
        """生成测试报告"""
        if report_type == "summary":
            return self._generate_summary_report(test_results)
        elif report_type == "detailed":
            return self._generate_detailed_report(test_results)
        else:
            return f"不支持的报告类型: {report_type}"
    
    def _generate_summary_report(self, results: List[dict]) -> str:
        """生成摘要报告"""
        total = len(results)
        passed = sum(1 for r in results if r.get('status') == 'passed')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')
        
        pass_rate = passed / total * 100 if total > 0 else 0
        
        report = f"""
╔══════════════════════════════════════════╗
║         测试执行摘要报告                 ║
╠══════════════════════════════════════════╣
║ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}               ║
║                                          ║
║ 总用例数: {total}                          ║
║ 通过:     {passed} ({pass_rate:.1f}%)                      ║
║ 失败:     {failed}                          ║
║ 跳过:     {skipped}                          ║
╚══════════════════════════════════════════╝
"""
        if failed > 0:
            report += "\n失败用例详情:\n"
            for r in results:
                if r.get('status') == 'failed':
                    report += f"  ❌ {r.get('name', 'N/A')}: {r.get('error', '未知错误')}\n"
        
        return report
    
    def _generate_detailed_report(self, results: List[dict]) -> str:
        """生成详细报告"""
        report = "# 测试执行详细报告\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for i, r in enumerate(results, 1):
            status_icon = "✅" if r.get('status') == 'passed' else "❌" if r.get('status') == 'failed' else "⏭️"
            report += f"## {i}. {status_icon} {r.get('name', 'N/A')}\n\n"
            report += f"- **状态**: {r.get('status', 'N/A')}\n"
            report += f"- **耗时**: {r.get('duration', 'N/A')}ms\n"
            if r.get('error'):
                report += f"- **错误**: {r['error']}\n"
            report += "\n"
        
        return report


# ──────────────────────────────────────────────
# 使用示例：完整的测试 Agent 配置
# ──────────────────────────────────────────────
# 创建所有工具
env_check = EnvironmentHealthCheckTool()
data_gen = TestDataGeneratorTool()
api_test = AdvancedAPITestTool()
report_gen = TestReportGeneratorTool()

# 创建测试工程师 Agent
test_engineer = Agent(
    role="高级测试工程师",
    goal="执行全面的测试工作，确保软件质量",
    backstory="""你是拥有 10 年经验的高级测试工程师，擅长：
    1. 设计覆盖各种边界条件的测试用例
    2. 执行自动化测试并分析结果
    3. 生成专业的测试报告
    4. 发现潜在的系统风险
    
    你工作严谨，注重细节，对质量问题零容忍。""",
    tools=[env_check, data_gen, api_test, report_gen],
    verbose=True
)

# 创建测试任务
test_task = Task(
    description="""请执行以下测试任务：
    1. 首先检查测试环境是否健康
    2. 生成 5 个测试用户数据
    3. 使用生成的用户数据测试登录 API (https://api.example.com/login)
    4. 根据测试结果生成摘要报告""",
    agent=test_engineer,
    expected_output="完整的测试报告，包含环境检查、数据生成、API 测试结果和汇总分析"
)

crew = Crew(
    agents=[test_engineer],
    tasks=[test_task],
    verbose=True
)

result = crew.kickoff()
print(result)
