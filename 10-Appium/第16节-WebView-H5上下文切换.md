# 第16节-WebView-H5上下文切换 — 混合应用的自动化难点

> 对应代码：配套代码 `utils/webview_helper.py`
>
> 说明：本节代码示例与配套代码中的 `webview_helper.py` 完全对应。

---

## 这节讲什么

现在大部分 App 都不是纯原生的了。

你打开一个电商 App，首页是原生写的，点进商品详情页就变成了 H5 网页。再点「支付」，又切到一个内嵌的 H5 收银台页面。页面看起来是一个 App，实际是**原生壳 + 内嵌网页**混着来的。

这种叫**混合应用（Hybrid App）**。

自动化测试混合应用的难点在于：**原生页面的操作方式和 H5 页面的操作方式不一样**。在原生页面你用 `find_element` 找控件，到了 H5 页面你其实是在操作一个浏览器里的网页——得用 CSS/JS 那一套。

Appium 通过「上下文切换」来解决这个问题。这节讲清楚：

1. **上下文（Context）是什么**——NATIVE_APP vs WEBVIEW
2. **switch_to_webview / switch_to_native**——核心切换方法
3. **wait_for_webview**——等 WebView 加载完成再操作
4. **在 WebView 里执行 JS**——直接操作 H5 页面元素
5. **踩坑经验**——ChromeDriver 版本、debuggable、iOS Safari 调试

---

## 1. 混合应用场景

先看一个典型场景：

```python
# 这是一个混合应用的典型流程
# 1. 原生页面：登录（原生控件）
# 2. 原生 → H5：点击某个入口，跳转到 H5 页面
# 3. H5 页面：填写表单（网页元素）
# 4. H5 → 原生：提交后回到原生页面

电商 App、金融 App、社交 App 基本都是这个模式。

**为什么 App 要这么设计？**

- **原生壳**：保证启动速度、系统权限调用、流畅的导航体验
- **H5 页面**：高效更新、跨平台复用（iOS 和 Android 用同一套 H5）、不需发版就能改页面内容

对测试来说，这意味着你的脚本必须能在「原生模式」和「网页模式」之间来回切换。

---

## 2. 上下文（Context）概念

Appium 把 App 里的每一种「环境」称为一个上下文（Context）。常见的上下文有两种：

| 上下文 | 含义 | 说明 |
|--------|------|------|
| `NATIVE_APP` | 原生应用环境 | App 本身的原生界面 |
| `WEBVIEW_com.package.name` | WebView 环境 | App 内嵌的 H5 网页 |

**怎么理解？**

- `NATIVE_APP` 是「App 自己的世界」——你能用 `find_element` 找到按钮、输入框、列表
- `WEBVIEW_xxx` 是「浏览器世界」——你得用 CSS 选择器、XPath 或者 JS 来操作页面元素

Appium 拿到 `driver.contexts` 就能看到当前有哪些上下文可用：

```python
contexts = driver.contexts
print(contexts)
# ['NATIVE_APP', 'WEBVIEW_com.example.app']
```

刚启动 App 时只有 `NATIVE_APP`。进入某个 H5 页面后，`WEBVIEW_xxx` 才会出现。

---

## 3. switch_to_webview / switch_to_native

配套代码的 `webview_helper.py` 封装了上下文切换的核心逻辑。

### switch_to_webview

```python
def switch_to_webview(driver, package_name=None):
    """
    切换到WebView上下文（H5页面）

    参数说明：
    - driver: Appium WebDriver实例
    - package_name: 应用包名（可选），用于精确匹配WebView上下文。
                    如果为None则自动切换到第一个可用的WebView

    返回：
    - bool: 是否成功切换到WebView
    """
    try:
        contexts = driver.contexts
        logger.info(f"当前可用上下文: {contexts}")

        target_context = None

        if package_name:
            webview_name = f"WEBVIEW_{package_name}"
            if webview_name in contexts:
                target_context = webview_name
        else:
            for ctx in contexts:
                if ctx.lower().startswith("webview"):
                    target_context = ctx
                    break

        if target_context is None:
            logger.warning("未找到可用的WebView上下文")
            return False

        driver.switch_to.context(target_context)
        logger.info(f"成功切换到WebView: {target_context}")
        return True

    except Exception as e:
        logger.error(f"切换到WebView失败: {str(e)}")
        return False
