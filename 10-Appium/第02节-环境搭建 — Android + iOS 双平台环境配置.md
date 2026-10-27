# 第02节-环境搭建 — Android + iOS 双平台环境配置

> 对应代码：配套代码 `scripts/check_android_env.py`、`config.yaml`
>
> 说明：本节是所有配置的实际操作方法，配套代码中提供了一个环境检测脚本帮你诊断环境问题。

---

## 这节讲什么

Appium 环境搭建我搞过 3 次，每次都得重新查资料。JDK、Android SDK、ADB、Appium Server、UiAutomator2、Xcode、WebDriverAgent、Tidevice……十几个组件，版本不对就报错。

原项目环境配置文档写了 581 行，就是因为坑太多。这节把核心流程整理出来，下次搭环境不用再翻十几个页面。

---

## 系统要求

| 平台 | 能测什么 | 要装什么 |
|------|---------|---------|
| macOS | Android + iOS | JDK、Android SDK、Xcode、Node.js |
| Windows | Android only | JDK、Android SDK、Node.js |
| Linux | Android only | JDK、Android SDK、Node.js |

**iOS 自动化依赖 Apple 官方工具链（Xcode、代码签名、Simulator 等），官方仅提供 macOS 版本**。在本节「本机搭全套环境」的语境下，iOS 侧需要 Mac。没有本机 Mac 时，常见做法是 **云 Mac / CI 的 macOS Runner**（远端仍是 macOS），或 **第三方真机/云测**（由厂商提供设备与执行环境）。纯 Windows / Linux 无法用 Xcode 在本机等价复刻同一套流程；所谓变通，通常是 **把 macOS 或合规托管环境挪到云端/厂商侧**，而不是在单一非 Mac 工作机上替代整套官方工具链。
---

## Android 环境（四步）

### 第一步：JDK

```bash
# 检查是否已装
java -version

# macOS
brew install openjdk@17

# Windows：去 Oracle 官网下载 JDK 17+ 安装包
```

**版本注意**：Appium 2.0 要求 JDK 17+，但 JDK 21 在某些 UiAutomator2 场景下兼容性有问题。推荐 JDK 17。

### 第二步：Android SDK

```bash
# macOS
brew install --cask android-commandlinetools

# 配环境变量
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin

# 装必要的组件
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

**环境变量要写到 shell 配置文件里**（`.zshrc` 或 `.bash_profile`），否则新开终端就得重设。我吃过这个亏——明明装好了，新开窗口跑测试说找不到 adb。

### 第三步：验证 ADB

```bash
adb version
adb devices
```

真机需要开启 USB 调试。模拟器启动后会自动连接。

### 第四步：Appium Server + 推动

```bash
# 装 Node.js
brew install node

# 装 Appium 2.0
npm install -g appium

# 装 Android 推动
appium driver install uiautomator2

# 验证
appium driver list

**注意**：Appium 2.0 跟 1.x 不一样。1.x 装完 `appium` 就能用。2.0 必须额外装 driver。我第一次装的时候就踩了这个坑——装完跑测试报错，查了半天才发现少了这步。

---

## iOS 环境（两种方式）

### 方式一：Tidevice（推荐）

不用 Xcode 编译，省掉签名配置的麻烦。

```bash
pip3 install tidevice

# 查看设备
tidevice list

# 启动 WDA 代理
tidevice wdaproxy -B com.example.WebDriverAgent --port 8100

# 验证
curl http://127.0.0.1:8100/status

**优点**：不需要 Xcode 编译 WDA，不需要配置开发者签名，启动速度快。

### 方式二：传统 WebDriverAgent

```bash
# 需要 Xcode（App Store 下载）
git clone https://github.com/appium/WebDriverAgent.git
# 在 Xcode 中打开，配好签名，编译安装到设备
# 设备上信任开发者证书
```

**麻烦的地方**：每次 Xcode 升级或 WDA 重新编译都要折腾签名配置。团队里新来一个人，光配 WDA 环境就要半天。

---

## 环境变量配置

配套代码里的配置方式：

```bash
# Android
export PLATFORM=android
export ANDROID_PLATFORM_VERSION=14
export ANDROID_DEVICE_NAME="Android Emulator"
export APP_PACKAGE=com.example.app
export APP_ACTIVITY=.MainActivity

# iOS
export PLATFORM=ios
export IOS_PLATFORM_VERSION=17.0
export IOS_DEVICE_NAME="iPhone 15"
export BUNDLE_ID=com.example.app
export USE_TIDEVICE=true

# API
export API_BASE_URL=https://api.example.com
export API_TIMEOUT=30
```

`config.yaml` 里也有对应的配置项，两套机制都可以用。

---

## 验证环境

```bash
# 1. Java 版本
java -version

# 2. ADB 连接
adb devices

# 3. Appium
appium --version

# 4. 推动列表
appium driver list

# 5. Tidevice（iOS）
tidevice list

# 6. 用配套代码的环境检测脚本
python scripts/check_android_env.py

---

## 踩过的坑

### 1. Appium Server 没启动
症状：`Connection refused: localhost:4723`
原因：忘了先跑 `appium`。测试脚本是去连 Server 的，Server 没起来当然连不上。

### 2. JDK 版本不对
JDK 21 在某些 Android 模拟器场景下导致 UiAutomator2 安装失败。降回 JDK 17 就好了。

### 3. ADB 找不到设备
真机连接电脑后，手机弹窗要点"允许 USB 调试"。不点的话 `adb devices` 显示 `unauthorized`。

### 4. 环境变量忘了 source
配好了 `ANDROID_HOME`，但新开终端窗口后忘了 `source ~/.zshrc`，跑脚本报找不到 adb。

### 5. Appium 2.0 的 driver 没装
`npm install -g appium` 后直接跑测试，报错 `The desired capabilities must include either an app, appPackage or browserName`。查了半天才发现 2.0 还要 `appium driver install uiautomator2`。

### 6. iOS 的 WDA 签名问题
用传统方式配 WDA，Xcode 签名配置稍微不对就编译失败。后来改用 Tidevice，省心多了。

---

## 高效启动清单

1. `java -version` 
2. `adb devices` 
3. `appium --version` 
4. `appium driver list` （能看到 uiautomator2）
5. `appium` （启动 Server，保持终端开着）
6. 新开终端：`pytest tests/ -v` 
