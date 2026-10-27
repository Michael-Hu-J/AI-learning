# test_router.py - 测试用例路由器
"""
测试用例路由器
功能：根据测试用例类型，智能选择使用接口测试还是UI测试
"""
from enum import Enum
from typing import Dict, Any, Optional
from utils.logger import Logger

logger = Logger().get_logger()


class TestType(Enum):
    """测试类型枚举"""
    API = "api"  # 接口测试
    UI = "ui"  # UI测试
    HYBRID = "hybrid"  # 混合测试（先接口后UI）


class TestRouter:
    """
    测试用例路由器
    
    作用：
    1. 根据测试用例的特征，决定使用接口测试还是UI测试
    2. 支持混合测试模式（接口准备数据 + UI验证）
    """
    
    # 接口测试关键词（如果用例包含这些，优先使用接口测试）
    API_KEYWORDS = [
        "接口", "api", "API", "请求", "响应", "http", "rest", "restful",
        "数据准备", "数据清理", "批量操作", "后台", "服务端"
    ]
    
    # UI测试关键词（如果用例包含这些，使用UI测试）
    UI_KEYWORDS = [
        "界面", "页面", "UI", "点击", "输入", "滑动", "显示", "展示",
        "按钮", "输入框", "下拉", "弹窗", "跳转", "导航"
    ]
    
    @classmethod
    def determine_test_type(cls, test_case: Dict[str, Any]) -> TestType:
        """
        根据测试用例内容，判断应该使用哪种测试方式
        
        参数：
        - test_case: 测试用例字典，包含name、description、steps等字段
        
        返回：
        - TestType: 测试类型
        """
        # 如果用例明确指定了测试类型
        if "test_type" in test_case:
            test_type = test_case["test_type"].lower()
            if test_type in ["api", "接口"]:
                return TestType.API
            elif test_type in ["ui", "界面"]:
                return TestType.UI
            elif test_type in ["hybrid", "混合"]:
                return TestType.HYBRID
        
        # 根据用例名称和描述判断
        name = test_case.get("name", "").lower()
        description = test_case.get("description", "").lower()
        steps = " ".join([step.get("action", "").lower() for step in test_case.get("steps", [])])
        
        text = f"{name} {description} {steps}"
        
        # 统计关键词出现次数
        api_count = sum(1 for keyword in cls.API_KEYWORDS if keyword.lower() in text)
        ui_count = sum(1 for keyword in cls.UI_KEYWORDS if keyword.lower() in text)
        
        logger.debug(f"测试用例关键词统计 - API: {api_count}, UI: {ui_count}")
        
        # 判断逻辑
        if api_count > ui_count and api_count > 0:
            logger.info(f"选择接口测试: {test_case.get('name')}")
            return TestType.API
        elif ui_count > api_count and ui_count > 0:
            logger.info(f"选择UI测试: {test_case.get('name')}")
            return TestType.UI
        else:
            # 默认使用UI测试（因为UI测试更能验证用户体验）
            logger.info(f"默认选择UI测试: {test_case.get('name')}")
            return TestType.UI
    
    @classmethod
    def should_use_api(cls, test_case: Dict[str, Any]) -> bool:
        """
        判断是否应该使用接口测试
        
        返回：
        - bool: True表示使用接口测试，False表示使用UI测试
        """
        test_type = cls.determine_test_type(test_case)
        return test_type in [TestType.API, TestType.HYBRID]
    
    @classmethod
    def should_use_ui(cls, test_case: Dict[str, Any]) -> bool:
        """
        判断是否应该使用UI测试
        
        返回：
        - bool: True表示使用UI测试，False表示使用接口测试
        """
        test_type = cls.determine_test_type(test_case)
        return test_type in [TestType.UI, TestType.HYBRID]
    
    @classmethod
    def is_hybrid(cls, test_case: Dict[str, Any]) -> bool:
        """
        判断是否是混合测试
        
        返回：
        - bool: True表示混合测试
        """
        test_type = cls.determine_test_type(test_case)
        return test_type == TestType.HYBRID

