# 错误做法：共享全局状态
class GlobalState:
    memory = {}  # 所有智能体共享

# 正确做法：每个实例独立
class EcommerceAgent:
    def __init__(self):
        self.memory = {}  # 每个实例独立，存销售数据查询结果
        self.context_history = []

# 错误做法：用例之间共享状态
agent = EcommerceAgent()
agent.run("查询上个月华东区销售额")  # memory 里存了华东区销售数据
agent.run("计算本月促销ROI")         # 任务 2 看到了任务 1 的 memory，结果串了

# 正确做法：每个用例前重置
for case in test_cases:
    agent = EcommerceAgent()  # 新实例
    agent.run(case.task)

agent = EcommerceAgent()
for case in test_cases:
    agent.reset()  # 清空 memory，不留上一次查询的客户数据
    agent.run(case.task)

class MockToolRegistry:
    """Mock 工具注册中心（工具名与 ToolRegistry.TOOLS 统一）"""

    # 预设响应：search 合并「查数」与「生成报告」两类子键
    MOCK_RESPONSES = {
        "search": {
            "default": "[search] 查询完成，返回占位结果",
            "华东区_上月销售额": "[search/经营数据] 华东区上月销售额：¥2,450,000，共 1,280 笔订单",
            "本月促销ROI": "[search/经营数据] 本月促销活动：投入 ¥120,000，带来额外销售额 ¥380,000，ROI = 2.17",
            "异常订单": "[search/经营数据] 发现 3 笔异常订单：订单号 #20240315-001、#20240315-002、#20240315-003，金额均超过 ¥50,000",
            "月度销售报告": "[search/报告] 月度销售报告已生成，包含：销售趋势、品类分析、区域对比、TOP10 商品",
            "促销评估报告": "[search/报告] 促销评估报告已生成，包含：活动效果、ROI 分析、用户反馈汇总",
        },
        "calculator": {
            "default": "[计算结果] 表达式 = 结果",
            "2 + 3": "[计算结果] 2 + 3 = 5",
            "25 * 4": "[计算结果] 25 * 4 = 100",
        },
        "code_executor": {
            "default": "[代码执行结果]\n输出内容",
            "print(1+1)": "[代码执行结果]\n2",
            "print('hello')": "[代码执行结果]\nhello",
        },
        "memory_store": {
            "default": "[记忆存储] 已保存",
        },
        "web_fetch": {
            "default": "[网页内容] https://example.com\n页面文本",
        },
        "safety_checker": {
            "default": "[安全检测] 输入安全，未发现威胁。",
        },
    }

    # 异常配置
    MOCK_ERRORS = {
        "timeout": "[错误] 工具执行超时（10秒限制）",
        "not_found": "[错误] 工具不存在",
        "invalid_params": "[错误] 参数格式错误",
        "db_connection_failed": "[错误] 数据库连接失败，请检查网络配置",
        "report_template_missing": "[错误] 报告模板缺失，无法生成报告",
    }

    @classmethod
    def execute(cls, tool_name: str, tool_input: str, state,
                force_error: str = None) -> str:
        """
        执行 Mock 工具

        Args:
            tool_name: 工具名
            tool_input: 工具参数
            state: 智能体状态
            force_error: 强制错误类型（timeout/not_found/invalid_params/db_connection_failed/report_template_missing）

        Returns:
            工具执行结果
        """
        if force_error and force_error in cls.MOCK_ERRORS:
            return cls.MOCK_ERRORS[force_error]

        tool_responses = cls.MOCK_RESPONSES.get(tool_name, {})
        return tool_responses.get(tool_input, tool_responses.get("default", ""))

# 正常执行 — 查询销售数据
result = MockToolRegistry.execute("search", "华东区_上月销售额", state)
# 返回: "[销售数据查询] 华东区上月销售额：¥2,450,000，共 1,280 笔订单"

# 正常执行 — 生成月度报告
result = MockToolRegistry.execute("search", "月度销售报告", state)
# 返回: "[报告生成] 月度销售报告已生成，包含：销售趋势、品类分析、区域对比、TOP10 商品"

# 模拟数据库连接失败
result = MockToolRegistry.execute("search", "华东区_上月销售额", state, force_error="db_connection_failed")
# 返回: "[错误] 数据库连接失败，请检查网络配置"

# 模拟报告模板缺失
result = MockToolRegistry.execute("search", "促销评估报告", state, force_error="report_template_missing")
# 返回: "[错误] 报告模板缺失，无法生成报告"

# 模拟超时
result = MockToolRegistry.execute("search", "异常订单", state, force_error="timeout")
# 返回: "[错误] 工具执行超时（10秒限制）"

def test_agent_picks_search_for_sales_query():
    mock_llm = MockLLM()
    mock_llm.register(
        "查询销售额",
        '[{"id": "task_1", "description": "查询华东区上月销售额", '
        '"depends_on": [], "tool": "search", "tool_input": "华东区_上月销售额"}]',
    )
    agent = CustomAgent()
    agent._call_llm = mock_llm.call
    plan = agent.plan("查询销售额")
    assert plan[0]["tool"] == "search"
    assert "华东区" in plan[0]["tool_input"]

