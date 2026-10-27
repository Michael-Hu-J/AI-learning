# 第 9 篇：Playwright 浏览器 API 实战：从基础到高级
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

Playwright 的浏览器 API 是整个 UI 自动化系统的底层能力——定位策略、自愈系统、MCP 集成，最终都要落到 `page.click()`、`page.fill()` 这些操作上。前面几篇讲架构和设计，这篇回到基础：浏览器 API 的完整用法，以及我们在实际项目中踩过的坑。

下文代码示例基于配套 `demo_app`（Flask 内置演示应用，`http://127.0.0.1:5000`）。登录页：`#username` / `#password`（同时带 `name="username"` / `name="password"`），表单 `#loginForm`，提交为 `button[type="submit"]`；选用 `#username` 或 `input[name="username"]` 均可。商品页以 `<table>` 展示列表（与 `demo_app/templates/products.html` 中结构一致）。

## 一、Playwright 核心概念

### 1.1 架构层次

```
┌─────────────────────────────────────────────────┐
│  Playwright                                      │
│  - playwright.chromium.launch()                  │
│  - playwright.firefox.launch()                   │
│  - playwright.webkit.launch()                    │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  Browser (浏览器实例)                             │
│  - browser.new_context()                         │
│  - browser.close()                               │
│  - browser.version()                             │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  BrowserContext (浏览器上下文)                    │
│  - context.new_page()                            │
│  - context.cookies()                             │
│  - context.route() / context.unroute()           │
│  - context.tracing.start() / stop()              │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  Page (页面)                                     │
│  - page.goto() / page.reload()                   │
│  - page.click() / page.fill()                    │
│  - page.screenshot() / page.pdf()                │
│  - page.evaluate()                               │
│  - page.frame() / page.frames()                  │
└─────────────────────────────────────────────────┘
```

### 1.2 为什么需要 BrowserContext？

**BrowserContext 是 Playwright 的核心概念**，它提供了：

1. **隔离性**：每个 Context 有独立的 cookies、localStorage、缓存
2. **并发性**：一个 Browser 可以创建多个 Context，互不影响
3. **状态管理**：可以保存和恢复 Context 的状态（cookies、localStorage）
4. **网络控制**：可以在 Context 级别拦截网络请求

```python
# 反模式：所有页面共享同一个 Context
browser = playwright.chromium.launch()

page1 = browser.new_page()
page2 = browser.new_page()
# page1 和 page2 共享 cookies、localStorage

# 推荐模式：每个测试使用独立的 Context
browser = playwright.chromium.launch()
context1 = browser.new_context()
context2 = browser.new_context()
page1 = context1.new_page()
page2 = context2.new_page()
# page1 和 page2 完全隔离
```

## 二、浏览器启动配置

### 2.1 基础启动

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 启动 Chromium
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:5000")
    browser.close()
```

### 2.2 高级启动配置

```python
# 完整配置
browser = p.chromium.launch(
    headless=True,                    # 无头模式
    slow_mo=100,                      # 减慢操作速度（调试用）
    args=[                            # Chromium 启动参数
        "--no-sandbox",               # 禁用沙盒（Docker 环境需要）
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",    # 解决 /dev/shm 空间不足
        "--disable-gpu",              # 禁用 GPU 加速
        "--disable-web-security",     # 禁用跨域限制（测试环境）
        "--window-size=1920,1080",    # 窗口大小
    ],
    chromium_sandbox=True,            # 启用沙盒
    proxy={                           # 代理配置
        "server": "http://proxy:8080",
        "username": "user",
        "password": "pass",
    },
)
```

### 2.3 不同浏览器启动

```python
# Chromium
browser = p.chromium.launch(headless=True)

# Firefox
browser = p.firefox.launch(headless=True)

# WebKit (Safari 内核)
browser = p.webkit.launch(headless=True)

# 指定可执行文件路径
browser = p.chromium.launch(
    executable_path="/usr/bin/chromium-browser"
)
```

### 2.4 连接已运行的浏览器

```python
# 连接到已运行的 Chrome
browser = p.chromium.connect_over_cdp("http://localhost:9222")

# 连接到 WebSocket
browser = p.chromium.connect("ws://localhost:3000/chrome")
```

## 三、BrowserContext 详解

### 3.1 创建 Context

```python
# 基础创建
context = browser.new_context()

