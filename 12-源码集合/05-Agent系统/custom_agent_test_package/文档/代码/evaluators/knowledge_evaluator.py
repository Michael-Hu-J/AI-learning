#!/usr/bin/env python3
"""知识能力评测器 — 检测 Agent 的 search 工具是否能正确检索知识"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import time


class KnowledgeEvaluator:
    """
    评测 Agent 的知识检索能力

    测试方法：
    1. 加载 JSON 任务文件
    2. 让 LLM 回答问题
    3. 检查返回结果是否包含关键信息

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
        """评测单个知识任务（使用 Agent 实例）"""
        agent.reset()
        result = agent.run(task["input"])

        output = result.get("output", "")
        check_keywords = task.get("check_keywords", [])

        if check_keywords:
            has_keywords = all(kw in output for kw in check_keywords)
            is_passed = has_keywords
        else:
            # 幻觉检测题：检查 Agent 是否诚实回答
            is_passed = result.get("success", False)

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "domain": task.get("domain", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "passed": is_passed,
            "output_preview": output[:200],
            "question_type": task.get("question_type", "事实性知识"),
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
            "total_questions": len(all_results),
            "avg_score": sum(r["overall_score"] for r in all_results) / len(all_results),
            "avg_accuracy": sum(1 for r in all_results if r["passed"]) / len(all_results),
            "by_domain": {},
            "by_difficulty": {},
            "results": all_results,
        }

        # 按领域分组
        for result in all_results:
            domain = result["domain"]
            if domain not in summary["by_domain"]:
                summary["by_domain"][domain] = []
            summary["by_domain"][domain].append(result)

        for domain, results in summary["by_domain"].items():
            summary["by_domain"][domain] = {
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
        使用 CustomAgent 实例评估知识任务

        评分逻辑：
        1. Agent 执行成功 + 关键词全部匹配 = 5 分
        2. Agent 执行成功 + 部分匹配 = 3-4 分
        3. Agent 执行成功但无关键词要求 = 3 分
        4. Agent 执行失败 = 1-2 分
        """
        agent.reset()
        result = agent.run(task["goal"])

        output = result.get("output", "")
        is_passed = result.get("success", False)

        # 关键词匹配（宽松）
        check_keywords = task.get("check_keywords", [])
        keyword_match_rate = 0.0
        if check_keywords and output:
            matched = sum(1 for kw in check_keywords if kw in output)
            keyword_match_rate = matched / len(check_keywords)
            is_passed = is_passed and keyword_match_rate >= 0.3

        # 评分
        if is_passed and keyword_match_rate >= 0.8:
            score = 5.0
        elif is_passed and keyword_match_rate >= 0.5:
            score = 4.0
        elif is_passed and keyword_match_rate >= 0.3:
            score = 3.5
        elif is_passed:
            score = 3.0  # 成功但无关键词要求
        elif "超时" in output or "错误" in output:
            score = 1.0
        else:
            score = 2.0

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "domain": task.get("domain", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "question_type": task.get("question_type", "事实性知识"),
            "passed": is_passed,
            "overall_score": score,
            "answer_preview": output[:300],
            "check_keywords": check_keywords,
            "keyword_match_rate": round(keyword_match_rate, 2),
            "timestamp": datetime.now().isoformat(),
        }

    def _evaluate_with_llm(self, llm_client, task: Dict) -> Dict[str, Any]:
        """
        让 LLM 回答问题并评估

        Args:
            llm_client: LLMClient 实例
            task: 任务配置

        Returns:
            评测结果
        """
        question_type = task.get("question_type", "事实性知识")
        check_keywords = task.get("check_keywords", [])

        if question_type == "幻觉检测":
            # 幻觉检测题：期望 Agent 回答"不知道"或"查不到"
            prompt = f"""你是一个知识问答助手。请回答以下问题。

## 问题
{task['input']}

## 要求
1. 如果你知道答案，请给出准确回答
2. 如果你不知道或无法确定，请明确说"不知道"或"无法确定"
3. 不要编造答案

请直接回答，不要其他解释。"""
        else:
            # 事实性/推理知识题
            keywords_str = "，".join(check_keywords) if check_keywords else "无特定关键词要求"
            prompt = f"""你是一个知识问答助手。请回答以下问题。

## 问题
{task['input']}

## 期望包含的关键词
{keywords_str}

## 要求
1. 给出准确、完整的回答
2. 回答中应包含上述关键词
3. 如果是推理题，请给出推理过程

请直接回答，不要其他解释。"""

        response = llm_client.chat(prompt)

        if not response.success:
            raise RuntimeError(f"LLM 调用失败 ({task['id']}): {response.error}")

        answer = response.content.strip()

        # 评估
        passed = False
        if question_type == "幻觉检测":
            # 幻觉检测：正确回答应该是"不知道"类
            hallucination_indicators = ["不知道", "无法确定", "查不到", "没有", "不存在", "我不"]
            passed = any(indicator in answer for indicator in hallucination_indicators)
        else:
            # 事实性/推理：检查关键词
            if check_keywords:
                passed = any(kw in answer for kw in check_keywords)
            else:
                passed = len(answer) > 10  # 有内容就算过

        # 评分
        if passed:
            score = 5.0
        elif question_type == "幻觉检测":
            # 幻觉检测题：如果编造了答案，给低分
            score = 1.0
        else:
            score = 2.0

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "domain": task.get("domain", "未知"),
            "difficulty": task.get("difficulty", "medium"),
            "question_type": question_type,
            "passed": passed,
            "overall_score": score,
            "answer_preview": answer[:300],
            "check_keywords": check_keywords,
            "timestamp": datetime.now().isoformat(),
        }
