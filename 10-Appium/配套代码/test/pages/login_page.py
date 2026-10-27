# login_page.py - 登录页面对象
"""
登录页面Page Object
基于设计稿和测试用例生成
"""
import time
from base.base_page import BasePage
from utils.logger import Logger

logger = Logger().get_logger()


class LoginPage(BasePage):
    """登录页面对象"""
    
    # 元素定位（需要根据实际App更新）
    # 这些ID是示例，需要通过Appium Inspector获取真实ID
    LOGIN_TITLE = ("accessibility_id", "login_title")  # 登录标题/Logo
    PHONE_EMAIL_INPUT = ("accessibility_id", "phone_email_input")  # 手机号/邮箱输入框
    PASSWORD_INPUT = ("accessibility_id", "password_input")  # 密码输入框
    LOGIN_BUTTON = ("accessibility_id", "login_button")  # 登录按钮
    FORGOT_PASSWORD_LINK = ("accessibility_id", "forgot_password_link")  # 忘记密码链接
    REGISTER_LINK = ("accessibility_id", "register_link")  # 注册链接
    
    def __init__(self, driver):
        """
        初始化登录页面
        
        参数：
        - driver: Appium driver
        """
        super().__init__(driver)
        logger.info("初始化登录页面")
    
    def input_phone_email(self, value: str):
        """
        输入手机号/邮箱
        
        参数：
        - value: 手机号或邮箱
        """
        logger.info(f"输入手机号/邮箱: {value}")
        self.input_text(*self.PHONE_EMAIL_INPUT, value)
        time.sleep(0.5)
    
    def input_password(self, value: str):
        """
        输入密码
        
        参数：
        - value: 密码
        """
        logger.info(f"输入密码: {value}")
        self.input_text(*self.PASSWORD_INPUT, value)
        time.sleep(0.5)
    
    def click_login_button(self):
        """点击登录按钮"""
        logger.info("点击登录按钮")
        self.click(*self.LOGIN_BUTTON)
        time.sleep(2)
    
    def click_forgot_password_link(self):
        """点击忘记密码链接"""
        logger.info("点击忘记密码链接")
        self.click(*self.FORGOT_PASSWORD_LINK)
        time.sleep(2)
    
    def click_register_link(self):
        """点击注册链接"""
        logger.info("点击注册链接")
        self.click(*self.REGISTER_LINK)
        time.sleep(2)
    
    def verify_login_title_exists(self) -> bool:
        """
        验证登录标题/Logo是否存在
        
        返回：
        - bool: 是否存在
        """
        try:
            element = self.find_element(*self.LOGIN_TITLE, timeout=5)
            return element is not None and element.is_displayed()
        except Exception as e:
            logger.warning(f"验证登录标题失败: {str(e)}")
            return False
    
    def verify_phone_email_input_enabled(self) -> bool:
        """
        验证手机号/邮箱输入框是否可编辑
        
        返回：
        - bool: 是否可编辑
        """
        try:
            element = self.find_element(*self.PHONE_EMAIL_INPUT, timeout=5)
            return element is not None and element.is_enabled()
        except Exception as e:
            logger.warning(f"验证输入框失败: {str(e)}")
            return False
    
    def verify_password_input_enabled(self) -> bool:
        """
        验证密码输入框是否可编辑
        
        返回：
        - bool: 是否可编辑
        """
        try:
            element = self.find_element(*self.PASSWORD_INPUT, timeout=5)
            return element is not None and element.is_enabled()
        except Exception as e:
            logger.warning(f"验证密码输入框失败: {str(e)}")
            return False
    
    def verify_login_button_enabled(self) -> bool:
        """
        验证登录按钮是否可点击
        
        返回：
        - bool: 是否可点击
        """
        try:
            element = self.find_element(*self.LOGIN_BUTTON, timeout=5)
            return element is not None and element.is_enabled()
        except Exception as e:
            logger.warning(f"验证登录按钮失败: {str(e)}")
            return False
    
    def get_phone_email_input_text(self) -> str:
        """
        获取手机号/邮箱输入框的文本
        
        返回：
        - str: 输入框文本
        """
        try:
            element = self.find_element(*self.PHONE_EMAIL_INPUT, timeout=5)
            return element.text if element else ""
        except Exception as e:
            logger.warning(f"获取输入框文本失败: {str(e)}")
            return ""
