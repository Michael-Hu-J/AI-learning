# login_page.py
class LoginPage:
    def __init__(self, page):
        self.page = page
    
    def login(self, username, password):
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')

# 使用
login_page = LoginPage(page)
login_page.login("admin", "Admin1234")  # 一行搞定
