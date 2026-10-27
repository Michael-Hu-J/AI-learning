"""
MCP + 并发控制 + asyncio 测试
对应文章：第6/7/10篇
"""
import pytest
from worker.execution_service import UIExecutionService


class TestExecService:
    def test_init(self):
        s = UIExecutionService(2)
        assert s.max_concurrent == 2
        assert s.active_count == 0

    def test_stop_nonexist(self):
        s = UIExecutionService()
        assert s.stop("nope") is not None


class TestMCP:
    def test_import(self):
        try:
            from mcp.server.fastmcp import FastMCP
            from mcp.playwright_server import navigate, click, fill
            assert callable(navigate)
            assert callable(click)
            assert callable(fill)
        except ImportError:
            pytest.skip("mcp 包未安装")


class TestAsync:
    def test_semaphore_concept(self):
        """验证信号量概念（不启动事件循环）"""
        import asyncio
        sem = asyncio.Semaphore(2)
        assert sem._value == 2

    def test_coroutine_concept(self):
        """验证协程函数定义"""
        async def dummy():
            return 42
        import inspect
        assert inspect.iscoroutinefunction(dummy)
