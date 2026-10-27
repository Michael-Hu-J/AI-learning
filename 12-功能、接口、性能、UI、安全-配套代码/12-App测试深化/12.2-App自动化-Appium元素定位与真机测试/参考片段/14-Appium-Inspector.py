# 从屏幕底部滑到顶部（下拉刷新）
driver.swipe(500, 1500, 500, 500, duration=500)

# Appium 2.0 推荐用 Scroll
driver.scroll(driver.find_element(by="id", value="item_10"),
             driver.find_element(by="id", value="item_1"))
