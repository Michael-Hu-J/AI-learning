# 测试环境不隔离，你的 Agent 评测一文不值


> **数据真实性声明**：本文中的所有评分、耗时、Token消耗等数据均来自真实 LLM 调用测试（通义千问 qwen-plus），使用本包中的 `run_full_eval.py` 脚本在 2026 年实际运行获得。数据可复现，欢迎读者自行验证。
> 

## 引子

去年跑一组对比评测，两个电商数据分析智能体用同一组测试用例。A 得分 85%，B 得分 65%。

看起来 A 明显更好。但查日志发现，A 跑的时候 search 命中了缓存，B 跑的时候缓存刚好失效，走了真实数据库查询。A 的平均响应时间 3 秒，B 是 12 秒。

这不是能力差异，是环境差异。

评测结果不可比，根源在于测试环境不隔离。环境变量不一致，跑出来的数据没有决策价值。

这篇文章讲三件事：环境怎么隔离、外部依赖怎么 Mock、智能体状态怎么重置。

## 环境隔离的三个层次

环境隔离不是"关掉重启"，是分三个层次控制变量。

### 第一层：进程隔离

每个智能体跑在独立进程中，不共享内存、不共享文件、不共享网络连接。

进程隔离的意义在于：
1. 防止状态污染：智能体 A 查询的华东区销售数据不会泄露到智能体 B
2. 防止资源竞争：两个智能体同时调用 search，不会因为并发导致数据库连接池耗尽
3. 防止副作用：智能体 A 生成的临时报告文件不会干扰智能体 B

实现方式很简单：每个智能体实例化时创建独立的对象，不共享全局状态。

```python
# 错误做法：共享全局状态
class GlobalState:
    memory = {}  # 所有智能体共享

# 正确做法：每个实例独立
class EcommerceAgent:
    def __init__(self):
        self.memory = {}  # 每个实例独立，存销售数据查询结果
        self.context_history = []
```

### 第二层：数据隔离

每个测试用例用独立的数据，不共享状态。

数据隔离的核心是：用例之间无依赖。用例 1 的执行结果不影响用例 2 的输入。

```python
# 错误做法：用例之间共享状态
agent = EcommerceAgent()
agent.run("查询上个月华东区销售额")  # memory 里存了华东区销售数据
agent.run("计算本月促销ROI")         # 任务 2 看到了任务 1 的 memory，结果串了

# 正确做法：每个用例前重置
for case in test_cases:
    agent = EcommerceAgent()  # 新实例
    agent.run(case.task)
```

或者用同一个实例，但每次运行前调用 `reset()`：

```python
agent = EcommerceAgent()
for case in test_cases:
    agent.reset()  # 清空 memory，不留上一次查询的客户数据
    agent.run(case.task)
```

### 第三层：网络隔离

外部依赖（`search` / `web_fetch`、LLM API 等）不依赖真实服务，用 Mock 替代。

网络隔离的意义在于：
1. 速度：Mock 响应是毫秒级，真实数据库查询是秒级
2. 稳定：Mock 不会超时、不会 500、不会限流
3. 可重复：Mock 返回固定响应，每次跑结果一致
4. 成本：Mock 不消耗 API 配额

## Mock 策略

Mock 不是"随便返回一个值"，需要覆盖三种场景：成功、失败、超时。

### 工具 Mock

工具 Mock 的核心是：模拟工具的正常执行和异常情况。与 `CustomAgent` 默认表一致时，**经营数据拉取与报告模板都走 `search`**（由 `tool_input` 区分语义），评测里重点 Mock 的也是它，外加 `web_fetch` / LLM 等外部依赖。

```python
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
```

使用方式：

```python
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
```

### LLM Mock

LLM Mock 不调用真实 LLM API，按 prompt 关键字返回预设内容。目的不是「假装模型很聪明」，而是让 **Agent 上层逻辑** 在测试里 **确定、可控、可复现**。

和工具 Mock 一样，测的是「规划 → 解析 → 调工具 → 反思」这条链路，不是测模型会不会写 SQL、会不会编报告。

#### 为什么要 Mock 大模型

真实 LLM 在自动化测试里有四个硬伤：

| 问题 | 真实 LLM | Mock LLM |
|------|----------|----------|
| 结果稳定性 | 同 prompt 多次调用可能不同 | 同一 pattern 永远返回同一 JSON |
| 速度与成本 | 秒级延迟 + 消耗 Token | 毫秒级、零费用 |
| 环境依赖 | 需要 API Key、外网、配额 | CI 无外网也能跑 |
| 异常复现 | 坏 JSON、空输出很难稳定触发 | `register` 一条即可注入 |

因此：**单元测试、集成测试、CI 冒烟、异常注入** 应 Mock；**Prompt 调优、模型效果评测、上线前验收** 必须用真实模型，Mock 没有意义。

#### 典型使用场景（结合 CustomAgent）

