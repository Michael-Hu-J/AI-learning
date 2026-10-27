# 页面会弹出一个确认框，需要自动处理
page.on("dialog", lambda dialog: dialog.accept())  # 自动点击"确定"
page.click('text=删除')

# 或者
page.on("dialog", lambda dialog: dialog.dismiss())  # 自动点击"取消"
page.click('text=取消订单')
