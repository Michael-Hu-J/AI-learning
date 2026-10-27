# App 测试走 Appium：和浏览器 Playwright 不要混在一锅

> Appium 环境与 capabilities 字段以包内 **`templates/appium_*.md`**、**`mobile-skills`** 为准。

问移动端的同学，最容易犯的错是：

在 Chat 里 @ 了 `UI-skills`，却拿着 Android 包名说「帮我点登录」。

专业版里 **浏览器** 和 **App** 是两条技能线，声明式 kind 也不同。

---

## 默认技术栈

| 项 | 选择 |
|----|------|
| 驱动 | Appium 2 |
| 语言 | Python |
| 框架 | pytest |
| 声明式 kind | `appium_pytest` |

前置：本机或 CI 能连上 Appium Server，模拟器/真机已就绪。这和「只装 playwright install」不是同一套环境。

---

## 推荐顺序：先规划，再执行

| 阶段 | 目录 | 作用 |
|------|------|------|
| 规划 | `mobile-skills/规划` | 测哪些版本、哪些机型、定位策略、风险 |
| 执行 | `mobile-skills/执行` | 出 spec / pytest、环境变量约定 |
| 自我修复 | `mobile-skills/自我修复` | 脚本红了、定位飘了时的收敛流程 |

话术示例：

```text
@mobile-skills/规划/SKILL.md

App：某某 Android 包，版本 2.3.0，核心流程：登录、下单、支付结果页。
请输出测试范围与优先级，不要写代码。
```

规划认可后再：

```text
@mobile-skills/执行/SKILL.md

按规划生成 appium_pytest spec 到 output/app_login_smoke.md。
```

---

## 声明式：不打开 AI 也能生成

```bash
./generate.sh templates/appium_e2e.md
# 或 appium_login 等（以 templates/ 实际文件名为准）
```

改 YAML 里的 capabilities、包名、activity、步骤后重新 `generate.sh`。  
**不要**把 Web 的 `ui_pytest_playwright` spec 硬改成 Appium 字段——kind 不同，生成器不同。

---

## 和 UI-skills 的边界

| 场景 | 用 |
|------|-----|
| Chrome 里 H5 | 多数仍走 UI-skills（Playwright） |
| 原生 / 混合 App 壳 | mobile-skills |
| 微信小程序 | 看你们技术栈；包内 mobile 线按 Appium 约定，特殊渠道需自备驱动说明 |

听不清时问一句：**「测的是浏览器里的页面，还是安装的 APK/IPA？」**

---

## 失败排查（现象级）

1. Appium 服务是否监听、设备是否 `adb devices` 可见  
2. capabilities 里 `appPackage` / `appActivity` 是否与当前包一致  
3. 是否混用了 Web 定位 API（Appium 用 AppiumBy）  
4. 纯 `sleep` 过多导致偶发失败——执行 SKILL 更推荐显式等待（细节在包内）

仍解决不了 @ `mobile-skills/自我修复/SKILL.md`。

---