**1. 单元测试：验证「规划 / 工具选择」解析是否正确**

Agent 收到用户任务后，LLM 应输出结构化任务列表（含 `tool`、`tool_input`）。这里只关心 JSON 能否被正确解析、是否调用了 `search`，不关心模型是否真的理解「华东区」。

```python
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
```

**2. 集成测试：多轮「规划 → 执行 → 反思」状态机**

CustomAgent 在任务完成后会走反思（`status` / `reason` / `adjustments`）。用 Mock 固定每一步 LLM 说什么，才能断言 Agent 是否进入「完成」「重试」或「调整计划」分支。

```python
mock_llm.register("反思", '{"status": "done", "reason": "已完成", "adjustments": ""}')
# 或构造需要重试的路径：
mock_llm.register("反思", '{"status": "error", "reason": "数据缺失", "adjustments": "补查华东区数据"}')
```

**3. 异常与边界：Parser / Retry / Fallback 是否健壮**

真实模型很难稳定返回「非法 JSON」「空字符串」「幻觉工具名」。Mock 专门用来打这些边界：

```python
mock_llm.register("坏JSON", "{not valid json")
mock_llm.register("空响应", "")
mock_llm.register("未知工具", '[{"tool": "unknown_tool", "tool_input": "x"}]')
# 断言：解析失败是否重试、是否降级为 none、是否记录错误日志
```

**4. CI / 回归：无外网、秒级完成**

流水线里跑 `pytest tests/agent/`，不能依赖通义/OpenAI 配额。Mock 保证每次 MR 合并前，Agent 框架逻辑回归稳定通过。

**5. 调用次数与成本估算（不跑真模型）**

`MockLLM.call_count` 可统计一轮任务里 LLM 被调了几次（规划几次、反思几次），用于发现「重复规划」「反思死循环」等问题，无需真实 Token 账单。

**6. 前端 Demo / UI 开发：后端未就绪时先跑通界面**

Chat 界面、Copilot 侧边栏、管理台里的「智能分析」模块，往往在 Agent 后端或 LLM 网关还没接好时就要开工。用 Mock 固定对话与任务卡片展示，避免每次输入都等真实 API、也避免 Demo 时模型「发挥不稳定」。

```python
mock_llm.register("你好", '{"content": "你好，我是经营分析助手，可以查销售额或生成报告。"}')
mock_llm.register("总结", '[{"id": "task_1", "tool": "none", "tool_input": "华东区上月销售平稳，环比 +8%"}]')
# 前端只调统一 HTTP/WebSocket；后端暂挂 MockLLM，联调时再切真实 LLM
```

**7. 协议 / 契约测试：多模型切换时不改 Agent 代码**

通义、OpenAI、自研推理服务返回格式不一，但 Agent 只应依赖统一契约（例如 `call(prompt) -> {"content", "tokens"}`）。`MockLLM` 实现同一接口，用来验证：换模型适配层时，规划、反思、日志埋点等上层逻辑无需改动。

```python
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
```

#### 实现与接入

```python
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
```

接入示例（三条 `register` 分别对应：规划查数、规划出报告、反思完成）：

```python
mock_llm = MockLLM()
mock_llm.register("查询销售额", '[{"id": "task_1", "description": "查询华东区上月销售额", "depends_on": [], "tool": "search", "tool_input": "华东区_上月销售额"}]')
mock_llm.register("生成报告", '[{"id": "task_1", "description": "生成月度销售报告", "depends_on": [], "tool": "search", "tool_input": "月度销售报告"}]')
mock_llm.register("反思", '{"status": "done", "reason": "已完成", "adjustments": ""}')

# 在智能体中使用
agent = CustomAgent()
agent._call_llm = mock_llm.call  # 替换真实 LLM 调用（示意，接口以实际 Agent 为准）
```

与 `MockToolRegistry` 配合：LLM Mock 管「说什么、选什么工具」，Tool Mock 管「工具执行返回什么」。两层都固定后，整条 Agent 链路才可在本地重复跑通。

### 外部 API Mock

经营数据与报告在默认实现里均由 **`search`** 的 `tool_input` 语义区分；外部依赖用 Mock 替代真实调用。

```python
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
```

## 环境隔离框架

把上面的组件组合起来，形成一个完整的环境隔离框架。

```python
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
```

## 数据：环境隔离前后对比

| 场景 | 隔离前 | 隔离后 | 差异 |
|------|--------|--------|------|
| 同一智能体跑 3 次 | 得分波动大 | 得分稳定 | 波动显著降低 |
| Mock search vs 真实数据库 | 秒级响应 | 毫秒级响应 | 速度提升两个数量级 |
| 用例间状态污染 | 用例之间互相影响（上一个查询的客户数据残留到下一个用例） | 用例间完全隔离 | 消除污染 |
| 网络波动影响 | 数据库超时导致失败 | Mock 无超时 | 消除网络影响 |