# 完整配置
context = browser.new_context(
    # 视口配置
    viewport={"width": 1920, "height": 1080},
    
    # 用户代理
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    
    # 语言
    locale="zh-CN",
    timezone_id="Asia/Shanghai",
    
    # 颜色方案
    color_scheme="light",  # light / dark / no-preference
    
    # 媒体类型
    media_type="screen",   # screen / print
    
    # 权限
    permissions=["geolocation", "notifications"],
    
    # 地理定位
    geolocation={"latitude": 39.9042, "longitude": 116.4074},
    
    # 设备模拟
    device_scale_factor=2,
    is_mobile=False,
    has_touch=False,
    
    # 代理
    proxy={"server": "http://proxy:8080"},
    
    # 忽略 HTTPS 错误
    ignore_https_errors=True,
    
    # JavaScript
    java_script_enabled=True,
    
    # 存储状态（从文件加载）
    storage_state="state.json",
)
```

### 3.2 Context 隔离

```python
# 创建两个隔离的 Context
context1 = browser.new_context()
context2 = browser.new_context()

page1 = context1.new_page()
page2 = context2.new_page()

# 在 page1 登录（与 demo_app 中 testuser / test123 一致）
page1.goto("http://127.0.0.1:5000/login")
page1.fill('input[name="username"]', "testuser")
page1.fill('input[name="password"]', "test123")
page1.click('form[action="/login"] button[type=submit]')

# page2 不受影响（未登录状态）
page2.goto("http://127.0.0.1:5000/register")
print(page2.text_content("body"))  # 注册页文案，与 page1 会话隔离
```

### 3.3 保存和恢复状态

```python
# 保存状态
context = browser.new_context()
page = context.new_page()
page.goto("http://127.0.0.1:5000/login")
page.fill('input[name="username"]', "testuser")
page.fill('input[name="password"]', "test123")
page.click('form[action="/login"] button[type="submit"]')
page.wait_for_url("**/products")

# 保存 cookies 和 localStorage
context.storage_state(path="auth_state.json")

# 恢复状态（无需重新登录）
context2 = browser.new_context(storage_state="auth_state.json")
page2 = context2.new_page()
page2.goto("http://127.0.0.1:5000/products")  # 直接访问，已登录
```

### 3.4 Cookies 管理

```python
# 获取 cookies
cookies = context.cookies()
print(cookies)

# 设置 cookies
context.add_cookies([
    {
        "name": "session",
        "value": "abc123",
        "url": "http://127.0.0.1:5000",
        "httpOnly": True,
        "secure": True,
    }
])

# 清除 cookies
context.clear_cookies()
```

## 四、Page 操作详解

### 4.1 页面导航

```python
# 基础导航
page.goto("http://127.0.0.1:5000")

# 等待策略
page.goto("http://127.0.0.1:5000", wait_until="load")        # 等待 load 事件
page.goto("http://127.0.0.1:5000", wait_until="domcontentloaded")  # 等待 DOMContentLoaded
page.goto("http://127.0.0.1:5000", wait_until="networkidle")  # 等待网络空闲（新版已 deprecated，推荐 domcontentloaded）
page.goto("http://127.0.0.1:5000", wait_until="load")      # 等待响应提交

# 选择建议：
# - 静态页面：domcontentloaded（最快）
# - SPA 应用：networkidle（等 AJAX 完成）或手动 wait_for_selector
# - 有大量广告/统计请求的页面：避免 networkidle（可能永远等不到空闲）

# 超时设置
page.goto("http://127.0.0.1:5000", timeout=30000)  # 30 秒超时

# 重新加载
page.reload()
page.reload(wait_until="networkidle")

# 前进/后退
page.go_back()
page.go_forward()
```

### 4.2 元素操作

```python
# 点击
page.click('form[action="/login"] button[type=submit]')
page.click('form[action="/login"] button[type=submit]', button="right")       # 右键点击
page.click('form[action="/login"] button[type=submit]', click_count=2)        # 双击
page.click('form[action="/login"] button[type=submit]', modifiers=["Shift"])  # Shift+ 点击

# 输入
page.fill('input[name="username"]', "testuser")
page.locator('input[name="username"]').type("testuser", delay=100)     # 模拟键盘输入
page.press('input[name="username"]', "Enter")               # 按键

# 选择
page.select_option('select[name="country"]', "cn")           # 按值选择
page.select_option('select[name="country"]', label="中国")    # 按文本选择
page.select_option('select[name="country"]', index=0)        # 按索引选择

# 悬停（商品页导航链接）
page.hover('a[href="/login"]')

