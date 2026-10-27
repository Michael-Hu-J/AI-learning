# XPath（不推荐，太死）
page.click('/html/body/div[1]/div[2]/form/input[1]')
# 页面结构一变，这个路径就废了

# CSS Selector（推荐）
page.click('input[name="username"]')
# 只要 name 不变，路径就有效

# Text（最简单，适合按钮）
page.click('text=登录')
# 只要按钮文字不变，就有效
