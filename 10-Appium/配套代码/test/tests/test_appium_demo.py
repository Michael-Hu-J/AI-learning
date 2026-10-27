"""
Appium UI 测试示例 — 真机 Chrome 打开本地 Mock 电商页面

前置条件：
1. Appium Server（如 appium --port 4723）
2. Android 真机 USB 调试已开，adb devices 可见
3. 本机已启动 demo_app（默认端口 5001，与 config.MOCK_SERVER_URL 一致）
4. 环境变量 ANDROID_BROWSER=chrome（由 BaseDriver 建立手机 Chrome 会话，非原生 App）
5. MOCK_SERVER_URL 填「手机能访问到的地址」，不要用 127.0.0.1（真机上那是手机自己）
   例如：http://192.168.1.100:5001（换成本机局域网 IP）

与原生 App 用例勿在同一 pytest 进程中混跑；见 conftest.py 中 pytest_collection_modifyitems。

对应文章：第 01–16 节中的 Web UI 自动化演示部分。
"""
import time

import pytest

from config import MOCK_SERVER_URL


class TestLoginUIChromeMock:
    """Appium + 真机 Chrome：Mock 登录页与流程"""

    @pytest.mark.appium
    def test_login_page_elements(self, driver):
        driver.get(f"{MOCK_SERVER_URL}/login")
        username_input = driver.find_element("id", "username")
        password_input = driver.find_element("id", "password")
        login_btn = driver.find_element("id", "login-btn")

        assert username_input.is_displayed(), "用户名输入框应可见"
        assert password_input.is_displayed(), "密码输入框应可见"
        assert login_btn.is_displayed(), "登录按钮应可见"
        assert login_btn.is_enabled(), "登录按钮应可点击"

    @pytest.mark.appium
    def test_login_flow(self, driver):
        driver.get(f"{MOCK_SERVER_URL}/login")

        username_input = driver.find_element("id", "username")
        username_input.clear()
        username_input.send_keys("admin")

        password_input = driver.find_element("id", "password")
        password_input.clear()
        password_input.send_keys("admin123")

        login_btn = driver.find_element("id", "login-btn")
        login_btn.click()

        time.sleep(2)

        current_url = driver.current_url
        assert "/products" in current_url, f"登录后应跳转到商品页，实际: {current_url}"
