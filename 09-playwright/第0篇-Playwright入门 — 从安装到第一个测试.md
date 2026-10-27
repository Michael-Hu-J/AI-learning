# 第0篇：Playwright 入门 — 从安装到第一个测试




这篇所有代码示例基于配套 `demo_app`（Flask 内置演示应用，`http://127.0.0.1:5000`）。HTML 结构：登录页 `#username`、`#password`、`button[type=submit]`；商品页 `<table id="product-table">` 展示商品列表。配套代码 `tests/test_browser_api.py` 中有可直接运行的测试用例。

---

## 一、Playwright 是什么

Playwright 是微软开源的浏览器自动化框架。它做的事情很简单：用代码控制浏览器——打开页面、点击按钮、填写表单、截图、拦截网络请求。

**它和 Selenium 的区别**：

Selenium 4 通过 W3C WebDriver 协议和浏览器通信（需要 chromedriver 等推动），Playwright 则直接基于浏览器原生协议（Chromium 用 CDP）。两者都能完成浏览器自动化，但 Playwright 在自动等待、API 简洁性上做得更彻底。

- 不需要下载 chromedriver、geckodriver
- 自动等待——不用写 `WebDriverWait`
- 更快的执行速度

**它和 Cypress 的区别**：

Cypress 体验好，但只支持 JavaScript。如果你的项目后端是 Python，选 Playwright 不需要跨语言。

---

## 二、安装

```bash
# 安装 Playwright Python 包
pip install playwright

# 安装浏览器（只需执行一次）
playwright install chromium

# 如果还需要 Firefox 和 WebKit
playwright install firefox
playwright install webkit
```

验证安装：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

输出 `Example Domain` 就说明安装成功了。

---

## 三、第一个测试

用配套的 demo_app 做第一个测试。先启动演示应用：

```bash
cd 配套代码/demo_app
python app.py
# 演示应用已启动
#   地址: http://127.0.0.1:5000
#   账号: admin / admin123
```

然后写测试：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 1. 打开登录页
    page.goto("http://127.0.0.1:5000/login")
    
    # 2. 填写用户名和密码
    page.fill("#username", "admin")
    page.fill("#password", "admin123")
    
    # 3. 点击登录按钮
    page.click("button[type=submit]")
    
    # 4. 等待页面跳转
    page.wait_for_url("**/products")
    
    # 5. 验证结果
    assert "商品" in page.text_content("body")
    print("登录成功")
    
    browser.close()
```

这段代码做了五件事：打开页面、填表单、点击、等待、验证。这就是 Playwright 测试的基本流程。

---

## 四、选择器：怎么找到页面上的元素

Playwright 支持多种选择器。最常见的是 CSS 选择器，但不是唯一的选择。

### 4.1 CSS 选择器

```python
# ID 选择器
page.fill("#username", "admin")

# Class 选择器
page.click(".btn-primary")

# 属性选择器
page.click("button[type=submit]")

# 组合选择器
page.fill("form#loginForm input[name=password]", "admin123")
```

CSS 选择器是最常用的，但它的弱点是：前端一改版，class 名一变，选择器就失效了。

### 4.2 text= 选择器

```python
# 按文本内容定位
page.click("text=登录")

# 精确匹配（用引号）
page.click("text='登录'")

# 部分匹配（不用引号）
page.click("text=登")
```

text= 选择器不依赖 HTML 结构，只要页面上有这段文字就能找到。适合按钮文字、提示文案这类不会变的元素。

### 4.3 role= 选择器

```python
# 按 ARIA 角色定位
page.click("role=button[name='登录']")
page.fill("role=textbox[name='用户名']", "admin")
```

role= 选择器依赖页面的无障碍属性。如果前端写了 `aria-label` 或 `role`，用这个最稳定。

### 4.4 定位器（Locator）

Playwright 推荐用 `page.locator()` 而不是直接调用 `page.click()`。Locator 是延迟执行的，它不会立即查找元素，而是在你调用操作时才查找：

```python
# 创建定位器（不执行查找）
username_input = page.locator("#username")
password_input = page.locator("#password")
login_button = page.locator("button[type=submit]")

# 使用定位器（此时才查找元素）
username_input.fill("admin")
password_input.fill("admin123")
login_button.click()
```

Locator 的好处是自动等待。如果元素还没渲染出来，Locator 会等它出现，不会立刻报错。

---

## 五、基本操作

### 5.1 页面导航

```python
# 打开页面
page.goto("http://127.0.0.1:5000/login")

# 等待策略
page.goto(url, wait_until="domcontentloaded")  # DOM加载完就返回
page.goto(url, wait_until="networkidle")       # 等网络空闲（适合SPA）
page.goto(url, wait_until="load")              # 等所有资源加载完（默认）

# 刷新
page.reload()

# 前进/后退
page.go_forward()
page.go_back()
```

### 5.2 元素操作

```python
# 输入文本
page.fill("#username", "admin")           # 清空后填入
page.type("#username", "admin")           # 逐个字符输入（模拟键盘）