mock_llm.register("反思", '{"status": "done", "reason": "已完成", "adjustments": ""}')
# 或构造需要重试的路径：
mock_llm.register("反思", '{"status": "error", "reason": "数据缺失", "adjustments": "补查华东区数据"}')

mock_llm.register("坏JSON", "{not valid json")
mock_llm.register("空响应", "")
mock_llm.register("未知工具", '[{"tool": "unknown_tool", "tool_input": "x"}]')
# 断言：解析失败是否重试、是否降级为 none、是否记录错误日志

mock_llm.register("你好", '{"content": "你好，我是经营分析助手，可以查销售额或生成报告。"}')
mock_llm.register("总结", '[{"id": "task_1", "tool": "none", "tool_input": "华东区上月销售平稳，环比 +8%"}]')
# 前端只调统一 HTTP/WebSocket；后端暂挂 MockLLM，联调时再切真实 LLM

from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def call(self, prompt: str) -> dict: ...

class MockLLM(BaseLLM):  # 测试与契约实现
    ...

class QwenAdapter(BaseLLM):  # 生产实现
    ...

# 测试里注入 Mock；上线注入 Adapter，Agent 构造参数不变
agent = CustomAgent(llm=MockLLM())

class MockLLM:
    """Mock LLM，返回预设响应"""

    def __init__(self):
        self.responses = {}
        self.call_count = 0

    def register(self, prompt_pattern: str, response: str):
        """注册预设响应"""
        self.responses[prompt_pattern] = response

    def call(self, prompt: str) -> dict:
        """
        模拟 LLM 调用

        Returns:
            {"content": str, "tokens": int}
        """
        self.call_count += 1

        # 查找匹配的预设响应
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return {"content": response, "tokens": len(response) // 4}

        # 默认响应
        return {
            "content": '[{"id": "task_1", "description": "默认任务", "depends_on": [], "tool": "none", "tool_input": "直接回答"}]',
            "tokens": 50,
        }

mock_llm = MockLLM()
mock_llm.register("查询销售额", '[{"id": "task_1", "description": "查询华东区上月销售额", "depends_on": [], "tool": "search", "tool_input": "华东区_上月销售额"}]')
mock_llm.register("生成报告", '[{"id": "task_1", "description": "生成月度销售报告", "depends_on": [], "tool": "search", "tool_input": "月度销售报告"}]')
mock_llm.register("反思", '{"status": "done", "reason": "已完成", "adjustments": ""}')

# 在智能体中使用
agent = CustomAgent()
agent._call_llm = mock_llm.call  # 替换真实 LLM 调用（示意，接口以实际 Agent 为准）

import unittest.mock as mock

def mock_search(tool_input: str) -> str:
    """与 ToolRegistry 统一：search 同时覆盖「查数」与「报告」示例。"""
    if "华东区" in tool_input and "销售额" in tool_input:
        return "华东区上月销售额：¥2,450,000，共 1,280 笔订单"
    if "促销" in tool_input:
        return "本月促销活动：投入 ¥120,000，带来额外销售额 ¥380,000"
    if "timeout" in tool_input:
        raise TimeoutError("search 查询超时")
    if tool_input == "月度销售报告":
        return "月度销售报告已生成，包含：销售趋势、品类分析、区域对比、TOP10 商品"
    if tool_input == "促销评估报告":
        return "促销评估报告已生成，包含：活动效果、ROI 分析、用户反馈汇总"
    raise ConnectionError("search 执行失败（连接/参数）")

with mock.patch(
    "agents.custom_agent.agent.ToolRegistry.execute",
    side_effect=lambda name, inp, state: mock_search(inp) if name == "search" else "",
):
    from agents.custom_agent.agent import ToolRegistry
    r1 = ToolRegistry.execute("search", "华东区_上月销售额", state=None)
    r2 = ToolRegistry.execute("search", "月度销售报告", state=None)

#!/usr/bin/env python3
"""
测试环境管理器

功能：
1. 环境初始化（隔离、Mock）
2. 状态重置
3. 状态快照/恢复
4. 环境清理
"""

import os
import tempfile
import shutil
import json
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class StateSnapshot:
    """状态快照"""
    memory: Dict[str, str] = field(default_factory=dict)
    context_history: List[Dict] = field(default_factory=list)
    reflection_log: List[str] = field(default_factory=list)
    total_tokens: int = 0
    total_llm_calls: int = 0
    timestamp: float = 0.0


class TestEnvironment:
    """测试环境管理器"""

    def __init__(self, agent_class, **agent_kwargs):
        """
        Args:
            agent_class: 智能体类
            **agent_kwargs: 智能体初始化参数
        """
        self.agent_class = agent_class
        self.agent_kwargs = agent_kwargs
        self.agent = None
        self.temp_dir = None
        self.snapshot = None

    def setup(self):
        """初始化测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="agent_test_")

        # 创建智能体实例
        self.agent = self.agent_class(**self.agent_kwargs)

        # 设置临时目录为工作目录（可选）
        os.environ["AGENT_TEST_DIR"] = self.temp_dir

    def teardown(self):
        """清理测试环境"""
        # 重置智能体
        if self.agent:
            self.agent.reset()

        # 删除临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # 清理环境变量
        os.environ.pop("AGENT_TEST_DIR", None)

    def reset_agent(self):
        """重置智能体状态"""
        if self.agent:
            self.agent.reset()
            # 额外清理
            if hasattr(self.agent, '_context_history'):
                self.agent._context_history = []
            if hasattr(self.agent, 'state'):
                self.agent.state = None

    def snapshot_state(self) -> StateSnapshot:
        """
        保存智能体状态快照

        Returns:
            状态快照
        """
        if not self.agent:
            return StateSnapshot()

        return StateSnapshot(
            memory=getattr(self.agent, 'state', None).memory.copy() if hasattr(self.agent, 'state') and self.agent.state else {},
            context_history=getattr(self.agent, '_context_history', []).copy(),
            reflection_log=getattr(self.agent, 'state', None).reflection_log.copy() if hasattr(self.agent, 'state') and self.agent.state else [],
            total_tokens=getattr(self.agent, 'state', None).total_tokens if hasattr(self.agent, 'state') and self.agent.state else 0,
            total_llm_calls=getattr(self.agent, 'state', None).total_llm_calls if hasattr(self.agent, 'state') and self.agent.state else 0,
            timestamp=time.time(),
        )

    def restore_state(self, snapshot: StateSnapshot):
        """
        恢复智能体状态

        Args:
            snapshot: 状态快照
        """
        if not self.agent:
            return

        if hasattr(self.agent, 'state') and self.agent.state:
            self.agent.state.memory = snapshot.memory.copy()
            self.agent.state.reflection_log = snapshot.reflection_log.copy()
            self.agent.state.total_tokens = snapshot.total_tokens
            self.agent.state.total_llm_calls = snapshot.total_llm_calls

        if hasattr(self.agent, '_context_history'):
            self.agent._context_history = snapshot.context_history.copy()

    def run_task(self, task: str, context: List[Dict] = None) -> Dict:
        """
        执行任务（带环境隔离）

        Args:
            task: 任务描述
            context: 对话历史

        Returns:
            执行结果
        """
        if not self.agent:
            self.setup()

        # 执行前重置
        self.reset_agent()

        # 执行任务
        result = self.agent.run(task, context)

        return result

    def save_snapshot_to_file(self, path: str):
        """保存快照到文件"""
        snapshot = self.snapshot_state()
        data = {
            "memory": snapshot.memory,
            "context_history": snapshot.context_history,
            "reflection_log": snapshot.reflection_log,
            "total_tokens": snapshot.total_tokens,
            "total_llm_calls": snapshot.total_llm_calls,
            "timestamp": snapshot.timestamp,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_snapshot_from_file(self, path: str) -> StateSnapshot:
        """从文件加载快照"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StateSnapshot(
            memory=data.get("memory", {}),
            context_history=data.get("context_history", []),
            reflection_log=data.get("reflection_log", []),
            total_tokens=data.get("total_tokens", 0),
            total_llm_calls=data.get("total_llm_calls", 0),
            timestamp=data.get("timestamp", 0),
        )


