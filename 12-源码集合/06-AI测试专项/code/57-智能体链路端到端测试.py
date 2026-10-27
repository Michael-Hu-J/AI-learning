"""
智能体端到端测试框架 v2
作者：测试员周周 测试员周周
"""
import pytest
import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TraceStep:
    """执行轨迹步骤——记录每个环节的详细过程"""
    step_id: int
    phase: str          # perceive / planning / executing / memory
    action: str
    input_data: Dict
    output_data: Dict
    tool_called: Optional[str] = None
    duration_ms: float = 0
    token_usage: int = 0
    error: Optional[str] = None

@dataclass
class EndToEndResult:
    """端到端测试结果"""
    task: str
    status: TaskStatus
    total_steps: int
    trace: List[TraceStep] = field(default_factory=list)
    phases_covered: List[str] = field(default_factory=list)
    total_duration_ms: float = 0
    final_output: str = ""
    errors: List[str] = field(default_factory=list)
    token_consumption: int = 0

class TestSingleTaskE2E:
    """单任务端到端测试"""
    
    async def test_simple_task(self):
        """简单任务端到端测试"""
        task = "北京今天天气怎么样？"
        result = await self.agent.execute(task)
        
        # 验证任务完成
        assert result.status == TaskStatus.COMPLETED
        
        # 验证四环节全覆盖
        phases = set(step.phase for step in result.trace)
        for expected_phase in ["perceive", "planning", "executing", "memory"]:
            assert expected_phase in phases, f"缺少{expected_phase}环节"
        
        # 验证输出质量
        assert len(result.final_output) > 10, "输出太短，可能信息不完整"
        assert any(kw in result.final_output for kw in ["天气", "温度", "降水"])
    
    async def test_multi_step_task(self):
        """多步骤任务——验证工具调用顺序"""
        task = "帮我订明天上午去北京的机票"
        result = await self.agent.execute(task)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.total_steps >= 3, "订票应至少 3 步"
        
        # 验证工具调用顺序
        tools_called = [s.tool_called for s in result.trace if s.tool_called]
        if "search_flight" in tools_called and "book_ticket" in tools_called:
            search_idx = tools_called.index("search_flight")
            book_idx = tools_called.index("book_ticket")
            assert search_idx < book_idx, "必须先查航班再下单"

class TestCrossTaskE2E:
    """跨任务端到端测试"""
    
    async def test_task_chain(self):
        """任务链测试——验证任务间信息传递"""
        tasks = [
            "帮我查明天北京的天气",
            "如果下雨就订后天的航班",
            "订首都机场附近的酒店",
        ]
        
        agent = create_agent()
        
        for i, task in enumerate(tasks):
            result = await agent.execute(task)
            assert result.status == TaskStatus.COMPLETED
            
            # 验证后续任务能引用前面任务的结果
            if i > 0:
                memory = agent.get_memory()
                assert memory.has_relevant_info(tasks[i-1]), \
                    f"任务 {i+1} 应能引用任务 {i} 的结果"
    
    async def test_context_preservation(self):
        """上下文保持——偏好跨任务传递"""
        agent = create_agent()
        
        await agent.execute("我喜欢靠窗的座位")
        result = await agent.execute("帮我订一张机票")
        
        booking = self.extract_booking_details(result.final_output)
        assert "靠窗" in booking, "订票应考虑靠窗偏好"

class TestExceptionE2E:
    """异常场景端到端测试"""
    
    async def test_tool_failure_recovery(self):
        """工具失败恢复——Agent 的自救能力"""
        agent = create_agent()
        agent.mock_tool_failure("search_flight")
        
        result = await agent.execute("帮我订明天去北京的机票")
        
        # Agent 应该能处理工具失败
        # 策略：重试 → 换工具 → 告知用户
        assert result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        
        if result.status == TaskStatus.FAILED:
            assert any("暂时" in e or "稍后" in e or "重试" in e 
                       for e in result.errors), "错误消息应友好"
    
    async def test_infinite_loop_detection(self):
        """死循环检测"""
        agent = create_agent(max_steps=20)
        result = await agent.execute("一直查天气直到下雨")
        
        assert result.total_steps <= 20, "不应超过最大步骤数"
        if result.total_steps == 20:
            assert result.status == TaskStatus.FAILED