```

**关键点**：

- `package_name` 参数：如果你的 App 有多个 WebView 实例，可以精确指定切到哪个。比如支付页面和商品详情页可能在不同的 WebView 里。
- 不传 `package_name` 时，自动选第一个可用的 WebView。大部分场景下够用，因为同一时间只有一个 H5 页面是激活的。

### switch_to_native

```python
def switch_to_native(driver):
    """
    切换回原生（Native）上下文

    返回：
    - bool: 是否成功切换回原生上下文
    """
    try:
        driver.switch_to.context("NATIVE_APP")
        logger.info("成功切换回原生上下文: NATIVE_APP")
        return True
    except Exception as e:
        logger.error(f"切换回原生上下文失败: {str(e)}")
        return False
```

**为什么叫 `NATIVE_APP`**：这是 Appium 的约定名称，不可更改。不管什么 App，原生上下文的名字都是 `"NATIVE_APP"`。

### 使用示例

```python
# 场景：从原生页面进入 H5 页面，填写表单后返回

# 1. 当前在原生，点击"打开H5页面"按钮
native_page.click_open_h5_button()

# 2. 切换到 WebView
if switch_to_webview(driver, package_name="com.example.app"):
    # 现在可以操作 H5 页面了
    h5_input = driver.find_element("css selector", "#username")
    h5_input.send_keys("admin")

    # 3. 操作完切回原生
    switch_to_native(driver)
else:
    print("没有找到 WebView，页面可能没加载出来")
```

---

## 4. wait_for_webview 等待 WebView 加载完成

H5 页面不会瞬间加载完。点了一个原生按钮后，App 要启动 WebView、加载网页、渲染 DOM——这个过程可能要几秒钟。

如果不等就切上下文，`driver.contexts` 里只有 `NATIVE_APP`，WebView 还没出现，切换必然失败。

```python
def wait_for_webview(driver, timeout=10, package_name=None, interval=1):
    """
    等待WebView上下文出现

    参数说明：
    - driver: Appium WebDriver实例
    - timeout: 最大等待时间（秒），默认10秒
    - package_name: 应用包名（可选），用于精确匹配WebView上下文
    - interval: 轮询间隔（秒），默认1秒

    返回：
    - str: 成功时返回WebView上下文的名称，超时未找到返回None
    """
    start_time = time.time()
    logger.info(f"开始等待WebView上下文，超时时间: {timeout}秒")

    while time.time() - start_time < timeout:
        try:
            contexts = driver.contexts
            logger.debug(f"当前上下文: {contexts}")

            target_context = None

            if package_name:
                webview_name = f"WEBVIEW_{package_name}"
                if webview_name in contexts:
                    target_context = webview_name
            else:
                for ctx in contexts:
                    if ctx.lower().startswith("webview"):
                        target_context = ctx
                        break

            if target_context:
                logger.info(f"WebView上下文已出现: {target_context}")
                return target_context

            time.sleep(interval)

        except Exception as e:
            logger.warning(f"检查WebView上下文时出错: {str(e)}")
            time.sleep(interval)

    logger.warning(f"等待WebView上下文超时（{timeout}秒），未找到可用WebView")
    return None
```

**使用方式**：

```python
# 点击打开 H5 页面
native_page.click_open_h5_button()

# 等 WebView 出现，最多等 10 秒
webview_name = wait_for_webview(driver, timeout=10)
if webview_name:
    driver.switch_to.context(webview_name)
    # 开始操作 H5 页面
else:
    # 超时处理
    print("H5 页面加载超时")
