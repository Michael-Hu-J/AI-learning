from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
    
    # ✅ 元素定位集中在属性里，改页面只改这里
    @property
    def username_input(self):
        return self.page.get_by_label("用户名")
    
    @property
    def password_input(self):
        return self.page.get_by_label("密码")
    
    @property
    def login_button(self):
        return self.page.get_by_role("button", name="登录")
    
    @property
    def error_msg(self):
        return self.page.get_by_text("用户名或密码错误")
    
    # ✅ 业务方法：封装完整操作
    def goto(self):
        self.page.goto("http://localhost:8080/login")
    
    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
    
    def login_success(self, username: str, password: str):
        """登录成功后等待跳转"""
        self.login(username, password)
        self.page.wait_for_url("**/dashboard")
    
    def get_error_message(self) -> str:
        return self.error_msg.text_content()
