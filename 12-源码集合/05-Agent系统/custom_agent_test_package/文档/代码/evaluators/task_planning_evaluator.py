"""
任务规划评测器 — 基于 CustomAgent 实际执行结果评分

改动 (2026-05-18): 从"让 LLM 生成计划字符串"改为"调用 CustomAgent.run() 获取真实执行日志"
评分数据来自 Agent 的 _meta.subtasks，包括：
  - 子任务描述 → 分解质量
  - 依赖关系 → 依赖识别准确率
  - 执行状态/重试次数 → 执行质量
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskStep:
    """任务步骤"""
    id: int
    description: str
    status: str = "pending"  # pending/running/completed/failed
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: str
    task_name: str
    goal: str
    steps: List[TaskStep] = field(default_factory=list)
    total_time: float = 0.0
    success: bool = False
    agent_plan: List[str] = field(default_factory=list)
    expected_plan: List[str] = field(default_factory=list)


class TaskPlanningEvaluator:
    """
    任务规划评测器

    评测维度:
    1. 任务分解 (Decomposition): 能否将复杂任务拆分为合理子任务
    2. 依赖识别 (Dependency): 能否识别任务间先后关系
    3. 执行效率 (Execution): 完成质量和时间
    """

    def __init__(self, tasks_file: str):
        """
        初始化评测器

        Args:
            tasks_file: 任务配置文件路径
        """
        self.tasks_file = Path(tasks_file)
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> Dict:
        """加载任务配置"""
        with open(self.tasks_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def evaluate_decomposition(self, agent_plan: List[str], expected_subtasks: List[str]) -> Dict[str, Any]:
        """
        评测任务分解能力

        Args:
            agent_plan: Agent 生成的任务分解（子任务描述列表）
            expected_subtasks: 期望的子任务列表

        Returns:
            分解评分和详情
        """
        metrics = {
            "coverage": 0.0,      # 覆盖率 (多少必需步骤被覆盖)
            "precision": 0.0,     # 精确度 (分解是否合理)
            "granularity": 0.0,   # 粒度 (子任务大小是否合适)
            "score": 0.0
        }

        if not agent_plan:
            return metrics

        # 1. 覆盖率：必需步骤的覆盖情况
        matched = 0
        for expected in expected_subtasks:
            for agent_step in agent_plan:
                if self._semantic_match(expected, agent_step):
                    matched += 1
                    break

        metrics["coverage"] = matched / len(expected_subtasks) if expected_subtasks else 0

        # 2. 精确度：分解步骤的合理性
        # 过多步骤 = 过度分解，过少 = 分解不足
        optimal_count = len(expected_subtasks)
        agent_count = len(agent_plan)

        if agent_count == 0:
            metrics["precision"] = 0
        elif agent_count <= optimal_count * 1.5:
            # 在合理范围内
            metrics["precision"] = min(1.0, agent_count / optimal_count)
        else:
            # 过度分解
            metrics["precision"] = optimal_count / agent_count

        # 3. 粒度：子任务大小是否合适
        # 简单启发式：步骤描述长度适中 (10-100 字)
        good_granularity = sum(
            1 for step in agent_plan
            if 10 <= len(step) <= 100
        )
        metrics["granularity"] = good_granularity / len(agent_plan) if agent_plan else 0

        # 综合评分
        metrics["score"] = (
            metrics["coverage"] * 0.5 +
            metrics["precision"] * 0.3 +
            metrics["granularity"] * 0.2
        ) * 5  # 转换为 5 分制

        return metrics

    def evaluate_dependency(self, agent_plan: List[str], dependencies: List[Dict]) -> Dict[str, Any]:
        """
        评测依赖识别能力

        Args:
            agent_plan: Agent 生成的任务顺序
            dependencies: 期望的依赖关系

        Returns:
            依赖识别评分
        """
        metrics = {
            "order_accuracy": 0.0,  # 顺序正确率
            "critical_path": 0.0,   # 关键路径识别
            "score": 0.0
        }

        if not agent_plan or not dependencies:
            return metrics

        # 1. 顺序正确率：检查依赖关系是否被遵守
        correct_orders = 0
        total_deps = len(dependencies)

        for dep in dependencies:
            from_idx = dep["from"]
            to_idx = dep["to"]

            # 检查在 agent_plan 中，to 是否在 from 之前
            if isinstance(to_idx, list):
                # 多个前置任务
                all_before = all(
                    self._find_step_index(agent_plan, to) < self._find_step_index(agent_plan, from_idx)
                    for to in to_idx
                )
                if all_before:
                    correct_orders += 1
            else:
                if self._find_step_index(agent_plan, to_idx) < self._find_step_index(agent_plan, from_idx):
                    correct_orders += 1

        metrics["order_accuracy"] = correct_orders / total_deps if total_deps else 0

        # 2. 关键路径识别：链式依赖越长，关键路径越重要
        if agent_plan and dependencies:
            dep_map = {}
            for dep in dependencies:
                from_idx = dep["from"]
                to_idx = dep["to"]
                if isinstance(to_idx, list):
                    for t in to_idx:
                        dep_map.setdefault(t, set()).add(from_idx)
                else:
                    dep_map.setdefault(to_idx, set()).add(from_idx)

            def _longest_chain(node, visited=None):
                if visited is None:
                    visited = set()
                if node in visited:
                    return 0
                visited.add(node)
                parents = dep_map.get(node, set())
                if not parents:
                    return 1
                return 1 + max(_longest_chain(p, visited) for p in parents)

            max_chain = max(
                (_longest_chain(n) for n in dep_map.keys()), default=1
            )
            chain_ratio = max_chain / len(dependencies)
            metrics["critical_path"] = min(1.0, chain_ratio)
        else:
            metrics["critical_path"] = 0.0

        metrics["score"] = (
            metrics["order_accuracy"] * 0.7
            + metrics["critical_path"] * 0.3
        ) * 5

        return metrics

    def evaluate_execution(self, execution: TaskExecution, time_limit: float) -> Dict[str, Any]:
        """
        评测执行质量

        Args:
            execution: 任务执行记录
            time_limit: 时间限制 (秒)

        Returns:
            执行评分
        """
        metrics = {
            "completion_rate": 0.0,  # 完成率
            "time_efficiency": 0.0,  # 时间效率
            "error_handling": 0.0,   # 错误处理
            "score": 0.0
        }

        if not execution.steps:
            return metrics

        # 1. 完成率
        completed = sum(1 for step in execution.steps if step.status == "completed")
        metrics["completion_rate"] = completed / len(execution.steps)

        # 2. 时间效率
        if execution.total_time > 0:
            if execution.total_time <= time_limit:
                metrics["time_efficiency"] = 1.0
            else:
                metrics["time_efficiency"] = time_limit / execution.total_time

        # 3. 错误处理
        failed = sum(1 for step in execution.steps if step.status == "failed")
        if failed > 0:
            # 有失败但有重试/恢复
            metrics["error_handling"] = 0.5
        else:
            metrics["error_handling"] = 1.0

        metrics["score"] = (
            metrics["completion_rate"] * 0.5 +
            metrics["time_efficiency"] * 0.3 +
            metrics["error_handling"] * 0.2
        ) * 5

        return metrics

    def _semantic_match(self, text1: str, text2: str) -> bool:
        """
        语义匹配 — 关键词重叠 + 字符级 N-gram 相似度

        不使用外部 NLP 模型，纯字符串匹配：
        1. 去除停用词后计算 Jaccard 重叠
        2. 计算 2-gram 重叠度
        3. 任一超过阈值即判定匹配
        """
        # 1. 关键词 Jaccard
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        stopwords = {
            "the", "a", "an", "is", "are", "to", "for", "and", "or",
            "的", "是", "一个", "并", "或", "在", "有", "和", "与",
            "中", "等", "这", "那", "它", "他", "她",
        }
        words1 -= stopwords
        words2 -= stopwords

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = overlap / union if union > 0 else 0

        if jaccard > 0.3:
            return True

        # 2. 2-gram 重叠（处理中文分词问题）
        def _bigrams(text: str) -> set:
            chars = text.lower().replace(" ", "")
            return {chars[i:i+2] for i in range(len(chars) - 1)}

        bg1 = _bigrams(text1)
        bg2 = _bigrams(text2)
        if bg1 and bg2:
            bg_overlap = len(bg1 & bg2)
            bg_union = len(bg1 | bg2)
            bg_jaccard = bg_overlap / bg_union if bg_union > 0 else 0
            if bg_jaccard > 0.25:
                return True

        return False

    def _find_step_index(self, plan: List[str], step_id: int) -> int:
        """查找步骤在计划中的索引"""
        if 0 <= step_id < len(plan):
            return step_id
        return len(plan)  # 未找到返回末尾

    def run_evaluation(self, task_id: str, agent_plan: List[str], execution_steps: List[Dict] = None) -> Dict[str, Any]:
        """
        运行完整评测

        Args:
            task_id: 任务 ID
            agent_plan: Agent 生成的任务计划（子任务描述列表）
            execution_steps: 执行步骤记录 (可选)

        Returns:
            完整评测结果
        """
        # 查找任务
        task = None
        for t in self.tasks["tasks"]:
            if t["id"] == task_id:
                task = t
                break

        if not task:
            return {"error": f"Task {task_id} not found"}

        # 1. 分解评测
        decomp_result = self.evaluate_decomposition(
            agent_plan,
            task["subtasks"]
        )

        # 2. 依赖评测
        dep_result = self.evaluate_dependency(
            agent_plan,
            task["dependencies"]
        )

        # 3. 执行评测
        if execution_steps:
            execution = TaskExecution(
                task_id=task_id,
                task_name=task["name"],
                goal=task["goal"],
                steps=[TaskStep(**step) for step in execution_steps],
                total_time=sum(
                    (step.get("end_time", 0) - step.get("start_time", 0))
                    for step in execution_steps
                )
            )
            exec_result = self.evaluate_execution(execution, task["time_limit"])
        else:
            exec_result = {"score": 0, "completion_rate": 0, "time_efficiency": 0, "error_handling": 0}

        # 综合评分
        weights = task["scoring"]
        overall_score = (
            decomp_result["score"] * weights["decomposition"] +
            dep_result["score"] * weights["dependency"] +
            exec_result["score"] * weights["execution"]
        )

        return {
            "task_id": task_id,
            "task_name": task["name"],
            "difficulty": task["difficulty"],
            "decomposition": decomp_result,
            "dependency": dep_result,
            "execution": exec_result,
            "overall_score": overall_score,
            "timestamp": datetime.now().isoformat()
        }

    def run_batch_evaluation(self, agent, llm_client=None) -> Dict[str, Any]:
        """
        批量评测所有任务 — 调用 CustomAgent 实际执行

        Args:
            agent: CustomAgent 实例（必须提供）
            llm_client: 保留兼容，不再使用

        Returns:
            批量评测汇总
        """
        if agent is None:
            raise ValueError("agent 参数必须提供，不再支持裸 LLM 模式")

        all_results = []

        for idx, task in enumerate(self.tasks["tasks"]):
            task_id = task["id"]
            task_goal = task["goal"]

            # 限流控制：每 3 个任务之间等待 2 秒
            if idx > 0 and idx % 3 == 0:
                print(f"  限流等待 2 秒...")
                time.sleep(2)

            print(f"  执行任务: {task_id} - {task['name'][:40]}...")

            # 重置 Agent 状态
            agent.reset()

            # 调用 Agent 实际执行
            start_time = time.time()
            try:
                result = agent.run(task_goal)
                elapsed = time.time() - start_time
            except Exception as e:
                print(f"    Agent 执行失败: {e}")
                all_results.append({
                    "task_id": task_id,
                    "task_name": task["name"],
                    "difficulty": task["difficulty"],
                    "overall_score": 0.0,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                continue

            # 从 Agent 返回结果中提取评分数据
            meta = result.get("_meta", {})
            subtasks = meta.get("subtasks", [])

            # 提取子任务描述列表（用于分解和依赖评分）
            agent_plan = [s.get("description", "") for s in subtasks]

            # 构建执行步骤记录（用于执行质量评分）
            execution_steps = []
            for i, s in enumerate(subtasks):
                status_map = {
                    "success": "completed",
                    "failed": "failed",
                    "skipped": "failed",
                    "pending": "pending",
                    "running": "running",
                }
                execution_steps.append({
                    "id": i,
                    "description": s.get("description", ""),
                    "status": status_map.get(s.get("status", "pending"), "pending"),
                    "result": s.get("result", "")[:200] if s.get("result") else "",
                    "error": "" if s.get("status") == "success" else f"重试{ s.get('retry_count', 0)}次",
                    "start_time": start_time + i * 0.1,  # 近似时间
                    "end_time": start_time + (i + 1) * 0.1,
                })

            # 运行评分
            eval_result = self.run_evaluation(task_id, agent_plan, execution_steps)
            eval_result["agent_success"] = result.get("success", False)
            eval_result["subtasks_total"] = meta.get("subtasks_total", 0)
            eval_result["subtasks_success"] = meta.get("subtasks_success", 0)
            eval_result["elapsed"] = round(elapsed, 2)
            eval_result["llm_calls"] = meta.get("llm_calls", 0)
            eval_result["tokens"] = meta.get("tokens", 0)

            all_results.append(eval_result)

            # 打印进度
            status_icon = "OK" if result.get("success") else "FAIL"
            print(f"    [{status_icon}] 得分: {eval_result['overall_score']:.2f}/5 "
                  f"(子任务: {meta.get('subtasks_success', 0)}/{meta.get('subtasks_total', 0)}) "
                  f"耗时: {elapsed:.1f}s")

        # 汇总统计
        successful = [r for r in all_results if r.get("agent_success")]
        summary = {
            "total_tasks": len(all_results),
            "successful_tasks": len(successful),
            "success_rate": len(successful) / len(all_results) if all_results else 0,
            "avg_score": sum(r["overall_score"] for r in all_results) / len(all_results) if all_results else 0,
            "by_difficulty": {},
            "results": all_results
        }

        # 按难度分组
        for task_result in all_results:
            diff = task_result.get("difficulty", "unknown")
            if diff not in summary["by_difficulty"]:
                summary["by_difficulty"][diff] = []
            summary["by_difficulty"][diff].append(task_result)

        for diff, tasks in summary["by_difficulty"].items():
            summary["by_difficulty"][diff] = {
                "count": len(tasks),
                "avg_score": sum(t["overall_score"] for t in tasks) / len(tasks),
                "success_rate": sum(1 for t in tasks if t.get("agent_success")) / len(tasks),
            }

        return summary