# 点击
page.click("button[type=submit]")
page.dblclick("#item")                    # 双击
page.click("#item", button="right")       # 右键

# 选择下拉框
page.select_option("select#city", "beijing")

# 勾选复选框
page.check("#agree")
page.uncheck("#agree")

# 悬停
page.hover("#menu-item")

# 上传文件
page.set_input_files("input[type=file]", "/path/to/file.pdf")
```

### 5.3 获取页面信息

```python
# 获取文本
title = page.title()
url = page.url
body_text = page.text_content("body")

# 获取属性
href = page.get_attribute("a[href]", "href")

# 判断元素状态
is_visible = page.locator("#error").is_visible()
is_enabled = page.locator("button").is_enabled()
```

---

## 六、等待策略

Playwright 的自动等待已经覆盖了 90% 的场景。你不需要写 `time.sleep()` 或 `WebDriverWait`。

**自动等待**：

```python
# Playwright 会自动等待元素可见、可操作
page.click("button[type=submit]")  # 自动等按钮出现且可点击
page.fill("#username", "admin")    # 自动等输入框出现且可编辑
```

**显式等待**（自动等待不够用时）：

```python
# 等待特定元素出现
page.wait_for_selector("#product-table")

# 等待 URL 变化
page.wait_for_url("**/products")

# 等待网络响应
with page.expect_response("**/api/products") as response_info:
    page.click("#load-products")
response = response_info.value
assert response.status == 200

# 等待弹窗
with page.expect_popup() as popup_info:
    page.click("a[target=_blank]")
new_page = popup_info.value
```

**不要做的事**：

```python
# 不要用 time.sleep
import time
time.sleep(2)  # 不好——不管页面是否加载完都等2秒

# 应该用 wait_for
page.wait_for_timeout(2000)  # 也不行——和 sleep 一样
page.wait_for_selector("#target")  # 好——元素出现了就继续
```

---

## 七、pytest-playwright 集成

直接用 `sync_playwright()` 写测试可以，但用 pytest-playwright 插件更方便。它提供了 `page` fixture，自动管理浏览器生命周期。

安装：

```bash
pip install pytest-playwright
```

写测试：

```python
import pytest

def test_login(page):
    """登录测试"""
    page.goto("http://127.0.0.1:5000/login")
    page.fill("#username", "admin")
    page.fill("#password", "admin123")
    page.click("button[type=submit]")
    page.wait_for_url("**/products")
    assert "商品" in page.text_content("body")

def test_login_wrong_password(page):
    """错误密码测试"""
    page.goto("http://127.0.0.1:5000/login")
    page.fill("#username", "admin")
    page.fill("#password", "wrong")
    page.click("button[type=submit]")
    body = page.text_content("body")
    assert "错误" in body or "失败" in body
```

运行：

```bash
pytest tests/test_browser_api.py -v
```

pytest-playwright 会自动启动和关闭浏览器，每个测试用例拿到一个干净的 `page` 对象。

---

## 八、截图和调试

测试失败时，截图是最好的调试手段。

```python
# 页面截图
page.screenshot(path="login_page.png")

# 元素截图
page.locator("#error").screenshot(path="error.png")

# 全页面截图
page.screenshot(path="full.png", full_page=True)
```

pytest-playwright 默认在测试失败时自动截图。你也可以手动启用：

```bash
# 每次运行都截图
pytest --screenshot=on

# 只在失败时截图
pytest --screenshot=only-on-failure
```

---

## 九、踩坑记录

### 坑1：headless=False 看到浏览器一闪而过

```python
# 问题代码
browser = p.chromium.launch(headless=False)
page = browser.new_page()
page.goto("http://127.0.0.1:5000/login")
# 浏览器打开后立刻关闭
```

原因：`with sync_playwright() as p:` 代码块结束后，`browser.close()` 自动执行。如果测试函数没有等待操作，浏览器就关了。

解决：保证测试函数中有等待操作，或者在调试时加 `page.wait_for_timeout(5000)`。

### 坑2：click 报 "element is not visible"

```python
# 问题代码
page.click("#submit-btn")  # Element is not visible
```

原因：元素被其他元素遮挡，或者还没渲染出来。

解决：
- 用 `page.wait_for_selector("#submit-btn", state="visible")` 先等元素可见
- 或者用 `page.click("#submit-btn", force=True)` 强制点击（不推荐，跳过了 Playwright 的安全检查）

### 坑3：SPA 页面跳转后 URL 变了但页面没刷新

```python
# 问题代码
page.click("a[href='/products']")
# SPA 路由变化，URL 变了但 DOM 没刷新
assert "商品" in page.text_content("body")  # 可能失败
```

原因：SPA 应用的路由变化不触发页面导航，`page.goto()` 的 `wait_until` 不生效。

解决：等待目标页面的特征元素出现，而不是依赖 URL 变化。

```python
page.click("a[href='/products']")
page.wait_for_selector("#product-table")  # 等商品表格出现
```

### 坑4：`headless=True` 下截图全是空白

遇到过几次：在 headless 模式下截图，页面内容是空白的。原因通常是截图的时机不对——页面还没渲染完成。

```python
# 问题：goto 还没完成就截图
page.goto(url)
page.screenshot(path="page.png")  # 可能空白

