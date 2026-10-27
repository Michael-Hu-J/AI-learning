# test_all.py（5000 行）
def test_1():
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "Admin1234")
    page.click('button[type="submit"]')
    # ...

def test_2():
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "Admin1234")
    page.click('button[type="submit"]')
    # ...

# ... 50 个函数，每个都重复登录逻辑
