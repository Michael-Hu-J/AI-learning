# UI 自动化为什么坚持 pytest + Playwright（Python）

> Playwright 安装与无头环境变量以 zip 内 **`README.md`**、**`UI-skills`** 为准。

专业版在浏览器 E2E 上的立场很明确：

**主交付 = Python + pytest + Playwright。**

不是 MidScene 脚本，不是 Playwright 的 TypeScript `.spec.ts` 作为主产物。这样和接口线一样，能进同一套 CI、同一套缺陷流程。

---

## 和「录屏 / 自然语言点页面」的差别

| | 录屏 / 纯 NL 驱动 | 专业版 UI 线 |
|--|-------------------|--------------|
| 产物 | 往往是一次性脚本 | pytest 模块，可 diff |
| 维护 | 页面一变全重录 | spec + 定位层级 + 自我修复（见第 12 篇） |
| CI | 接入成本高 | 与 API 共用 pytest 命令 |
| 人员 | 测试可参与 | 测开与测试都能改 spec |

不是说 NL 没用——适合**探索**；**回归**仍建议落到 spec / pytest。

---

## 两条入口

### 1. 声明式 spec

```bash
./generate.sh templates/ui_login.md
# 或 ui_smoke_one_page.md 等
cd output && python3 -m pytest ui_login.py --collect-only -q
```

依赖安装：

```bash
pip install pytest-playwright
playwright install chromium
```

### 2. AI 执行线

```text
@UI-skills/执行/SKILL.md

被测 URL: https://test.example.com/login
场景：正确账号登录后跳转到首页；错误密码提示错误文案。
请生成 ui_pytest_playwright spec 到 output/ui_login_smoke.md，
并说明 generate 与 pytest 命令。
```

可选附上截图（脱敏），便于 AI 理解布局。

---

## 定位思路：L1 → L2 → L3（只记名字）

专业版 UI SKILL 要求按层级选定位，降低脆弱性：

- **L1**：角色、文案、placeholder 等用户可见语义（优先）  
- **L2**：稳定 `data-testid`、表单 name  
- **L3**：CSS / XPath（最后手段）  

具体怎么选、失败了怎么升档，在 `UI-skills` 执行与自我修复文档里。**本篇不展开选择器表。**

---

## 自然语言一句话执行 UI（nl_ui_client.py）

如果你不想写 spec，也不想打开 AI编辑器，包内提供了 `nl_ui_client.py`，用自然语言直接驱动 Playwright：

```bash
# 安装 playwright 后
python nl_ui_client.py "给我新增一个商品"
python nl_ui_client.py "登录后进入商品列表，搜索关键词 abc"
```

工作原理：

- 优先连接本地 NL API 服务（`http://localhost:5010`），由服务端解析指令并执行 Playwright 步骤
- API 不可用时自动回退为同进程 import（需自行准备 nl_service 模块，通过环境变量 `NL_PLAYWRIGHT_CODE` 指定路径）
- 支持 `--parse-only` 只解析不执行、`--no-headless` 显示浏览器窗口、`--json` 输出结构化结果

适合探索性操作和快速验证；**回归测试**仍建议走 spec → generate → pytest 的标准流程（稳定性可追踪）。

---

## 和 MidScene、MCP 的关系

你的工作区可能装了 Playwright MCP、MidScene 等插件。专业版**不把它们作为主交付**，避免团队里同时维护 TS 与 Python 两套回归。

若你已用 MCP 探路，可以把探到的步骤整理成自然语言，再 @ `UI-skills/执行` 出 **Python spec**。

---

## 常见安装与运行问题

| 现象 | 处理 |
|------|------|
| `Executable doesn't exist` | `playwright install chromium` |
| 无头环境失败 | 加 `HEADLESS=1` 或 SKILL 里约定的环境变量（以包内为准） |
| 超时 | 先加大等待或检查 URL；别在未启动服务时长时间 `-v` |
| 选择器找不到 | 走 UI 自我修复 SKILL，或改 spec 后重新 generate |

---

## 视觉回归别和功能 UI 混为一谈

改版防布局可以用 `visual_regression` kind（第 10 篇）。功能点击、表单校验仍用 `ui_pytest_playwright`。

---
