# 处理 JS 弹窗（alert/confirm/prompt）
page.on("dialog", lambda dialog: dialog.accept())  # 自动点确定
page.click('text=删除')
