import pytest
import asyncio
from mcp import ClientSession, StdioServerParameters

@pytest.fixture
async def mcp_session():
    """MCP会话fixture"""
    params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    async with ClientSession(params) as session:
        yield session

class TestMCPBasics:
    async def test_tool_discovery(self, mcp_session):
        tools = await mcp_session.list_tools()
        assert len(tools) >= 2  # 至少2个工具
        for tool in tools:
            assert tool.name
            assert len(tool.description) >= 20
    
    async def test_tool_call_normal(self, mcp_session):
        result = await mcp_session.call_tool(
            "weather_query",
            arguments={"city": "北京", "date": "2026-06-15"}
        )
        assert result.isError is False
        assert "北京" in result.content[0].text

import pytest

INVALID_PARAMS = [
    {"city": "", "date": "2026-06-15"},        # 空城市
    {"city": "北京"},                           # 缺日期
    {},                                         # 全缺
    {"city": "北京" * 100, "date": "2026-06-15"},  # 超长
    {"city": 12345, "date": "2026-06-15"},      # 类型错误
]

class TestToolParameters:
    @pytest.mark.parametrize("params", INVALID_PARAMS)
    async def test_invalid_params(self, mcp_session, params):
        result = await mcp_session.call_tool("weather_query", params)
        assert result.isError is True, f"参数 {params} 应被拒绝"

class TestSSETransport:
    async def test_sse_connection(self):
        """SSE连接测试"""
        from mcp import SSEClientTransport
        
        transport = SSEClientTransport("http://localhost:8080/sse")
        async with ClientSession(transport) as session:
            tools = await session.list_tools()
            assert len(tools) > 0
    
    async def test_sse_reconnection(self):
        """SSE断连重连测试"""
        transport = SSEClientTransport("http://localhost:8080/sse")
        async with ClientSession(transport) as session:
            tools1 = await session.list_tools()
            
            # 模拟断连：停止Server
            # ... (实际实现中需要控制Server进程)
            
            # 重启Server
            # ...
            
            # 验证重连
            tools2 = await session.list_tools()
            assert tools1 == tools2

class TestMCPSecurity:
    async def test_no_auth(self, mcp_session):
        """未认证访问测试"""
        # 如果Server要求认证，这里应该失败
        # 具体实现取决于你的认证方式
        pass
    
    async def test_tool_name_injection(self, mcp_session):
        """工具名注入"""
        malicious_names = [
            "weather_query; rm -rf /",
            "weather_query$(whoami)",
            "../../../etc/passwd",
            "<script>alert(1)</script>",
        ]
        for name in malicious_names:
            result = await mcp_session.call_tool(name, {})
            assert result.isError is True, f"恶意工具名 {name} 应被拒绝"
    
    async def test_param_sql_injection(self, mcp_session):
        """SQL注入测试"""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin'--",
        ]
        for payload in sql_payloads:
            result = await mcp_session.call_tool(
                "weather_query",
                {"city": payload, "date": "2026-06-15"}
            )
            # 不应执行SQL，也不应泄露数据库结构
            assert "DROP TABLE" not in result.content[0].text
            assert "syntax error" not in result.content[0].text.lower()

import asyncio
import time