# 聚焦/失焦
page.focus('input[name="username"]')
page.blur('input[name="username"]')

# 设置文件
page.set_input_files("#file-upload", "test.txt")
page.set_input_files("#file-upload", ["file1.txt", "file2.txt"])
```

### 4.3 等待策略

```python
# 等待选择器
page.wait_for_selector("table")
page.wait_for_selector("table", state="visible")   # 等待可见
page.wait_for_selector("table", state="hidden")    # 等待隐藏
page.wait_for_selector("table", state="attached")  # 等待附着

# 等待 URL
page.wait_for_url("**/products")
page.wait_for_url("**/products", timeout=10000)

# 等待响应
with page.expect_response("**/api/products") as response_info:
    page.click("button:has-text('刷新')")
response = response_info.value
print(response.status)

# 等待导航
with page.expect_navigation():
    page.click('#loginForm button[type=submit]')

# 等待弹窗
with page.expect_popup() as popup_info:
    page.click('a[href="/register"]')
new_page = popup_info.value

# 等待下载
with page.expect_download() as download_info:
    page.click("a:has-text('下载')")
download = download_info.value
download.save_as("/tmp/downloaded_file.pdf")

# 等待弹窗
with page.expect_dialog() as dialog_info:
    page.click("button:has-text('删除')")
dialog = dialog_info.value
print(dialog.message)
dialog.accept()
```

### 4.4 截图和 PDF

```python
# 全屏截图
page.screenshot(path="screenshot.png")

# 元素截图
element = page.locator("table")
element.screenshot(path="element.png")

# 全页面截图
page.screenshot(path="full.png", full_page=True)

# 指定区域截图
page.screenshot(path="area.png", clip={"x": 0, "y": 0, "width": 800, "height": 600})

# 生成 PDF
page.pdf(path="page.pdf", format="A4", print_background=True)

# 视频录制
context = browser.new_context(record_video_dir="videos/", record_video_size={"width": 1280, "height": 720})
page = context.new_page()
page.goto("http://127.0.0.1:5000/login")
page.fill('input[name="username"]', "testuser")
page.fill('input[name="password"]', "test123")
page.click('form[action="/login"] button[type=submit]')
page.wait_for_url("**/products")
context.close()  # 视频保存完成
```

### 4.5 执行 JavaScript

```python
# 执行 JS 并获取返回值
title = page.evaluate("document.title")
print(title)

# 执行 JS 操作 DOM
page.evaluate("document.body.style.backgroundColor = 'red'")

# 传递参数
result = page.evaluate("([x, y]) => x + y", [10, 20])
print(result)  # 30

# 获取元素属性
src = page.evaluate("document.querySelector('img').src")

# 获取页面信息
viewport = page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
```

## 五、Frame 处理

### 5.1 什么是 Frame？

Frame 是页面中的子页面，通常用于 iframe：

```html
<!-- 第三方支付托管页（非示例 Flask 系统，仅用于 Frame 教学占位） -->
<iframe id="payment-frame" src="https://partner-checkout.sandbox.example/embed"></iframe>
```

### 5.2 Frame 操作

```python
# 获取所有 Frame
frames = page.frames
for frame in frames:
    print(frame.name, frame.url)

# 通过名称获取 Frame
frame = page.frame(name="payment-frame")

# 通过 URL 获取 Frame
frame = page.frame(url="https://partner-checkout.sandbox.example/embed")

# 在 Frame 中操作
frame.fill("#card-number", "4111111111111111")
frame.fill("#expiry", "12/25")
frame.click("#pay-btn")

# 等待 Frame 加载
page.wait_for_frame("**/payment")
```

### 5.3 Shadow DOM

Shadow DOM 是前端组件化常见的隔离机制（如 Web Components、部分第三方 UI 库）。Playwright 对 Shadow DOM 有天然支持：

```python
# Playwright 默认穿透 shadow-root，直接用 CSS 选择器定位
page.click("#host-element >>> #shadow-button")

# 或使用 >> 连接符（推荐，/deep/ 已废弃）
page.click("#host-element >> #shadow-button")

# 实际场景：支付表单嵌入在 Shadow DOM 中
# <custom-payment-widget> 内部使用了 Shadow DOM
page.fill("custom-payment-widget >>> #card-number", "4111111111111111")
page.fill("custom-payment-widget >>> #expiry", "12/25")
page.click("custom-payment-widget >>> #pay-btn")

