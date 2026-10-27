"""
Agent评测指标计算

所有评测器的评分结果最终汇聚到这里，计算综合评分和改进建议。

数据流：
  各 Evaluator.run_batch_evaluation() → 返回各维度得分
    → AgentMetrics.calculate_overall_score() → 综合评分
    → AgentMetrics.generate_improvement_suggestions() → 改进建议
"""
from typing import Dict, List, Any
from datetime import datetime


class AgentMetrics:
    """Agent评测指标计算器"""

    # ---- 各维度权重（默认） ----
    DEFAULT_WEIGHTS = {
        "task_planning": 0.25,
        "tool_use": 0.25,
        "dialogue": 0.20,
        "coding": 0.15,
        "knowledge": 0.15,
    }

    # ---- 评级阈值 ----
    GRADE_THRESHOLDS = [
        (4.5, "S"),
        (4.0, "A"),
        (3.5, "B"),
        (3.0, "C"),
        (0.0, "D"),
    ]

    # ============================================================
    #  综合评分
    # ============================================================

    @staticmethod
    def calculate_overall_score(
        dimension_scores: Dict[str, Dict],
        weights: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """
        计算综合评分（加权平均）

        Args:
            dimension_scores: 各维度得分，格式：
                {
                    "task_planning": {"overall": 3.5, "details": {...}},
                    "tool_use": {"overall": 4.0},
                    ...
                }
            weights: 各维度权重，默认使用 DEFAULT_WEIGHTS

        Returns:
            {
                "overall_score": 3.72,
                "grade": "B",
                "dimension_scores": {...},
                "dimension_weights_used": {...},
                "timestamp": "..."
            }
        """
        weights = weights or AgentMetrics.DEFAULT_WEIGHTS

        # 加权平均
        overall = 0.0
        total_weight = 0.0
        for dim, score_dict in dimension_scores.items():
            weight = weights.get(dim, 0.0)
            dim_score = score_dict.get("overall", 0.0)
            overall += weight * dim_score
            total_weight += weight

        # 归一化（如果传入的维度不全，按实际有的权重归一化）
        if total_weight > 0:
            overall /= total_weight

        # 评级
        grade = AgentMetrics._grade(overall)

        return {
            "overall_score": round(overall, 2),
            "grade": grade,
            "dimension_scores": dimension_scores,
            "dimension_weights_used": weights,
            "timestamp": datetime.now().isoformat(),
        }

    # ============================================================
    #  任务规划评分（从执行日志中提取）
    # ============================================================

    @staticmethod
    def calculate_task_planning_score(
        execution_log: List[Dict],
    ) -> Dict[str, float]:
        """
        从 Agent 执行日志计算任务规划评分

        Args:
            execution_log: Agent 执行日志，每个元素包含：
                {
                    "id": "task_1",
                    "description": "子任务描述",
                    "depends_on": ["task_0"],
                    "tool": "search",
                    "status": "success" | "failed" | "skipped",
                    "retry_count": 0,
                }

        Returns:
            {
                "decomposition_score": 4.2,   # 任务分解质量 (0-5)
                "dependency_accuracy": 3.8,    # 依赖识别准确率 (0-5)
                "replanning_success": 4.0,     # 重规划成功率 (0-5)
                "overall": 4.0,                # 综合 (0-5)
            }
        """
        metrics = {
            "decomposition_score": 0.0,
            "dependency_accuracy": 0.0,
            "replanning_success": 0.0,
            "overall": 0.0,
        }

        if not execution_log:
            return metrics

        # ---- 1. 任务分解质量 ----
        # 评估维度：
        #   a) 步骤数量合理性（3-8 步为佳）
        #   b) 每步描述是否具体（长度 10-100 字）
        #   c) 是否覆盖了多种工具（多样性）
        steps = len(execution_log)

        # a) 步骤数量评分
        if 3 <= steps <= 8:
            count_score = 1.0
        elif steps < 3:
            count_score = steps / 3  # 分解不足
        else:
            count_score = max(0.3, 1.0 - (steps - 8) * 0.05)  # 过度分解扣分

        # b) 描述具体性评分
        specific_steps = sum(
            1 for step in execution_log
            if 10 <= len(step.get("description", "")) <= 100
        )
        specificity_score = specific_steps / steps if steps > 0 else 0

        # c) 工具多样性评分
        tools_used = set(
            step.get("tool", "")
            for step in execution_log
            if step.get("tool") and step.get("tool") != "none"
        )
        diversity_score = min(1.0, len(tools_used) / 3)  # 3 种以上工具满分

        decomposition = (
            count_score * 0.35
            + specificity_score * 0.35
            + diversity_score * 0.30
        ) * 5  # 转 5 分制

        # ---- 2. 依赖识别准确率 ----
        # 评估维度：
        #   a) 依赖声明是否完整（有 depends_on 的步数占比）
        #   b) 依赖关系是否无环（拓扑排序验证）
        #   c) 依赖引用是否有效（引用的 task_id 存在）
        steps_with_deps = sum(
            1 for step in execution_log
            if step.get("depends_on")
        )
        dep_completeness = steps_with_deps / steps if steps > 0 else 0

        # 依赖引用有效性
        all_ids = {step.get("id", "") for step in execution_log}
        valid_refs = 0
        total_refs = 0
        for step in execution_log:
            for dep_id in step.get("depends_on", []):
                total_refs += 1
                if dep_id in all_ids:
                    valid_refs += 1
        ref_validity = valid_refs / total_refs if total_refs > 0 else 1.0

        # 无环检测（简单拓扑排序）
        has_cycle = AgentMetrics._has_cycle(execution_log)
        acyclic_score = 0.0 if has_cycle else 1.0

        dependency = (
            dep_completeness * 0.30
            + ref_validity * 0.35
            + acyclic_score * 0.35
        ) * 5

        # ---- 3. 重规划成功率 ----
        # 评估维度：
        #   a) 失败后是否重试（retry_count > 0 的步数）
        #   b) 重试后是否成功（retry 后 status == success）
        #   c) 最终完成率
        retried_steps = [s for s in execution_log if s.get("retry_count", 0) > 0]
        if retried_steps:
            retry_success = sum(
                1 for s in retried_steps if s.get("status") == "success"
            )
            retry_rate = retry_success / len(retried_steps)
        else:
            retry_rate = 1.0  # 没失败，自然不需要重试

        completed = sum(1 for s in execution_log if s.get("status") == "success")
        completion_rate = completed / steps if steps > 0 else 0

        # 有失败但成功恢复 = 加分项
        failed_then_recovered = sum(
            1 for s in retried_steps if s.get("status") == "success"
        )
        recovery_bonus = min(1.0, failed_then_recovered / max(1, steps * 0.2))

        replanning = (
            retry_rate * 0.35
            + completion_rate * 0.35
            + recovery_bonus * 0.30
        ) * 5

        # ---- 综合 ----
        overall = (
            decomposition * 0.40
            + dependency * 0.30
            + replanning * 0.30
        )

        metrics.update({
            "decomposition_score": round(decomposition, 2),
            "dependency_accuracy": round(dependency, 2),
            "replanning_success": round(replanning, 2),
            "overall": round(overall, 2),
        })

        return metrics

    # ============================================================
    #  工具使用评分（从工具调用记录中提取）
    # ============================================================

    @staticmethod
    def calculate_tool_use_score(
        tool_calls: List[Dict],
    ) -> Dict[str, float]:
        """
        从工具调用记录计算工具使用评分

        Args:
            tool_calls: 工具调用记录，每个元素包含：
                {
                    "tool_name": "search",
                    "success": True,
                    "parameter_accuracy": 0.8,
                    "latency_ms": 150,
                }

        Returns:
            {
                "api_success_rate": 4.0,     # API 调用成功率 (0-5)
                "tool_efficiency": 3.5,      # 工具使用效率 (0-5)
                "parameter_accuracy": 4.2,   # 参数准确性 (0-5)
                "overall": 3.9,              # 综合 (0-5)
            }
        """
        metrics = {
            "api_success_rate": 0.0,
            "tool_efficiency": 0.0,
            "parameter_accuracy": 0.0,
            "overall": 0.0,
        }

        if not tool_calls:
            return metrics

        n = len(tool_calls)

        # ---- 1. API 调用成功率 ----
        success_count = sum(1 for c in tool_calls if c.get("success", False))
        success_rate = success_count / n

        # ---- 2. 工具使用效率 ----
        # 评估维度：
        #   a) 平均延迟（< 200ms 满分，> 2s 不及格）
        #   b) 是否有无效调用（success=False 的比例）
        #   c) 工具选择是否精简（去重后的工具数 / 总调用数）
        avg_latency = sum(
            c.get("latency_ms", 1000) for c in tool_calls
        ) / n

        if avg_latency < 200:
            latency_score = 1.0
        elif avg_latency < 2000:
            latency_score = 1.0 - (avg_latency - 200) / 1800 * 0.5
        else:
            latency_score = 0.5

        # 有效调用比例
        effective_rate = success_count / n

        # 工具选择精简度（避免重复调用同一工具）
        unique_tools = len(set(c.get("tool_name", "") for c in tool_calls))
        efficiency_ratio = unique_tools / n if n > 0 else 0
        # 0.5-1.0 区间为佳（每个工具调 1-2 次）
        efficiency_score = 1.0 if 0.5 <= efficiency_ratio <= 1.0 else 0.6

        tool_efficiency = (
            latency_score * 0.30
            + effective_rate * 0.40
            + efficiency_score * 0.30
        ) * 5

        # ---- 3. 参数准确性 ----
        param_scores = [
            c.get("parameter_accuracy", 0)
            for c in tool_calls
            if "parameter_accuracy" in c
        ]
        if param_scores:
            avg_param = sum(param_scores) / len(param_scores)
        else:
            # 没有 parameter_accuracy 字段时，用成功率近似
            avg_param = success_rate

        # ---- 综合 ----
        overall = (
            success_rate * 5 * 0.40
            + tool_efficiency * 0.30
            + avg_param * 5 * 0.30
        )

        metrics.update({
            "api_success_rate": round(success_rate * 5, 2),
            "tool_efficiency": round(tool_efficiency, 2),
            "parameter_accuracy": round(avg_param * 5, 2),
            "overall": round(overall, 2),
        })

        return metrics

    # ============================================================
    #  多轮对话评分（从对话轮次记录中提取）
    # ============================================================

    @staticmethod
    def calculate_dialogue_score(
        dialogue_turns: List[Dict],
    ) -> Dict[str, float]:
        """
        从对话轮次记录计算多轮对话评分

        Args:
            dialogue_turns: 对话轮次记录，每个元素包含：
                {
                    "user_utterance": "用户输入",
                    "agent_response": "Agent 回复",
                    "context_items": ["需要记住的信息"],
                }

        Returns:
            {
                "context_retention": 4.0,      # 上下文保持率 (0-5)
                "coreference_accuracy": 3.5,   # 指代消解准确率 (0-5)
                "intent_recognition": 4.2,     # 意图识别准确率 (0-5)
                "overall": 3.9,                # 综合 (0-5)
            }
        """
        metrics = {
            "context_retention": 0.0,
            "coreference_accuracy": 0.0,
            "intent_recognition": 0.0,
            "overall": 0.0,
        }

        if not dialogue_turns:
            return metrics

        n = len(dialogue_turns)

        # ---- 1. 上下文保持率 ----
        # 评估：后续轮次是否正确引用了早期上下文信息
        context_hits = 0
        context_total = 0
        for i, turn in enumerate(dialogue_turns):
            required = turn.get("context_items", [])
            if not required:
                continue
            context_total += len(required)
            response = turn.get("agent_response", "").lower()
            for item in required:
                if item.lower() in response:
                    context_hits += 1

        context_rate = context_hits / context_total if context_total > 0 else 1.0

        # 衰减检测：后半段是否比前半段差
        if n >= 4:
            mid = n // 2
            first_half = dialogue_turns[:mid]
            second_half = dialogue_turns[mid:]

            def _context_hit_rate(turns):
                hits = total = 0
                for t in turns:
                    for item in t.get("context_items", []):
                        total += 1
                        if item.lower() in t.get("agent_response", "").lower():
                            hits += 1
                return hits / total if total > 0 else 1.0

            first_rate = _context_hit_rate(first_half)
            second_rate = _context_hit_rate(second_half)
            decay = max(0, first_rate - second_rate)  # 衰减量
            # 衰减越小越好
            context_rate = context_rate * (1.0 - decay * 0.5)

        # ---- 2. 指代消解准确率 ----
        # 评估：Agent 是否将"它""这个""那个"等代词正确展开
        coref_keywords = ["它", "他", "她", "这个", "那个", "这些", "那些", "此", "其"]
        coref_total = 0
        coref_correct = 0
        for turn in dialogue_turns:
            user_text = turn.get("user_utterance", "").lower()
            agent_text = turn.get("agent_response", "").lower()
            for kw in coref_keywords:
                if kw in user_text:
                    coref_total += 1
                    # 简化：检查 Agent 回复是否包含前一轮的关键信息
                    if agent_text and len(agent_text) > 5:
                        coref_correct += 0.7  # 有具体回复 = 部分正确
                    # 如果回复中直接展开了代词 = 满分
                    # （需要 NER，这里简化处理）

        coref_rate = coref_correct / coref_total if coref_total > 0 else 1.0

        # ---- 3. 意图识别准确率 ----
        # 评估：Agent 是否正确理解了用户意图
        intent_total = 0
        intent_correct = 0
        for turn in dialogue_turns:
            expected = turn.get("expected_intent", "")
            actual = turn.get("actual_intent", "")
            if expected:
                intent_total += 1
                if actual == expected:
                    intent_correct += 1
                elif not actual:
                    # 没有标注 actual_intent 时，用回复长度近似
                    # 有具体回复 ≈ 理解了指向
                    if len(turn.get("agent_response", "")) > 10:
                        intent_correct += 0.8

        intent_rate = intent_correct / intent_total if intent_total > 0 else 1.0

        # ---- 综合 ----
        overall = (
            context_rate * 5 * 0.40
            + coref_rate * 5 * 0.30
            + intent_rate * 5 * 0.30
        )

        metrics.update({
            "context_retention": round(context_rate * 5, 2),
            "coreference_accuracy": round(coref_rate * 5, 2),
            "intent_recognition": round(intent_rate * 5, 2),
            "overall": round(overall, 2),
        })

        return metrics

    # ============================================================
    #  改进建议生成
    # ============================================================

    @staticmethod
    def generate_improvement_suggestions(
        dimension_scores: Dict[str, Dict],
    ) -> List[str]:
        """
        根据各维度得分生成改进建议

        Args:
            dimension_scores: 各维度得分

        Returns:
            改进建议列表
        """
        suggestions = []

        dim_names = {
            "task_planning": "任务规划",
            "tool_use": "工具使用",
            "dialogue": "多轮对话",
            "coding": "代码能力",
            "knowledge": "知识应用",
        }

        for dim, score_dict in dimension_scores.items():
            score = score_dict.get("overall", 0.0)
            name = dim_names.get(dim, dim)

            if score < 3.0:
                advice = {
                    "task_planning": (
                        f" {name}能力较弱（{score:.1f}/5），建议："
                        "① 优化任务分解 Prompt，增加 Few-shot 示例；"
                        "② 引入依赖图验证，避免循环依赖"
                    ),
                    "tool_use": (
                        f" {name}能力不足（{score:.1f}/5），建议："
                        "① 完善工具描述，让 Agent 更清楚何时用哪个工具；"
                        "② 增加参数校验和错误恢复逻辑"
                    ),
                    "dialogue": (
                        f" {name}能力需提升（{score:.1f}/5），建议："
                        "① 扩大上下文窗口，避免早期信息丢失；"
                        "② 增加指代消解模块"
                    ),
                    "coding": (
                        f" {name}待提高（{score:.1f}/5），建议："
                        "① 增加代码生成 Prompt 的约束条件；"
                        "② 引入单元测试作为验证循环"
                    ),
                    "knowledge": (
                        f" {name}不足（{score:.1f}/5），建议："
                        "① 接入 RAG 检索增强；"
                        "② 增加幻觉检测机制"
                    ),
                }
                suggestions.append(advice.get(dim, f" {name}（{score:.1f}/5）需改进"))
            elif score < 4.0:
                suggestions.append(f" {name}表现良好（{score:.1f}/5），仍有提升空间")
            else:
                suggestions.append(f" {name}表现优秀（{score:.1f}/5）")

        if not suggestions:
            suggestions.append(" 暂无评测维度数据，请先运行评测")

        return suggestions

    # ============================================================
    #  内部工具方法
    # ============================================================

    @staticmethod
    def _grade(score: float) -> str:
        """根据分数返回评级"""
        for threshold, grade in AgentMetrics.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "D"

    @staticmethod
    def _has_cycle(execution_log: List[Dict]) -> bool:
        """
        检测依赖图中是否有环（拓扑排序）

        Returns:
            True = 有环，False = 无环
        """
        # 构建邻接表
        graph: Dict[str, List[str]] = {}
        all_nodes: set = set()

        for step in execution_log:
            step_id = step.get("id", "")
            all_nodes.add(step_id)
            if step_id not in graph:
                graph[step_id] = []
            for dep_id in step.get("depends_on", []):
                graph.setdefault(dep_id, [])  # 确保被依赖的节点也在图中
                graph[step_id].append(dep_id)  # step_id 依赖 dep_id

        # Kahn 算法
        in_degree = {node: 0 for node in all_nodes}
        for node, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0) + 1

        queue = [node for node, deg in in_degree.items() if deg == 0]
        visited = 0

        while queue:
            node = queue.pop(0)
            visited += 1
            for dep in graph.get(node, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        return visited < len(all_nodes)