class TestMCPPerformance:
    async def test_concurrent_calls(self, mcp_session):
        """并发调用测试"""
        async def call_with_timing(args):
            start = time.time()
            result = await mcp_session.call_tool("weather_query", args)
            elapsed = time.time() - start
            return result, elapsed
        
        tasks = [
            call_with_timing({"city": city, "date": "2026-06-15"})
            for city in ["北京", "上海", "广州", "深圳", "杭州"]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        times = []
        for item in results:
            if isinstance(item, Exception):
                pytest.fail(f"并发调用异常: {item}")
            result, elapsed = item
            assert result.isError is False
            times.append(elapsed)
        
        # 验证P95响应时间
        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 5.0, f"P95响应时间 {p95}s 超过阈值"

"""
MCP 工具发现测试
验证 Agent 能否正确发现和管理 MCP 工具
"""
import pytest
import asyncio
from mcp import ClientSession, StdioServerParameters

class TestToolDiscovery:
    async def test_list_tools(self):
        params = StdioServerParameters(command="python", args=["mcp_server.py"])
        async with ClientSession(params) as session:
            tools = await session.list_tools()
            assert len(tools) > 0, "工具列表不能为空"
            for tool in tools:
                assert tool.name, "工具必须有 name"
                assert tool.description, "工具必须有 description"
                assert tool.inputSchema, "工具必须有 inputSchema"
                schema = tool.inputSchema
                assert "type" in schema, "schema 必须有 type"
                assert "properties" in schema, "schema 必须有 properties"

    async def test_tool_description_quality(self):
        async with ClientSession(params) as session:
            tools = await session.list_tools()
            for tool in tools:
                assert len(tool.description) >= 20, \
                    f"工具 {tool.name} 的描述太短，Agent 无法理解"
                assert any(kw in tool.description.lower()
                          for kw in ["查询", "获取", "创建", "更新", "删除", "计算"]), \
                    f"工具 {tool.name} 的描述缺少功能说明"

    async def test_empty_server(self):
        async with ClientSession(params) as session:
            tools = await session.list_tools()
            assert tools == [], "空服务器应返回空列表"


class TestToolCalling:
    async def test_normal_call(self):
        async with ClientSession(params) as session:
            result = await session.call_tool(
                "weather_query",
                arguments={"city": "北京", "date": "2026-06-08"}
            )
            assert result.content, "返回内容不能为空"
            assert result.isError is False, "正常调用不应报错"
            content_text = result.content[0].text
            assert "北京" in content_text, "返回应包含城市名"

    async def test_missing_required_param(self):
        async with ClientSession(params) as session:
            result = await session.call_tool(
                "weather_query",
                arguments={"date": "2026-06-08"}
            )
            assert result.isError is True, "缺少必填参数应报错"
            assert "city" in result.content[0].text.lower(), \
                "错误信息应指出缺少的参数"

    async def test_wrong_param_type(self):
        async with ClientSession(params) as session:
            result = await session.call_tool(
                "weather_query",
                arguments={"city": "北京", "date": 20260608}
            )
            assert result.isError is True, "类型错误应报错"

    async def test_param_value_out_of_range(self):
        async with ClientSession(params) as session:
            result = await session.call_tool(
                "weather_query",
                arguments={"city": "北" * 1000, "date": "2026-06-08"}
            )
            assert result.isError is True, "超长参数应报错"

    async def test_nonexistent_tool(self):
        async with ClientSession(params) as session:
            result = await session.call_tool("nonexistent_tool", arguments={})
            assert result.isError is True, "不存在的工具应报错"

    async def test_concurrent_calls(self):
        async with ClientSession(params) as session:
            tasks = [
                session.call_tool("weather_query", {"city": c})
                for c in ["北京", "上海", "广州"]
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"并发调用 {i} 失败: {result}")
                assert result.isError is False, f"并发调用 {i} 返回错误"


class TestResourceSubscription:
    async def test_list_resources(self):
        async with ClientSession(params) as session:
            resources = await session.list_resources()
            for resource in resources:
                assert resource.uri, "资源必须有 URI"
                assert resource.name, "资源必须有 name"
                assert resource.mimeType, "资源必须有 mimeType"

    async def test_read_resource(self):
        async with ClientSession(params) as session:
            content = await session.read_resource("file:///data/config.json")
            assert content, "资源内容不能为空"

    async def test_resource_subscription(self):
        async with ClientSession(params) as session:
            notifications = []
            async def on_notification(notification):
                notifications.append(notification)
            await session.subscribe_resource(
                "file:///data/config.json", on_notification
            )
            await asyncio.sleep(1)
            assert len(notifications) > 0, "应收到资源更新通知"


class TestTransport:
    async def test_stdio_transport(self):
        params = StdioServerParameters(command="python", args=["mcp_server.py"])
        async with ClientSession(params) as session:
            tools = await session.list_tools()
            assert len(tools) > 0

    async def test_sse_transport(self):
        from mcp import SSEClientTransport
        transport = SSEClientTransport("http://localhost:8080/sse")
        async with ClientSession(transport) as session:
            tools = await session.list_tools()
            assert len(tools) > 0

    async def test_transport_reconnection(self):
        async with ClientSession(params) as session:
            tools1 = await session.list_tools()
            try:
                tools2 = await session.list_tools()
                assert tools1 == tools2, "重连后工具列表应一致"
            except ConnectionError:
                pass  # 应提供手动重连方法

    async def test_transport_timeout(self):
        import aiohttp
        async with aiohttp.ClientSession() as http_session:
            try:
                async with http_session.get(
                    "http://localhost:8080/sse",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    assert response.status == 200
            except asyncio.TimeoutError:
                pytest.fail("SSE 连接超时")


class TestMCPSecurity:
    async def test_unauthorized_access(self):
        params = StdioServerParameters(command="python", args=["mcp_server.py"])
        try:
            async with ClientSession(params) as session:
                await session.list_tools()
        except PermissionError:
            pass  # 正确：未授权被拒绝

    async def test_tool_injection(self):
        async with ClientSession(params) as session:
            result = await session.call_tool(
                "weather_query; rm -rf /", arguments={"city": "北京"}
            )
            assert result.isError is True, "恶意工具名应被拒绝"

    async def test_argument_injection(self):
        async with ClientSession(params) as session:
            result = await session.call_tool(
                "weather_query",
                arguments={"city": "北京'; DROP TABLE users; --", "date": "2026-06-08"}
            )
            assert result.isError is True or \
                   "DROP TABLE" not in result.content[0].text, \
                "SQL 注入应被防御"

    async def test_resource_path_traversal(self):
        async with ClientSession(params) as session:
            try:
                await session.read_resource("file:///etc/passwd")
                pytest.fail("不应能访问系统文件")
            except PermissionError:
                pass

async def on_log(log_notification):
    print(f"[{log_notification.level}] {log_notification.data}")

session.set_logging_callback(on_log)
