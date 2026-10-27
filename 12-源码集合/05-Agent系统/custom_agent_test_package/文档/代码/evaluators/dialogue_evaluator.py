#!/usr/bin/env python3
"""多轮对话评测器 — 检测 Agent 在多轮对话中是否保持上下文"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import time


class DialogueEvaluator:
    """
    评测 Agent 的多轮对话能力

    测试方法：
    1. 加载 JSON 任务文件
    2. 让 LLM 模拟多轮对话并评估
    3. 检查上下文保持、指代理解、话题管理

    评分：5分制
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

    def evaluate_single_turn(self, agent, task: Dict) -> Dict[str, Any]:
        """评测单个对话任务（使用 Agent 实例）"""
        agent.reset()

        last_result = None
        all_turns_success = True

        for turn in task.get("turns", []):
            if turn["role"] == "user":
                last_result = agent.run(turn["content"])
                if not last_result.get("success", False):
                    all_turns_success = False

        is_passed = last_result.get("success", False) if last_result else False

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "turns": len(task.get("turns", [])),
            "passed": is_passed,
            "all_turns_success": all_turns_success,
            "output_preview": last_result.get("output", "")[:200] if last_result else "",
            "expected_behavior": task.get("expected_behavior", []),
        }

    def run_batch_evaluation(self, agent=None, llm_client=None) -> Dict[str, Any]:
        """
        批量评测所有任务

        Args:
            agent: CustomAgent 实例（优先使用）
            llm_client: LLMClient 实例（备用）

        Returns:
            批量评测汇总
        """
        if agent is None and llm_client is None:
            raise ValueError("必须提供 agent 或 llm_client 参数")

        all_results = []

        for idx, task in enumerate(self.tasks["tasks"]):
            # 限流控制：每 3 个任务之间等待 2 秒
            if idx > 0 and idx % 3 == 0:
                time.sleep(2)
            if agent is not None:
                result = self._evaluate_with_agent(agent, task)
            else:
                result = self._evaluate_with_llm(llm_client, task)
            all_results.append(result)

        # 汇总统计
        summary = {
            "total_tasks": len(all_results),
            "avg_score": sum(r["overall_score"] for r in all_results) / len(all_results),
            "by_category": {},
            "by_difficulty": {},
            "results": all_results,
        }

        # 按类别分组
        for result in all_results:
            cat = result["category"]
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = []
            summary["by_category"][cat].append(result)

        for cat, results in summary["by_category"].items():
            summary["by_category"][cat] = {
                "count": len(results),
                "avg_score": sum(r["overall_score"] for r in results) / len(results),
            }

        # 按难度分组
        for result in all_results:
            diff = result["difficulty"]
            if diff not in summary["by_difficulty"]:
                summary["by_difficulty"][diff] = []
            summary["by_difficulty"][diff].append(result)

        for diff, results in summary["by_difficulty"].items():
            summary["by_difficulty"][diff] = {
                "count": len(results),
                "avg_score": sum(r["overall_score"] for r in results) / len(results),
            }

        return summary

    def _evaluate_with_agent(self, agent, task: Dict) -> Dict[str, Any]:
        """
        使用 CustomAgent 实例评估对话任务

        评分逻辑：
        1. 所有轮次执行成功 = 基础 3 分
        2. expected_behavior 关键词匹配 = 加分
        3. Agent 输出有实际内容（非空/非错误）= 加分
        4. 综合 1-5 分
        """
        agent.reset()

        last_output = ""
        all_turns_success = True
        context_items_found = []
        total_turns = 0

        for turn in task.get("turns", []):
            if turn["role"] == "user":
                total_turns += 1
                result = agent.run(turn["content"])
                if result.get("success"):
                    last_output = result.get("output", "")
                else:
                    all_turns_success = False

        # 检查 expected_behavior 匹配（宽松：部分匹配即可）
        expected_count = len(task.get("expected_behavior", []))
        if expected_count > 0 and last_output:
            for expected in task.get("expected_behavior", []):
                # 提取期望行为中的关键词（去掉解释性文字）
                keywords = [kw.strip() for kw in expected.replace("中", " ").replace("了", " ").replace("的", " ").split() if len(kw.strip()) > 1]
                if keywords:
                    matched = sum(1 for kw in keywords if kw.lower() in last_output.lower())
                    if matched >= max(1, len(keywords) * 0.3):  # 30% 关键词匹配即算命中
                        context_items_found.append(expected)

        context_rate = len(context_items_found) / expected_count if expected_count > 0 else 0.5

        # 评分：综合多个因素
        if all_turns_success and context_rate >= 0.5 and len(last_output) > 20:
            score = 4.0
        elif all_turns_success and context_rate >= 0.3:
            score = 3.5
        elif all_turns_success:
            score = 3.0
        elif context_rate >= 0.5:
            score = 2.5
        elif context_rate >= 0.2:
            score = 2.0
        else:
            score = 1.5

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "turns": total_turns,
            "overall_score": float(score),
            "context_kept": context_rate >= 0.3,
            "reference_understood": context_rate >= 0.2,
            "context_match_rate": round(context_rate, 2),
            "reason": f"全部成功={all_turns_success}, 上下文匹配={context_rate:.0%}, 输出长度={len(last_output)}",
            "timestamp": datetime.now().isoformat(),
        }

    def _evaluate_with_llm(self, llm_client, task: Dict) -> Dict[str, Any]:
        """
        让 LLM 评估对话任务

        Args:
            llm_client: LLMClient 实例
            task: 任务配置

        Returns:
            评测结果
        """
        turns_text = "\n".join(
            f"{turn['role']}: {turn['content']}"
            for turn in task.get("turns", [])
        )

        expected_text = "\n- ".join(task.get("expected_behavior", []))

        prompt = f"""你是一个对话质量评估专家。请评估以下多轮对话场景中，Agent 的表现。

## 对话内容
{turns_text}

## 期望行为
- {expected_text}

## 检查维度
1. **上下文保持**：Agent 是否记住了前面的对话内容
2. **指代理解**：Agent 是否正确理解"它"、"呢"、"占"等指代词
3. **话题管理**：切换话题后能否切回来
4. **情绪识别**：能否识别用户情绪变化

## 评分标准（5分制）
- 5分：所有维度都表现优秀
- 4分：大部分维度表现良好
- 3分：基本满足要求，有小瑕疵
- 2分：有明显不足
- 1分：严重不足

请输出一个 JSON 对象，包含以下字段：
{{"score": 分数(1-5), "context_kept": true/false, "reference_understood": true/false, "reason": "评分理由"}}

只输出 JSON，不要其他内容。"""

        response = llm_client.chat(prompt)

        if not response.success:
            raise RuntimeError(f"LLM 调用失败 ({task['id']}): {response.error}")

        # 从回复中提取 JSON
        content = response.content.strip()
        code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if code_match:
            content = code_match.group(1)

        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            raw_json = json_match.group(1)
            try:
                eval_result = json.loads(raw_json)
                score = eval_result.get("score", 3)
                context_kept = eval_result.get("context_kept", False)
                reference_understood = eval_result.get("reference_understood", False)
                reason = eval_result.get("reason", "")
            except json.JSONDecodeError:
                score = 3
                context_kept = False
                reference_understood = False
                reason = content[:200]
        else:
            score = 3
            context_kept = False
            reference_understood = False
            reason = content[:200]

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "turns": len(task.get("turns", [])),
            "overall_score": float(score),
            "context_kept": context_kept,
            "reference_understood": reference_understood,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
