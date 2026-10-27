# test_login_data_driven_example.py - 登录数据驱动测试示例
"""
登录功能数据驱动测试示例（需 Appium + 真机/模拟器；**未设置 APP_PACKAGE，或误开 ANDROID_BROWSER=chrome 时整模块跳过**）。

适用于大批登录用例场景：
1. 编写一次核心流程代码
2. 在 YAML 中准备测试数据（如 testcases/data/login_users.yaml）
3. 自动执行所有用例

注意：下方步骤仍为占位演示（TODO），接上真实 Page Object 与业务断言后即可在已配置 APP_PACKAGE 时执行。
与 test_appium_demo（真机 Chrome + MOCK_SERVER_URL）会话不同：**原生用例请勿设置 ANDROID_BROWSER=chrome**；
勿与 Chrome Mock 混在同一 pytest 进程，见 conftest.py 中 pytest_collection_modifyitems。
"""

import os

import pytest
import allure
from core.data_driver import DataDriver
from utils.allure_helper import AllureHelper
from utils.logger import Logger

logger = Logger().get_logger()

_pkg = os.getenv("APP_PACKAGE", "").strip()
_chrome = os.getenv("ANDROID_BROWSER", "").strip().lower() in ("chrome", "chromium", "browser")

pytestmark = pytest.mark.skipif(
    not _pkg or _chrome,
    reason="原生 App 数据驱动：须设置 APP_PACKAGE（可选 APP_ACTIVITY），且不要设置 ANDROID_BROWSER=chrome；"
           "与 test_appium_demo 勿同进程混跑。",
)


@allure.epic("用户登录")
@allure.feature("登录功能数据驱动测试")
class TestLoginDataDriven:
    """
    登录功能数据驱动测试类
    
    使用数据驱动测试，一次编写流程，覆盖所有登录用例
    """
    
    @pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
    @pytest.mark.android
    @pytest.mark.ios
    def test_login(self, driver, test_data):
        """
        数据驱动登录测试
        
        参数：
        - test_data: 从YAML文件加载的测试数据
        
        注意：
        - 需要在testcases/data/login_users.yaml中准备测试数据
        - 每个测试数据会生成一个独立的测试用例
        """
        # 从测试数据中获取参数
        username = test_data.get("username", "")
        password = test_data.get("password", "")
        expected_result = test_data.get("expected_result", "success")  # "success" 或 "fail"
        error_message = test_data.get("error_message", "")
        case_name = test_data.get("name", f"登录测试-{username}")
        description = test_data.get("description", "")
        
        # 设置Allure报告信息
        allure.dynamic.title(case_name)
        if description:
            allure.dynamic.description(description)
        
        logger.info(f"开始执行登录测试: {case_name}")
        logger.info(f"用户名: {username}, 预期结果: {expected_result}")
        
        # 注意：这里需要根据实际应用的页面对象来修改
        # 以下是示例代码，需要替换为实际的Page对象和方法
        
        try:
            # TODO: 替换为实际的登录页面对象
            # from pages.login_page import LoginPage
            # login_page = LoginPage(driver)
            
            with allure.step(f"输入用户名: {username}"):
                # TODO: 替换为实际的输入方法
                # login_page.input_username(username)
                logger.info(f"输入用户名: {username}")
                AllureHelper.attach_screenshot(driver, f"输入用户名_{username}")
            
            with allure.step(f"输入密码: {'*' * len(password)}"):
                # TODO: 替换为实际的输入方法
                # login_page.input_password(password)
                logger.info(f"输入密码")
                AllureHelper.attach_screenshot(driver, "输入密码")
            
            with allure.step("点击登录按钮"):
                # TODO: 替换为实际的点击方法
                # login_page.click_login_button()
                logger.info("点击登录按钮")
                AllureHelper.attach_screenshot(driver, "点击登录前")
            
            # 等待登录结果
            import time
            time.sleep(2)
            
            with allure.step(f"验证登录结果: {expected_result}"):
                if expected_result == "success":
                    # 验证登录成功
                    # TODO: 替换为实际的验证方法
                    # assert login_page.is_logged_in(), f"登录应该成功，但失败了"
                    logger.info(" 验证登录成功")
                    AllureHelper.attach_screenshot(driver, "登录成功")
                    allure.attach("登录成功", "验证结果", allure.attachment_type.TEXT)
                    
                else:
                    # 验证登录失败
                    # TODO: 替换为实际的验证方法
                    # assert login_page.has_error_message(error_message), \
                    #     f"应该显示错误信息: {error_message}"
                    logger.info(f" 验证登录失败，错误信息: {error_message}")
                    AllureHelper.attach_screenshot(driver, "登录失败")
                    allure.attach(
                        f"登录失败，错误信息: {error_message}",
                        "验证结果",
                        allure.attachment_type.TEXT
                    )
            
            logger.info(f" 测试完成: {case_name}")
            
        except Exception as e:
            logger.error(f"测试执行失败: {case_name}, 错误: {str(e)}")
            AllureHelper.attach_screenshot(driver, f"失败截图_{case_name}")
            allure.attach(
                f"测试执行失败: {str(e)}",
                "错误信息",
                allure.attachment_type.TEXT
            )
            raise


# 示例：如果需要在同一个测试中处理多个测试数据文件
class TestLoginMultipleDataFiles:
    """多数据文件登录测试示例"""
    
    @pytest.mark.parametrize("test_data", DataDriver.load_data("testcases/data/login_users.yaml"))
    @pytest.mark.smoke
    def test_smoke_login(self, driver, test_data):
        """冒烟测试：只测试正常登录场景"""
        if test_data.get("expected_result") == "success":
            # 复用上面的测试逻辑
            TestLoginDataDriven.test_login(driver, test_data)