```

**为什么不用 `time.sleep(5)`**：

- 网络好的时候 1 秒就加载完了，你白等了 4 秒
- 网络差的时候 5 秒不够，还在加载你就切过去了，直接失败
- `wait_for_webview` 每秒检查一次，加载好了就立刻返回，不浪费一秒钟

---

## 5. 在 WebView 中执行 JS 操作页面

切换到 WebView 之后，你可以用 `driver.find_element` 配合 CSS/XPath 定位元素。但有些操作用 Appium 的 find_element 搞不定——比如滚动到页面底部、获取页面标题、修改某个元素的样式，这时候直接用 JS 更爽。

```python
def execute_js_in_webview(driver, script, *args):
    """
    在WebView中通过JavaScript操作页面

    参数说明：
    - driver: Appium WebDriver实例
    - script: 要执行的JavaScript代码字符串
    - args: 传递给JavaScript的参数（可选）

    返回：
    - any: JavaScript执行结果

    使用示例：
    # 获取页面标题
    title = execute_js_in_webview(driver, "return document.title")

    # 点击页面中的某个元素
    execute_js_in_webview(driver, "document.getElementById('submit-btn').click()")

    # 滚动到页面底部
    execute_js_in_webview(driver, "window.scrollTo(0, document.body.scrollHeight)")
    """
    try:
        current_context = driver.current_context
        if current_context == "NATIVE_APP":
            logger.warning("当前在原生上下文中，请先调用 switch_to_webview() 切换到WebView")

        result = driver.execute_script(script, *args)
        logger.info(f"执行JavaScript成功，脚本: {script[:80]}{'...' if len(script) > 80 else ''}")
        return result

    except Exception as e:
        logger.error(f"执行JavaScript失败: {str(e)}, 脚本: {script[:100]}")
        raise
```

**一些实用的 JS 操作**：

```python
# 获取 H5 页面标题（用于断言当前页面是否正确）
title = execute_js_in_webview(driver, "return document.title")
assert "注册" in title, f"预期在注册页面，实际标题为: {title}"

# 获取输入框的值
value = execute_js_in_webview(driver,
    "return document.getElementById('phone').value")

# 修改输入框的值（某些情况下 send_keys 不好使）
execute_js_in_webview(driver,
    "document.getElementById('phone').value = '13800138000'")

# 触发某个元素的点击事件（原生 click() 被 JS 拦截时）
execute_js_in_webview(driver,
    "document.querySelector('.submit-btn').dispatchEvent(new Event('click'))")
```

**用 JS 还是用 find_element**：

- 简单操作（点击、输入）→ 用 `find_element` + CSS/XPath，代码更清晰
- 需要返回值（获取文本/属性/页面信息）→ 用 JS 更方便
- 页面用了复杂的 Vue/React 框架，Appium 的 click 经常点不上 → 试试用 JS 的 `.click()`
- 页面滚动、修改属性 → 这是 JS 的强项

---

## 6. get_available_contexts 查看当前上下文

有时候你不太确定当前在哪个上下文，可以先用 `get_available_contexts` 看看：

```python
def get_available_contexts(driver):
    """
    获取当前所有可用的上下文列表

    返回：
    - list: 上下文名称列表，如 ['NATIVE_APP', 'WEBVIEW_com.package.name']
    """
    try:
        contexts = driver.contexts
        logger.info(f"获取可用上下文列表: {contexts}")
        return contexts
    except Exception as e:
        logger.error(f"获取上下文列表失败: {str(e)}")
        raise

这个函数在调试时特别有用。比如你的脚本突然报错找不到元素了，可以先打印 `get_available_contexts(driver)`，看看是不是上下文意外切换了。

---

## 踩过的坑

### 1. ChromeDriver 版本匹配

这是 WebView 测试**最坑**的问题，没有之一。

Appium 底层是通过 ChromeDriver 来操作 WebView 的。Android 系统内置的 WebView（或者 Chrome）版本变了，你的 ChromeDriver 版本也必须跟着变。

**表现**：切换到 WebView 时没有任何报错，但 `find_element` 一直超时，或者 `driver.contexts` 里一直看不到 WebView。

**原因**：ChromeDriver 和 WebView 的 Chromium 内核版本不匹配。

**解决**：

- 方法一：查看设备上 WebView 的版本号，下载对应版本的 ChromeDriver
- 方法二：用 `appium:chromeDriverExecutable` 指定 ChromeDriver 路径
- 方法三：Appium 2.x 自带 Chromedriver 自动下载，但如果公司内网限制了下载，还是会失败

