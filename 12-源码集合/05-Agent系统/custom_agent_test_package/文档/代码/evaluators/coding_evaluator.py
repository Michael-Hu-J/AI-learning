#!/usr/bin/env python3
"""代码能力评测器 — 检测 Agent 的 code_executor 工具是否正确执行代码"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import time


class CodingEvaluator:
    """
    评测 Agent 的代码执行能力

    测试方法：
    1. 加载 JSON 任务文件
    2. 让 LLM 生成代码并执行
    3. 检查执行结果是否正确

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

    def evaluate_single_task(self, agent, task: Dict) -> Dict[str, Any]:
        """评测单个代码任务（使用 Agent 实例）"""
        agent.reset()
        result = agent.run(task["input"])

        is_passed = result.get("success", False)
        output = result.get("output", "")

        # 检查关键词
        check_keywords = task.get("check_keywords", [])
        if check_keywords and output:
            has_keywords = any(kw in output for kw in check_keywords)
            is_passed = is_passed and has_keywords

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "passed": is_passed,
            "output_preview": output[:200],
            "expected_tool": task.get("expected_tool", ""),
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
            "avg_pass_rate": sum(1 for r in all_results if r["passed"]) / len(all_results),
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
        使用 CustomAgent 实例评估代码任务

        评分逻辑：
        1. Agent 执行成功 + 关键词匹配 = 5 分
        2. Agent 执行成功但关键词部分匹配 = 3-4 分
        3. Agent 执行成功但无关键词 = 2 分
        4. Agent 执行失败 = 1 分
        """
        agent.reset()
        result = agent.run(task["goal"])

        output = result.get("output", "")
        is_passed = result.get("success", False)

        # 关键词匹配（宽松：部分匹配即可）
        check_keywords = task.get("check_keywords", [])
        keyword_match_rate = 0.0
        if check_keywords and output:
            matched = sum(1 for kw in check_keywords if kw in output)
            keyword_match_rate = matched / len(check_keywords)
            is_passed = is_passed and keyword_match_rate >= 0.3  # 30% 关键词匹配即算过

        # 评分
        if is_passed and keyword_match_rate >= 0.8:
            score = 5.0
        elif is_passed and keyword_match_rate >= 0.5:
            score = 4.0
        elif is_passed and keyword_match_rate >= 0.3:
            score = 3.5
        elif is_passed:
            score = 2.5
        elif "超时" in output or "错误" in output:
            score = 1.0
        else:
            score = 2.0

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "passed": is_passed,
            "overall_score": score,
            "generated_code": output[:300],
            "execution_output": output[:200],
            "keyword_match_rate": round(keyword_match_rate, 2),
            "timestamp": datetime.now().isoformat(),
        }

    def _evaluate_with_llm(self, llm_client, task: Dict) -> Dict[str, Any]:
        """
        让 LLM 生成代码并评估

        Args:
            llm_client: LLMClient 实例
            task: 任务配置

        Returns:
            评测结果
        """
        check_keywords_str = ", ".join(task.get("check_keywords", []))

        prompt = f"""你是一个代码生成专家。请根据任务描述生成 Python 代码。

## 任务
{task['description']}

## 目标
{task['goal']}

## 检查关键词（输出中应包含以下关键词）
{check_keywords_str}

## 要求
1. 生成完整的、可执行的 Python 代码
2. 代码应包含必要的 import
3. 输出结果应清晰（使用 print）
4. 代码应简洁高效

请输出 Python 代码，用 ```python 包裹。"""

        response = llm_client.chat(prompt)

        if not response.success:
            raise RuntimeError(f"LLM 调用失败 ({task['id']}): {response.error}")

        # 从回复中提取代码
        content = response.content.strip()
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', content, re.DOTALL)
        generated_code = code_match.group(1).strip() if code_match else content

        # 尝试执行代码
        passed = False
        execution_output = ""
        try:
            exec_result = subprocess.run(
                ["python3", "-c", generated_code],
                capture_output=True,
                text=True,
                timeout=30,
            )
            execution_output = exec_result.stdout.strip()
            if exec_result.returncode == 0 and execution_output:
                # 检查关键词
                check_keywords = task.get("check_keywords", [])
                if check_keywords:
                    passed = any(kw in execution_output for kw in check_keywords)
                else:
                    passed = True
        except subprocess.TimeoutExpired:
            execution_output = "执行超时"
        except Exception as e:
            execution_output = f"执行错误: {str(e)}"

        # 评分
        score = 5.0 if passed else 1.0
        if not passed and "超时" not in execution_output and "错误" not in execution_output:
            score = 2.0  # 代码能跑但结果不对

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "category": task.get("category", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "passed": passed,
            "overall_score": score,
            "generated_code": generated_code[:300],
            "execution_output": execution_output[:200],
            "timestamp": datetime.now().isoformat(),
        }
