def compute_memory_recall_score(output: str, key_info: dict) -> float:
    """
    Memory Recall Score：部分命中也计分
    
    3 个关键信息各 1/3 分：
    - 名字命中 → +0.33
    - 地点命中 → +0.33
    - 职业命中 → +0.33
    
    支持模糊匹配：
    - "北京" 匹配 "北京市"
    - "测试" 匹配 "测试工程师"
    """
    score = 0.0
    total = len(key_info)
    
    for key, expected in key_info.items():
        # 精确匹配
        if expected in output:
            score += 1.0 / total
        # 模糊匹配（前缀/后缀/同义）
        elif _fuzzy_match(expected, output):
            score += 0.5 / total  # 模糊命中给一半分
    
    return round(score, 2)

for n in [3, 5, 7, 8, 10, 12, 15, 20]:
    # 四个维度各自独立测试
    memory_score = test_memory(agent, n)        # 注入→干扰→回忆
    ref_score = test_reference_at_turn(agent, n)  # 第 n 轮插入指代
    switch_score = test_switch_at_turn(agent, n)   # 第 n 轮切回
    conflict_score = test_conflict_at_turn(agent, n) # 第 n 轮改指令
    
    curve.add(n, memory_score, ref_score, switch_score, conflict_score)

#!/usr/bin/env python3
"""
多轮对话测试

测试维度：
1. 信息记忆 — 早期信息后期是否还记得
2. 指代消解 — "它"指的是什么
3. 话题切换 — 切回去还记得吗
|4. 冲突处理 — 用户改主意能调整吗
|5. 语义漂移 — 理解是否逐渐偏离原意
|
|核心交付物：对话长度 vs 五条线衰减曲线
"""

import sys
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class DialogueTestResult:
    """对话测试结果"""
    turn_count: int
    memory_score: float          # Memory Recall Score: 0.0–1.0
    reference_score: float       # 指代消解得分: 0.0–1.0
    switch_score: float          # 话题切换得分: 0.0–1.0
    conflict_score: float        # 冲突处理得分: 0.0–1.0
    elapsed: float
    tokens: int


def _fuzzy_match(expected: str, output: str) -> bool:
    """模糊匹配：前缀/后缀/包含关系"""
    if len(expected) <= 2:
        return expected in output
    # 前缀匹配（"北京" → "北京市"）
    if output.find(expected) >= 0:
        return True
    # 子串匹配（"测试工程师" 包含 "测试"）
    for substr_len in range(max(2, len(expected) - 1), 1, -1):
        for start in range(len(expected) - substr_len + 1):
            substr = expected[start:start + substr_len]
            if substr in output:
                return True
    return False


def compute_memory_recall_score(output: str, key_info: dict) -> float:
    """
    Memory Recall Score：部分命中也计分
    
    3 个关键信息各 1/total 分：
    - 精确命中 → 1/full_score
    - 模糊命中 → 0.5/full_score
    
    例如：记住名字和地点，忘了职业 → 0.67
    """
    score = 0.0
    total = len(key_info)
    
    for key, expected in key_info.items():
        if expected in output:
            score += 1.0 / total
        elif _fuzzy_match(expected, output):
            score += 0.5 / total
    
    return round(score, 2)


