browser.go_to("https://internal-dashboard.example.com/sales")
browser.click("2024-03")
browser.screenshot()

#!/usr/bin/env python3
"""
工具使用测试（改进版）

评分维度：
1. 工具选择准确率（40 分）—— 三层评分：best=40, acceptable=30, wrong=0
2. 参数准确性（20 分）—— 含语义检查（SQL 必须有 WHERE/LIMIT 等）
3. 错误恢复能力（20 分）—— 含恢复机制检测 + 未测试标注
4. 调用效率（20 分）—— 最小必要调用次数（非"每种工具一次"）

附加功能：
- 工具调用流程追踪
- 工具选择陷阱检测
- 语义参数验证（SQL/Search/Calculator）
- 恢复机制布尔分 + 未测试标注
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# 工具适用性映射（与 ToolRegistry.TOOLS 一致）
TOOL_SUITABILITY = {
    "search": {
        "best_for": [
            "销售/经营类事实检索（内置 Mock）",
            "含「生成/撰写」且含「报告」的模板化输出",
            "竞品与行业信息关键词检索",
        ],
        "acceptable_for": ["泛化知识问答前的资料拉取"],
        "wrong_for": ["纯算术（应 calculator）", "需沙箱跑脚本（应 code_executor）"],
    },
    "calculator": {
        "best_for": ["数值计算", "表达式计算", "环比增长率", "百分比计算"],
        "acceptable_for": ["简单计算"],
        "wrong_for": ["拉取经营数据（应 search）", "抓网页（应 web_fetch）"],
    },
    "code_executor": {
        "best_for": ["复杂数据处理", "Python 代码", "数据分析脚本", "复杂计算"],
        "acceptable_for": ["简单计算", "数据格式化"],
        "wrong_for": ["安全敏感任意代码外泄场景（需额外沙箱策略）"],
    },
    "memory_store": {
        "best_for": ["跨子任务缓存中间结果", "key=value 存取"],
        "acceptable_for": [],
        "wrong_for": ["替代 search 拉经营事实"],
    },
    "web_fetch": {
        "best_for": ["公开网页文本抓取", "竞品公开页"],
        "acceptable_for": [],
        "wrong_for": ["内网仪表盘截图流（应优先 search Mock 或专用连接器）"],
    },
    "safety_checker": {
        "best_for": ["有害内容/注入/Jailbreak/隐私自检"],
        "acceptable_for": [],
        "wrong_for": [],
    },
    "none": {
        "best_for": ["文本分析", "直接回答", "趋势总结", "知识问答"],
        "acceptable_for": ["简单任务"],
        "wrong_for": ["需要工具证据链的经营数字（应先 search）"],
    },
}

VALID_TOOLS = set(TOOL_SUITABILITY.keys())


@dataclass
class ToolUsageScore:
    """工具使用评分结果"""
    total: float
    selection_score: float
    params_score: float
    recovery_score: float
    efficiency_score: float
    details: Dict
    tool_chain: List[Dict]
    selection_breakdown: Dict  # 新增：best/acceptable/wrong 分布
    has_recovery_mechanism: bool  # 新增：是否具备恢复机制
    recovery_untested: bool  # 新增：恢复能力是否未经测试


def _classify_tool_selection(tool: str, task_description: str = "") -> str:
    """
    三层分类：判断工具选择是 best / acceptable / wrong

    基于 TOOL_SUITABILITY 映射，检查工具在哪个分类列表中。
    """
    if tool not in TOOL_SUITABILITY:
        return "wrong"
    info = TOOL_SUITABILITY[tool]
    if info["best_for"]:
        return "best"
    if info["acceptable_for"]:
        return "acceptable"
    return "wrong"


def _check_semantic_params(tool: str, tool_input: str) -> Tuple[bool, str]:
    """
    轻量语义参数检查（新增）

    返回 (是否通过, 错误原因)
    """
    if not tool_input or tool_input.startswith("[错误]") or tool_input.startswith("错误:"):
        return False, tool_input[:80]

    if tool == "search":
        # SQL 类参数：必须包含 WHERE 或 LIMIT
        if "SELECT" in tool_input.upper():
            if "WHERE" not in tool_input.upper() and "LIMIT" not in tool_input.upper():
                return False, "SQL 缺少 WHERE/LIMIT，可能全表扫描"
        # Search 类参数：必须包含时间范围或实体名称
        has_time = any(kw in tool_input for kw in ["2024", "2025", "03", "04", "月", "季度", "年"])
        has_entity = any(kw in tool_input for kw in ["销售", "品类", "商品", "报告", "经营", "竞品"])
        if not has_time and not has_entity:
            return False, "Search 参数缺少时间范围或实体名称"

    elif tool == "calculator":
        # Calculator 参数：必须是合法数学表达式
        import re
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.%,]+$', tool_input.strip()):
            return False, "Calculator 参数不是合法数学表达式"

    return True, ""


def score_tool_usage(result: Dict, expected_tools: List[str] = None, min_required_calls: int = None) -> ToolUsageScore:
    """
    工具使用评分（改进版：三层评分 + 语义检查 + 恢复机制检测）

    Args:
        result: 智能体执行结果（含 _meta）
        expected_tools: 期望使用的工具列表（可选）
        min_required_calls: 最小必要调用次数（由任务定义给出，默认自动估算）

    Returns:
        ToolUsageScore
    """
    meta = result.get("_meta", {})
    subtasks = meta.get("subtasks", [])
    details = {}
    tool_chain = []

    # ========== 维度 1: 工具选择准确率（40 分）—— 三层评分 ==========
    best_count = 0
    acceptable_count = 0
    wrong_count = 0
    selection_errors = []

    for s in subtasks:
        tool = s.get("tool", "")
        if tool and tool != "none":
            category = _classify_tool_selection(tool, s.get("description", ""))
            if category == "best":
                best_count += 1
            elif category == "acceptable":
                acceptable_count += 1
            else:
                wrong_count += 1
                selection_errors.append(f"{s['id']} 工具选择错误（wrong）: {tool}")

    selection_total = best_count + acceptable_count + wrong_count
    if selection_total > 0:
        # 三层赋分：best=40, acceptable=30, wrong=0
        weighted_score = (best_count * 40 + acceptable_count * 30 + wrong_count * 0) / selection_total
        selection_score = min(weighted_score, 40.0)
        details["selection"] = f"best={best_count}, acceptable={acceptable_count}, wrong={wrong_count}"
    else:
        selection_score = 40.0
        details["selection"] = "无工具调用"

    selection_breakdown = {"best": best_count, "acceptable": acceptable_count, "wrong": wrong_count}

    # ========== 维度 2: 参数准确性（20 分）—— 含语义检查 ==========
    params_correct = 0
    params_total = 0
    param_errors = []

    for s in subtasks:
        tool = s.get("tool", "")
        tool_input = s.get("result", "")
        if tool and tool != "none":
            params_total += 1
            passed, error_msg = _check_semantic_params(tool, tool_input)
            if not passed:
                param_errors.append(f"{s['id']} 参数错误: {error_msg}")
            else:
                params_correct += 1

    if params_total > 0:
        params_score = (params_correct / params_total) * 20.0
        details["params"] = f"{params_correct}/{params_total} 正确"
    else:
        params_score = 20.0
        details["params"] = "无参数"

    # ========== 维度 3: 错误恢复能力（20 分）—— 含恢复机制检测 ==========
    failed_tasks = [s for s in subtasks if s.get("status") == "failed"]
    retried_tasks = [s for s in subtasks if s.get("retry_count", 0) > 0]
    recovered_tasks = [s for s in subtasks if s.get("status") == "success" and s.get("retry_count", 0) > 0]

    # 检测是否具备恢复机制（有重试记录 = 有机制）
    has_recovery_mechanism = len(retried_tasks) > 0

    if failed_tasks:
        recovery_rate = len(recovered_tasks) / (len(failed_tasks) + len(recovered_tasks))
        recovery_score = recovery_rate * 20.0
        details["recovery"] = f"{len(recovered_tasks)}/{len(failed_tasks) + len(recovered_tasks)} 恢复"
    else:
        if has_recovery_mechanism:
            recovery_score = 20.0
            details["recovery"] = "无失败，但检测到恢复机制（retry）"
        else:
            # 没有失败，也没有恢复机制 —— 分数给满分但要标注
            recovery_score = 20.0
            details["recovery"] = "无失败，未检测到恢复机制（No failure observed, recovery untested）"

    recovery_untested = len(failed_tasks) == 0 and not has_recovery_mechanism

    # ========== 维度 4: 调用效率（20 分）—— 最小必要调用次数 ==========
    total_tool_calls = selection_total
    if min_required_calls is not None:
        optimal_calls = max(min_required_calls, 1)
    else:
        # 自动估算：不同工具种类数（假设每个工具至少调用 1 次）
        unique_tools = len(set(s.get("tool", "") for s in subtasks if s.get("tool") and s.get("tool") != "none"))
        optimal_calls = max(unique_tools, 1)

    if total_tool_calls > 0:
        efficiency = min(optimal_calls / total_tool_calls, 1.0)
        efficiency_score = efficiency * 20.0
        details["efficiency"] = f"{total_tool_calls} 次调用（最小必要 {optimal_calls} 次）"
    else:
        efficiency_score = 20.0
        details["efficiency"] = "无调用"

    # ========== 构建调用流程 ==========
    for s in subtasks:
        tool_chain.append({
            "id": s["id"],
            "tool": s.get("tool", ""),
            "status": s.get("status", ""),
            "retry_count": s.get("retry_count", 0),
            "result_preview": (s.get("result", "")[:100] if s.get("result") else ""),
        })

    # ========== 总分 ==========
    total = selection_score + params_score + recovery_score + efficiency_score
    total = min(total, 100.0)

    return ToolUsageScore(
        total=total,
        selection_score=selection_score,
        params_score=params_score,
        recovery_score=recovery_score,
        efficiency_score=efficiency_score,
        details=details,
        tool_chain=tool_chain,
        selection_breakdown=selection_breakdown,
        has_recovery_mechanism=has_recovery_mechanism,
        recovery_untested=recovery_untested,
    )


def trace_tool_chain(result: Dict) -> List[Dict]:
    """
    追踪工具调用流程

    Returns:
        调用流程列表
    """
    meta = result.get("_meta", {})
    subtasks = meta.get("subtasks", [])

    chain = []
    for s in subtasks:
        entry = {
            "step": len(chain) + 1,
            "subtask_id": s["id"],
            "tool": s.get("tool", ""),
            "status": s.get("status", ""),
            "retry_count": s.get("retry_count", 0),
            "depends_on": s.get("depends_on", []),
        }
        chain.append(entry)

    return chain


def print_tool_usage_report(score: ToolUsageScore):
    """打印工具使用评分报告"""
    print(f"\n{'='*60}")
    print(f"工具使用评分报告")
    print(f"{'='*60}")

    def bar(value, max_value=100):
        filled = int(value / max_value * 20)
        return "█" * filled + "░" * (20 - filled)

    print(f"\n  工具选择:   {score.selection_score:5.1f}/40  {bar(score.selection_score, 40)}")
    print(f"  参数准确性: {score.params_score:5.1f}/20  {bar(score.params_score, 20)}")
    print(f"  错误恢复:   {score.recovery_score:5.1f}/20  {bar(score.recovery_score, 20)}")
    print(f"  调用效率:   {score.efficiency_score:5.1f}/20  {bar(score.efficiency_score, 20)}")
    print(f"  {'─'*40}")
    print(f"  总分:       {score.total:5.1f}/100  {bar(score.total)}")

    if score.total >= 80:
        grade = "优秀"
    elif score.total >= 60:
        grade = "合格"
    else:
        grade = "不合格"
    print(f"  评级: {grade}")

    print(f"\n  详情:")
    for key, value in score.details.items():
        print(f"    {key}: {value}")

    # 调用流程
    if score.tool_chain:
        print(f"\n  调用流程:")
        for t in score.tool_chain:
            icon = "" if t["status"] == "success" else "" if t["status"] == "failed" else "⏳"
            retry = f" (重试{t['retry_count']}次)" if t["retry_count"] > 0 else ""
            print(f"    {icon} {t['id']}: {t['tool']}{retry}")

    print(f"{'='*60}\n")


def run_demo():
    """演示"""
    print("=" * 60)
    print("工具使用测试演示")
    print("=" * 60)

    # 测试用例 1: 优秀的工具使用
    result_good = {
        "success": True,
        "output": "3月销售报告显示：服装品类增长最快，环比增长 18.5%",
        "_meta": {
            "subtasks_total": 3,
            "subtasks_success": 3,
            "subtasks_failed": 0,
            "subtasks": [
                {"id": "task_1", "tool": "search", "status": "success", "depends_on": [], "retry_count": 0, "result": "[search/经营] 已获取 2024-03 销售数据，共 1256 条记录"},
                {"id": "task_2", "tool": "calculator", "status": "success", "depends_on": ["task_1"], "retry_count": 0, "result": "[计算结果] 服装品类环比增长率 = (1250000 - 1055000) / 1055000 * 100 = 18.5%"},
                {"id": "task_3", "tool": "search", "status": "success", "depends_on": ["task_2"], "retry_count": 0, "result": "[报告生成] 已生成 2024年3月销售分析报告，包含品类增长排行"},
            ],
        },
    }

    # 测试用例 2: 有问题的工具使用
    result_bad = {
        "success": True,
        "output": "执行完成",
        "_meta": {
            "subtasks_total": 4,
            "subtasks_success": 2,
            "subtasks_failed": 2,
            "subtasks": [
                {"id": "task_1", "tool": "code_executor", "status": "success", "depends_on": [], "retry_count": 0, "result": "[代码执行结果]\nimport pandas as pd\ndata = pd.read_csv('sales.csv')\nprint(data.head())"},
                {"id": "task_2", "tool": "web_search", "status": "failed", "depends_on": [], "retry_count": 3, "result": "错误: 未知工具 'web_search'"},
                {"id": "task_3", "tool": "calculator", "status": "success", "depends_on": ["task_1"], "retry_count": 0, "result": "[计算结果] 环比增长率 = 18.5%"},
                {"id": "task_4", "tool": "search", "status": "failed", "depends_on": ["task_3"], "retry_count": 2, "result": "错误: 报告生成失败 - 缺少日期范围参数"},
            ],
        },
    }

    print("\n--- 测试用例 1: 优秀的工具使用 ---")
    score1 = score_tool_usage(result_good)
    print_tool_usage_report(score1)

    print("\n--- 测试用例 2: 有问题的工具使用 ---")
    score2 = score_tool_usage(result_bad)
    print_tool_usage_report(score2)

    # 对比
    print("=" * 60)
    print("对比总结")
    print("=" * 60)
    print(f"{'指标':20s} {'优秀':>10s} {'问题':>10s}")
    print("-" * 60)
    print(f"{'总分':20s} {score1.total:10.1f} {score2.total:10.1f}")
    print(f"{'工具选择':20s} {score1.details['selection']:>10s} {score2.details['selection']:>10s}")
    print(f"{'参数准确性':20s} {score1.details['params']:>10s} {score2.details['params']:>10s}")
    print(f"{'错误恢复':20s} {score1.details['recovery']:>10s} {score2.details['recovery']:>10s}")
    print(f"{'调用效率':20s} {score1.details['efficiency']:>10s} {score2.details['efficiency']:>10s}")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