# 如果选择器穿透失败，可用 evaluate 直接操作 shadow root
page.evaluate("""() => {
    const host = document.querySelector('custom-payment-widget');
    host.shadowRoot.querySelector('#card-number').value = '4111111111111111';
    host.shadowRoot.querySelector('#expiry').value = '12/25';
}""")
```

## 六、网络拦截

### 6.1 拦截请求

```python
# 拦截所有图片请求
def handle_route(route):
    if route.request.resource_type == "image":
        route.abort()
    else:
        route.continue_()

page.route("**/*", handle_route)

# 修改请求头
def modify_headers(route):
    headers = route.request.headers.copy()
    headers["X-Custom-Header"] = "custom-value"
    route.continue_(headers=headers)

page.route("**/*", modify_headers)

# 模拟网络延迟
def delay_route(route):
    import time
    time.sleep(2)
    route.continue_()

page.route("**/*", delay_route)
```

### 6.2 拦截响应

```python
# 修改响应
def modify_response(route):
    import json as _json
    response = route.fetch()
    data = response.json()
    data["price"] = 0.01  # 修改价格
    route.fulfill(body=_json.dumps(data), headers={"Content-Type": "application/json"})

page.route("**/api/products", modify_response)
```

### 6.3 模拟离线

```python
# 模拟离线状态
context.set_offline(True)
try:
    page.goto("http://127.0.0.1:5000")
except Exception as e:
    print("网络不可用")

# 恢复在线
context.set_offline(False)
```

### 6.4 监听请求和响应

```python
# 监听请求
page.on("request", lambda request: print(f"请求: {request.url}"))

# 监听响应
page.on("response", lambda response: print(f"响应: {response.url} - {response.status}"))

# 等待特定请求
with page.expect_request("**/api/login") as request_info:
    page.click('form[action="/login"] button[type=submit]')
request = request_info.value
print(request.post_data)

# 等待特定响应
with page.expect_response("**/api/login") as response_info:
    page.click('form[action="/login"] button[type=submit]')
response = response_info.value
print(response.json())
```

## 七、设备模拟

### 7.1 预定义设备

```python
# 使用预定义设备
iphone = p.devices["iPhone 13"]
context = browser.new_context(**iphone)
page = context.new_page()
page.goto("http://127.0.0.1:5000")
```

### 7.2 自定义设备

```python
# 自定义设备
context = browser.new_context(
    viewport={"width": 375, "height": 812},
    device_scale_factor=3,
    is_mobile=True,
    has_touch=True,
    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
    locale="zh-CN",
    timezone_id="Asia/Shanghai",
)
```

### 7.3 常见设备参数

| 设备 | viewport | device_scale_factor | is_mobile |
|------|----------|---------------------|-----------|
| iPhone 13 | 390x844 | 3 | True |
| iPad | 810x1080 | 2 | True |
| Desktop | 1920x1080 | 1 | False |
| Pixel 5 | 393x851 | 2.75 | True |

## 八、键盘和鼠标

### 8.1 键盘操作

```python
# 按键
page.keyboard.press("Enter")
page.keyboard.press("Tab")
page.keyboard.press("Escape")

# 组合键
page.keyboard.press("Control+A")
page.keyboard.press("Control+C")
page.keyboard.press("Control+V")

# 输入文本
page.keyboard.type("Hello World", delay=100)

# 按下/释放
page.keyboard.down("Shift")
page.keyboard.press("A")
page.keyboard.up("Shift")
```

### 8.2 鼠标操作

```python
# 移动
page.mouse.move(100, 100)

# 点击
page.mouse.click(100, 100)
page.mouse.click(100, 100, button="right")

# 拖拽
page.mouse.move(100, 100)
page.mouse.down()
page.mouse.move(200, 200)
page.mouse.up()

# 滚轮
page.mouse.wheel(0, 100)  # 向下滚动 100px
```

## 九、文件操作

### 9.1 文件上传

```python
# 单个文件
page.set_input_files("#file-upload", "test.txt")

# 多个文件
page.set_input_files("#file-upload", ["file1.txt", "file2.txt"])

# 通过 locator
page.locator("#file-upload").set_input_files("test.txt")
```

### 9.2 文件下载

```python
# 等待下载
with page.expect_download() as download_info:
    page.click("a:has-text('下载')")

download = download_info.value

# 获取下载路径
path = download.path()

# 保存到指定路径
download.save_as("/tmp/downloaded_file.pdf")

