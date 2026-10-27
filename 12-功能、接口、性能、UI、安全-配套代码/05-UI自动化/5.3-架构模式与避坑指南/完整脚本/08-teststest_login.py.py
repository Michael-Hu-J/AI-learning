import pytest
from pages.login_page import LoginPage

def test_login_success(page):
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login_success("admin", "Admin1234")
    # 断言首页元素可见
    expect(page.get_by_text("欢迎回来")).to_be_visible()

def test_login_wrong_password(page):
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("admin", "wrong_pwd")
    # 断言错误提示
    assert "用户名或密码错误" in login_page.get_error_message()
