# 10 — Appium 移动端自动化测试（20 篇 + 配套代码）

> 从 Appium 入门到工程化的系列文章 + **可直接运行** 的 pytest + Appium 混合测试框架。  
> **配套代码目录**：[`配套代码/test/`](配套代码/test/README.md)（依赖安装、Demo 启动、pytest 均在该目录执行）。

---

## 一分钟看懂

| 你能立刻跑什么 | 需要什么 |
|----------------|----------|
| **14 个 API 冒烟测试**（登录 / 商品 / 注册购物流程） | Python 3.8+，Flask Demo |
| **Appium UI 测试**（手势、Toast、WebView 等） | Appium 2.x + 真机/模拟器 + 自行替换 `pages/` 定位符 |
| **真机 Chrome 打开 Mock 页面**（`test_appium_demo.py`） | 额外设置 `ANDROID_BROWSER=chrome` 与 `MOCK_SERVER_URL` 局域网 IP |

**不需要手机也能学主线**：先跑通 API 测试，再按需配置 Appium 环境。

---

## 怎么开始（3 步）

```bash
cd 配套代码/test
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 终端 1：启动 Demo（Mock 电商后端）
cd demo_app && python app.py

# 终端 2：API 冒烟（推荐首次验证）
cd ..
pytest tests/test_login_api.py tests/test_products_api.py tests/test_user_flow_api.py -v
```

**预期结果**：`14 passed`。

更完整的目录说明、文章↔代码对照、UI 环境配置见 **[配套代码/test/README.md](配套代码/test/README.md)**。

---

## 文章列表（建议阅读顺序）

| 顺序 | 文件 | 讲什么 |
|------|------|--------|
| 01 | 第01节-Appium 是什么 — 移动端自动化的行业标准.md | 架构、工具选型、Appium 2.0 |
| 02 | 第02节-环境搭建 — Android + iOS 双平台环境配置.md | JDK / SDK / Node / Appium |
| 03 | 第03节-驱动初始化 — BaseDriver 的设计与实现.md | Capabilities、双平台驱动 |
| 04 | 第04节-Page Object 模式 — BasePage 基类设计.md | POM 基类、三级定位降级 |
| 05 | 第05节-元素定位策略全解.md | 定位方式与实战 |
| 06 | 第06节-页面对象实现 — LoginPage 实战.md | LoginPage 实战 |
| 07 | 第07节-API测试封装 — BaseAPI 的设计与实现.md | HTTP 封装 |
| 08 | 第08节-pytest 集成 — conftest.py 中的 fixture 与 hook.md | fixture / hook |
| 09 | 第09节-数据驱动测试 — YAML 数据 + parametrize.md | YAML 数据驱动 |
| 10 | 第10节-手势操作实战.md | 滑动、轻拂、捏合 |
| 11 | 第11节-Toast+弹窗处理.md | Toast / 系统弹窗 |
| 12 | 第12节-智能路由 — API测试 vs UI 测试的自动选择.md | 智能路由 |
| 13 | 第13节-混合测试执行器 — API + UI 的协同执行.md | 混合执行器 |
| 14 | 第14节-断言与验证 — Validator 的设计.md | 断言验证器 |
| 15 | 第15节-视觉测试 — 截图、对比、视觉回归.md | 视觉回归 |
| 16 | 第16节-WebView-H5上下文切换.md | WebView 切换 |
| 17 | 第17节-XMind用例转换 — 从思维导图到 YAML.md | XMind → YAML |
| 18 | 第18节-重试与容错 — 移动端测试的稳定性保障.md | 重试机制 |
| 19 | 第19节-Allure 报告与 Bug 管理 — 测试结果的可视化.md | Allure / Bug 上报 |
| 20 | 第20节-测试项目结构设计 — 从脚本到工程.md | 工程化结构 |

---

## 文件夹结构（顶层）

```
10-Appium/
├── README.md                         ← 你正在看的总说明
├── 第01节-....md ～ 第20节-....md    ← 课程正文（Markdown）
└── 配套代码/
    └── test/                         ← 可运行工程（必读 test/README.md）
        ├── demo_app/                 ← Flask Mock 电商（默认端口 5001）
        ├── base/ core/ api/ pages/ utils/
        ├── tests/                    ← pytest 用例
        ├── conftest.py
        └── requirements.txt
```

---

## 演示账号（与 `demo_app/app.py` 一致）

| 用户名 | 密码 | 说明 |
|--------|------|------|
| `admin` | `admin123` | 管理员，API 测试默认账号 |
| `testuser` | `test123` | 普通用户 |

---

## 常见问题

**Q：pytest 报连接失败 / 商品名是「测试商品A」而不是「iPhone 15」？**  
说明 **5001 端口被其他程序占用**（例如本系列 Skill 包的秒杀 Demo）。请先确认端口：

```bash
curl -s http://127.0.0.1:5001/api/products | head -c 120
# 正确应看到 "iPhone 15"
```

改端口启动 Demo，并同步测试环境变量：

```bash
# 终端 1
MOCK_SERVER_PORT=5011 python app.py

# 终端 2
MOCK_SERVER_URL=http://127.0.0.1:5011 pytest tests/test_login_api.py tests/test_products_api.py tests/test_user_flow_api.py -v
```

**Q：跑 `pytest tests/` 很多 skipped？**  
正常。未启动 Appium / 未配置 `APP_PACKAGE` 时，UI 相关用例会自动 **skip**，不会报错。API 冒烟见上表命令。

**Q：`pages/shell_*.py` 能直接跑吗？**  
不能。其中 `demo_` 前缀的定位符是 **POM 教学骨架**，接入真实 App 前须整段替换为你们应用的 `resource-id` / accessibility id。

**Q：环境自检脚本？**  
`python scripts/check_android_env.py`（Android 环境）  
`python scripts/check_test_ready.py`（Appium + 设备 + Demo 综合检查）

---

## 对外打包说明（勿随课包外发）

打 zip / 上传网盘前请**不要**收录：

| 类型 | 路径 / 说明 |
|------|-------------|
| 虚拟环境与缓存 | `.venv/`、`.pytest_cache/`、`__pycache__/` |
| 运行产物 | `logs/`、`reports/`、`screenshots/` |
| 本地密钥 | `.env`、真实 API Token |

---

**作者**：测试员周周 · 公众号：测试员周周