环境隔离后的核心收益：评测结果可重复。同一智能体跑 3 次，得分波动从明显可见降到几乎不可见。

## 交付物

### 1. 状态重置清单

每次测试前需重置的 8 项内容：

| # | 重置项 | 说明 | 重置方式 |
|---|--------|------|---------|
| 1 | 记忆（memory） | 智能体的 key-value 存储，存销售数据查询结果 | `agent.state.memory = {}` |
| 2 | 对话历史（context_history） | 多轮对话记录 | `agent._context_history = []` |
| 3 | 反思日志（reflection_log） | 反思阶段的记录 | `agent.state.reflection_log = []` |
| 4 | Token 计数器（total_tokens） | 累计 Token 消耗 | `agent.state.total_tokens = 0` |
| 5 | LLM 调用计数器（total_llm_calls） | 累计 LLM 调用次数 | `agent.state.total_llm_calls = 0` |
| 6 | 子任务结果（subtask_results） | 已执行的子任务结果 | `agent.state.subtask_results = {}` |
| 7 | 规划（plan） | 当前任务的规划 | `agent.state.plan = None` |
| 8 | 临时文件 | 测试过程中创建的临时文件 | 删除临时目录 |

> 重点提醒：memory 里存的是销售数据查询结果（比如华东区销售额、促销 ROI），重置时必须清空，不能残留上一次查询的客户数据。否则下一个用例会读到上一个用例的数据，结果直接串了。

### 2. Mock 工具模板

| 工具 | Mock 成功响应 | Mock 失败响应 | Mock 超时响应 |
|------|-------------|-------------|-------------|
| search | 经营类：`[search/经营数据]…`；报告类：`[search/报告]…` | `[错误] 数据库连接失败`（示例） | `[错误] 工具执行超时` |
| calculator | `[计算结果] 表达式 = 结果` | `[错误] 计算失败` | `[错误] 工具执行超时` |
| code_executor | `[代码执行结果]\n输出` | `[错误] 代码执行失败` | `[错误] 代码执行超时` |
| memory_store | `[记忆存储] 已保存: key = value` | `[记忆读取] 未找到: key` | `[错误] 工具执行超时` |
| web_fetch | `[网页内容] URL\n文本` | `[错误] 网页获取失败` | `[错误] 请求超时` |
| safety_checker | `[安全检测] 输入安全` | `[安全检测] 检测到威胁` | `[错误] 工具执行超时` |

### 3. 环境隔离检查清单

| # | 检查项 | 标准 |
|---|--------|------|
| 1 | 每个智能体实例独立 | 不共享全局状态 |
| 2 | 每个用例前重置状态 | 调用 reset() |
| 3 | 外部依赖 Mock | 不依赖真实 API |
| 4 | 临时目录隔离 | 每个测试用例独立临时目录 |
| 5 | 环境变量清理 | 测试后清理测试设置的环境变量 |
| 6 | 网络连接关闭 | 测试后关闭所有网络连接 |
| 7 | 日志文件隔离 | 每个测试用例独立日志文件 |
| 8 | 时间戳记录 | 记录测试开始和结束时间 |

## 总结

测试环境不隔离，评测结果不可比。隔离分三个层次：进程隔离、数据隔离、网络隔离。

Mock 是网络隔离的核心。与默认表一致时，**`search`（经营/报告双场景）**、`web_fetch`、LLM 调用等最易引入外部不确定性的环节应优先 Mock，覆盖成功、失败、超时三种场景。

状态重置是数据隔离的核心。每次测试前重置 8 项内容，memory 里不能残留上一次查询的客户数据，避免用例之间状态互相污染。

下一篇讲可测性设计。不可测的系统无法自动化，智能体需要主动暴露内部状态。


---

## 面试题模块

### Q1：测试环境隔离的三个层次是什么？

A：1) 数据隔离——每个测试用例使用独立的数据（唯一用户名、商品ID等）；2) 状态隔离——测试开始前重置 Agent 状态（清空对话历史、重置工具调用计数）；3) 环境隔离——使用 Mock 外部服务（把真实 API 替换为固定响应），避免外部依赖影响测试结果。

### Q2：Mock 服务在智能体测试中的作用是什么？

A：Mock 服务让测试可复现。真实 API 可能因为网络、限流、数据变化等原因不稳定，Mock 保证每次运行的响应一致。这样 Agent 的决策路径是可控的——失败时能确定是 Agent 的逻辑问题，而不是外部服务的问题。

### Q3：测试环境的"状态重置"为什么对智能体测试特别重要？

A：智能体有上下文记忆。如果前一个测试的对话历史没有清空，会影响下一个测试的结果。比如上一个测试让 Agent "记住用户叫张三"，下一个测试查询"用户叫什么"——Agent 会回答"张三"而不是"不知道"。这就是状态污染。
