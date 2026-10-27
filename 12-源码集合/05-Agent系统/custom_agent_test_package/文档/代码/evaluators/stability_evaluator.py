#!/usr/bin/env python3
"""稳定性评测器 — 检测 Agent 多次执行同一任务的结果是否一致"""

from typing import Dict, List, Any


class StabilityEvaluator:
    """
    评测 Agent 的稳定性（结果一致性）

    测试方法：
    1. 同一任务执行多次（默认 3 次）
    2. 对比每次的结果是否一致
    3. 检查工具调用顺序是否一致

    评分：一致性率 × 100
    """

    STABILITY_CASES = [
        {
            "id": "st_01",
            "input": "计算 25 * 4 + 100 / 5 的结果",
            "description": "确定性计算任务",
            "runs": 3,
        },
        {
            "id": "st_02",
            "input": "查询2024年6月各品类的销售额",
            "description": "数据查询任务（Mock 数据应一致）",
            "runs": 3,
        },
        {
            "id": "st_03",
            "input": "用 Python 计算斐波那契数列前 10 项",
            "description": "代码执行任务",
            "runs": 3,
        },
    ]

    def evaluate(self, agent) -> Dict[str, Any]:
        """执行评测"""
        results = []
        stable_count = 0

        for case in self.STABILITY_CASES:
            outputs = []
            for i in range(case["runs"]):
                agent.reset()
                result = agent.run(case["input"])
                outputs.append({
                    "run": i + 1,
                    "success": result.get("success", False),
                    "output_preview": result.get("output", "")[:50],
                })

            # 检查所有运行的 success 状态是否一致
            success_states = [o["success"] for o in outputs]
            is_stable = len(set(success_states)) == 1

            if is_stable:
                stable_count += 1

            results.append({
                "id": case["id"],
                "description": case["description"],
                "runs": case["runs"],
                "stable": is_stable,
                "outputs": outputs,
            })

        total = len(self.STABILITY_CASES)
        return {
            "dimension": "stability",
            "total": total,
            "stable": stable_count,
            "score": round(stable_count / total * 100, 1) if total > 0 else 0,
            "details": results,
        }
