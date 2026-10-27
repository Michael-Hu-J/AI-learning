# 09 配套代码 — 使用说明

> **课程总览**（11 篇文章、和 08/Skill 关系）：请先看 [`../README.md`](../README.md)  
> **本目录**：所有命令的 **工作目录**（`pytest`、`playwright install` 均在这里执行）。

---

## 本目录能干什么（一张表）

| 你想做的事 | 要不要 demo_app | 命令 / 文件 |
|------------|-----------------|-------------|
| 跑通环境（定位+自愈） | 否（部分用例） | `pytest tests/test_locator.py tests/test_healer.py -v` |
| 浏览器 API 入门 | **是**（:5000） | 先 `cd demo_app && python app.py`，再 `pytest tests/test_browser_api.py -v` |
| 视觉语义定位 | 视用例 | `pytest tests/test_visual.py -v` |
| 像素截图回归 | **是** | `pytest tests/test_snapshot_demo.py --update-snapshots -v` 首次 |
| 自然语言 → 步骤 → 执行 | **是** | `python tests/test_e2e_natural_language.py --demo login` |
| 看声明式 UI spec 结构 | 否 | `cat examples/ui_login_spec_example.md` |
| 看元素 JSON 契约 | 否 | `cat examples/locator_tiers_example.json` |
| MCP / asyncio | 可选 mcp 包 | `pytest tests/test_mcp_and_async.py -v` |
| 真实秒杀项目联调 | 你的后端 :5000 | 改 `tests/test_seckill_playwright.py` 后 pytest |

---

## 和 08、Skill 怎么分（必读）

| 能力 | 09 本目录（引擎课） | — | — |
|------|---------------------|--------------|--------------|
| `ui_worker` / JSON 步骤 | **源码 `worker/`** | — | 编排提示词 |
| L1/L2/L3 定位 | **`locator/resolver.py`** | — | `locator_tiers` 规范 + Agent |
| 运行时自愈（换 selector） | **`healer/`** | API 侧 `api_self_healing` | 弱 |
| 改 pytest 脚本（LLM 纪律） | 概念（第 4 篇附） | — | **UI-skills/自我修复** |
| 自然语言 UI | **`step_parser` 已实现** | — | `nl_ui_client`、何时调 |
| 声明式 `ui_pytest` + generate.sh | **仅 examples 示例** | API spec 示例 | **全套模板** |
| 像素截图回归 | `test_snapshot_demo.py` | — | `visual_regression.md` |
| MCP / SSE / asyncio | **第 6～10 篇 + 代码** | — | 不教 |

**一句话**：09 教你 **引擎怎么写**；Skill 教你 **在 AI 编辑器里怎么用**。

全文对照：[../附录-进阶路线与三件套分工.md](../附录-进阶路线与三件套分工.md)

---

## 快速开始（3 步）

### 1. 安装

```bash
cd 配套代码
pip install -r requirements.txt
playwright install chromium
```

镜像慢时：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/ playwright install chromium
```

验证：

```bash
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

### 2. 启动演示站（需要浏览器用例时）

```bash
cd demo_app
python app.py
# 保持运行：http://127.0.0.1:5000  账号 admin / admin123（或 testuser / test123）
```

### 3. 跑测试（新开终端，回到 配套代码 根目录）

```bash
cd 配套代码

pytest tests/test_locator.py -v
pytest tests/test_healer.py -v
pytest tests/test_browser_api.py -v
```

---

## 两条 UI 路径

| | 路径一（本课主路径） | 路径二（Skill 包） |
|---|---------------------|-------------------|
| 输入 | JSON：`action` / `target` / `value` | Markdown：`kind: ui_pytest_playwright` |
| 执行 | `worker/ui_worker.py` | `./generate.sh` → pytest |
| 本仓库 | **完整代码** | **仅示例** |

```bash
# 路径二：只看结构，不生成
cat examples/ui_login_spec_example.md
cat examples/page_intent_example.md
cat examples/locator_tiers_example.json
```