def run_demo():
    """演示"""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.custom_agent.agent import CustomAgent

    print("=" * 60)
    print("CustomAgent — 测试环境管理演示（与 agents/custom_agent 配套）")
    print("=" * 60)

    # 创建环境（需 DASHSCOPE_API_KEY 等环境变量时与仓库 README 一致）
    env = TestEnvironment(CustomAgent, temperature=0.3, max_context_turns=5)

    # 初始化
    env.setup()
    print(f" 环境初始化完成")
    print(f"   临时目录: {env.temp_dir}")

    # 执行任务 — 查询销售数据
    result = env.run_task("查询上个月华东区销售额")
    print(f" 任务执行完成")
    print(f"   成功: {result['success']}")

    # 保存快照
    snapshot = env.snapshot_state()
    print(f" 状态快照保存")
    print(f"   记忆: {snapshot.memory}")
    print(f"   Token: {snapshot.total_tokens}")

    # 重置 — 清空 memory，不留上一次查询的客户数据
    env.reset_agent()
    print(f" 智能体已重置")
    print(f"   memory 已清空，不会残留华东区销售数据")

    # 恢复快照
    env.restore_state(snapshot)
    print(f" 状态已恢复")
    # 注意：本仓库 CustomAgent 的 AgentState 在 run() 内为局部变量，默认不挂在 self.state；
    # 若需快照/恢复，请在智能体实现里把运行态赋给 self.state，或改为基于最近一次 run 的 _meta 做持久化。
    _st = getattr(env.agent, "state", None)
    if _st is not None:
        print(f"   记忆: {_st.memory}")
    else:
        print("   记忆: (未绑定 self.state，见上文说明)")

    # 清理
    env.teardown()
    print(f" 环境已清理")
    print(f"   临时目录已删除: {not os.path.exists(env.temp_dir)}")

    print("=" * 60)


if __name__ == "__main__":
    run_demo()
