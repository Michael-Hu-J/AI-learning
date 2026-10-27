# onboarding_page.py - 应用启动/欢迎页面对象（教学演示用）
"""
OnboardingPage 页面对象

虚构「示例商城 DemoStore」启动/欢迎页，与真实公司业务无关。
以下 resource-id、文案均为占位，接入真实 App 时请整段替换为你的元素策略。
"""
import time
from base.base_page import BasePage
from utils.logger import Logger

logger = Logger().get_logger()


class OnboardingPage(BasePage):
    """示例应用启动页：仅演示 POM 拆分与组合步骤写法。"""

    # ---------- 欢迎页区域（占位 id，请按被测包名与 id 修改）----------
    PAGE_TITLE = ("id", "demo_onboarding_title")
    PAGE_SUBTITLE = ("id", "demo_onboarding_subtitle")

    REGISTER_BUTTON = ("id", "demo_btn_register")
    LOGIN_BUTTON = ("id", "demo_btn_login")

    NAVIGATION_DOTS = ("id", "demo_onboarding_indicator")

    def __init__(self, driver):
        super().__init__(driver)
        logger.info("初始化示例启动页 OnboardingPage")
        time.sleep(2)

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """等待欢迎页加载完成。"""
        try:
            self.wait_for_element(*self.REGISTER_BUTTON, timeout=timeout)
            logger.info("启动页面加载完成")
            return True
        except Exception as e:
            logger.warning("等待启动页面加载超时: %s", e)
            return False

    def click_register(self):
        """点击注册入口（演示用）。"""
        logger.info("点击注册按钮")
        self.click(*self.REGISTER_BUTTON)
        time.sleep(2)

    def click_create_account(self):
        """点击注册入口 — 别名，兼容旧用例命名。"""
        self.click_register()

    def click_login(self):
        """点击登录入口（演示用）。"""
        logger.info("点击登录按钮")
        self.click(*self.LOGIN_BUTTON)
        time.sleep(2)

    def click_i_already_have_account(self):
        """点击登录入口 — 别名，兼容旧用例命名。"""
        self.click_login()

    def is_page_loaded(self) -> bool:
        """检查欢迎页是否已加载。"""
        try:
            if self.is_element_visible(*self.REGISTER_BUTTON, timeout=3):
                return True
            if self.is_element_visible(*self.PAGE_TITLE, timeout=2):
                return True
            return False
        except Exception:
            return False

    def get_page_title(self) -> str:
        """获取欢迎页标题文案。"""
        try:
            element = self.find_element(*self.PAGE_TITLE, timeout=5)
            return element.text
        except Exception:
            return ""
