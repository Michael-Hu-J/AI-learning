# 原因 1：App 还没加载完，元素还没出现
# ✅ 解决：加等待
element = WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located(...)
)

# 原因 2：元素不在当前页面（需要滑动）
# ✅ 解决：先滑到元素位置
driver.swipe(500, 1500, 500, 500)  # 向下滑
