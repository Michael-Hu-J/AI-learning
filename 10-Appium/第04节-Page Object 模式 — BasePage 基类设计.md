# 第04节-Page Object 模式 — BasePage 基类设计

> 对应代码：配套代码 `base/base_page.py`
>
> 说明：本节代码示例与配套代码中的 `BasePage` 完全对应。

---

## 这节讲什么

Page Object 模式（POM）说白了就是一个规则：**每个页面写成一个类，页面上有什么元素、能做什么操作，都放在这个类里**。测试用例只调页面类的方法，不直接写 `driver.find_element()`。

没有 POM 的时候，测试代码长这样：

```python
def test_login(driver):
    driver.find_element("id", "username").send_keys("admin")
    driver.find_element("id", "password").send_keys("admin123")
    driver.find_element("id", "login-btn").click()

一个测试里写几行 `find_element` 还行。但如果有 50 个测试都用到了登录按钮，登录按钮的 id 一改，50 个测试全要改。

有了 POM，就变成了：

```python
login_page = LoginPage(driver)
login_page.login("admin", "admin123")
```python

登录按钮的 id 改了，只改 `LoginPage` 这一个文件就行。

---

## BasePage 的设计

配套代码的 `base_page.py` 有 823 行，封装了移动端所有基础操作。这节只看核心部分。

### 1. 智能元素定位

```python
def find_element_smart(self, locators: list, timeout: int = 10):
    """
    按优先级依次尝试多个定位方式。
    前面的不行就试后面的，全部失败才报错。
    """
    last_exception = None
    for idx, (locator_type, locator_value) in enumerate(locators):
        try:
            element = self.find_element(locator_type, locator_value, timeout=timeout)
            return element
        except (TimeoutException, NoSuchElementException) as e:
            last_exception = e
            continue

    raise TimeoutException(f"全部定位失败，最后错误: {last_exception}")

**使用方式**：

```python
login_btn = page.find_element_smart([
    ("accessibility_id", "login_button"),     # 首选
    ("id", "com.app:id/login_btn"),            # 备选
    ("xpath", "//*[@text='登录']"),             # 最后才用
])
```

**为什么要有这么多层定位**：
- `accessibility_id` 最稳定，跨平台通用
- `resource-id`（即 `id`）在 Android 上稳定
- `xpath` 容易因为页面结构调整而失效，只做最后保底

### 2. 元素查找（带显式等待）

```python
def find_element(self, locator_type: str, locator_value: str, timeout: int = 10):
    locator_map = {
        "id": (AppiumBy.ID, locator_value),
        "xpath": (AppiumBy.XPATH, locator_value),
        "class_name": (AppiumBy.CLASS_NAME, locator_value),
        "accessibility_id": (AppiumBy.ACCESSIBILITY_ID, locator_value),
        "android_uiautomator": (AppiumBy.ANDROID_UIAUTOMATOR, locator_value),
        "ios_predicate": (AppiumBy.IOS_PREDICATE, locator_value),
    }

    element = WebDriverWait(self.driver, timeout).until(
        EC.presence_of_element_located(locator_map[locator_type])
    )
    return element
```

`WebDriverWait` 做了显式等待——元素还没出现时，最多等 timeout 秒，而不是立刻报错。这比 `time.sleep(5)` 高效得多。

### 3. 点击操作

```python
def click(self, locator_type: str, locator_value: str, timeout: int = 10):
    element = self.find_element(locator_type, locator_value, timeout)
    element.click()
    time.sleep(0.5)  # 点击后稍等，避免操作过快
```

**为什么点完要等 0.5 秒**：移动端的操作比 Web 慢。点击一个按钮后，页面可能需要几百毫秒才能响应。连点两个操作之间不加延迟，第二个操作可能还没找到页面就执行了。

### 4. 输入文本

```python
def input_text(self, locator_type: str, locator_value: str, text: str,
               clear_first: bool = True, timeout: int = 10):
    element = self.find_element(locator_type, locator_value, timeout)
    if clear_first:
        element.clear()
    element.send_keys(text)
```

### 5. 滑动操作

```python
def swipe_up(self, duration: int = 1000, distance: Optional[int] = None):
    size = self.driver.get_window_size()
    width = size['width']
    height = size['height']

    start_x = width // 2
    start_y = int(height * 0.8)   # 从屏幕 80% 位置开始
    end_y = int(height * 0.2)     # 滑到屏幕 20% 位置
    end_x = start_x

    self.driver.swipe(start_x, start_y, end_x, end_y, duration)

`swipe_down`、`swipe_left`、`swipe_right` 同理，只是坐标方向不同。

---

## 三级定位降级策略

实际使用中，一个元素可能同时有 accessibility_id、resource-id、xpath 三种定位方式。优先级原则：

```
accessibility_id > resource-id/id > xpath

- **accessibility_id**：开发给元素加的辅助标签，除非开发主动改，否则不变
- **resource-id**：Android 原生属性，比较稳定
- **xpath**：依赖页面 DOM 结构，前端一改版就废

配套代码的 `find_element_smart` 就是按这个优先级依次尝试的。

---

## 踩过的坑

### 1. xpath 太脆弱了
第一次写 Appium 测试时，所有定位都用 xpath，因为方便——`//*[@text='登录']` 一行搞定。
然后 App 发版了，登录按钮外面包了一层布局，xpath 路径变了，全部定位失效。
后来全部改成用 accessibility_id，发版 3 次都没动过。

### 2. 显式等待 vs 隐式等待
刚开始不明白两者的区别，混着用。隐式等待设了 10 秒，显式等待又设了 10 秒，结果就是 timeout 响应慢了一倍。
**规则**：用显式等待（`WebDriverWait`），别用隐式等待（`implicitly_wait`）。

### 3. 点击操作太快
不加延迟连续点击两个元素，第二个点击总是报 `element is not attached to the page document`。
加 0.5 秒延迟之后就好了。移动端不比 Web，操作之间要给页面反应时间。

### 4. 找不到元素就截图
`find_element_smart` 在所有定位方式都失败后，会自动截一张图保存，文件名带 `element_not_found` 时间戳。
这个习惯特别好——看日志只能看到"元素找不到"，看到截图才知道"哦，原来页面压根没加载出来"。
