"""
工具使用评测器 — 基于 CustomAgent 实际工具调用记录评分

改动 (2026-05-18): 从"让 LLM 选择工具并构造参数"改为"调用 CustomAgent.run() 获取真实工具调用流程"
评分数据来自 Agent 的 _meta.subtasks，包括：
  - tool 字段 → 工具选择准确性
  - tool_input 字段 → 参数准确性
  - status + retry_count → 错误恢复能力
  - 调用顺序 → 多工具协作能力
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: str = ""


@dataclass
class ToolTaskResult:
    """工具任务结果"""
    task_id: str
    task_name: str
    category: str
    tool_calls: List[ToolCall]
    success_criteria_met: List[str]
    overall_success: bool
    score: float


class ToolUseEvaluator:
    """
    工具使用评测器

    评测维度:
    1. API 调用成功率
    2. 参数准确性
    3. 工具选择合理性
    4. 多工具协作能力
    5. 错误处理能力
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

    def evaluate_tool_call(self, tool_call: ToolCall, expected_params: Dict) -> Dict[str, float]:
        """
        评测单次工具调用

        Args:
            tool_call: 实际调用记录
            expected_params: 期望参数

        Returns:
            各项指标得分
        """
        metrics = {
            "success": 1.0 if tool_call.success else 0.0,
            "parameter_accuracy": 0.0,
            "latency_score": 1.0,
            "error_handling": 0.0
        }

        # 参数准确性
        if tool_call.parameters:
            matched = 0
            total = len(expected_params)

            for key, expected_value in expected_params.items():
                if key in tool_call.parameters:
                    actual_value = tool_call.parameters[key]
                    if actual_value == expected_value:
                        matched += 1
                    elif str(actual_value).lower() == str(expected_value).lower():
                        matched += 0.5

            metrics["parameter_accuracy"] = matched / total if total > 0 else 0

        # 延迟评分 (100ms 内满分，1s 内及格)
        if tool_call.latency_ms < 100:
            metrics["latency_score"] = 1.0
        elif tool_call.latency_ms < 1000:
            metrics["latency_score"] = 0.5
        else:
            metrics["latency_score"] = 0.2

        # 错误处理
        if tool_call.success:
            metrics["error_handling"] = 1.0
        elif tool_call.error:
            metrics["error_handling"] = 0.5

        return metrics

    def evaluate_tool_selection(self, selected_tools: List[str], required_tools: List[str]) -> float:
        """
        评测工具选择合理性

        Args:
            selected_tools: Agent 选择的工具
            required_tools: 任务需要的工具

        Returns:
            选择评分 (0-1)
        """
        if not selected_tools:
            return 0.0

        required_set = set(required_tools)
        selected_set = set(selected_tools)

        coverage = len(required_set & selected_set) / len(required_set) if required_set else 1.0

        # 多余工具惩罚
        extra_tools = len(selected_set - required_set)
        penalty = min(0.2, extra_tools * 0.05)

        return max(0.0, coverage - penalty)

    def evaluate_multi_tool_coordination(self, tool_calls: List[ToolCall]) -> float:
        """
        评测多工具协作能力

        Args:
            tool_calls: 工具调用序列

        Returns:
            协作评分 (0-1)
        """
        if len(tool_calls) <= 1:
            return 1.0

        all_success = all(call.success for call in tool_calls)

        # 检查连续调用之间是否有工具名变化（避免无意义重复）
        unique_consecutive = 0
        for i in range(len(tool_calls) - 1):
            if tool_calls[i].tool_name != tool_calls[i + 1].tool_name:
                unique_consecutive += 1
        data_flow_score = unique_consecutive / (len(tool_calls) - 1) if len(tool_calls) > 1 else 1.0

        # 连续失败超过 2 次说明错误没有处理
        consecutive_failures = 0
        max_consecutive = 0
        for call in tool_calls:
            if not call.success:
                consecutive_failures += 1
                max_consecutive = max(max_consecutive, consecutive_failures)
            else:
                consecutive_failures = 0

        error_handled = max_consecutive <= 2

        return (1.0 if all_success else 0.5) * (1.0 if error_handled else 0.5)

    def evaluate_task(self, task_id: str, agent_tool_calls: List[Dict]) -> Dict[str, Any]:
        """
        评测单个任务

        Args:
            task_id: 任务 ID
            agent_tool_calls: Agent 的工具调用记录

        Returns:
            评测结果
        """
        # 查找任务
        task = None
        for t in self.tasks["tasks"]:
            if t["id"] == task_id:
                task = t
                break

        if not task:
            return {"error": f"Task {task_id} not found"}

        # 转换工具调用记录
        tool_calls = []
        for call in agent_tool_calls:
            tool_call = ToolCall(
                tool_name=call.get("tool_name", ""),
                parameters=call.get("parameters", {}),
                success=call.get("success", False),
                result=call.get("result"),
                error=call.get("error"),
                latency_ms=call.get("latency_ms", 0),
                timestamp=call.get("timestamp", "")
            )
            tool_calls.append(tool_call)

        # 1. 工具调用评测
        call_scores = []
        expected_tools = task.get("tools", [])

        for i, tool_call in enumerate(tool_calls):
            expected_params = expected_tools[i].get("parameters", {}) if i < len(expected_tools) else {}
            scores = self.evaluate_tool_call(tool_call, expected_params)
            call_scores.append(scores)

        # 2. 工具选择评测
        selected_tools = [call.tool_name for call in tool_calls]
        required_tools = [tool["name"] for tool in expected_tools]
        selection_score = self.evaluate_tool_selection(selected_tools, required_tools)

        # 3. 多工具协作评测
        coordination_score = self.evaluate_multi_tool_coordination(tool_calls)

        # 4. 成功标准检查
        criteria_met = []
        for criterion in task.get("success_criteria", []):
            if all(call.success for call in tool_calls):
                criteria_met.append(criterion)

        # 计算综合评分
        avg_call_score = sum(
            sum(scores.values()) / len(scores)
            for scores in call_scores
        ) / len(call_scores) if call_scores else 0

        overall_score = (
            avg_call_score * 0.4 +
            selection_score * 0.2 +
            coordination_score * 0.2 +
            (len(criteria_met) / len(task.get("success_criteria", [1]))) * 0.2
        ) * 5

        return {
            "task_id": task_id,
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "tool_calls": len(tool_calls),
            "success_rate": sum(1 for c in tool_calls if c.success) / len(tool_calls) if tool_calls else 0,
            "parameter_accuracy": sum(
                s["parameter_accuracy"] for s in call_scores
            ) / len(call_scores) if call_scores else 0,
            "tool_selection": selection_score,
            "coordination": coordination_score,
            "criteria_met": len(criteria_met),
            "total_criteria": len(task.get("success_criteria", [])),
            "overall_score": overall_score,
            "timestamp": datetime.now().isoformat()
        }

    def run_batch_evaluation(self, agent, llm_client=None) -> Dict[str, Any]:
        """
        批量评测所有任务 — 调用 CustomAgent 实际执行

        改动 (2026-05-18): 不再让 LLM 选择工具，
        而是调用 agent.run(task_goal) 获取真实工具调用流程，
        从 _meta.subtasks 中提取 tool/tool_input/status/retry_count 来评分。

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
            # 限流控制：每 3 个任务之间等待 2 秒
            if idx > 0 and idx % 3 == 0:
                time.sleep(2)
            task_id = task["id"]
            task_goal = task["goal"]

            print(f"  执行任务: {task_id} - {task['name'][:40]}...")

            # 重置 Agent 状态
            agent.reset()

            # 调用 Agent 实际执行
            start_time = time.time()
            try:
                result = agent.run(task_goal)
                elapsed = time.time() - start_time
            except Exception as e:
                print(f"    Agent 执行异常: {e}")
                all_results.append({
                    "task_id": task_id,
                    "task_name": task["name"],
                    "category": task.get("category", "未知"),
                    "difficulty": task.get("difficulty", "medium"),
                    "overall_score": 0.0,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                continue

            # 从 Agent 返回结果中提取工具调用数据
            meta = result.get("_meta", {})
            subtasks = meta.get("subtasks", [])

            # 如果 agent 执行失败，记录详细错误
            if not result.get("success"):
                error_msg = result.get("error", "未知错误")
                print(f"    [WARN] Agent返回失败: {error_msg[:100]}")

            # 构建工具调用记录
            agent_tool_calls = []
            for s in subtasks:
                tool_name = s.get("tool", "none")
                if tool_name == "none":
                    continue

                tool_input = s.get("result", "")
                is_success = s.get("status") == "success"
                retry_count = s.get("retry_count", 0)

                agent_tool_calls.append({
                    "tool_name": tool_name,
                    "parameters": {"input": tool_input[:200]} if tool_input else {},
                    "success": is_success,
                    "result": tool_input[:200] if is_success else None,
                    "error": None if is_success else f"重试{retry_count}次后仍失败",
                    "latency_ms": (elapsed / max(1, len(subtasks))) * 1000,
                    "timestamp": datetime.now().isoformat()
                })

            # 运行评分
            eval_result = self.evaluate_task(task_id, agent_tool_calls)
            eval_result["agent_success"] = result.get("success", False)
            eval_result["subtasks_total"] = meta.get("subtasks_total", 0)
            eval_result["subtasks_success"] = meta.get("subtasks_success", 0)
            eval_result["elapsed"] = round(elapsed, 2)
            eval_result["llm_calls"] = meta.get("llm_calls", 0)
            eval_result["tokens"] = meta.get("tokens", 0)

            all_results.append(eval_result)

            # 打印进度
            status_icon = "OK" if result.get("success") else "FAIL"
            tool_names = [c["tool_name"] for c in agent_tool_calls]
            print(f"    [{status_icon}] 得分: {eval_result['overall_score']:.2f}/5 "
                  f"工具: {', '.join(tool_names) if tool_names else '无'} "
                  f"耗时: {elapsed:.1f}s")

        # 汇总统计
        successful = [r for r in all_results if r.get("agent_success")]
        summary = {
            "total_tasks": len(all_results),
            "successful_tasks": len(successful),
            "success_rate": len(successful) / len(all_results) if all_results else 0,
            "avg_score": sum(r["overall_score"] for r in all_results) / len(all_results) if all_results else 0,
            "by_category": {},
            "by_difficulty": {},
            "results": all_results
        }

        # 按类别分组
        for result in all_results:
            cat = result.get("category", "未知")
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = []
            summary["by_category"][cat].append(result)

        for cat, results in summary["by_category"].items():
            summary["by_category"][cat] = {
                "count": len(results),
                "avg_score": sum(r["overall_score"] for r in results) / len(results),
                "success_rate": sum(1 for r in results if r.get("agent_success")) / len(results),
            }

        # 按难度分组
        for result in all_results:
            diff = result.get("difficulty", "unknown")
            if diff not in summary["by_difficulty"]:
                summary["by_difficulty"][diff] = []
            summary["by_difficulty"][diff].append(result)

        for diff, results in summary["by_difficulty"].items():
            summary["by_difficulty"][diff] = {
                "count": len(results),
                "avg_score": sum(r["overall_score"] for r in results) / len(results),
                "success_rate": sum(1 for r in results if r.get("agent_success")) / len(results),
            }

        return summary
