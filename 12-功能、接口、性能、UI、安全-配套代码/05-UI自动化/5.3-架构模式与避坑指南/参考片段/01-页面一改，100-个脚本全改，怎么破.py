# 脚本 1：登录
page.fill('input[name="username"]', "admin")
page.fill('input[name="password"]', "Admin1234")
page.click('button[type="submit"]')

# 脚本 2：修改密码
page.fill('input[name="username"]', "admin")
page.fill('input[name="password"]', "Admin1234")
page.click('button[type="submit"]')
page.click('text=修改密码')

# 脚本 3：下单
page.fill('input[name="username"]', "admin")
page.fill('input[name="password"]', "Admin1234")
page.click('button[type="submit"]')
page.click('text=商品列表')
