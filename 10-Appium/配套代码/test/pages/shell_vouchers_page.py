# shell_vouchers_page.py - 优惠券页面
"""
ShellVouchersPage 页面对象
优惠券（Vouchers）页面
"""
import time
from base.base_page import BasePage
from utils.logger import Logger

logger = Logger().get_logger()


class ShellVouchersPage(BasePage):
    """
    优惠券页面类

    元素定位和操作封装
    """

    # ==================== 元素定位 ====================
    # Bill & Payment 标签
    TAB_BILL_PAYMENT = ("xpath", "//*[@text='Bill & Payment' or contains(@text, 'Bill')]")

    # 内购/门店券等第二分段标签（请按实际产品界面文案或 resource-id 修改）
    TAB_SEGMENT_SECOND = ("xpath", "//*[@content-desc='vouchers_tab_segment_2']")

    # Partner Rewards 标签
    TAB_PARTNER_REWARDS = ("xpath", "//*[@text='Partner Rewards']")

    # 第一个Use按钮（在Bill & Payment标签下）
    FIRST_USE_BUTTON = ("xpath", "(//*[@text='Use' or contains(@text, 'Use')])[1]")

    # 第一个Use按钮（更精确的定位，在优惠券卡片中的Use按钮）
    FIRST_USE_BUTTON_IN_CARD = ("xpath", "(//*[@text='Bill & Payment' or contains(@text, 'Bill')]/following::*//*[@text='Use'])[1]")

    def __init__(self, driver):
        """
        初始化页面对象

        参数：
        - driver: WebDriver实例
        """
        super().__init__(driver)
        logger.info("初始化优惠券页面")

    # ==================== 操作方法 ====================
    def click_bill_payment_tab(self):
        """
        点击Bill & Payment标签
        """
        logger.info("点击Bill & Payment标签")
        try:
            self.click(*self.TAB_BILL_PAYMENT)
            time.sleep(1)  # 等待标签切换
        except Exception as e:
            logger.warning(f"Bill & Payment标签可能已经选中或定位失败: {e}")
            # 如果已经选中，不报错，继续执行

    def click_first_use_button(self):
        """
        点击第一个Use按钮

        在Bill & Payment标签下的第一个优惠券的Use按钮

        定位策略：
        1. 先确认在Bill & Payment标签（如果未选中）
        2. 定位第一个Use按钮（在第一个优惠券卡片中）
        """
        logger.info("点击第一个Use按钮")

        # 先确认在Bill & Payment标签（如果未选中）
        try:
            self.click_bill_payment_tab()
            time.sleep(1)
        except Exception:
            # 标签可能已经选中，继续执行
            logger.info("Bill & Payment标签可能已经选中")

        # 尝试多种方式定位第一个Use按钮
        try:
            # 方式1：定位Bill & Payment标签下的第一个Use按钮
            logger.info("尝试方式1：定位Bill & Payment标签下的第一个Use按钮")
            self.click(*self.FIRST_USE_BUTTON_IN_CARD)
            self.wait(2)
            logger.info("方式1成功：点击了第一个Use按钮")
        except Exception as e1:
            logger.warning(f"方式1定位失败: {e1}")
            try:
                # 方式2：直接定位页面中第一个Use按钮
                logger.info("尝试方式2：定位页面中第一个Use按钮")
                self.click(*self.FIRST_USE_BUTTON)
                self.wait(2)
                logger.info("方式2成功：点击了第一个Use按钮")
            except Exception as e2:
                logger.warning(f"方式2定位失败: {e2}")
                try:
                    # 方式3：通过XPath查找所有Use按钮，点击第一个
                    logger.info("尝试方式3：通过XPath查找所有Use按钮")
                    use_buttons = self.find_elements("xpath", "//*[@text='Use' or contains(@text, 'Use')]")
                    if use_buttons and len(use_buttons) > 0:
                        use_buttons[0].click()
                        time.sleep(2)
                        logger.info("方式3成功：点击了第一个Use按钮")
                    else:
                        raise Exception("未找到Use按钮")
                except Exception as e3:
                    logger.error(f"所有定位方式都失败: {e3}")
                    # 截图以便调试
                    self.screenshot_helper.take_screenshot("use_button_not_found")
                    raise
