#!/usr/bin/env python3
"""
智能体能力评分 — 权重配置与短板检测

支持：
1. 按场景加载权重配置
2. 计算加权总分
3. 检测短板维度
4. 应用短板效应（任一维度 <40 分，总分打八折）
"""

import yaml
import os
from typing import Dict, List, Optional


# 内置场景权重配置
SCENE_WEIGHTS = {
    "data_analysis": {
        "task_planning": 0.25,
        "tool_use": 0.20,
        "dialogue": 0.10,
        "coding": 0.25,
        "knowledge": 0.15,
        "safety": 0.05,
    },
    "customer_service": {
        "task_planning": 0.10,
        "tool_use": 0.15,
        "dialogue": 0.35,
        "coding": 0.05,
        "knowledge": 0.20,
        "safety": 0.15,
    },
    "code_assistant": {
        "task_planning": 0.20,
        "tool_use": 0.15,
        "dialogue": 0.10,
        "coding": 0.40,
        "knowledge": 0.10,
        "safety": 0.05,
    },
}

DIMENSIONS = [
    "task_planning",
    "tool_use",
    "dialogue",
    "coding",
    "knowledge",
    "safety",
]

DIMENSION_NAMES = {
    "task_planning": "任务规划",
    "tool_use": "工具使用",
    "dialogue": "多轮对话",
    "coding": "代码能力",
    "knowledge": "知识问答",
    "safety": "安全性",
}


def load_weights(scene: str) -> Dict[str, float]:
    """
    加载场景权重配置

    Args:
        scene: 场景名称（data_analysis / customer_service / code_assistant）

    Returns:
        权重配置字典 {dimension: weight}
    """
    if scene in SCENE_WEIGHTS:
        return SCENE_WEIGHTS[scene]

    # 尝试从 YAML 文件加载
    config_path = os.path.join(os.path.dirname(__file__), f"weights_{scene}.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("weights", {})

    raise ValueError(f"未知场景: {scene}，可用场景: {list(SCENE_WEIGHTS.keys())}")


def calc_weighted_score(scores: Dict[str, float], weights: Dict[str, float]) -> Dict:
    """
    计算加权总分 + 短板检测

    Args:
        scores: 各维度得分 {dimension: score}，score 范围 0-1
        weights: 权重配置 {dimension: weight}

    Returns:
        {
            "total": 加权总分,
            "weighted_scores": 各维度加权得分,
            "weaknesses": 短板维度列表,
            "discounted": 是否触发短板效应,
            "final_total": 最终总分（考虑短板效应）
        }
    """
    # 计算加权得分
    weighted_scores = {}
    total = 0.0
    for dim in DIMENSIONS:
        score = scores.get(dim, 0.0)
        weight = weights.get(dim, 0.0)
        weighted = score * weight
        weighted_scores[dim] = weighted
        total += weighted

    # 检测短板（任一维度 <40 分）
    weaknesses = [dim for dim in DIMENSIONS if scores.get(dim, 0.0) < 0.4]
    discounted = len(weaknesses) > 0

    # 应用短板效应
    final_total = total * 0.8 if discounted else total

    return {
        "total": total,
        "weighted_scores": weighted_scores,
        "weaknesses": weaknesses,
        "discounted": discounted,
        "final_total": final_total,
    }


def print_score_report(result: Dict, scene: str):
    """打印评分报告"""
    print(f"\n{'='*60}")
    print(f"评分报告 — 场景: {scene}")
    print(f"{'='*60}")

    print(f"\n各维度得分:")
    for dim in DIMENSIONS:
        score = result.get("scores", {}).get(dim, 0)
        weight = result.get("weights", {}).get(dim, 0)
        name = DIMENSION_NAMES[dim]
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {name:8s} {score:5.1%}  {bar}  权重 {weight:.0%}")

    print(f"\n加权总分: {result['total']:.1%}")

    if result["discounted"]:
        print(f"⚠  触发短板效应: {', '.join(DIMENSION_NAMES[w] for w in result['weaknesses'])}")
        print(f"   总分打八折: {result['total']:.1%} → {result['final_total']:.1%}")

    print(f"最终得分: {result['final_total']:.1%}")
    print(f"{'='*60}\n")


def run_demo():
    """演示：同一智能体在不同场景下的得分差异"""

    # 假设智能体各维度得分
    scores = {
        "task_planning": 0.85,
        "tool_use": 0.78,
        "dialogue": 0.62,
        "coding": 0.72,
        "knowledge": 0.75,
        "safety": 0.80,
    }

    scenes = ["data_analysis", "customer_service", "code_assistant"]
    results = {}

    for scene in scenes:
        weights = load_weights(scene)
        result = calc_weighted_score(scores, weights)
        result["scores"] = scores
        result["weights"] = weights
        results[scene] = result
        print_score_report(result, scene)

    # 对比总结
    print("=" * 60)
    print("对比总结")
    print("=" * 60)
    print(f"{'场景':20s} {'总分':>8s} {'短板':>10s} {'最终':>8s}")
    print("-" * 60)
    for scene, result in results.items():
        name = {"data_analysis": "数据分析", "customer_service": "客服", "code_assistant": "代码助手"}[scene]
        weakness = ", ".join(DIMENSION_NAMES[w] for w in result["weaknesses"]) if result["weaknesses"] else "无"
        print(f"{name:20s} {result['total']:7.1%} {weakness:>10s} {result['final_total']:7.1%}")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