详见 **第 2 篇**「附一、两条 UI 自动化路径」。

---

## 自然语言 UI（本课已实现）

```bash
# 需 demo_app 已启动
python tests/test_e2e_natural_language.py --demo login
python tests/test_e2e_natural_language.py --demo add_product
python tests/test_e2e_natural_language.py --custom "用户名：admin，密码：admin123，点击登录"
```

| | 本课 | — |
|---|------|--------------|
| 实现 | `step_parser_service.py` → `ui_worker` | `nl_ui_client.py`、`nl_api_server` |
| 适合 | 学解析器、改规则 | AI 编辑器「一句话操作页面」 |

**NL 不是 Skill 独有**；Skill 卖的是 Agent 入口与环境约定。

---

## 像素截图回归 vs 视觉语义（第 5 篇）

| 类型 | 测什么 | 本课 |
|------|--------|------|
| **语义定位** | 文案、role、OpenCV 红字 | `tests/test_visual.py` |
| **像素回归** | 整页 PNG 与基线 diff | `tests/test_snapshot_demo.py` |

```bash
# 需 demo_app；首次写基线
pytest tests/test_snapshot_demo.py --update-snapshots -v
pytest tests/test_snapshot_demo.py -v
```

声明式 `visual_regression.md` + `generate.sh` 在 **Skill 包**。

---

## 文章 ↔ 测试对照

| 文章 | 建议运行 |
|------|----------|
| 第 0、9 篇 | `tests/test_browser_api.py` |
| 第 3 篇 | `tests/test_locator.py` |
| 第 4 篇 | `test_healer.py`、`test_healing_tools.py`（扩展工具层）、`test_heal_login_btn_article.py`、`test_self_heal_e2e.py` |
| 第 5 篇 | `test_visual.py`、`test_snapshot_demo.py` |
| 第 6、10 篇 | `tests/test_mcp_and_async.py`（`pip install mcp`） |
| 第 7、8 篇 | 架构阅读，可不跑代码 |
| 附录 | `../附录-进阶路线与三件套分工.md` |

---

## 目录结构

```
配套代码/
├── README.md                 ← 本文件
├── demo_app/                 ← Flask 演示站（:5000）
├── examples/                 ← 教学示例（非 generate.sh 产出）
├── locator/                  ← 三层定位
├── healer/                   ← 运行时自愈（diagnostic / strategies / healing_graph / healing_tools）
├── test_data/healing_stub/   ← 扩展工具层 stub 落盘（datasets、logs、snapshots）
├── worker/                   ← 步骤执行引擎
├── mcp/                      ← MCP Server（可选）
├── tests/
├── step_parser_service.py    ← 自然语言解析
├── conftest.py / pytest.ini / requirements.txt
└── 生产版参考/               ← 与真实项目对比阅读
```

---

## 真实业务系统联调

编辑 `tests/test_seckill_playwright.py`：

```python
BASE_URL = "http://你的系统:端口"
```

```bash
pytest tests/test_seckill_playwright.py -v
```

**注意**：默认 `5000` 与 `demo_app` 相同，不要两个服务抢同一端口。

---

## 常见问题

**Q：`ModuleNotFoundError: No module named 'locator'`**  
在 `配套代码` 根目录执行 pytest，或：`export PYTHONPATH=$PWD:$PWD`

**Q：MCP 测不了**  
`pip install mcp`；不装不影响第 0～5 篇。

**Q：没学过 pytest**  
建议先掌握 pytest 的 Fixture、断言等基础概念。

**Q：演示账号是什么？**  
`admin` / `admin123`，或 `testuser` / `test123`（见 `demo_app/app.py`）。

---

## 对外打包说明（勿随课包外发）

与上一级 [`../README.md`](../README.md#对外打包说明勿随课包外发) 相同。本目录额外注意：**不要**打包 `.venv/`、`.pytest_cache/`、`.env`、含真实 Key 的本地配置。

---

**作者**：测试员周周 · 公众号：测试员周周
