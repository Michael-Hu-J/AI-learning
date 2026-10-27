# shell_home_page.py - 应用首页壳层（教学演示用）
"""
ShellHomePage 页面对象

虚构「示例商城 DemoStore」首页壳层，与真实公司业务无关。
以下 resource-id、文案均为占位，接入真实 App 时请整段替换为你的元素策略。
"""
from base.base_page import BasePage
from utils.logger import Logger

logger = Logger().get_logger()


class ShellHomePage(BasePage):
    """示例应用首页：仅演示 POM 拆分、组合步骤与多策略定位写法。"""

    # ---------- 顶部与通用区域（占位 id，请按被测包名与 id 修改）----------
    HEADER_BADGE = ("id", "demo_header_badge")
    APP_LOGO = ("id", "demo_app_logo")
    SEARCH_BAR = ("id", "demo_search_input")
    HOME_BANNER = ("id", "demo_home_banner")

    # ---------- 首页瓷片区（三个并列入口，无具体金融产品语义）----------
    TILE_CATALOG = ("id", "demo_tile_catalog")
    TILE_PROMOTIONS = ("id", "demo_tile_promotions")
    TILE_ORDERS = ("id", "demo_tile_orders")
    QUICK_ACTIONS = ("id", "demo_quick_actions_area")

    # ---------- 底部导航（五 Tab 壳层，命名中性）----------
    NAV_HOME = ("id", "demo_nav_home")
    NAV_CATALOG = ("id", "demo_nav_catalog")
    NAV_SCAN = ("id", "demo_nav_scan")
    NAV_CART = ("id", "demo_nav_cart")
    NAV_PROFILE = ("id", "demo_nav_profile")

    def __init__(self, driver):
        super().__init__(driver)
        logger.info("初始化示例首页 ShellHomePage")

    def click_header_badge(self):
        """点击顶部角标/消息入口（演示用）。"""
        logger.info("点击顶部角标入口")
        self.click(self.HEADER_BADGE[0], self.HEADER_BADGE[1])

    def click_app_logo(self):
        logger.info("点击应用 Logo")
        self.click(self.APP_LOGO[0], self.APP_LOGO[1])

    def input_search_bar(self, text: str):
        logger.info("搜索框输入: %s", text)
        self.input_text(
            locator_type=self.SEARCH_BAR[0],
            locator_value=self.SEARCH_BAR[1],
            text=text,
        )

    def click_home_banner(self):
        logger.info("点击首页运营位/Banner")
        self.click(self.HOME_BANNER[0], self.HOME_BANNER[1])

    def click_tile_catalog(self):
        logger.info("点击瓷区：分类/逛一逛")
        self.click(self.TILE_CATALOG[0], self.TILE_CATALOG[1])

    def click_tile_promotions(self):
        logger.info("点击瓷区：活动/优惠")
        self.click(self.TILE_PROMOTIONS[0], self.TILE_PROMOTIONS[1])

    def click_tile_orders(self):
        logger.info("点击瓷区：订单/物流")
        self.click(self.TILE_ORDERS[0], self.TILE_ORDERS[1])

    def click_quick_actions(self):
        logger.info("点击快捷操作区")
        self.click(self.QUICK_ACTIONS[0], self.QUICK_ACTIONS[1])

    def click_nav_home(self):
        logger.info("底部导航：首页")
        self.click(self.NAV_HOME[0], self.NAV_HOME[1])

    def click_nav_catalog(self):
        logger.info("底部导航：分类")
        self.click(self.NAV_CATALOG[0], self.NAV_CATALOG[1])

    def click_nav_scan(self):
        logger.info("底部导航：扫一扫")
        self.click(self.NAV_SCAN[0], self.NAV_SCAN[1])

    def click_nav_cart(self):
        logger.info("底部导航：购物车")
        self.click(self.NAV_CART[0], self.NAV_CART[1])

    def click_nav_profile(self):
        """
        底部导航：个人中心（多策略定位示例）。

        演示在 iOS / Android 上对「Profile / 我的」类 Tab 做链式兜底；
        真实项目请改为你的产品 accessibility 与 resource-id。
        """
        logger.info("底部导航：个人中心（多策略定位）")

        platform_name = (self.driver.capabilities.get("platformName") or "").lower()

        if platform_name == "ios":
            locators = [
                ("accessibility_id", "Profile"),
                ("id", "Profile"),
                ("xpath", "//XCUIElementTypeButton[@name='Profile' or @label='Profile']"),
                ("xpath", "//XCUIElementTypeStaticText[@name='我的' or @label='我的']"),
                ("xpath", "//*[@name='Profile' or @label='Profile' or @name='我的' or @label='我的']"),
            ]
        else:
            locators = [
                ("xpath", "//*[@content-desc='Profile' or @content-desc='我的' or contains(@content-desc, 'Profile')]"),
                (
                    "xpath",
                    "//*[contains(@resource-id, 'nav') and (contains(@resource-id, 'profile') or contains(@resource-id, 'me'))]",
                ),
                ("xpath", "//*[@text='Profile' or @text='我的']"),
                ("xpath", "//android.widget.TextView[@text='Profile' or @text='我的']"),
            ]

        for loc_type, loc_value in locators:
            try:
                logger.info("尝试定位: %s=%s...", loc_type, loc_value[:60])
                self.click(loc_type, loc_value)
                logger.info("点击成功: %s", loc_type)
                return
            except Exception as e:  # 教学演示：依次尝试下一套定位
                logger.warning("定位失败 %s: %s", loc_type, str(e)[:100])
                continue

        raise RuntimeError("未找到个人中心 Tab，请检查被测 App 的文案与层级")

    # ---------- 组合操作（业务无关的示例流程）----------

    def search_catalog(self, keyword: str):
        """在首页搜索框输入关键词并收起键盘（可按真实搜索按钮扩展）。"""
        logger.info("搜索示例: %s", keyword)
        self.input_search_bar(keyword)
        self.hide_keyboard()
        self.wait(1)

    def navigate_to_catalog(self):
        logger.info("进入分类 Tab")
        self.click_nav_catalog()
        self.wait(2)

    def navigate_to_profile(self):
        logger.info("进入个人中心 Tab")
        self.click_nav_profile()
        self.wait(2)

    def open_header_badge_detail(self):
        logger.info("从角标进入详情（演示）")
        self.click_header_badge()
        self.wait(2)

    def open_catalog_tile(self):
        logger.info("从瓷区进入分类/列表（演示）")
        self.click_tile_catalog()
        self.wait(2)

    def open_promotions_tile(self):
        logger.info("从瓷区进入活动列表（演示）")
        self.click_tile_promotions()
        self.wait(2)

    def open_orders_tile(self):
        logger.info("从瓷区进入订单（演示）")
        self.click_tile_orders()
        self.wait(2)

    def open_quick_actions_panel(self):
        logger.info("打开快捷操作区（演示）")
        self.click_quick_actions()
        self.wait(2)
