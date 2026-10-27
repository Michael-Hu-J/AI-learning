# register_page.py - 注册页面对象
"""
注册页面Page Object
基于设计稿生成
"""
import time
from base.base_page import BasePage
from utils.logger import Logger

logger = Logger().get_logger()


class RegisterPage(BasePage):
    """注册页面对象"""
    
    # 元素定位（需要根据实际App更新）
    # 这些ID是示例，需要通过Appium Inspector获取真实ID
    REGISTER_TITLE = ("accessibility_id", "register_title")  # 注册标题
    EMAIL_INPUT = ("accessibility_id", "email_input")  # 邮箱输入框
    PHONE_INPUT = ("accessibility_id", "phone_input")  # 手机号输入框
    PASSWORD_INPUT = ("accessibility_id", "password_input")  # 密码输入框
    CONFIRM_PASSWORD_INPUT = ("accessibility_id", "confirm_password_input")  # 确认密码输入框
    REGISTER_BUTTON = ("accessibility_id", "register_button")  # 注册按钮
    LOGIN_LINK = ("accessibility_id", "login_link")  # 登录链接
    
    def __init__(self, driver):
        """
        初始化注册页面
        
        参数：
        - driver: Appium driver
        """
        super().__init__(driver)
        logger.info("初始化注册页面")
    
    def input_email(self, value: str):
        """输入邮箱"""
        logger.info(f"输入邮箱: {value}")
        self.input_text(*self.EMAIL_INPUT, value)
        time.sleep(0.5)
    
    def input_phone(self, value: str):
        """输入手机号"""
        logger.info(f"输入手机号: {value}")
        self.input_text(*self.PHONE_INPUT, value)
        time.sleep(0.5)
    
    def input_password(self, value: str):
        """输入密码"""
        logger.info("输入密码")
        self.input_text(*self.PASSWORD_INPUT, value)
        time.sleep(0.5)
    
    def input_confirm_password(self, value: str):
        """输入确认密码"""
        logger.info("输入确认密码")
        self.input_text(*self.CONFIRM_PASSWORD_INPUT, value)
        time.sleep(0.5)
    
    def click_register_button(self):
        """点击注册按钮"""
        logger.info("点击注册按钮")
        self.click(*self.REGISTER_BUTTON)
        time.sleep(2)
    
    def click_login_link(self):
        """点击登录链接"""
        logger.info("点击登录链接")
        self.click(*self.LOGIN_LINK)
        time.sleep(2)

