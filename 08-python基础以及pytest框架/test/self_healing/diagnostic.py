# diagnostic.py - 失败智能诊断
"""
失败诊断模块

功能：
1. 自动分类失败原因（环境问题 vs 代码 bug vs 数据问题）
2. 提取根因（从长错误信息中提取关键信息）
3. 生成修复建议
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class FailureCategory:
    """失败原因分类"""
    ENVIRONMENT = "environment"       # 环境问题（服务挂了、网络不通、依赖缺失）
    CODE_BUG = "code_bug"             # 代码逻辑错误（断言失败、空指针等）
    DATA_ISSUE = "data_issue"         # 数据问题（测试数据不对、数据被污染）
    TIMEOUT = "timeout"               # 超时（元素等待超时、请求超时）
    FLAKY = "flaky"                   # 偶发性失败（概率性问题）
    UNKNOWN = "unknown"               # 无法识别


# 环境问题关键词
ENV_KEYWORDS = [
    "Connection refused",
    "Connection refused",
    "Cannot connect",
    "no such host",
    "connection refused",
    "Connection reset",
    "Connection timed out",
    "Name or service not known",
    "Unable to connect",
    "Service unavailable",
    "500 Server Error",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "ModuleNotFoundError",
    "ImportError: No module named",
    "selenium.common.exceptions.WebDriverException",
    "Appium UnknownError",
]

# 超时关键词
TIMEOUT_KEYWORDS = [
    "timeout",
    "Timeout",
    "Timed out",
    "waiting for element",
    "Element not found",
    "NoSuchElementException",
    "StaleElementReferenceException",
    "ElementClickInterceptedException",
    "TimeoutException",
    "Read timed out",
    "timed out",
]

# 数据问题关键词
DATA_KEYWORDS = [
    "duplicate",
    "Duplicate",
    "already exists",
    "Unique constraint",
    "foreign key constraint",
    "not found",
    "Invalid data",
    "DataError",
    "IntegrityError",
]

# 断言语义关键词（代码 bug）
ASSERT_KEYWORDS = [
    "AssertionError",
    "assert",
    "Expected",
    "expected",
    "not equal",
    "!= ",
    "failed",
]


def classify_failure(report) -> str:
    """分类失败原因"""
    error_text = _extract_error_text(report)
    if not error_text:
        return FailureCategory.UNKNOWN

    # 检查超时
    for kw in TIMEOUT_KEYWORDS:
        if kw.lower() in error_text.lower():
            return FailureCategory.TIMEOUT

    # 检查环境问题
    for kw in ENV_KEYWORDS:
        if kw in error_text:
            return FailureCategory.ENVIRONMENT

    # 检查数据问题
    for kw in DATA_KEYWORDS:
        if kw.lower() in error_text.lower():
            return FailureCategory.DATA_ISSUE

    # 检查断言失败
    for kw in ASSERT_KEYWORDS:
        if kw in error_text:
            return FailureCategory.CODE_BUG

    return FailureCategory.UNKNOWN


def _extract_error_text(report) -> str:
    """从 pytest 报告中提取错误文本"""
    if hasattr(report, 'longreprtext') and report.longreprtext:
        return report.longreprtext
    if hasattr(report, 'longrepr'):
        return str(report.longrepr)
    return ""


def extract_root_cause(report) -> Optional[str]:
    """
    提取根因。
    从长错误信息中提取最有价值的那一行。
    """
    error_text = _extract_error_text(report)
    if not error_text:
        return None

    lines = error_text.split("\n")

    # 找断言失败的行
    for line in lines:
        if "AssertionError" in line or "assert " in line:
            return line.strip()

    # 找异常类型
    for line in lines:
        if re.match(r"^[A-Za-z_]+(\.[A-Za-z_]+)*Error", line.strip()):
            return line.strip()
        if re.match(r"^[A-Za-z_]+(\.[A-Za-z_]+)*Exception", line.strip()):
            return line.strip()

    # 找第一个非空非 traceback 行
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("Traceback"):
            if not stripped.startswith("  File"):
                if not stripped.startswith("    "):
                    return stripped[:200]

    return error_text[:200]


def suggest_fix(category: str, root_cause: str = "") -> str:
    """根据失败分类生成修复建议"""
    suggestions = {
        FailureCategory.ENVIRONMENT: (
            "环境问题：检查目标服务是否启动、网络是否连通、"
            "依赖服务是否正常运行。\n"
            "  建议：先执行健康检查脚本确认环境状态，再重新跑测试。"
        ),
        FailureCategory.CODE_BUG: (
            "代码逻辑错误：检查断言逻辑、数据准备和期望值是否正确。\n"
            "  建议：本地调试复现，确认是代码 bug 还是测试数据问题。"
        ),
        FailureCategory.DATA_ISSUE: (
            "数据问题：检查测试数据是否被污染、唯一性约束、"
            "关联数据是否存在。\n"
            "  建议：重置测试数据后重试，或检查是否有并发操作覆盖了数据。"
        ),
        FailureCategory.TIMEOUT: (
            "超时失败：可能是网络延迟、服务响应慢、或元素定位失效。\n"
            "  建议：增加等待时间、检查元素定位器是否有效。"
            "如果偶发，重试通常能解决。"
        ),
        FailureCategory.FLAKY: (
            "偶发性失败：多次执行结果不一致。\n"
            "  建议：增加等待策略稳定性、避免共享状态、"
            "考虑标记为 flaky 后续排查。"
        ),
        FailureCategory.UNKNOWN: (
            "无法自动分类的失败原因。\n"
            "  建议：查看完整的 Allure 报告，人工分析失败原因。"
        ),
    }
    return suggestions.get(category, suggestions[FailureCategory.UNKNOWN])