class TestE2EPerformance:
    """端到端性能测试"""
    
    async def test_phase_breakdown(self):
        """环节耗时分解——定位性能瓶颈"""
        result = await self.agent.execute("帮我订明天去北京的机票")
        
        phase_times = {}
        for step in result.trace:
            phase_times.setdefault(step.phase, []).append(step.duration_ms)
        
        for phase, times in phase_times.items():
            total = sum(times)
            avg = total / len(times)
            print(f"{phase}: 总耗时 {total:.0f}ms, 平均 {avg:.0f}ms, 次数 {len(times)}")
        
        # 验证：执行环节通常耗时最多
        if "executing" in phase_times and "planning" in phase_times:
            exec_total = sum(phase_times["executing"])
            plan_total = sum(phase_times["planning"])
            assert exec_total >= plan_total * 0.5, \
                "执行耗时不应显著低于规划（除非任务极其简单）"

class TestE2EQuality:
    """端到端质量测试"""
    
    def test_output_relevance(self):
        """输出相关性——用关键词 + 语义双重验证"""
        test_cases = [
            ("北京今天天气怎么样？", ["天气", "温度", "北京"]),
            ("帮我订机票", ["航班", "订单", "订票"]),
        ]
        
        for task, expected_keywords in test_cases:
            result = self.agent.execute(task)
            matched = [kw for kw in expected_keywords if kw in result.final_output]
            assert len(matched) >= 2, \
                f"任务 '{task}' 输出相关性不足，匹配: {matched}"
    
    def test_output_consistency(self):
        """输出一致性——temperature=0 时多次执行应基本一致"""
        task = "北京今天的天气"
        results = [self.agent.execute(task, temperature=0).final_output 
                   for _ in range(5)]
        
        unique_outputs = set(results)
        assert len(unique_outputs) <= 2, \
            f"temperature=0 时输出应一致，但有 {len(unique_outputs)} 种"

"""
端到端测试数据集——分级设计
"""
E2E_TEST_DATASET = {
    "simple": [
        {
            "task": "北京今天天气怎么样？",
            "expected_phases": ["perceive", "planning", "executing", "memory"],
            "expected_tools": ["weather_query"],
            "max_steps": 3,
            "max_duration_ms": 5000,
        },
    ],
    "medium": [
        {
            "task": "帮我订明天上午去北京的机票",
            "expected_phases": ["perceive", "planning", "executing", "memory"],
            "expected_tools": ["weather_query", "search_flight", "book_ticket"],
            "max_steps": 8,
            "max_duration_ms": 15000,
        },
    ],
    "complex": [
        {
            "task": "如果明天下雨就改订后天，不下雨就订明天",
            "expected_phases": ["perceive", "planning", "executing", "memory"],
            "expected_tools": ["weather_query", "search_flight", "book_ticket"],
            "max_steps": 12,
            "max_duration_ms": 20000,
        },
    ],
    "exception": [
        {
            "task": "帮我飞到月球",
            "expected_status": "failed",
            "max_steps": 5,
        },
    ],
}

"""
用 pytest 组织端到端测试——标记和分组
"""
import pytest

@pytest.mark.e2e
@pytest.mark.simple
class TestSimpleE2E:
    """简单任务端到端测试组"""
    pass

@pytest.mark.e2e
@pytest.mark.medium
class TestMediumE2E:
    """中等任务端到端测试组"""
    pass

@pytest.mark.e2e
@pytest.mark.exception
class TestExceptionE2E:
    """异常场景端到端测试组"""
    pass

@pytest.mark.e2e
@pytest.mark.performance
class TestPerformanceE2E:
    """性能端到端测试组"""
    pass
