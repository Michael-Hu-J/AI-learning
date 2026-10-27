# Appium 混合测试框架 — 配套代码

> 基于 **pytest + Appium + Page Object 模式** 的移动端自动化测试框架  
> 配套 16 节课程，覆盖 Android/iOS 双平台、API + UI 混合执行  
> 附带 **Flask Demo 应用**，无需手机即可运行 14 个 API 测试

---

##  这套代码能做什么

你拿到的是一个**完整的 Appium 测试框架**，包含：

| 模块 | 作用 |
|------|------|
| **混合测试执行器** | API 准备数据 + UI 验证效果，一套代码两种测试方式 |
| **智能路由** | 自动判断该用 API 测试还是 UI 测试 |
| **断言验证器** | 支持嵌套字段、正则匹配、大小比较 |
| **Page Object 基类** | 封装了移动端所有基础操作（点击、输入、滑动、截图） |
| **工具集** | 日志、重试、Bug 上报、Allure 报告、截图 |

**配套一个 Flask Demo 应用**（模拟电商系统），包含登录、注册、商品、购物车、订单 5 个功能模块。

---

##  3 分钟跑起来

### 第 1 步：安装依赖

在 **`配套代码/test`** 目录（不是 `demo_app` 子目录）执行：

```bash
cd 配套代码/test
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 第 2 步：启动 Demo 应用

```bash
cd demo_app
python app.py
```

看到类似输出说明启动成功：
```
 Mock Server 启动: http://127.0.0.1:5001
 测试账号: testuser/test123, admin/admin123
```

浏览器访问 http://127.0.0.1:5001 可以看到 Demo 应用。

> **端口冲突**：若 5001 已被占用（例如本系列其他 Demo），用 `MOCK_SERVER_PORT=5011 python app.py` 启动，测试时加 `MOCK_SERVER_URL=http://127.0.0.1:5011`。

### 第 3 步：运行测试

回到 `配套代码/test` 目录：

```bash
pytest tests/test_login_api.py tests/test_products_api.py tests/test_user_flow_api.py -v
```

**预期输出：**
```
tests/test_login_api.py::TestLoginAPI::test_login_success                
tests/test_login_api.py::TestLoginAPI::test_login_wrong_password         
tests/test_login_api.py::TestLoginAPI::test_login_empty_username         
tests/test_login_api.py::TestLoginAPI::test_login_nonexistent_user       
tests/test_login_api.py::TestLoginAPI::test_login_session_persist        
tests/test_login_api.py::TestLoginAPI::test_login_required_for_user_info 
tests/test_products_api.py::TestProductsAPI::test_product_list_returns_data      
tests/test_products_api.py::TestProductsAPI::test_product_detail                 
tests/test_products_api.py::TestProductsAPI::test_product_detail_not_found       
tests/test_products_api.py::TestProductsAPI::test_all_products_have_required_fields 
tests/test_products_api.py::TestProductsAPI::test_highest_price_product          
tests/test_user_flow_api.py::TestUserFlowAPI::test_full_user_flow        
tests/test_user_flow_api.py::TestRegisterAPI::test_register_duplicate_username 
tests/test_user_flow_api.py::TestRegisterAPI::test_register_empty_fields 
======================== 14 passed in 1.3s ========================
```

**更多 skipped 是正常的** — 未启动 Appium / 未配置 `APP_PACKAGE` 时，UI 用例会自动 skip。跑全部用例：`pytest tests/ -v`。

---

##  目录结构

```
配套代码/
├── demo_app/                     #  被测系统（Flask 电商 Demo）
│   ├── app.py                    # 主应用（端口 5001）
│   └── templates/                # 6 个页面模板
│       ├── index.html            # 首页
│       ├── login.html            # 登录页
│       ├── register.html         # 注册页
│       ├── products.html         # 商品页
│       ├── cart.html             # 购物车页
│       └── orders.html           # 订单页
├── base/                         #  基础层
│   ├── base_driver.py            # 推动管理（Android + iOS）
│   └── base_page.py              # Page Object 基类
├── api/                          #  API 封装
│   └── base_api.py               # HTTP 请求封装
├── core/                         #  核心引擎（差异化功能）
│   ├── hybrid_test_executor.py   # 混合测试执行器（API + UI）
│   ├── test_router.py            # 智能路由
│   ├── validator.py              # 断言验证器
│   ├── data_driver.py            # 数据推动引擎
│   ├── test_case_executor.py     # 用例执行器
│   ├── test_case_preparer.py     # 用例准备器
│   └── test_recorder.py          # 测试录制工具
├── utils/                        #  工具模块
│   ├── logger.py                 # 日志
│   ├── retry.py                  # 重试机制
│   ├── screenshot.py             # 截图
│   ├── bug_reporter.py           # Bug 自动上报
│   ├── allure_helper.py          # Allure 报告辅助
│   └── ...                       # 其他工具
├── tests/                        #  测试用例（14 个真实测试）
│   ├── test_login_api.py         # 登录测试（6 个场景）
│   ├── test_products_api.py      # 商品测试（5 个场景）
│   ├── test_user_flow_api.py     # 完整流程（注册→购物→下单）
│   └── test_appium_demo.py       # Appium UI 测试（需真机）
├── scripts/                      #  辅助脚本
├── testcases/yaml/               #  YAML 用例数据
├── conftest.py                   # pytest 全局配置
├── config.py                     # 系统地址配置
├── pytest.ini                    # pytest 配置
└── requirements.txt              # 依赖清单
```

