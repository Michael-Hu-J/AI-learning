# test_toast_handling.py - Toast消息和弹窗处理测试用例
"""
Toast消息和弹窗处理测试用例
覆盖：获取Toast文本、等待特定Toast、处理系统权限弹窗、通用弹窗

运行方式：
  pytest tests/test_toast_handling.py -v --tb=short
  pytest tests/test_toast_handling.py -v -k "toast or alert"
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.toast_helper import (
    get_toast_text,
    wait_for_toast,
    handle_system_alert,
    handle_alert,
    DEFAULT_TOAST_XPATH,
    SYSTEM_ALERT_BUTTONS,
)
from utils.logger import Logger
from base.base_page import BasePage

logger = Logger().get_logger()


class TestToastHandling:
    """Toast消息处理测试类"""

    def test_get_toast_text(self, driver):
        """测试：获取当前页面上的Toast文本
        触发一个操作（如登录），然后捕获Toast
        """
        logger.info("=== 测试：获取Toast文本 ===")
        toast_text = get_toast_text(driver, timeout=5)
        if toast_text:
            logger.info(f"✅ 捕获到Toast: {toast_text}")
        else:
            logger.warning("⚠️ 未捕获到Toast，可能需要先触发Toast操作")
        time.sleep(0.5)

    def test_wait_for_toast(self, driver):
        """测试：等待特定Toast出现
        使用环境变量 TOAST_TEXT 指定期望的文本
        默认: "登录成功"
        """
        logger.info("=== 测试：等待特定Toast ===")
        expected_text = os.getenv("TOAST_TEXT", "登录成功")
        logger.info(f"期望Toast文本: {expected_text}")
        found = wait_for_toast(driver, text=expected_text, timeout=5)
        if found:
            logger.info(f"✅ 找到期望的Toast: {expected_text}")
        else:
            logger.warning(f"⚠️ 未找到Toast: {expected_text}")
        time.sleep(0.5)

    def test_get_toast_with_custom_xpath(self, driver):
        """测试：使用自定义XPath获取Toast"""
        logger.info("=== 测试：自定义XPath获取Toast ===")
        text = get_toast_text(driver, toast_xpath=DEFAULT_TOAST_XPATH, timeout=3)
        if text:
            logger.info(f"✅ 获取到Toast: {text}")
        else:
            logger.info("ℹ️ 当前无Toast")
        time.sleep(0.5)


class TestSystemAlertHandling:
    """系统权限弹窗处理测试类"""

    def test_handle_system_alert_accept(self, driver):
        """测试：处理系统权限弹窗（点击允许/同意）"""
        logger.info("=== 测试：处理系统权限弹窗（允许）===")
        result = handle_system_alert(driver, action="accept", timeout=5)
        if result:
            logger.info("✅ 系统权限弹窗已处理（允许）")
        else:
            logger.info("ℹ️ 无系统权限弹窗或处理失败")
        time.sleep(0.5)

    def test_handle_system_alert_deny(self, driver):
        """测试：处理系统权限弹窗（点击拒绝）"""
        logger.info("=== 测试：处理系统权限弹窗（拒绝）===")
        result = handle_system_alert(driver, action="deny", timeout=3)
        if result:
            logger.info("✅ 系统权限弹窗已处理（拒绝）")
        else:
            logger.info("ℹ️ 无系统权限弹窗")
        time.sleep(0.5)

    def test_system_alert_button_texts(self, driver):
        """测试：验证系统权限弹窗按钮文本配置"""
        logger.info("=== 测试：验证系统权限按钮文本 ===")
        accept_btns = SYSTEM_ALERT_BUTTONS.get("accept", [])
        deny_btns = SYSTEM_ALERT_BUTTONS.get("deny", [])
        logger.info(f"允许按钮文本: {accept_btns}")
        logger.info(f"拒绝按钮文本: {deny_btns}")
        assert len(accept_btns) > 0, "允许按钮文本列表为空"
        assert len(deny_btns) > 0, "拒绝按钮文本列表为空"
        logger.info("✅ 按钮文本配置正常")


class TestGenericAlertHandling:
    """通用弹窗处理测试类"""

    def test_handle_alert_accept(self, driver):
        """测试：处理通用弹窗（点击确定/确认）"""
        logger.info("=== 测试：处理通用弹窗（确定）===")
        result = handle_alert(driver, action="accept", timeout=5)
        if result:
            logger.info("✅ 通用弹窗已处理（确定）")
        else:
            logger.info("ℹ️ 无通用弹窗")
        time.sleep(0.5)

    def test_handle_alert_dismiss(self, driver):
        """测试：处理通用弹窗（点击取消/关闭）"""
        logger.info("=== 测试：处理通用弹窗（取消）===")
        result = handle_alert(driver, action="dismiss", timeout=3)
        if result:
            logger.info("✅ 通用弹窗已处理（取消）")
        else:
            logger.info("ℹ️ 无通用弹窗")
        time.sleep(0.5)

    def test_handle_alert_custom_text(self, driver):
        """测试：处理通用弹窗（自定义按钮文本）
        使用环境变量 ALERT_BUTTON_TEXT 指定按钮文本
        """
        logger.info("=== 测试：处理通用弹窗（自定义文本）===")
        custom_text = os.getenv("ALERT_BUTTON_TEXT", "我知道了")
        logger.info(f"自定义按钮文本: {custom_text}")
        result = handle_alert(driver, action=custom_text, timeout=3)
        if result:
            logger.info(f"✅ 通用弹窗已处理（{custom_text}）")
        else:
            logger.info(f"ℹ️ 未找到按钮: {custom_text}")
        time.sleep(0.5)

    def test_handle_alert_accept_all(self, driver):
        """测试：处理通用弹窗（有确定点确定，没有就点取消）"""
        logger.info("=== 测试：处理通用弹窗（accept_all）===")
        result = handle_alert(driver, action="accept_all", timeout=3)
        if result:
            logger.info("✅ 通用弹窗已处理（accept_all）")
        else:
            logger.info("ℹ️ 无通用弹窗")
        time.sleep(0.5)


class TestPageObjectWithPopups:
    """在 BasePage 中集成弹窗处理"""

    def test_safe_click_with_popup_handling(self, driver):
        """测试：在点击操作前先处理弹窗
        模拟一个场景：先处理可能存在的弹窗，再执行点击
        """
        logger.info("=== 测试：带弹窗处理的安全点击 ===")
        # 先处理弹窗
        handle_system_alert(driver, action="accept", timeout=2)
        handle_alert(driver, action="dismiss", timeout=2)
        logger.info("✅ 弹窗预处理完成")
        time.sleep(1)

    def test_popup_handling_in_conftest(self, driver):
        """测试：在 conftest fixture 中统一处理弹窗
        这只是一个演示——实际应该在 conftest.py 里用 autouse fixture 自动处理
        """
        logger.info("=== 测试：fixture 层弹窗处理 ===")
        # 模拟 conftest 中的弹窗处理逻辑
        try:
            handle_system_alert(driver, action="accept", timeout=2)
            handle_alert(driver, action="dismiss", timeout=2)
            logger.info("✅ fixture 层弹窗处理完成")
        except Exception as e:
            logger.warning(f"弹窗处理异常: {e}")
