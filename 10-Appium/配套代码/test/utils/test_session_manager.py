# test_session_manager.py - 测试会话管理器
"""
测试会话管理器
功能：管理每次测试运行的目录结构（报告目录、截图目录等）
命名规则：设备-类型-时间
例如：ios-ui-20251225_150852
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from utils.logger import Logger

logger = Logger().get_logger()

# 全局变量，存储当前会话的目录信息
_current_session_dir = None
_current_screenshot_dir = None
_current_report_dir = None


def get_test_type_from_env() -> str:
    """
    从环境变量获取测试类型
    
    返回：
    - str: 测试类型（api/ui/hybrid/visual），默认ui
    """
    test_type = os.getenv("TEST_TYPE", "ui").lower()
    # 验证测试类型
    valid_types = ["api", "ui", "hybrid", "visual"]
    if test_type not in valid_types:
        logger.warning(f"无效的测试类型: {test_type}，使用默认值: ui")
        test_type = "ui"
    return test_type


def get_platform_from_env() -> str:
    """
    从环境变量获取平台
    
    返回：
    - str: 平台（android/ios），默认android
    """
    platform = os.getenv("PLATFORM", "android").lower()
    # 验证平台
    valid_platforms = ["android", "ios"]
    if platform not in valid_platforms:
        logger.warning(f"无效的平台: {platform}，使用默认值: android")
        platform = "android"
    return platform


def create_session_directory(platform: Optional[str] = None, test_type: Optional[str] = None) -> dict:
    """
    创建本次测试会话的目录结构
    
    参数：
    - platform: 平台（android/ios），如果为None则从环境变量读取
    - test_type: 测试类型（api/ui/hybrid/visual），如果为None则从环境变量读取
    
    返回：
    - dict: 包含目录信息的字典
        {
            "session_name": "ios-ui-20251225_150852",
            "report_dir": "reports/ios-ui-20251225_150852",
            "screenshot_dir": "screenshots/ios-ui-20251225_150852",
            "allure_results_dir": "reports/ios-ui-20251225_150852/allure-results",
            "allure_report_dir": "reports/ios-ui-20251225_150852/allure-report"
        }
    """
    global _current_session_dir, _current_screenshot_dir, _current_report_dir
    
    # 获取平台和测试类型
    if platform is None:
        platform = get_platform_from_env()
    if test_type is None:
        test_type = get_test_type_from_env()
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 生成会话名称：设备-类型-时间
    session_name = f"{platform}-{test_type}-{timestamp}"
    
    # 创建目录结构
    base_dir = Path.cwd()
    
    # 报告目录：reports/设备-类型-时间/
    report_dir = base_dir / "reports" / session_name
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Allure结果目录：reports/设备-类型-时间/allure-results/
    allure_results_dir = report_dir / "allure-results"
    allure_results_dir.mkdir(parents=True, exist_ok=True)
    
    # Allure报告目录：reports/设备-类型-时间/allure-report/
    allure_report_dir = report_dir / "allure-report"
    allure_report_dir.mkdir(parents=True, exist_ok=True)
    
    # 截图目录：screenshots/设备-类型-时间/
    screenshot_dir = base_dir / "screenshots" / session_name
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存到全局变量
    _current_session_dir = session_name
    _current_screenshot_dir = str(screenshot_dir)
    _current_report_dir = str(report_dir)
    
    # 设置环境变量（供其他模块使用）
    os.environ["SESSION_NAME"] = session_name
    os.environ["ALLURE_RESULTS_DIR"] = str(allure_results_dir)
    os.environ["SCREENSHOT_DIR"] = str(screenshot_dir)
    os.environ["REPORT_DIR"] = str(report_dir)
    
    logger.info(f"创建测试会话目录: {session_name}")
    logger.info(f"  报告目录: {report_dir}")
    logger.info(f"  截图目录: {screenshot_dir}")
    logger.info(f"  Allure结果目录: {allure_results_dir}")
    
    return {
        "session_name": session_name,
        "report_dir": str(report_dir),
        "screenshot_dir": str(screenshot_dir),
        "allure_results_dir": str(allure_results_dir),
        "allure_report_dir": str(allure_report_dir)
    }


def get_session_info() -> dict:
    """
    获取当前会话的目录信息
    
    返回：
    - dict: 包含目录信息的字典，如果未初始化则返回None
    """
    if _current_session_dir is None:
        return None
    
    return {
        "session_name": _current_session_dir,
        "report_dir": _current_report_dir,
        "screenshot_dir": _current_screenshot_dir,
        "allure_results_dir": os.getenv("ALLURE_RESULTS_DIR"),
        "allure_report_dir": os.getenv("REPORT_DIR", "") + "/allure-report" if os.getenv("REPORT_DIR") else None
    }


def get_screenshot_dir() -> str:
    """
    获取当前会话的截图目录
    
    返回：
    - str: 截图目录路径
    """
    screenshot_dir = os.getenv("SCREENSHOT_DIR")
    if screenshot_dir:
        return screenshot_dir
    # 如果环境变量未设置，使用默认值
    return "screenshots"


def get_allure_results_dir() -> str:
    """
    获取当前会话的Allure结果目录
    
    返回：
    - str: Allure结果目录路径
    """
    allure_results_dir = os.getenv("ALLURE_RESULTS_DIR")
    if allure_results_dir:
        return allure_results_dir
    # 如果环境变量未设置，使用默认值
    return "reports/allure-results"


def get_report_dir() -> str:
    """
    获取当前会话的报告目录
    
    返回：
    - str: 报告目录路径
    """
    report_dir = os.getenv("REPORT_DIR")
    if report_dir:
        return report_dir
    # 如果环境变量未设置，使用默认值
    return "reports"