---

## 真实设备上跑 UI：替换占位定位符

`pages/` 里部分页面对象（例如 `shell_home_page.py`）使用了以 **`demo_` 开头的 `resource-id`** 以及教学用的 **XPath**，只是课程里的 **POM 骨架**，与任何真实安装包里的控件都不对应。

在 **真机 / 模拟器** 上跑你们公司 App 的自动化时，请务必：

1. 用你们应用的 **`applicationId` + `resource-id`**（Android 常见形如 `com.yourcompany.app:id/实际控件id`），或 **iOS 的 accessibility identifier / label**、**Android 的 `content-desc`** 等，**整段替换**文件里所有 `demo_` 相关常量与 XPath。
2. 若仍保留示例 XPath，请按你们 App 的实际层级与文案改写；否则会出现 **找不到元素、定位超时**。

未替换前，这些页面对象只适合对照文章理解结构，**不能直接对真实业务包跑通**。

---

##  文章 ↔ 代码对应表

> 每一篇文章讲的原理，都有对应代码可以对照。拿到代码后，直接按篇号找对应文件即可。

| 篇号 | 文章标题 | 对应的代码文件 | 核心内容 |
|------|---------|---------------|---------|
| 01 | Appium 是什么 — 移动端自动化的行业标准 | — | Appium 架构原理、工具对比、Appium 2.0 插件化 |
| 02 | 环境搭建 — Android + iOS 双平台环境配置 | `scripts/check_android_env.py` | JDK / SDK / Node.js 环境检测脚本 |
| 03 | 推动初始化 — BaseDriver 的设计与实现 | `base/base_driver.py` | Android + iOS 双平台推动管理、Capabilities 配置、单例模式 |
| 04 | Page Object 模式 — BasePage 基类设计 | `base/base_page.py` | 移动端操作封装（点击/输入/滑动/截图）、三级定位降级 |
| 05 | 页面对象实现 — LoginPage 实战 | `tests/test_login_api.py` | 登录测试实战（6 个场景：成功/错误密码/空密码/不存在用户/ Session/鉴权） |
| 06 | API 测试封装 — BaseAPI 的设计与实现 | `api/base_api.py` | HTTP 请求封装（GET/POST/PUT/DELETE）、Token 管理、错误处理 |
| 07 | pytest 集成 — conftest.py 中的 fixture 与 hook | `conftest.py` | fixture 管理 driver/api 生命周期、hook 收集运行结果 |
| 08 | 数据推动测试 — YAML 数据 + parametrize | `testcases/yaml/login_test_cases.yaml` | YAML 用例数据格式、pytest 参数化推动方式 |
| 09 | 智能路由 — API vs UI 自动选择 | `core/test_router.py` | 关键词匹配决策引擎、API/UI/Hybrid 三种路由策略 |
| 10 | 混合测试执行器 — API + UI 协同执行 | `core/hybrid_test_executor.py` | 接口准备数据 → UI 验证效果、流式执行、自定义断言 |
| 11 | 断言与验证 — Validator 的设计 | `core/validator.py` | 嵌套字段验证、正则匹配、大小比较、集合校验 |
| 12 | 视觉测试 — 截图、对比、视觉回归 | `utils/screenshot.py` | OpenCV 截图对比、多设备截图管理、视觉回归流程 |
| 13 | XMind 用例转换 — 从思维导图到 YAML | — | XMind → YAML 转换流程（概念性内容） |
| 14 | 重试与容错 — 移动端测试的稳定性保障 | `utils/retry.py` | 元素查找重试、接口调用重试、指数退避策略 |
| 15 | Allure 报告与 Bug 管理 — 可视化的力量 | `utils/allure_helper.py` | Allure 报告集成、Bug 自动上报、截图关联 |
| 16 | 工程化 — 从脚本到工程 | 整个项目结构 | 分层设计、包管理、CI 集成、团队协作 |

---

##  测试覆盖场景

### 登录测试（6 个场景）
| 场景 | 说明 |
|------|------|
| 正确账号密码登录 | admin/admin123 → 200 |
| 错误密码 | 返回 401 |
| 空密码 | 返回 400 |
| 不存在的用户 | 返回 404 |
| Session 持久化 | Token 格式验证 |
| 未登录访问受保护页面 | 返回 401 |