```python
# 在 Capabilities 中指定 ChromeDriver
capabilities = {
    "appium:chromeDriverExecutable": "/path/to/chromedriver",  # 指定特定版本
    "appium:chromedriverExecutableDir": "/path/to/chromedrivers/",  # 指定目录
}

**血泪教训**：有次 ChromeDriver 版本没跟上，排查了 3 个小时——切换 WebView 没报错，找元素也不报错，就是找不到。后来打印了 ChromeDriver 的日志才发现版本不匹配。

### 2. WebView debuggable 开关

Android 的 WebView 默认**不开调试模式**。不开的话 Appium 根本连不上——`driver.contexts` 里永远只有 `NATIVE_APP`，WebView 不会出现。

**需要开发在 WebView 初始化时加一行代码**：

```java
// Android 原生代码中
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
    WebView.setWebContentsDebuggingEnabled(true);
}

这是 Android 4.4（KitKat）以上版本的 WebView 调试开关。**只对 debug 包有效**。release 包就算开了这个开关也不行。

**测试时需要确认**：

- 测试包必须是 debug 版本，或者 release 包但开发专门开了 debuggable
- 某些第三方 SDK（如腾讯 X5 内核）有自己的 WebView 实现，调试方式可能不同

### 3. WebView 初始化延迟

刚点开 H5 页面时，WebView 还没初始化好，`driver.contexts` 里没有 `WEBVIEW_xxx`。

这个延迟不是网页加载的延迟，而是 WebView 本身创建和注册的延迟。有时候网页内容已经显示在屏幕上了，但 Appium 这边还没检测到 WebView 上下文。

**解决**：用 `wait_for_webview` 轮询等待，而不是直接切换。前面第 4 节讲过。

### 4. iOS 的 Safari 调试

iOS 上的 WebView 调试跟 Android 完全不一样。

iOS 用的是 **WKWebView**（iOS 8+ 之后）。要在自动化中访问 WKWebview，需要在 Capabilities 中开启：

```python
capabilities = {
    "appium:includeSafariInWebviews": True,  # 包含 Safari WebView
    "appium:webkitDebugProxyPort": 27753,    # 调试代理端口
}

**iOS 的额外限制**：

- iOS 真机需要在开发者设置里打开 `Enable Web Inspector`
- iOS 模拟器默认支持，但真机需要开发者账号签名
- iOS 上 WebView 的上下文名称格式是 `WEBVIEW_进程ID`，不是 `WEBVIEW_包名`
- 某些场景下 iOS 需要额外安装 `ios_webkit_debug_proxy` 才能访问 WebView

**iOS vs Android 差异总结**：

| 对比项 | Android | iOS |
|--------|---------|-----|
| WebView 引擎 | Chromium WebView / 腾讯 X5 | WKWebView |
| 调试开关 | `setWebContentsDebuggingEnabled(true)` | Web Inspector + webkitDebugProxyPort |
| 上下文命名 | `WEBVIEW_包名` | `WEBVIEW_进程ID` |
| 推动依赖 | ChromeDriver | ios_webkit_debug_proxy |
| 模拟器支持 | 大部分支持 | 模拟器默认支持 |
| 真机支持 | debug 包即可 | 需要开发者签名 |

### 5. 切换上下文后之前的元素引用失效

切到 WebView 后，你在原生上下文里找到的元素引用全部失效。切回来也一样——之前的引用不能用了，需要重新查找。

```python
#  错误：先找元素，再切上下文，然后用旧的元素
native_btn = driver.find_element("id", "native_button")
switch_to_webview(driver)
native_btn.click()  # 报错！元素引用已失效

#  正确：每次切回原生后重新找元素
switch_to_native(driver)
native_btn = driver.find_element("id", "native_button")
native_btn.click()
```

### 6. 多个 WebView 同时存在

有些 App 会同时有多个 WebView 实例——比如主页面一个 WebView，底部广告又是一个 WebView。`driver.contexts` 里可能有 `WEBVIEW_com.app.main` 和 `WEBVIEW_com.app.ad` 两个。

**切错了 WebView 会怎样**：你在广告 WebView 里找主页面的元素，永远找不到。

**解决**：用 `wait_for_webview` 的 `package_name` 参数精确匹配，或者先打印 `get_available_contexts` 看看有哪些，再决定切到哪个。

### 7. 在某些国产 ROM 上 WebView 异常

小米、华为、OPPO 等国产 ROM 会对 WebView 做一些魔改。常见问题：

- **小米**：MIUI 的 WebView 有安全限制，某些 JS 执行会失败
- **华为**：EMUI 的 WebView 可能会延迟注册，`wait_for_webview` 的 timeout 要设长一点
- **OPPO/Vivo**：ColorOS/Funtouch OS 的 WebView 在某些系统版本上完全不走 ChromeDriver，需要单独配置

**建议**：混合 App 的兼容测试至少准备 3 台不同品牌的主流真机。

---

## 实战：切换到 H5 页面完成表单填写后切回原生

把前面的内容串起来，看一个完整的场景：

```python
from utils.webview_helper import (
    get_available_contexts,
    switch_to_webview,
    switch_to_native,
    wait_for_webview,
    execute_js_in_webview,
)

