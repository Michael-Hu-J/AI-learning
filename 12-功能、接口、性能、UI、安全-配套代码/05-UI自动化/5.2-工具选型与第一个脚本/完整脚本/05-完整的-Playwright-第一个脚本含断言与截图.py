"""
文件: test_playwright_first.py
作用: Playwright 第一个完整测试脚本
运行: pytest test_playwright_first.py
"""

import re
from playwright.sync_api import Page, expect

def test_login_to_homepage(page: Page):
    """测试：用户登录后能正常进入首页"""
    
    # Step 1: 打开登录页
    page.goto("http://localhost:8080/login")
    expect(page).to_have_title(re.compile("登录", re.IGNORECASE))
    
    # Step 2: 输入登录信息
    page.get_by_label("用户名").fill("admin")
    page.get_by_label("密码").fill("Admin1234")
    
    # Step 3: 点击登录
    page.get_by_role("button", name="登录").click()
    
    # Step 4: 等待跳转并断言
    page.wait_for_url("**/dashboard")
    expect(page.get_by_text("欢迎回来, admin")).to_be_visible()
    
    # Step 5: 截图留证
    page.screenshot(path="./screenshots/login_success.png")
    print("✅ 登录成功，截图已保存")


def test_login_failed_shows_error(page: Page):
    """测试：错误密码显示错误提示"""
    
    page.goto("http://localhost:8080/login")
    page.get_by_label("用户名").fill("admin")
    page.get_by_label("密码").fill("wrong_password")
    page.get_by_role("button", name="登录").click()
    
    # 断言错误提示出现
    expect(page.get_by_text("用户名或密码错误")).to_be_visible()
    print("✅ 错误提示正确显示")