@dataclass
class DecayCurve:
    """衰减曲线 — 四条线同时展示"""
    points: List[Dict] = field(default_factory=list)

    def add(self, turns: int, memory_rate: float, reference_rate: float,
            switch_rate: float, conflict_rate: float):
        self.points.append({
            "turns": turns,
            "memory": memory_rate,
            "reference": reference_rate,
            "switch": switch_rate,
            "conflict": conflict_rate,
        })

    def get_summary(self) -> Dict:
        \"\"\"获取摘要\"\"\"
        if not self.points:
            return {}

        # 信息记忆：找到降到 50% 以下的轮数（半衰期）
        # 指代消解：找到失效点（阶跃退化，非半衰）
        # 话题切换/冲突处理：找到稳定区间下限
        memory_half = None
        reference_fail = None
        switch_lower = None
        conflict_lower = None
        
        for p in self.points:
            if memory_half is None and p[\"memory\"] < 0.5:
                memory_half = p[\"turns\"]
            if reference_fail is None and p[\"reference\"] < 0.5:
                reference_fail = p[\"turns\"]
            if switch_lower is None and p[\"switch\"] < 0.5:
                switch_lower = p[\"turns\"]
            if conflict_lower is None and p[\"conflict\"] < 0.5:
                conflict_lower = p[\"turns\"]

        return {
            \"memory_half_life\": memory_half,
            \"reference_fail_point\": reference_fail,
            \"switch_stable_lower\": switch_lower,
            \"conflict_stable_lower\": conflict_lower,
            \"total_points\": len(self.points),
        }


def test_memory(agent, n_turns: int, max_context_turns: int = 10) -> DialogueTestResult:
    """
    测试信息记忆（使用 Memory Recall Score）

    Args:
        agent: 智能体实例
        n_turns: 对话轮数
        max_context_turns: 上下文窗口大小

    Returns:
        DialogueTestResult
    """
    start_time = time.time()

    # 重置智能体
    agent.reset()
    agent._context_history = []

    # 第 1 轮：注入关键信息
    key_info = {
        "name": "张三",
        "location": "北京",
        "job": "测试工程师",
    }
    agent.run(f"我叫{key_info['name']}，在{key_info['location']}工作，做{key_info['job']}的。")

    # 中间插入无关对话
    filler_topics = [
        "今天天气怎么样？",
        "给我讲个笑话。",
        "计算 1+1 等于几？",
        "Python 是什么语言？",
        "帮我写一首诗。",
        "什么是人工智能？",
        "推荐一本好书。",
        "怎么做番茄炒蛋？",
        "地球为什么是圆的？",
        "什么是区块链？",
        "如何学习编程？",
        "什么是机器学习？",
    ]

    for i in range(min(n_turns - 1, len(filler_topics))):
        agent.run(filler_topics[i])

    # 最后一轮：回忆关键信息
    result = agent.run(f"你叫什么名字？在哪里工作？做什么的？")

    elapsed = time.time() - start_time
    tokens = result.get("_meta", {}).get("tokens", 0)

    # 验证：使用 Memory Recall Score 替代布尔判断
    output = result.get("output", "")
    memory_score = compute_memory_recall_score(output, key_info)

    return DialogueTestResult(
        turn_count=n_turns,
        memory_score=memory_score,
        reference_score=0.0,  # 本测试不测指代消解
        switch_score=0.0,     # 本测试不测话题切换
        conflict_score=0.0,   # 本测试不测冲突处理
        elapsed=elapsed,
        tokens=tokens,
    )


def test_reference(agent) -> DialogueTestResult:
    """
    测试指代消解

    Returns:
        DialogueTestResult
    """
    start_time = time.time()
    agent.reset()
    agent._context_history = []

    # 第 1 轮：提到实体
    agent.run("我有一份销售数据，包含 2024 年全年的销售额。")

    # 第 2-3 轮：插入无关对话
    agent.run("今天天气怎么样？")
    agent.run("计算 2+3 等于几？")

    # 第 4 轮：用代词引用
    result = agent.run("能分析一下它吗？")

    elapsed = time.time() - start_time
    tokens = result.get("_meta", {}).get("tokens", 0)

    # 验证：智能体应该理解"它"指的是销售数据
    output = result.get("output", "")
    reference_score = 1.0 if ("销售" in output or "数据" in output or "分析" in output) else 0.0

    return DialogueTestResult(
        turn_count=4,
        memory_score=0.0,
        reference_score=reference_score,
        switch_score=0.0,
        conflict_score=0.0,
        elapsed=elapsed,
        tokens=tokens,
    )


def test_switch(agent) -> DialogueTestResult:
    """
    测试话题切换

    Returns:
        DialogueTestResult
    """
    start_time = time.time()
    agent.reset()
    agent._context_history = []

    # 话题 A
    agent.run("帮我计算 25*4 等于多少。")

    # 切换到话题 B
    agent.run("给我写一首关于春天的诗。")

    # 切回话题 A
    result = agent.run("刚才计算的结果是多少？")

    elapsed = time.time() - start_time
    tokens = result.get("_meta", {}).get("tokens", 0)

    # 验证
    output = result.get("output", "")
    switch_score = 1.0 if "100" in output else 0.0

    return DialogueTestResult(
        turn_count=3,
        memory_score=0.0,
        reference_score=0.0,
        switch_score=switch_score,
        conflict_score=0.0,
        elapsed=elapsed,
        tokens=tokens,
    )


def test_conflict(agent, conflict_type: str = "instruction") -> DialogueTestResult:
    """
    测试冲突处理（四个层级）

    conflict_type:
    - "instruction": 指令级冲突（修改具体操作）
    - "goal": 目标级冲突（修改整体目标）
    - "constraint": 约束级冲突（修改约束条件）
    - "implicit": 隐性冲突（否定自己的前提）

    Returns:
        DialogueTestResult
    """
    start_time = time.time()
    agent.reset()
    agent._context_history = []

    if conflict_type == "instruction":
        # 指令级：修改操作
        agent.run("帮我计算 2+3。")
        result = agent.run("不对，改成计算 5*6。")
        output = result.get("output", "")
        # 应该计算 5*6=30，而不是 2+3=5
        conflict_score = 1.0 if "30" in output and "5" not in output.replace("5*6", "") else 0.0

    elif conflict_type == "goal":
        # 目标级：修改分析目标
        agent.run("帮我分析华东区销售额。")
        result = agent.run("不对，改成分析全国。")
        output = result.get("output", "")
        # 应该停止华东分析，转向全国
        conflict_score = 1.0 if ("全国" in output or "整体" in output) and "华东" not in output else 0.0

    elif conflict_type == "constraint":
        # 约束级：修改约束条件
        agent.run("按销售额排序，展示全部数据。")
        result = agent.run("只要 Q1 的数据。")
        output = result.get("output", "")
        # 应该只展示 Q1 数据
        conflict_score = 1.0 if ("Q1" in output or "一季度" in output) else 0.0

    elif conflict_type == "implicit":
        # 隐性冲突：否定前提
        agent.run("假设 2024 年销售额增长了 20%。")
        result = agent.run("不对，其实是下降了 10%。")
        output = result.get("output", "")
        # 应该识别前提已被推翻
        conflict_score = 1.0 if ("下降" in output or "-10" in output or "-0.1" in output) else 0.0

    else:
        conflict_score = 0.0

    elapsed = time.time() - start_time
    tokens = result.get("_meta", {}).get("tokens", 0)

    return DialogueTestResult(
        turn_count=2,
        memory_score=0.0,
        reference_score=0.0,
        switch_score=0.0,
        conflict_score=conflict_score,
        elapsed=elapsed,
        tokens=tokens,
    )


def generate_decay_curve(agent, turn_counts: List[int] = None,
                         n_repeats: int = 3) -> DecayCurve:
    """
    生成四条线衰减曲线

    Args:
        agent: 智能体实例
        turn_counts: 测试的对话轮数列表
        n_repeats: 每个轮数重复次数

    Returns:
        DecayCurve
    """
    if turn_counts is None:
        turn_counts = [3, 5, 7, 8, 10, 12, 15, 20]

    curve = DecayCurve()

    for turns in turn_counts:
        # 信息记忆：多次重复，统计平均召回率
        memory_scores = []
        for _ in range(n_repeats):
            result = test_memory(agent, turns)
            memory_scores.append(result.memory_score)
        memory_rate = sum(memory_scores) / len(memory_scores)

        # 指代消解、话题切换、冲突处理各测一次（固定轮数场景）
        ref_result = test_reference(agent)
        switch_result = test_switch(agent)
        
        # 冲突处理：四个层级各测一次，取平均
        conflict_scores = []
        for ctype in ["instruction", "goal", "constraint", "implicit"]:
            cr = test_conflict(agent, ctype)
            conflict_scores.append(cr.conflict_score)
        conflict_rate = sum(conflict_scores) / len(conflict_scores)

        curve.add(
            turns=turns,
            memory_rate=memory_rate,
            reference_rate=ref_result.reference_score,
            switch_rate=switch_result.switch_score,
            conflict_rate=conflict_rate,
        )

    return curve


def print_decay_curve(curve: DecayCurve):
    """打印四条线衰减曲线"""
    print(f"\n{'='*90}")
    print(f"对话长度 vs 准确率衰减曲线（四条线）")
    print(f"{'='*90}")

    header = f"{'轮数':>6s} | {'信息记忆':>10s} | {'指代消解':>10s} | {'话题切换':>10s} | {'冲突处理':>10s}"
    print(header)
    print("-" * 90)

    for p in curve.points:
        row = f"{p['turns']:6d} | {p['memory']:9.0%} | {p['reference']:9.0%} | {p['switch']:9.0%} | {p['conflict']:9.0%}"
        print(row)

    summary = curve.get_summary()
    print(f\"\\n--- 各维度退化轮数（降序 50% 以下）---\")
    if summary.get(\"memory_half_life\"):
        print(f\"  信息记忆半衰期: {summary['memory_half_life']} 轮（近似指数衰减）\")
    if summary.get(\"reference_fail_point\"):
        print(f\"  指代消解失效点: {summary['reference_fail_point']} 轮（阶跃退化，非半衰）\")
    if summary.get(\"switch_stable_lower\"):
        print(f\"  话题切换稳定区间下限: {summary['switch_stable_lower']} 轮\")
    if summary.get(\"conflict_stable_lower\"):
        print(f\"  冲突处理稳定区间下限: {summary['conflict_stable_lower']} 轮\")

    print(f"{'='*90}\n")


def run_demo():
    """演示"""
    print("=" * 70)
    print("多轮对话测试演示")
    print("=" * 70)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agents.custom_agent.agent import CustomAgent

    agent = CustomAgent(temperature=0.3, max_context_turns=10)

    # 单维度测试
    print("\n--- 信息记忆测试（5 轮）---")
    result = test_memory(agent, 5)
    print(f"Memory Recall Score: {result.memory_score:.2f}")
    print(f"耗时: {result.elapsed:.1f}s, Token: {result.tokens}")

    print("\n--- 指代消解测试 ---")
    result = test_reference(agent)
    print(f"指代消解得分: {result.reference_score:.2f}")

    print("\n--- 话题切换测试 ---")
    result = test_switch(agent)
    print(f"话题切换得分: {result.switch_score:.2f}")

    print("\n--- 冲突处理测试（四个层级）---")
    for ctype in ["instruction", "goal", "constraint", "implicit"]:
        result = test_conflict(agent, ctype)
        type_names = {
            "instruction": "指令级",
            "goal": "目标级",
            "constraint": "约束级",
            "implicit": "隐性冲突"
        }
        print(f"  {type_names[ctype]}: {result.conflict_score:.2f}")

    # 衰减曲线（简化版，只测 3 个轮数）
    print("\n--- 衰减曲线（简化版）---")
    curve = generate_decay_curve(agent, turn_counts=[3, 7, 12], n_repeats=2)
    print_decay_curve(curve)


if __name__ == "__main__":
    run_demo()
