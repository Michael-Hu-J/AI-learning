# 第01节-Appium 是什么 — 移动端自动化的行业标准

> 对应代码：配套代码（16节完整框架，含 API 测试 + UI 测试）
>
> 说明：本节涉及的代码示例，在配套代码中都能找到对应的真实实现。

---

## 这节讲什么

我手头一个项目，需要同时测 Android 和 iOS。两个平台，一套业务逻辑。如果为每个平台各写一套测试，工作量翻倍，维护成本也翻倍。

试了一圈市面上的工具：
- **UIAutomator2**：Android 上很快，但 iOS 用不了
- **XCUITest**：iOS 原生的，但 Android 不用想
- **Airtest**：图像识别直观，但精度和稳定性不够

最后选了 Appium。不是因为它比谁快——UIAutomator2 在 Android 上更快，XCUITest 在 iOS 上更原生——而是因为它是当时唯一一个能让我用同一套 Python 代码同时跑 Android 和 iOS 的工具。

---

## Appium 怎么工作的

Appium 是 C/S 架构：

```
测试脚本(Python) → HTTP请求 → Appium Server(Node.js) 
                                  ↓
                    ┌──────────────┼──────────────┐
                    ↓              ↓              ↓
              UiAutomator2    XCUITest      Espresso
              (Android)       (iOS)         (Android)
                    ↓              ↓              ↓
              Android设备     iOS设备        Android设备
```

你的 Python 脚本发 HTTP 请求给 Appium Server，Server 根据平台类型转发给对应的自动化引擎。Android 走 UiAutomator2，iOS 走 XCUITest。写代码的时候，`driver.find_element()` 在两个平台上调用方式一样——底层怎么转发你不用管。

## 和其他工具怎么选

| 工具 | 平台 | 语言 | 适合场景 |
|------|------|------|---------|
| Appium | Android + iOS | Python/Java/JS/C# | 双平台，统一代码 |
| UIAutomator2 | Android only | Java/Kotlin | 纯 Android 项目 |
| XCUITest | iOS only | Swift/Obj-C | 纯 iOS 项目 |
| Airtest | Android + iOS + Windows | Python | 游戏测试、图像识别 |

我个人的选择逻辑：
- **双平台 + 想用 Python** → Appium
- **只测 Android** → UIAutomator2（轻量，启动快）
- **只测 iOS** → XCUITest
- **游戏/图像匹配为主** → Airtest

## Appium 2.0 跟 1.x 有什么不一样

最大的变化：插件化。

1.x 版本装一个 `appium` 就自带所有推动。2.0 把推动拆成独立插件，需要手动装：

```bash
npm install -g appium

# 装 Android 推动
appium driver install uiautomator2

# 装 iOS 推动
appium driver install xcuitest

# 查看已装的推动
appium driver list

刚开始我还不适应，觉得多了一步麻烦。但用久了发现好处：推动可以独立升级。不用等 Appium 主版本更新就能用上最新的 UiAutomator2。

## 踩过的坑

### 1. 分不清 Appium Server 和 Appium Client
第一次用的时候，以为 `pip install Appium-Python-Client` 就够用了。结果跑测试报 `Connection refused` ——忘了启动 Appium Server。

**结论**：Appium Server 是一个独立的 Node.js 服务，需要先启动。测试脚本里的 `webdriver.Remote()` 是去连这个服务。Server 没起来，脚本连谁？

### 2. Appium 1.x 和 2.0 的教程混着看
网上大部分教程还是 1.x 的安装方式——`npm install -g appium` 就行了。但 2.0 还要多一步装 driver。一开始照着 1.x 的教程装完，跑测试报 `The desired capabilities must include either an app, appPackage or browserName`，查了半天才发现是推动没装。

### 3. 启动时间是真的慢
Android 上启动 UiAutomator2 Server 要 10-30 秒，iOS 上启动 WebDriverAgent 要 20-60 秒。注意，这不是一次性的——是每次测试会话都要等这么久。

**解决方案**：用 session 级 fixture，整个测试只初始化一次 driver。后面每篇细讲。

### 4. Appium Inspector 是必需品
不要凭想象写元素定位。先开 Appium Inspector 连上设备，看看页面上到底有哪些元素、它们的 accessibility_id 和 resource-id 是什么。我之前图省事，直接写 xpath，结果 App 一次改版 xpath 全废了。

---

## 什么时候不用 Appium

如果你的测试只需要验证 API 返回的数据对不对，用 `requests` 就够了，不需要启动 Appium。

Appium 只解决一个问题：**验证用户能看到什么、能操作什么**。API 层面的验证，用 requests 更轻更快。

配套代码里的 14 个测试，全是 API 测试，用 requests 直接调 Flask Mock Server，秒级跑完。如果改用 Appium 测相同逻辑，光是等推动启动就要半分钟。
