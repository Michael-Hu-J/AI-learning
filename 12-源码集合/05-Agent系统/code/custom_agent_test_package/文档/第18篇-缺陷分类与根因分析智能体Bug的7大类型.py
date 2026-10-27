#!/usr/bin/env python3
"""
电商数据分析智能体 - 缺陷分类与根因定位

功能：
1. 缺陷自动分类（7 大类型）
2. 根因定位辅助
3. 严重度评估
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


# 缺陷分类字典
DEFECT_CATALOG = {
    "规划缺陷": {
        "keywords": ["规划", "子任务", "依赖", "JSON", "解析"],
        "phases": ["planning"],
        "severity": "Medium",
        "ecommerce_example": "智能体先写报告再查数据——依赖顺序错误",
    },
    "工具缺陷": {
        "keywords": ["工具", "不存在", "参数", "格式"],
        "phases": ["executing"],
        "severity": "High",
        "ecommerce_example": "用 web_fetch 抓整页而不是 search/code_executor 读数",
    },
    "执行缺陷": {
        "keywords": ["超时", "失败", "错误", "代码"],
        "phases": ["executing"],
        "severity": "High",
        "ecommerce_example": "计算客单价时把订单量当成销售额",
    },
    "记忆缺陷": {
        "keywords": ["遗忘", "指代", "话题", "上下文"],
        "phases": ["executing", "summarizing"],
        "severity": "Medium",
        "ecommerce_example": "多轮对话中忘记用户说的是按月统计",
    },
    "知识缺陷": {
        "keywords": ["幻觉", "编造", "错误", "不准确"],
        "phases": ["summarizing"],
        "severity": "Medium",
        "ecommerce_example": "把同比算成环比",
    },
    "安全缺陷": {
        "keywords": ["安全", "注入", "Jailbreak", "有害"],
        "phases": ["planning", "executing"],
        "severity": "Critical",
        "ecommerce_example": "报告中明文展示客户手机号",
    },
    "性能缺陷": {
        "keywords": ["超时", "延迟", "Token", "内存", "OOM"],
        "phases": ["planning", "executing", "summarizing"],
        "severity": "Low",
        "ecommerce_example": "逐条查询订单而不是批量查询，Token 消耗过大",
    },
}


def classify_defect(log: Dict, error: str = "") -> Dict:
    """
    根据日志和错误信息自动分类缺陷

    Args:
        log: 智能体日志
        error: 错误信息

    Returns:
        {
            "type": 缺陷类型,
            "phase": 阶段,
            "severity": 严重度,
            "confidence": 置信度,
            "likely_causes": 可能的根因,
        }
    """
    # 合并日志和错误信息
    text = error.lower()
    phase = log.get("phase", "")

    best_match = None
    best_score = 0

    for defect_type, catalog in DEFECT_CATALOG.items():
        score = 0

        # 关键词匹配
        for keyword in catalog["keywords"]:
            if keyword.lower() in text:
                score += 1

        # 阶段匹配
        if phase in catalog["phases"]:
            score += 2

        if score > best_score:
            best_score = score
            best_match = defect_type

    if not best_match:
        best_match = "未知缺陷"

    # 置信度
    confidence = min(best_score / 5.0, 1.0)

    # 可能的根因
    likely_causes = _get_likely_causes(best_match)

    return {
        "type": best_match,
        "phase": phase,
        "severity": DEFECT_CATALOG.get(best_match, {}).get("severity", "Medium"),
        "confidence": confidence,
        "likely_causes": likely_causes,
    }


def _get_likely_causes(defect_type: str) -> List[str]:
    """获取可能的根因"""
    causes = {
        "规划缺陷": [
            "Prompt 中未限制子任务数量",
            "Prompt 中缺少依赖关系示例",
            "LLM 输出格式不稳定",
            "JSON 解析容错不足",
        ],
        "工具缺陷": [
            "Prompt 中未列出可用工具（search / calculator / code_executor / …）",
            "工具描述不清晰",
            "参数验证不足",
            "LLM 不理解工具用途",
        ],
        "执行缺陷": [
            "search 调用超时",
            "工具返回错误未处理",
            "生成的计算代码有 bug（如客单价公式错误）",
            "数据格式不匹配",
        ],
        "记忆缺陷": [
            "上下文窗口截断",
            "指代消解能力不足",
            "状态未隔离",
            "话题管理混乱（如忘记统计维度）",
        ],
        "知识缺陷": [
            "模型电商知识不足（如同比环比混淆）",
            "幻觉检测不足",
            "训练数据过时",
            "缺少 RAG 检索",
        ],
        "安全缺陷": [
            "安全关键词过滤不足",
            "注入检测规则不完善",
            "Jailbreak 检测不足",
            "隐私检测不足（如客户手机号未脱敏）",
        ],
        "性能缺陷": [
            "子任务数量过多",
            "Prompt 过长",
            "反思次数过多",
            "未批量查询导致 Token 消耗过大",
        ],
    }
    return causes.get(defect_type, ["未知根因"])


def assess_severity(defect_type: str, success_rate: float,
                    error_count: int) -> Dict:
    """
    评估严重度

    Args:
        defect_type: 缺陷类型
        success_rate: 成功率
        error_count: 错误数量

    Returns:
        {
            "severity": 严重度,
            "priority": 优先级,
            "sla": 修复 SLA,
        }
    """
    # 安全缺陷直接 Critical
    if defect_type == "安全缺陷":
        return {"severity": "Critical", "priority": "P0", "sla": "24 小时"}

    # 基于成功率评估
    if success_rate < 0.5:
        severity = "High"
        priority = "P1"
        sla = "3 天"
    elif success_rate < 0.8:
        severity = "Medium"
        priority = "P2"
        sla = "1 周"
    else:
        severity = "Low"
        priority = "P3"
        sla = "2 周"

    # 错误数量增加严重度
    if error_count > 10:
        if severity == "Low":
            severity = "Medium"
            priority = "P2"
            sla = "1 周"

    return {"severity": severity, "priority": priority, "sla": sla}


def print_defect_report(defects: List[Dict]):
    """打印缺陷报告"""
    print(f"\n{'='*60}")
    print(f"电商数据分析智能体 - 缺陷分类与根因分析报告")
    print(f"{'='*60}")

    # 按类型统计
    type_counts = {}
    for d in defects:
        t = d["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n缺陷分布:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count} 个")

    # 按严重度统计
    severity_counts = {}
    for d in defects:
        s = d["severity"]
        severity_counts[s] = severity_counts.get(s, 0) + 1

    print(f"\n严重度分布:")
    for s in ["Critical", "High", "Medium", "Low"]:
        count = severity_counts.get(s, 0)
        if count > 0:
            print(f"  {s}: {count} 个")

    # 缺陷详情
    print(f"\n缺陷详情:")
    for i, d in enumerate(defects[:15], 1):
        print(f"  {i}. [{d['severity']}] {d['type']} (置信度 {d['confidence']:.0%})")
        print(f"     可能根因: {', '.join(d['likely_causes'][:2])}")

    print(f"{'='*60}\n")


def run_demo():
    """演示 - 电商数据分析智能体缺陷场景"""
    print("=" * 60)
    print("电商数据分析智能体 - 缺陷分类与根因定位演示")
    print("=" * 60)

    # 模拟电商场景缺陷日志
    mock_defects = [
        {"phase": "planning", "error": "JSON 解析失败：月度报告子任务数量 12 个"},
        {"phase": "executing", "error": "工具 'browser_read' 不适用于 CSV 分析，应使用 code_executor 或 search"},
        {"phase": "executing", "error": "search 执行超时（10 秒限制）"},
        {"phase": "summarizing", "error": "促销效果分析输出过短，缺少关键指标"},
        {"phase": "planning", "error": "安全拦截：检测到 Prompt注入"},
        {"phase": "executing", "error": "代码执行失败：客单价计算中 order_count 字段误用为 sales_amount"},
        {"phase": "planning", "error": "依赖环检测：查询数据 → 生成报告 → 查询数据"},
        {"phase": "executing", "error": "search（报告类）执行超时（10 秒限制）"},
        {"phase": "summarizing", "error": "幻觉检测：编造了不存在的销售数据（618 大促数据在 5 月报告中）"},
        {"phase": "planning", "error": "JSON 解析失败：格式错误"},
        {"phase": "executing", "error": "安全拦截：报告中明文展示客户手机号 13812345678"},
        {"phase": "summarizing", "error": "记忆缺陷：用户要求按月统计，结果按天输出了"},
        {"phase": "summarizing", "error": "知识缺陷：同比增速计算错误，实际是环比增速"},
        {"phase": "executing", "error": "性能缺陷：逐条查询 1000 个订单详情，Token 消耗 12000+"},
    ]

    defects = []
    for log in mock_defects:
        result = classify_defect(log, log["error"])
        severity = assess_severity(result["type"], 0.7, len(mock_defects))
        result.update(severity)
        defects.append(result)

    print_defect_report(defects)

    print("=" * 60)


if __name__ == "__main__":
    run_demo()
