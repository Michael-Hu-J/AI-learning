# 监听新窗口
with page.expect_popup() as popup_info:
    page.click('text=打开新窗口')
new_page = popup_info.value
new_page.wait_for_load_state()
# 在新窗口里操作
new_page.click('text=确认')