def test_h5_form_fill(driver):
    """测试：从原生进入H5页面，填写表单，提交后回到原生"""

    # ===== 1. 当前在原生，找到并点击"H5表单"入口 =====
    h5_entry = driver.find_element("id", "com.example.app:id/btn_h5_form")
    h5_entry.click()

    # ===== 2. 等待 WebView 出现并切换 =====
    webview_name = wait_for_webview(driver, timeout=10, package_name="com.example.app")
    assert webview_name is not None, "WebView 未出现，H5 页面可能加载失败"

    switch_result = switch_to_webview(driver, package_name="com.example.app")
    assert switch_result, "切换到 WebView 失败"

    # ===== 3. 在 H5 页面填写表单 =====
    # 方式一：用 CSS 选择器
    name_input = driver.find_element("css selector", "#name")
    name_input.send_keys("张三")

    phone_input = driver.find_element("css selector", "#phone")
    phone_input.send_keys("13800138000")

    # 方式二：用 JS 点击提交按钮（某些前端框架中 click() 更可靠）
    execute_js_in_webview(driver,
        "document.getElementById('submit-btn').click()")

    # ===== 4. 等 H5 返回结果，验证后切回原生 =====
    # 等待提交成功的提示出现
    import time
    time.sleep(2)  # 简单等提交完成

    # 获取页面的提示信息
    result_text = execute_js_in_webview(driver,
        "return document.getElementById('result-msg').textContent")
    assert "提交成功" in result_text, f"提交失败: {result_text}"

    # ===== 5. 切回原生上下文继续操作 =====
    switch_result = switch_to_native(driver)
    assert switch_result, "切回原生上下文失败"

    # 现在又在原生界面了，可以继续原生操作
    back_btn = driver.find_element("id", "com.example.app:id/btn_back")
    back_btn.click()

**注意事项**：

- 每次切换上下文后，**先确认切换成功**（assert 返回值），再继续操作
- H5 页面里的操作，如果 `find_element` 不好使，果断用 `execute_js_in_webview`
- 切回原生后，之前找过的元素引用都失效了，重新 `find_element`
- 如果 H5 页面加载慢，把 `wait_for_webview` 的 timeout 设到 15-20 秒

---

## 要点回顾

| 问题 | 解决方案 | 对应函数 |
|------|---------|---------|
| 查看当前上下文 | 获取 `driver.contexts` | `get_available_contexts` |
| 切换到 H5 页面 | 自动匹配第一个 WebView 或按包名精确匹配 | `switch_to_webview` |
| 切回原生界面 | 切换到 `NATIVE_APP` | `switch_to_native` |
| 等 WebView 加载 | 轮询 `driver.contexts` 直到 WebView 出现 | `wait_for_webview` |
| 操作 H5 页面元素 | 在 WebView 中执行 JS | `execute_js_in_webview` |
| ChromeDriver 版本不匹配 | 指定 `chromeDriverExecutable` | Capabilities 配置 |
| iOS WebView 无法访问 | 开启 `webkitDebugProxyPort` | Capabilities 配置 |
| 国产 ROM 兼容 | 多品牌真机测试，延长 timeout | 设备策略 |

WebView/H5 上下文切换看起来只是几行 `switch_to.context()` 的调用，实际涉及 ChromeDriver 版本管理、WebView 生命周期、iOS/Android 双平台差异、国产 ROM 兼容等多个方面。

做好混合应用测试的关键就两句话：

1. **切换前确认 WebView 已就绪**——用 `wait_for_webview` 而不是 `time.sleep`
2. **切回原生后重新找元素**——之前缓存的引用全部失效

配套代码的 `webview_helper.py` 把这几个函数封装好了，拿来就能用。
