# ❌ 原始代码（零散）：
page.fill('input[name="username"]', "admin")
page.fill('input[name="password"]', "Admin1234")
page.click('button[type="submit"]')

page.fill('input[name="username"]', "admin")  # 重复
page.fill('input[name="password"]', "Admin1234")  # 重复
page.click('button[type="submit"]')  # 重复
page.click('text=修改密码')
