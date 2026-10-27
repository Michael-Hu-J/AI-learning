# 09 — Playwright AI 自动化测试（11 篇 + 配套代码）

> 从入门到 **UI 测试引擎** 的系列文章 + **可直接运行** 的 `locator/`、`healer/`、`worker/` 等源码。  \
> **配套代码目录**：[`配套代码/`](配套代码/README.md)（pytest、Playwright 命令均在该目录执行）。

---

## 一分钟看懂：和 08、Skill 怎么分

详细对照表见：[附录-进阶路线与三件套分工.md](附录-进阶路线与三件套分工.md)

---

## 文章列表（建议阅读顺序）

| 顺序 | 文件 | 讲什么 | 建议跑什么 |
|------|------|--------|------------|
| 0 | 第0篇-Playwright入门 | 安装、定位、等待、第一个测试 | `tests/test_browser_api.py` |
| 1 | 第1篇-架构定位 | 系统在项目中的位置 | 可选 |
| 2 | 第2篇-执行引擎 | JSON 步骤、`ui_worker`；**附：路径二 spec、Agent 认知图** | 读代码 `worker/` |
| 3 | 第3篇-三层定位降级 | L1/L2/L3；**附：`locator_tiers` JSON** | `tests/test_locator.py` |
| 4 | 第4篇-AI自愈系统 | 诊断→策略→重试；**附：运行时 vs 改脚本** | `tests/test_healer.py` |
| 5 | 第5篇-视觉语义定位 | 语义/OpenCV；**附：截图意图、像素回归** | `test_visual.py`、`test_snapshot_demo.py` |
| 6 | 第6篇-MCP协议集成 | Agent 控浏览器 | `test_mcp_and_async.py`（需 `pip install mcp`） |
| 7 | 第7篇-并发控制 | 多浏览器、进程隔离 | 架构阅读 |
| 8 | 第8篇-SSE实时日志 | 双通道前端 | 架构阅读 |
| 9 | 第9篇-浏览器 API 实战 | Context、Frame、网络拦截等 | `test_browser_api.py` |
| 10 | 第10篇-asyncio 协程 | 异步并发控制 | `test_mcp_and_async.py` |
| — | [附录-进阶路线与三件套分工.md](附录-进阶路线与三件套分工.md) | 08/09/Skill 怎么搭 | 选读 |

---

## 怎么开始（3 步）

```bash
cd 配套代码
pip install -r requirements.txt
playwright install chromium

# 终端1：演示站
cd demo_app && python app.py

# 终端2：冒烟
cd ..
pytest tests/test_locator.py tests/test_healer.py -v
```

更完整的说明、FAQ、NL 演示见 **[配套代码/README.md](配套代码/README.md)**。

---

## 两条 UI 自动化路径（本课 vs Skill）

```
         URL / 截图 / 自然语言
                  │
    ┌─────────────┴─────────────┐
    ▼                           ▼
路径一（本课主路径）          路径二（Skill）
JSON 步骤 → ui_worker         ui_pytest spec → generate.sh → pytest
配套代码完整实现              本课仅 examples/*.md 示例
```

---

## 本课增补文件（相对旧版）

| 文件 | 用途 |
|------|------|
| `配套代码/examples/ui_login_spec_example.md` | 声明式 UI spec 结构示例 |
| `配套代码/examples/page_intent_example.md` | 截图→测试意图表模板 |
| `配套代码/examples/locator_tiers_example.json` | 元素清单 JSON（对应 Skill） |
| `配套代码/tests/test_snapshot_demo.py` | 像素截图回归 demo |
| `附录-进阶路线与三件套分工.md` | 08/09/Skill 分工与进阶路线 |

---

## 文件夹结构（顶层）

```
09-playwright/
├── README.md                    ← 你正在看的总说明
├── 第0篇-....md ～ 第10篇-....md
├── 附录-进阶路线与三件套分工.md
└── 配套代码/                    ← 可运行工程（必读 配套代码/README.md）
    ├── demo_app/
    ├── locator/  healer/  worker/  mcp/
    ├── examples/
    └── tests/
```

---

## 演示账号（与 `demo_app/app.py` 一致）

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 管理员 |
| `testuser` | `test123` | 普通用户 |

文章与测试默认用 **`admin` / `admin123`**；MCP 示例中普通用户场景用 **`testuser` / `test123`**。

---

## 对外打包说明（勿随课包外发）

打 zip / 上传网盘前请**不要**收录以下内容：

| 类型 | 路径 / 说明 |
|------|-------------|
| 缓存与虚拟环境 | `.pytest_cache/`、`__pycache__/`、`配套代码/.venv/` |
| 本地密钥 | `.env`、`DASHSCOPE_API_KEY` 等真实 API Key（LLM 为可选能力） |
| 运行产物 | 测试截图 diff 基线若含内网页面，发布前请复核 |

**本课包不包含**（正文仅架构/概念引用，需另获取）：AI 测试执行平台完整前后端（第 7～8 篇 SSE 管理端）、专业版 Skill 全套 `generate.sh` 与 Agent 规则、独立部署的「秒杀财务」完整后端仓库。学员以本目录 `demo_app` 即可跑通主线。

---

## 常见问题

**Q：对外发出版第 4 篇和完整版区别？**  
内容更短，附录「运行时 vs 脚本自愈」已同步；工程细节以完整版 + 配套代码为准。

**Q：按文章抄登录失败？**  
确认 `demo_app` 已启动，且口令为上表 `admin123` / `test123`，不要用旧资料里的 `demo_pass`。

---

**作者**：测试员周周 · 公众号：测试员周周