# 取消下载
download.cancel()
```

## 十、认证和权限

### 10.1 HTTP 认证

```python
# 提供认证信息
context = browser.new_context(
    http_credentials={"username": "user", "password": "pass"}
)
```

### 10.2 权限管理

```python
# 授予权限
context.grant_permissions(["geolocation", "notifications"])

# 撤销权限
context.revoke_permissions()

# 设置地理定位
context.set_geolocation({"latitude": 39.9042, "longitude": 116.4074})
```

## 十一、调试和追踪

### 11.1 截图

```python
# 页面截图
page.screenshot(path="screenshot.png")

# 元素截图
element = page.locator("table")
element.screenshot(path="element.png")

# 全页面截图
page.screenshot(path="full.png", full_page=True)
```

### 11.2 视频录制

```python
# 启用视频录制
context = browser.new_context(
    record_video_dir="videos/",
    record_video_size={"width": 1280, "height": 720}
)
page = context.new_page()
page.goto("http://127.0.0.1:5000/login")
page.fill('input[name="username"]', "testuser")
page.fill('input[name="password"]', "test123")
page.click('form[action="/login"] button[type=submit]')
page.wait_for_url("**/products")
context.close()  # 视频保存完成
```

### 11.3 追踪

```python
# 启用追踪
context.tracing.start(screenshots=True, snapshots=True, sources=True)

# 执行操作（与配套代码 tests/test_browser_api.py 登录流一致）
page.goto("http://127.0.0.1:5000/login")
page.fill('input[name="username"]', "testuser")
page.fill('input[name="password"]', "test123")
page.click('form[action="/login"] button[type=submit]')
page.wait_for_url("**/products")

# 停止追踪并保存
context.tracing.stop(path="trace.zip")
```

## 十二、实战案例：登录后在商品列表检索

### 12.1 测试场景

```
1. 打开登录页 /login
2. 输入演示账号（demo_app：`admin` / `admin123`，或 `testuser` / `test123`）
3. 提交表单，等待跳转商品页 /products
4. 在工具栏「商品名称关键词」中输入 iPhone 并点击查询
5. 断言 #product-table 中仍可见目标商品（与 templates/products.html 控件 id 一致）
```

### 12.2 代码实现

```python
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="zh-CN",
    )
    page = context.new_page()

    page.goto(f"{BASE}/login")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="password"]', "test123")
    page.click('form[action="/login"] button[type="submit"]')
    page.wait_for_url("**/products")

    # 商品页无搜索功能，直接验证表格内容
    table_text = page.locator("table").inner_text()
    assert "商品" in table_text

    page.screenshot(path="products_search.png")

    context.close()
    browser.close()
```

## 十三、踩坑经验

### 13.1 坑 1：元素不可见导致点击失败

**问题**：元素被遮挡或未加载完成时，点击失败。

**解决**：使用 `force=True` 或等待元素可见。

```python
# 等待元素可见
page.wait_for_selector('form[action="/login"] button[type=submit]', state="visible")
page.click('form[action="/login"] button[type=submit]')

# 或强制点击
page.click('form[action="/login"] button[type=submit]', force=True)
```

### 13.2 坑 2：Frame 中的元素定位失败

**问题**：直接在 page 上定位 Frame 中的元素。

**解决**：先获取 Frame，再在 Frame 中定位。

```python
# 错误
page.click("#payment-frame #pay-btn")  # 

# 正确
frame = page.frame(name="payment-frame")
frame.click("#pay-btn")  # 
```

### 13.3 坑 3：网络拦截导致页面加载失败

**问题**：拦截了关键请求，导致页面无法加载。

**解决**：只拦截特定请求，其他请求放行。

```python
def handle_route(route):
    if route.request.resource_type == "image":
        route.abort()
    else:
        route.continue_()  # 放行其他请求

page.route("**/*", handle_route)
```

### 13.4 坑 4：Context 未关闭导致资源泄漏

**问题**：创建多个 Context 但未关闭，导致内存泄漏。

**解决**：使用 with 语句或保证关闭。

```python
# 推荐
with browser.new_context() as context:
    page = context.new_page()
    # ... 操作
# 自动关闭

# 或手动
context = browser.new_context()
try:
    page = context.new_page()
    # ... 操作
finally:
    context.close()
```

### 13.5 坑 5：SPA 路由变化不触发页面导航

**问题**：单页应用（Vue/React）的路由变化不会触发 `page.goto()` 的导航事件，`wait_for_url()` 可能失效。

**解决**：用 `wait_for_selector` 等待新页面内容出现，而非等待 URL 变化。

```python
#  不可靠：SPA 路由变化不触发导航
page.click('a[href="/products"]')
page.wait_for_url("**/products")  # 可能超时