### 商品测试（5 个场景）
| 场景 | 说明 |
|------|------|
| 商品列表 | 返回商品数组 |
| 商品详情 | 返回单个商品 |
| 不存在的商品 | 返回 404 |
| 所有字段验证 | 检查 price/stock 等字段 |
| 最高价格商品 | 排序验证 |

### 用户流程测试（3 个场景）
| 场景 | 说明 |
|------|------|
| 完整流程 | 注册 → 登录 → 加入购物车 → 下单 |
| 重复用户名 | 返回 409 |
| 空字段 | 返回 400 |

---

##  框架核心功能演示

### 1. 智能定位（对应第4课）

```python
# 三级定位降级：accessibility_id → resource-id → xpath
login_btn = page.find_element_smart([
    ("accessibility_id", "login_button"),
    ("resource-id", "com.app:id/login_btn"),
    ("xpath", "//*[@text='登录']"),
])
```

### 2. 混合测试（对应第10课）

```python
# API 准备数据 → UI 验证效果
executor = HybridTestExecutor()
result = executor.execute({
    "test_type": "hybrid",
    "steps": [
        {"action": "POST", "endpoint": "/api/register", "body": {...}},
        {"action": "点击元素", "target": "#login-btn"},
    ]
})
```

### 3. 断言验证器（对应第11课）

```python
# 嵌套字段验证 + 详细错误定位
from core.validator import Validator

expected = {
    "user.name": "admin",
    "status": "active",
    "token": r"^eyJ"  # 支持正则匹配
}
expected_dict = Validator.parse_expected(expected)
is_valid, error_msg = Validator.validate_api_response(response.json(), expected_dict)

if not is_valid:
    print(f"验证失败: {error_msg}")
    # 输出示例: "字段 user.name 不匹配: 期望 'admin'，实际 'guest'"
```

---

### 4. 重试机制（对应第14课）

```python
# 装饰器用法：给函数加"保护罩"，失败自动重试
from utils.retry import retry_on_failure

@retry_on_failure(max_attempts=3, delay=1.0)
def test_login():
    resp = session.post(f"{BASE_URL}/api/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert resp.status_code == 200

# 原理：第1次失败 → 等1秒 → 第2次 → 等1秒 → 第3次
# 日志输出:
#   [INFO] 执行 test_login - 尝试 1/3
#   [WARNING] test_login 第 1 次尝试失败: Connection timeout
#   [INFO] 执行 test_login - 尝试 2/3
#   [INFO] test_login 在第 2 次尝试时成功  ← 偶发错误不影响结果
```

### 5. YAML 数据推动（对应第8课）

```yaml
# testcases/yaml/login_test_cases.yaml
test_cases:
  - name: 有效用户登录成功
    test_type: api
    steps:
      - action: POST
        endpoint: /api/login
        body:
          username: admin
          password: admin123
    expected:
      status_code: 200
      fields:
        message: "登录成功"
        user.username: "admin"

  - name: 错误密码登录失败
    test_type: api
    steps:
      - action: POST
        endpoint: /api/login
        body:
          username: admin
          password: wrong_password
    expected:
      status_code: 401
```

```python
# 代码里加载 YAML，自动生成测试用例
from core.data_driver import DataDriver

cases = DataDriver.load_data("testcases/yaml/login_test_cases.yaml")
for case in cases:
    # 自动注入变量、执行请求、验证预期
    result = executor.execute(case)
    print(f"{case['name']}: {'' if result['pass'] else ''}")
```

### 6. Bug 自动上报（对应第15课）

```python
# 测试失败时自动记录 Bug，生成报告
from utils.bug_reporter import BugReporter

reporter = BugReporter()

# 测试失败时自动记录
reporter.record_failure(
    test_name="test_login_success",
    error="AssertionError: expected 200, got 500",
    screenshot="screenshots/login_fail.png",
    step="POST /api/login"
)

# 自动生成 Markdown 报告
report = reporter.generate_markdown_report("reports/bug_report.md")
# 输出:
#   | 测试用例 | 错误信息 | 截图 | 步骤 |
#   | test_login_success | AssertionError... | login_fail.png | POST /api/login |
```

---

##  环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 必需 |
| Flask | 自带 | Demo 应用 |
| Appium | 2.x | UI 测试需要 |
| Android SDK | API 30+ | Android UI 测试需要 |

**注意：**
- API 测试只需要 Python + Flask，不需要 Appium
- UI 测试需要 Appium Server + Android 模拟器/真机

---

##  课后练习

1. **添加新测试**：在 `tests/` 中编写购物车结算测试用例
2. **补充 YAML 数据**：在 `testcases/yaml/` 中添加注册功能的 YAML 用例
3. **配置真机环境**：安装 Appium，运行 `test_appium_demo.py`
4. **扩展框架**：在 `core/` 中添加自定义的测试执行策略
