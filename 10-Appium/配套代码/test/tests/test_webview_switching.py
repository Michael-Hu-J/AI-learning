# test_webview_switching.py - WebView/H5上下文切换测试用例
"""
WebView/H5上下文切换测试用例
覆盖：查看可用上下文、切换到WebView、切回原生、等待WebView加载、执行JS

运行方式：
  pytest tests/test_webview_switching.py -v --tb=short
  pytest tests/test_webview_switching.py -v -k "context or webview"

注意：需要被测 App 包含 WebView/H5 页面才能完整测试
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.webview_helper import (
    get_available_contexts,
    switch_to_webview,
    switch_to_native,
    wait_for_webview,
    execute_js_in_webview,
)
from utils.logger import Logger

logger = Logger().get_logger()

# WebView 测试相关的常量
TEST_PACKAGE_NAME = os.getenv("APP_PACKAGE", "com.example.app")


class TestWebViewContext:
    """WebView上下文基础操作测试类"""

    def test_get_available_contexts(self, driver):
        """测试：获取当前所有可用上下文列表"""
        logger.info("=== 测试：获取可用上下文列表 ===")
        contexts = get_available_contexts(driver)
        logger.info(f"当前可用上下文: {contexts}")
        assert isinstance(contexts, list), "上下文列表类型错误"
        assert "NATIVE_APP" in contexts, "至少应包含 NATIVE_APP 上下文"
        logger.info(f"✅ 共 {len(contexts)} 个可用上下文")

    def test_switch_to_native(self, driver):
        """测试：切换回原生上下文"""
        logger.info("=== 测试：切换到原生上下文 ===")
        result = switch_to_native(driver)
        assert result, "切换到原生上下文失败"
        assert driver.current_context == "NATIVE_APP", \
            f"当前上下文不是 NATIVE_APP: {driver.current_context}"
        logger.info(f"✅ 当前上下文: {driver.current_context}")

    def test_switch_to_webview(self, driver):
        """测试：切换到WebView上下文
        注意：需要 App 当前页面包含 WebView 才有效
        """
        logger.info("=== 测试：切换到WebView上下文 ===")
        result = switch_to_webview(driver, package_name=TEST_PACKAGE_NAME)
        if result:
            logger.info(f"✅ 已切换到WebView，当前上下文: {driver.current_context}")
            # 切回原生
            switch_to_native(driver)
        else:
            logger.warning("⚠️ 未找到WebView上下文，请确保已进入H5页面")
            # 尝试等待一下再看看
            contexts = get_available_contexts(driver)
            logger.info(f"当前可用上下文: {contexts}")

    def test_wait_for_webview(self, driver):
        """测试：等待WebView上下文出现
        先进入一个H5页面，然后等待WebView加载完成
        """
        logger.info("=== 测试：等待WebView上下文出现 ===")
        # 先检查是否已有WebView
        contexts = get_available_contexts(driver)
        webviews = [c for c in contexts if c.lower().startswith("webview")]

        if webviews:
            logger.info(f"WebView已就绪: {webviews}")
        else:
            logger.info("等待WebView出现...")
            webview_name = wait_for_webview(
                driver,
                timeout=10,
                package_name=TEST_PACKAGE_NAME,
                interval=1
            )
            if webview_name:
                logger.info(f"✅ WebView已出现: {webview_name}")
            else:
                logger.warning("⚠️ 等待WebView超时")


class TestJavaScriptInWebView:
    """在WebView中执行JavaScript测试类"""

    def test_find_context_and_switch(self, driver):
        """测试：自动查找并切换到WebView"""
        logger.info("=== 测试：自动查找并切换到WebView ===")
        contexts = get_available_contexts(driver)
        for ctx in contexts:
            if ctx.lower().startswith("webview"):
                driver.switch_to.context(ctx)
                logger.info(f"✅ 切换到WebView: {ctx}")
                return
        logger.warning("⚠️ 未找到WebView上下文")

    def test_execute_js_in_webview(self, driver):
        """测试：在WebView中执行JavaScript
        需要先切换到WebView上下文
        """
        logger.info("=== 测试：在WebView中执行JS ===")
        # 先尝试切换到WebView
        switched = switch_to_webview(driver, package_name=TEST_PACKAGE_NAME)

        if not switched:
            logger.warning("⚠️ 无法切换到WebView，跳过JS执行测试")
            return

        # 获取页面标题
        try:
            title = execute_js_in_webview(driver, "return document.title")
            logger.info(f"✅ H5页面标题: {title}")
        except Exception as e:
            logger.error(f"执行JS失败: {e}")

        # 获取页面URL
        try:
            url = execute_js_in_webview(driver, "return window.location.href")
            logger.info(f"✅ H5页面URL: {url}")
        except Exception as e:
            logger.error(f"获取URL失败: {e}")

        # 获取页面高度（用于判断是否有滚动）
        try:
            height = execute_js_in_webview(driver, "return document.body.scrollHeight")
            viewport_height = execute_js_in_webview(
                driver, "return window.innerHeight"
            )
            logger.info(f"✅ 页面高度: {height}, 视口高度: {viewport_height}")
            if height > viewport_height:
                logger.info("ℹ️ 页面可滚动")
        except Exception as e:
            logger.error(f"获取页面高度失败: {e}")

        # 切回原生
        switch_to_native(driver)
        logger.info("✅ JS执行测试完成，已切回原生上下文")


class TestWebViewElementOperations:
    """WebView元素操作测试类"""

    def test_find_element_in_webview(self, driver):
        """测试：在WebView中查找元素
        需要先切换到WebView上下文
        """
        logger.info("=== 测试：在WebView中查找元素 ===")
        switched = switch_to_webview(driver, package_name=TEST_PACKAGE_NAME)
        if not switched:
            logger.warning("⚠️ 无法切换到WebView，跳过元素查找测试")
            return

        # 尝试查找常用元素
        try:
            # 查找所有链接
            links = driver.find_elements("tag name", "a")
            logger.info(f"✅ 找到 {len(links)} 个链接")

            # 查找所有按钮
            buttons = driver.find_elements("tag name", "button")
            logger.info(f"✅ 找到 {len(buttons)} 个按钮")

            # 查找所有输入框
            inputs = driver.find_elements("tag name", "input")
            logger.info(f"✅ 找到 {len(inputs)} 个输入框")

        except Exception as e:
            logger.error(f"查找元素失败: {e}")

        # 切回原生
        switch_to_native(driver)

    def test_full_webview_workflow(self, driver):
        """测试：完整的WebView工作流
        原生 → 切换到WebView → 操作 → 切回原生
        """
        logger.info("=== 测试：完整的WebView工作流 ===")

        # 1. 确认当前在原生
        assert driver.current_context in ("NATIVE_APP",), \
            f"当前不在原生上下文: {driver.current_context}"
        logger.info("1️⃣ 当前在原生上下文")

        # 2. 查找并切换到WebView
        contexts = get_available_contexts(driver)
        webviews = [c for c in contexts if c.lower().startswith("webview")]

        if not webviews:
            logger.warning("⚠️ 无WebView上下文，跳过完整工作流测试")
            return

        # 3. 切换到第一个WebView
        driver.switch_to.context(webviews[0])
        logger.info(f"2️⃣ 已切换到WebView: {webviews[0]}")

        # 4. 在WebView中获取信息
        try:
            title = execute_js_in_webview(driver, "return document.title")
            logger.info(f"3️⃣ H5页面标题: {title}")
        except Exception as e:
            logger.warning(f"获取标题失败: {e}")

        # 5. 切回原生
        switch_to_native(driver)
        assert driver.current_context == "NATIVE_APP"
        logger.info("4️⃣ 已切回原生上下文")

        logger.info("✅ 完整工作流测试通过")

    def test_context_aware_operations(self, driver):
        """测试：上下文感知操作
        自动判断当前上下文，执行相应的操作
        """
        logger.info("=== 测试：上下文感知操作 ===")

        # 获取当前上下文
        contexts = get_available_contexts(driver)
        current = driver.current_context
        logger.info(f"当前上下文: {current}")

        if current == "NATIVE_APP":
            logger.info("当前在原生上下文，可执行原生操作")
        elif current.lower().startswith("webview"):
            logger.info("当前在WebView上下文，可执行JS/H5操作")

        logger.info(f"所有可用上下文: {contexts}")
