# config.py
import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "model": "qwen-plus",
    "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}

# 记忆配置
MEMORY_CONFIG = {
    "short_term": {
        "enabled": True,
        "storage": {
            "type": "chroma",
            "path": "./memory_data/short_term",
        },
    },
    "long_term": {
        "enabled": True,
        "storage": {
            "type": "json",
            "path": "./memory_data/long_term.json",
        },
    },
    "context_window": {
        "max_tokens": 4000,
        "priority": "recent_first",  # 优先保留最近的记忆
    },
}

# memory_manager.py
from crewai.tools import BaseTool
from typing import Optional, Dict, Any, List
import json
import os
from datetime import datetime


class MemoryStoreTool(BaseTool):
    """记忆存储工具：将重要信息存入长期记忆"""

    name: str = "memory_store"
    description: str = (
        "将重要信息存储到长期记忆中。"
        "参数：category（分类）、key（键名）、"
        "value（值）、metadata（元数据）"
    )

    def _run(
        self,
        category: str,
        key: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        memory_file = "./memory_data/long_term.json"
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)

        # 读取现有记忆
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                try:
                    memories = json.load(f)
                except json.JSONDecodeError:
                    memories = []
        else:
            memories = []

        # 添加新记忆
        memory_entry = {
            "category": category,
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "id": f"{category}_{key}_{len(memories)}",
        }
        memories.append(memory_entry)

        # 保存
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": f"记忆已存储：{category}/{key}",
            "total_memories": len(memories),
        }


class MemoryRetrieveTool(BaseTool):
    """记忆检索工具：从长期记忆中检索相关信息"""

    name: str = "memory_retrieve"
    description: str = (
        "从长期记忆中检索相关信息。"
        "参数：category（分类，可选）、keyword（关键词）"
    )

    def _run(
        self,
        keyword: str,
        category: Optional[str] = None,
    ) -> str:
        memory_file = "./memory_data/long_term.json"

        if not os.path.exists(memory_file):
            return json.dumps({"results": [], "message": "暂无记忆数据"})

        with open(memory_file, "r", encoding="utf-8") as f:
            try:
                memories = json.load(f)
            except json.JSONDecodeError:
                return json.dumps({"results": [], "message": "记忆文件损坏"})

        # 过滤记忆
        results = []
        keyword_lower = keyword.lower()

        for memory in memories:
            # 按分类过滤
            if category and memory.get("category") != category:
                continue

            # 关键词匹配
            searchable = (
                memory.get("value", "") + " " +
                memory.get("key", "") + " " +
                memory.get("category", "")
            ).lower()

            if keyword_lower in searchable:
                results.append(memory)

        # 按时间倒序排列（最近的在前）
        results.sort(
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )

        return json.dumps(results, ensure_ascii=False, indent=2)


class ContextWindowManagerTool(BaseTool):
    """上下文窗口管理工具：控制输入到 LLM 的上下文大小"""

    name: str = "context_manager"
    description: str = (
        "管理上下文窗口，保证输入不超过 LLM 的上下文限制。"
        "参数：context_items（上下文列表）、max_tokens（最大 Token 数）"
    )

    def _estimate_tokens(self, text: str) -> int:
        """粗略估算文本的 Token 数量"""
        # 中文：约 1.5 个字符 per token
        # 英文：约 4 个字符 per token
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def _run(
        self,
        context_items: str,
        max_tokens: int = 4000,
    ) -> str:
        try:
            items = json.loads(context_items) if isinstance(context_items, str) else context_items
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "上下文格式无效", "kept_items": []})

        kept_items = []
        total_tokens = 0

        # 按优先级保留上下文（最近的优先）
        for item in reversed(items):
            item_text = json.dumps(item, ensure_ascii=False)
            item_tokens = self._estimate_tokens(item_text)

            if total_tokens + item_tokens <= max_tokens:
                kept_items.insert(0, item)
                total_tokens += item_tokens
            else:
                # 尝试截断
                remaining = max_tokens - total_tokens
                if remaining > 100:
                    truncated = item_text[: int(remaining * 3)]
                    kept_items.insert(0, {
                        **item,
                        "content": truncated + "...（已截断）",
                    })
                    total_tokens += remaining

        return json.dumps({
            "kept_items": kept_items,
            "total_tokens": total_tokens,
            "max_tokens": max_tokens,
            "discarded_count": len(items) - len(kept_items),
        }, ensure_ascii=False, indent=2)


