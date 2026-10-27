# test_login.py - 测试脚本
from login_page import LoginPage

def test_login(page):
    login_page = LoginPage(page)
    login_page.login("admin", "Admin1234")
    assert "首页" in page.title()
