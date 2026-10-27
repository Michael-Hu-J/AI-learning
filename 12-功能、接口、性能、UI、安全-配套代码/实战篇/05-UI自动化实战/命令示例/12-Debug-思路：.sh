# 1. 处理弹窗：在页面操作之前监听弹窗
page.on("dialog", lambda dialog: dialog.accept())

# 2. 或者直接 dismiss
page.on("dialog", lambda dialog: dialog.dismiss())

# 3. 完整的处理：
page.on("dialog", lambda dialog: print(f"弹窗内容: {dialog.message}") or dialog.accept())