class BugHistoryTool(BaseTool):
    """Bug 历史查询工具：查询历史 Bug 记录"""

    name: str = "bug_history"
    description: str = (
        "查询历史 Bug 记录。"
        "参数：module（模块名）、severity（严重程度）、limit（返回数量）"
    )

    def _run(
        self,
        module: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        memory_file = "./memory_data/long_term.json"

        if not os.path.exists(memory_file):
            return json.dumps({"bugs": [], "message": "暂无 Bug 记录"})

        with open(memory_file, "r", encoding="utf-8") as f:
            try:
                memories = json.load(f)
            except json.JSONDecodeError:
                return json.dumps({"bugs": [], "message": "记忆文件损坏"})

        # 筛选 Bug 记录
        bugs = [
            m for m in memories
            if m.get("category") == "bug"
        ]

        # 按模块过滤
        if module:
            bugs = [
                b for b in bugs
                if module.lower() in b.get("value", "").lower()
                or module.lower() in b.get("key", "").lower()
            ]

        # 按严重程度过滤
        if severity:
            bugs = [
                b for b in bugs
                if severity.lower() in b.get("metadata", {}).get("severity", "").lower()
            ]

        # 按时间倒序
        bugs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 限制数量
        bugs = bugs[:limit]

        return json.dumps(bugs, ensure_ascii=False, indent=2)

# agents.py
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from memory_manager import (
    MemoryStoreTool,
    MemoryRetrieveTool,
    ContextWindowManagerTool,
    BugHistoryTool,
)
from config import LLM_CONFIG


def _create_llm():
    return LLM(
        model=LLM_CONFIG["model"],
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
    )


def create_memory_enabled_analyst() -> Agent:
    """带记忆功能的 Bug 分析 Agent"""
    return Agent(
        role="Bug 分析专家",
        goal="分析测试结果，识别 Bug 根因，生成改进建议",
        backstory="""你是拥有 12 年经验的测试分析专家，擅长 Bug 根因分析。
你有一个好习惯：每次分析完 Bug 后，会把关键信息记录下来。
下次遇到类似的问题时，你会先查阅历史记录，看看之前是怎么分析的。
你的工作原则是：不重复造轮子，充分利用历史经验。
你相信积累的力量，每一次记录都是为未来的分析做准备。""",
        llm=_create_llm(),
        verbose=True,
        allow_delegation=False,
        memory=True,
        tools=[
            MemoryStoreTool(),
            MemoryRetrieveTool(),
            BugHistoryTool(),
        ],
    )


def create_context_aware_executor() -> Agent:
    """上下文感知测试执行 Agent"""
    return Agent(
        role="测试执行工程师",
        goal="执行测试用例，结合历史测试结果做出判断",
        backstory="""你是经验丰富的测试执行工程师。
你执行测试时不只是机械地跑用例，还会参考历史测试结果。
如果某个接口上次测试时就慢，这次还是慢，你会标记为性能问题。
如果某个接口上次通过了，这次失败了，你会重点分析变化点。
你的工作风格是：对比分析，找出差异。""",
        llm=_create_llm(),
        verbose=True,
        allow_delegation=False,
        memory=True,
        tools=[
            MemoryRetrieveTool(),
            ContextWindowManagerTool(),
        ],
    )

# main.py
from crewai import Task, Crew
from agents import create_memory_enabled_analyst, create_context_aware_executor
import json


def demo_short_term_memory():
    """演示短期记忆：跨 Task 共享上下文"""
    print("=" * 60)
    print("演示 1：短期记忆（跨 Task 上下文共享）")
    print("=" * 60)

    analyst = create_memory_enabled_analyst()

    # Task 1：分析登录接口
    task1 = Task(
        description="""
请分析以下登录接口的测试结果：

接口地址：/api/auth/login
请求方法：POST
测试结果：
- 正常登录：通过，响应时间 120ms
- 密码错误：通过，返回 401
- 用户名不存在：通过，返回 401
- 空密码：失败，返回 500
- SQL 注入测试：失败，返回 500

请分析失败的原因。
""",
        expected_output="登录接口测试结果分析",
        agent=analyst,
    )

    # Task 2：基于 Task 1 的分析生成改进建议
    task2 = Task(
        description="""
基于之前的分析结果，为登录接口生成改进建议。

要求：
1. 针对每个失败用例提出具体的修复建议
2. 按优先级排序
3. 给出修复后的验证方法
""",
        expected_output="改进建议列表",
        agent=analyst,
        context=[task1],  # 依赖 task1 的输出
    )

    crew = Crew(
        agents=[analyst],
        tasks=[task1, task2],
        memory=True,
        verbose=True,
    )

    result = crew.kickoff()
    print(f"\n最终结果：{result}\n")


def demo_long_term_memory():
    """演示长期记忆：跨会话保留经验"""
    print("=" * 60)
    print("演示 2：长期记忆（存储和检索历史经验）")
    print("=" * 60)

    analyst = create_memory_enabled_analyst()

    # Task：分析 Bug 并存入长期记忆
    task = Task(
        description="""
请分析以下测试结果，将发现的 Bug 存入长期记忆。

测试场景：秒杀系统库存管理
测试结果：
- 正常下单：通过
- 并发下单（100 并发）：失败，出现超卖
- 库存为 0 时下单：失败，仍然生成了订单
- 重复点击下单按钮：失败，生成了重复订单

请将每个 Bug 用 memory_store 工具存储，分类为 "bug"。
""",
        expected_output="Bug 分析报告（已存入长期记忆）",
        agent=analyst,
    )

    crew = Crew(
        agents=[analyst],
        tasks=[task],
        memory=True,
        verbose=True,
    )

    result = crew.kickoff()
    print(f"\n最终结果：{result}\n")


def demo_context_management():
    """演示上下文窗口管理"""
    print("=" * 60)
    print("演示 3：上下文窗口管理")
    print("=" * 60)

    executor = create_context_aware_executor()

    # 模拟大量的历史测试结果
    history_results = [
        {
            "test_id": f"TC_{i:03d}",
            "result": "pass" if i % 5 != 0 else "fail",
            "response_time": 100 + i * 10,
            "timestamp": f"2026-01-{(i % 28) + 1:02d}",
        }
        for i in range(1, 51)
    ]

    task = Task(
        description=f"""
以下是 50 条历史测试结果，请分析趋势并给出建议。

历史结果（JSON）：
{json.dumps(history_results, ensure_ascii=False, indent=2)}

请分析：
1. 失败用例的共同特征
2. 响应时间的变化趋势
3. 是否需要关注某些接口
""",
        expected_output="趋势分析报告",
        agent=executor,
    )

    crew = Crew(
        agents=[executor],
        tasks=[task],
        memory=True,
        verbose=True,
    )

    result = crew.kickoff()
    print(f"\n最终结果：{result}\n")


def demo_bug_history_query():
    """演示 Bug 历史查询"""
    print("=" * 60)
    print("演示 4：Bug 历史查询与复用")
    print("=" * 60)

    analyst = create_memory_enabled_analyst()

    task = Task(
        description="""
请先用 bug_history 工具查询"秒杀"相关的历史 Bug 记录。
然后分析以下新的测试结果，对比历史 Bug，判断是否是已知问题。

新测试结果：
- 秒杀接口高并发下返回 500
- 库存扣减后数值不正确
- 订单生成重复

请判断这些问题是否在历史记录中出现过，如果是，引用之前的分析。
""",
        expected_output="Bug 对比分析报告",
        agent=analyst,
    )

    crew = Crew(
        agents=[analyst],
        tasks=[task],
        memory=True,
        verbose=True,
    )

    result = crew.kickoff()
    print(f"\n最终结果：{result}\n")


if __name__ == "__main__":
    demo_short_term_memory()
    demo_long_term_memory()
    demo_context_management()
    demo_bug_history_query()

def filter_context_by_priority(memories, max_tokens=4000):
    """
    按优先级和时效性过滤上下文

    Args:
        memories: 记忆列表
        max_tokens: 最大 Token 数

    Returns:
        过滤后的记忆列表
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    scored = []

    for mem in memories:
        # 基础优先级分数
        priority_scores = {"P0": 100, "P1": 50, "P2": 10}
        base_score = priority_scores.get(
            mem.get("metadata", {}).get("priority", "P2"), 10
        )

        # 时间衰减
        created = datetime.fromisoformat(mem.get("created_at", now.isoformat()))
        days_ago = (now - created).days
        time_weight = max(0.3, 1.0 - days_ago * 0.1)

        # 综合分数
        total_score = base_score * time_weight
        scored.append((mem, total_score))

    # 按分数降序排列
    scored.sort(key=lambda x: x[1], reverse=True)

    # 按 Token 限制截取
    result = []
    total_tokens = 0
    for mem, _ in scored:
        mem_tokens = estimate_tokens(json.dumps(mem))
        if total_tokens + mem_tokens <= max_tokens:
            result.append(mem)
            total_tokens += mem_tokens

    return result

def test_memory_functions():
    """测试记忆功能的正确性"""

    # 测试 1：存储和检索
    store_tool = MemoryStoreTool()
    retrieve_tool = MemoryRetrieveTool()

    # 存储一条记忆
    result = store_tool._run(
        category="bug",
        key="login_500_error",
        value="登录接口在空密码时返回 500",
        metadata={"severity": "P1", "module": "auth"},
    )
    assert result["success"] is True

    # 检索这条记忆
    result = retrieve_tool._run(keyword="登录", category="bug")
    memories = json.loads(result)
    assert len(memories) >= 1
    assert "登录" in memories[0]["value"]

    print("测试通过：存储和检索功能正常")


def test_context_window_limit():
    """测试上下文窗口限制"""
    manager = ContextWindowManagerTool()

    # 生成大量上下文
    items = [{"content": f"测试数据{i}" * 100} for i in range(100)]

    result = json.loads(manager._run(
        context_items=json.dumps(items),
        max_tokens=1000,
    ))

    # 验证截断后的 Token 数不超过限制
    assert result["total_tokens"] <= 1000
    assert result["discarded_count"] > 0  # 应该有被丢弃的内容

    print("测试通过：上下文窗口限制生效")

def test_memory_consistency():
    """验证记忆的一致性"""
    store_tool = MemoryStoreTool()
    retrieve_tool = MemoryRetrieveTool()

    # 存储 10 条不同类别的记忆
    categories = ["bug", "test_result", "config", "decision"]
    for i, cat in enumerate(categories * 3):
        store_tool._run(
            category=cat,
            key=f"test_key_{i}",
            value=f"测试值_{i}",
        )

    # 检索每个类别的记忆
    for cat in set(categories):
        result = retrieve_tool._run(keyword="测试", category=cat)
        memories = json.loads(result)
        for mem in memories:
            assert mem["category"] == cat

    print("测试通过：记忆分类一致性正常")

# # 不好的做法：只设置 memory=True
# agent = Agent(role="分析师", goal="分析 Bug", memory=True)
# 
# # 好的做法：提供记忆工具 + 在 Task 中明确指示
# agent = Agent(
#     role="分析师",
#     goal="分析 Bug",
#     memory=True,
#     tools=[MemoryStoreTool(), MemoryRetrieveTool()],
# )
# 
# task = Task(
#     description="""
# 请先用 memory_retrieve 工具查询历史 Bug 记录。
# 然后分析当前测试结果，对比历史记录。
# 最后用 memory_store 工具将新的发现存入记忆。
# """, pass  # 省略参数
# 

def cleanup_old_memories(memory_file, days=30):
    """清理过期记忆"""
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days)

    with open(memory_file, "r", encoding="utf-8") as f:
        memories = json.load(f)

    # 保留最近 N 天的记忆
    active = [
        m for m in memories
        if datetime.fromisoformat(m["created_at"]) >= cutoff
    ]

    # 去重：同一 key 只保留最新的
    seen_keys = set()
    deduped = []
    for m in reversed(active):
        key = f"{m['category']}_{m['key']}"
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(m)

    with open(memory_file, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"清理完成：保留 {len(deduped)} 条，清理 {len(memories) - len(deduped)} 条")

# 不可靠：依赖自动检索
task2 = Task(description="分析登录接口 Bug", agent=analyst)

# 可靠：明确指定上下文
task1 = Task(description="分析登录接口", agent=analyst)
task2 = Task(
    description="基于以下分析结果生成改进建议：{task1_output}",
    agent=analyst,
    context=[task1],  # 明确指定依赖
)