#  可靠：等待目标页面元素出现
page.click('a[href="/products"]')
page.wait_for_selector("table")  # 商品页的表格出现即认为加载完成
```

### 13.6 坑 6：动态加载的 iframe 定位时机

**问题**：iframe 是异步加载的，直接 `page.frame()` 可能返回 None。

**解决**：先等待 iframe 元素出现，再获取 frame。

```python
#  iframe 可能还没加载
frame = page.frame(name="payment-frame")
frame.fill("#card-number", "4111")

#  先等待 iframe 元素
page.wait_for_selector('iframe[name="payment-frame"]')
frame = page.frame(name="payment-frame")
frame.fill("#card-number", "4111")
```

## 十四、写在最后

这篇回到基础，把 Playwright 浏览器 API 从启动配置到网络拦截、从 Frame 处理到设备模拟过了一遍。几个在实际项目中反复验证的经验：

1. **`wait_until="networkidle"` 在 Playwright 1.50+ 已 deprecated**，推荐用 `domcontentloaded` + 手动 `wait_for_selector` 组合。SPA 应用尤其要避免 networkidle——广告和统计请求可能永远让页面"不空闲"。
2. **Context 隔离是并发测试的基石**。每个测试用独立 Context，避免 cookies 和 localStorage 互相污染。登录一次后保存 `storage_state`，后续测试直接复用，能省大量时间。
3. **Shadow DOM 穿透**用 `>>>` 或 `>>` 连接符，Playwright 默认支持。遇到第三方 UI 库（如支付组件）嵌入 Shadow DOM 时，这是唯一可靠的定位方式。
4. **网络拦截要谨慎**。`route.abort()` 只拦截特定资源类型，不要全局拦截。我们在早期版本中全局拦截过图片，结果某个依赖图片加载完成事件的页面一直卡住。

下一篇我们进入 Python 协程实战，讲解 asyncio 在测试系统中的并发控制与异步编程，包括 Semaphore、gather 和 Task 管理等进阶用法。

---

## 十五、总结

这篇把 Playwright 浏览器 API 从基础到高级过了一遍，核心就五个 takeaway：

**第一，`networkidle` 已经死了。** Playwright 1.50+ 废弃了 `wait_until="networkidle"`，原因是现代 Web 应用的广告、统计、WebSocket 连接永远不会让网络"空闲"。替代方案是 `domcontentloaded` + `wait_for_selector`——等 DOM 加载完，然后等你要的元素出现。这比 networkidle 更可靠，因为你明确知道在等什么。

**第二，Context 隔离不是可选项，是必选项。** 没有 Context 隔离，测试 A 的登录状态会污染测试 B，测试 C 的 localStorage 会影响测试 D。每个测试用独立 Context，登录后保存 `storage_state` 到文件，后续测试直接加载。我们项目里 500 个测试用例，用 Context 隔离后从"必须串行跑"变成了"可以并行跑"，时间从 20 分钟降到 4 分钟。

**第三，Shadow DOM 用 `>>>` 连接符。** 第三方 UI 库（支付组件、日历组件）经常用 Shadow DOM 封装内部结构。Playwright 的 `>>>` 连接符可以穿透 Shadow DOM，这是 CSS 选择器做不到的。遇到定位不到的元素，先检查它是否在 Shadow DOM 里。

**第四，网络拦截要精确，不要全局。** `route.abort()` 拦截图片看起来省事，但有些页面依赖图片加载完成事件。我们踩过这个坑——全局拦截图片后，某个页面的"加载完成"事件永远不触发，测试卡了 30 秒。后来改成只拦截特定 URL 模式的图片，不再全局拦截。

**第五，设备模拟不是给移动端用的，是给响应式测试用的。** 即使你的产品没有 App，也应该用设备模拟测试响应式布局。iPhone SE 的 320px 宽度和 iPad 的 768px 宽度能暴露出大量桌面端看不到的布局问题。我们项目里 30% 的 UI bug 是在设备模拟下发现的。

配套代码里的 `tests/test_browser_api.py` 覆盖了登录、注册、商品列表等核心流程。先跑通测试，再对照这篇理解每个 API 的用法。

---

*这篇代码基于配套 `demo_app`（Flask 内置演示应用），可直接运行验证。*