# 解决：等页面加载完成再截图
page.goto(url, wait_until="networkidle")
page.wait_for_selector("body.loaded")  # 等特定元素出现
page.screenshot(path="page.png")
```

还有一个注意点：某些浏览器渲染引擎在 headless 模式下可能缺少 GPU 加速，导致字体渲染和截图效果和 headed 模式不一样。如果截图用于对比测试，建议统一用 headless 模式截图，不要混合使用。

### 坑5：并行跑测试时资源冲突

多个测试用例并行执行时，如果它们操作同一个页面（比如使用同一个 demo_app 实例），会互相干扰。测试 A 填了用户名，测试 B 刷新了页面，测试 A 就报错了。

```python
# 场景：两个测试并行，共享同一个 Flask 服务
# test_A: 填表单 → 页面被 test_B 刷新 → 报错

# 解决：每个测试用例启动独立的会话
# 用 BrowserContext 隔离会话状态
context = browser.new_context()  # 独立 cookie/session
page = context.new_page()  # 不会共享状态
```

用 `browser.new_context()` 创建独立的浏览器上下文，每个测试用例拿到独立的 cookie 和 session 存储。这样即使并行执行，也不会互相污染状态。实际项目中，context 隔离让测试用例从"必须串行"变成了"可以并发执行"，大幅缩短了整体耗时。

---

## 十、完整示例：登录流程测试

把上面的知识点串起来，写一个完整的登录测试：

```python
import pytest

BASE_URL = "http://127.0.0.1:5000"

class TestLogin:
    """登录功能测试"""
    
    def test_login_success(self, page):
        """正常登录"""
        page.goto(f"{BASE_URL}/login")
        
        # 验证登录页元素存在
        assert page.locator("#username").is_visible()
        assert page.locator("#password").is_visible()
        
        # 填写并提交
        page.fill("#username", "admin")
        page.fill("#password", "admin123")
        page.click("button[type=submit]")
        
        # 等待跳转
        page.wait_for_url("**/products")
        
        # 验证结果
        assert "商品" in page.text_content("body")
    
    def test_login_wrong_password(self, page):
        """错误密码"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", "admin")
        page.fill("#password", "wrong_password")
        page.click("button[type=submit]")
        
        body = page.text_content("body")
        assert "错误" in body or "失败" in body
    
    def test_login_empty_fields(self, page):
        """空字段"""
        page.goto(f"{BASE_URL}/login")
        page.click("button[type=submit]")
        
        body = page.text_content("body")
        assert "错误" in body or "失败" in body or "用户名" in body
```

运行：

```bash
pytest tests/test_browser_api.py -v
# tests/test_browser_api.py::test_login_ok PASSED
# tests/test_browser_api.py::test_login_wrong_password PASSED
# tests/test_browser_api.py::test_login_empty_fields PASSED
```

---

## 十一、下一步

掌握了这些基础操作，就可以进入后面的进阶内容了：

- **第1篇**：Playwright 在测试系统中的架构定位——为什么用进程隔离而不是线程
- **第2篇**：从步骤到执行——测试引擎的核心流程
- **第3篇**：三层定位降级策略——让选择器失效不再是问题
- **第9篇**：Playwright 浏览器 API 实战——Frame、网络拦截、设备模拟等高级用法

---

## 十二、总结

这篇从零走了一遍 Playwright 的安装、选择器、基本操作和 pytest 集成。核心就三句话：

**第一，选对工具比写对代码重要。** 如果你的后端是 Python，Playwright 比 Selenium 少写一半的等待代码，比 Cypress 不用跨语言。选型不是比功能列表，是比你的技术栈和它匹不匹配。

**第二，Locator 比直接调用好。** `page.locator("#username").fill("admin")` 看起来多写了一行，但它自带自动等待和重试。前端加载慢的时候，直接 `page.fill()` 可能报错，Locator 会等到元素出现再继续。这一行差异，在大规模测试里能减少 30% 的 flaky test。

**第三，别用 `time.sleep()`。** 这不是 Playwright 的规则，这是所有自动化测试的铁律。`sleep(2)` 意味着：页面 0.5 秒就加载好了，你多等 1.5 秒；页面 3 秒才加载好，你只等 2 秒还是失败。`wait_for_selector()` 才是正确的等待方式——元素出现了就继续，不出现就等。

配套代码里的 `tests/test_browser_api.py` 已经把登录流程写成了 pytest 用例，直接 `pytest tests/test_browser_api.py -v` 就能跑。跑通了再继续往下看，别跳。
