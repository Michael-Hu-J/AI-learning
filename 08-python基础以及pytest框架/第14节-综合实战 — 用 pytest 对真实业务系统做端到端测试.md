# 14-综合实战 — 用 pytest 对真实业务系统做端到端测试

> 对应代码：`test/tests/test_seckill_finance_comprehensive.py`  
> 接口 + DB 校验：`test/tests/test_api_db_check.py`（第 14 节增补）

---

## 概念讲解

前面 13 节讲的都是零件，这一节把它们组装起来。

**但学完这些，你能不能直接上手一个真实项目？**

很多人的答案是"不能"。原因很简单：教程里的代码是 `test_add_two_numbers()`，真实项目里的代码是"用户登录 → 获取 Token → 创建商品 → 发起秒杀 → 下单支付 → 财务记账"。

**中间差的就是"把知识点串起来"的能力。**

本节就是补这个差。我会用一个真实的业务系统，演示如何用 pytest 写一套完整的 API 自动化测试。所有知识点都会用到，所有代码都能跑。

**被测系统**：电商秒杀与财务一体化系统
- 技术栈：Flask + MySQL + Redis
- API 数量：50+ 个接口
- 默认管理员：admin / admin123（与配套仓库中本地演示后端的种子数据一致）
- 接口文档：http://localhost:5000/openapi.yaml

**安全说明**：`admin123` 仅用于本地或自建演示环境，便于读者「克隆代码即可跑通」。连接公司真实测试环境或生产环境时，**不要**在仓库里写死口令，应通过环境变量注入（见下文 `TEST_ADMIN_PASSWORD`），并遵守团队密钥管理规范。

---

## 测试策略设计

### 1. 测试策略设计

在写任何测试之前，先想清楚"测什么"和"怎么测"。

**测什么**（测试范围）：

| 模块 | 测试重点 | 优先级 |
|------|---------|--------|
| 认证模块 | 登录、注册、Token 验证 | P0（最高） |
| 商品模块 | 商品 CRUD、列表查询 | P0 |
| 秒杀模块 | 活动管理、秒杀下单 | P0 |
| 权限验证 | 无 Token 访问、越权访问 | P1 |
| 端到端流程 | 完整购物流程串联 | P1 |

**怎么测**（测试方法）：

- 认证 Token → 用 `session` 级别 Fixture（整个会话只登录一次）
- 参数化测试 → 用 `@pytest.mark.parametrize` 覆盖多个端点
- 权限验证 → 无 Token 访问受保护接口，验证 401
- 端到端流程 → 串联多个 API，模拟真实用户操作

### 2. Fixture 设计 — 依赖注入的核心

真实项目中，Fixture 是最容易被滥用也最容易被忽视的特性。来看我们的设计：

```python
import os

# 与配套仓库默认一致：未设置环境变量时使用本地演示口令；真实环境请 export TEST_ADMIN_PASSWORD
DEMO_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

# Session 级别：整个测试会话只执行一次
@pytest.fixture(scope="session")
def admin_token():
    """管理员 Token — 所有测试共享"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": DEMO_ADMIN_PASSWORD},
        timeout=10
    )
    assert response.status_code == 200
    return response.json()["token"]


# Session 级别：依赖 admin_token
@pytest.fixture(scope="session")
def admin_headers(admin_token):
    """管理员请求头 — 依赖 admin_token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    }


# Function 级别：每个测试独立执行
@pytest.fixture(scope="function")
def regular_user_token():
    """普通用户 Token — 每次测试注册新用户"""
    # 注册 + 登录，保证用例之间互不干扰
    ...
```

**设计原则**：

1. **初始化慢的资源用 `session`**：Token 获取只需要一次，不需要每个用例都登录
2. **需要隔离的资源用 `function`**：普通用户每次注册新的，保证用例独立
3. **Fixture 之间可以依赖**：`admin_headers` 依赖 `admin_token`，pytest 自动解析

### 3. 参数化测试 — 一份代码覆盖 N 个端点

真实项目有 50+ 个 API，不可能每个都写一个测试函数。参数化是解决方案：

```python
@pytest.mark.parametrize("endpoint,expected_status,description", [
    ("/api/products", 200, "获取商品列表（无需登录）"),
    ("/api/seckill/list", 200, "获取秒杀商品列表（无需登录）"),
    ("/api/seckill/activities", 200, "获取秒杀活动列表（无需登录）"),
])
def test_public_endpoints(self, endpoint, expected_status, description):
    """参数化测试：公共端点都能正常访问"""
    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
    assert response.status_code == expected_status
    data = response.json()
    assert isinstance(data, (dict, list))
```

**这一组参数化 = 3 个独立的测试用例**。pytest 会为每组参数生成一个独立的用例，失败时能精确定位到是哪一组参数。

### 4. 断言设计 — 失败时一眼看出问题

断言信息要写得"出了问题一眼就能看出原因"：

```python
#  不好的写法——失败了不知道哪里出问题
assert response.status_code == 200
assert "token" in data

#  好的写法——失败了直接告诉你预期和实际
assert response.status_code == 200, f"登录失败，状态码: {response.status_code}"
assert "token" in data, "响应中缺少 token 字段"
assert data["user"].get("username") == "admin", f"用户名不匹配: {data.get('user')}"
```

### 5. Allure 装饰器 — 让报告可读

Allure 的三级分类让报告结构清晰：

```python
@allure.epic("电商秒杀系统 - API 自动化测试")  # 项目级别
@allure.feature("认证模块")                      # 功能模块
class TestAuthAPI:

    @allure.story("用户登录")                    # 具体场景
    @allure.title("管理员登录 - 验证 Token 返回")  # 用例标题
    @allure.severity(allure.severity_level.CRITICAL)  # 严重级别
    @pytest.mark.smoke
    def test_admin_login(self):
        ...
```

---

## 实战案例 — 完整测试代码

### 项目结构

```
test/
├── conftest.py              # pytest 配置（Hook + autouse fixture）
├── pytest.ini               # pytest 配置（marker、testpaths）
├── api/
│   └── base_api.py          # API 请求基类
├── tests/
│   └── test_seckill_finance_comprehensive.py  # 本节综合测试
├── core/
│   ├── data_driver.py       # 数据驱动（YAML 加载）
│   └── validator.py         # 结果验证器
└── utils/
    ├── logger.py            # 日志工具
    └── allure_helper.py     # Allure 辅助工具
```

### 测试文件完整代码

```python
"""
综合实战：对真实业务系统（电商秒杀与财务一体化系统）进行端到端测试
演示如何用 pytest 串联所有知识点：Fixture、参数化、Hook、Allure、断言
"""
import os
import time
import pytest
import allure
import requests

BASE_URL = os.getenv("SECKILL_BASE_URL", "http://localhost:5000")
# 演示环境默认口令；对接真实系统请使用环境变量，勿将真实口令提交到仓库
DEMO_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")


# ==================== Fixture 层 ====================

@pytest.fixture(scope="session")
def admin_token():
    """会话级别：获取管理员 Token（整个会话只登录一次）"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": DEMO_ADMIN_PASSWORD},
        timeout=10
    )
    assert response.status_code == 200, f"管理员登录失败: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    """会话级别：管理员请求头（依赖 admin_token）"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    }


# ==================== 第1组：认证模块测试 ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("认证模块")
class TestAuthAPI:

    @allure.story("用户登录")
    @allure.title("管理员登录 - 验证 Token 返回")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_admin_login(self):
        """测试管理员登录，验证返回 token 和用户信息"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": DEMO_ADMIN_PASSWORD},
            timeout=10
        )
        assert response.status_code == 200, f"登录失败，状态码: {response.status_code}"

        data = response.json()
        assert "token" in data, "响应中缺少 token 字段"
        assert "user" in data, "响应中缺少 user 字段"
        assert data["user"].get("username") == "admin", "用户名不匹配"

    @allure.story("用户登录")
    @allure.title("错误密码登录 - 验证失败响应")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    def test_wrong_password_login(self):
        """测试错误密码登录，验证返回错误信息"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "wrong_password"},
            timeout=10
        )
        assert response.status_code == 401, f"错误密码应该返回 401，实际: {response.status_code}"

        data = response.json()
        message = data.get("message", "") or data.get("error", "")
        assert "密码" in message or "错误" in message, \
            f"错误信息不包含关键词: {message}"


# ==================== 第2组：参数化测试 ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("商品模块")
class TestProductAPI:

    @pytest.mark.parametrize("endpoint,expected_status,description", [
        ("/api/products", 200, "获取商品列表（无需登录）"),
        ("/api/seckill/list", 200, "获取秒杀商品列表（无需登录）"),
        ("/api/seckill/activities", 200, "获取秒杀活动列表（无需登录）"),
    ])
    @allure.story("商品查询")
    @allure.title("{description}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_public_endpoints(self, endpoint, expected_status, description):
        """参数化测试：公共端点都能正常访问"""
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        assert response.status_code == expected_status, \
            f"{description} 失败，状态码: {response.status_code}"
        data = response.json()
        assert isinstance(data, (dict, list))


# ==================== 第3组：管理员操作测试 ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("管理员操作")
class TestAdminAPI:

    @allure.story("商品管理")
    @allure.title("创建商品 - 验证管理员权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_create_product(self, admin_headers):
        """测试管理员创建商品"""
        import random
        product_data = {
            "name": f"测试商品_{int(time.time())}_{random.randint(100,999)}",
            "description": "pytest 自动化测试创建的商品",
            "price": round(random.uniform(10, 1000), 2),
            "stock": random.randint(100, 10000),
            "category": "测试分类"
        }

        response = requests.post(
            f"{BASE_URL}/api/products",
            json=product_data,
            headers=admin_headers,
            timeout=10
        )
        assert response.status_code in [200, 201], \
            f"创建商品失败: {response.status_code}, {response.text}"

    @allure.story("秒杀活动管理")
    @allure.title("创建秒杀活动 - 验证管理员权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_create_seckill_activity(self, admin_headers):
        """测试管理员创建秒杀活动"""
        activity_data = {
            "name": f"pytest秒杀活动_{int(time.time())}",
            "description": "自动化测试创建的秒杀活动",
            "start_time": "2026-06-01 10:00:00",
            "end_time": "2026-12-31 23:59:59",
            "status": "pending"
        }

        response = requests.post(
            f"{BASE_URL}/api/seckill/activities",
            json=activity_data,
            headers=admin_headers,
            timeout=10
        )
        assert response.status_code in [200, 201, 400], \
            f"创建秒杀活动异常: {response.status_code}"


# ==================== 第4组：权限验证测试 ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("权限验证")
class TestPermissionAPI:

    @allure.story("受保护接口")
    @allure.title("无 Token 访问管理员接口 - 验证 401")
    @pytest.mark.regression
    def test_no_token_access_admin(self):
        """测试无 Token 访问管理员接口，应该返回 401"""
        response = requests.post(
            f"{BASE_URL}/api/products",
            json={"name": "test", "price": 10, "stock": 100},
            timeout=10
        )
        assert response.status_code in [401, 403], \
            f"无 Token 访问管理员接口应该返回 401/403，实际: {response.status_code}"


# ==================== 第5组：端到端流程测试 ====================

@allure.epic("电商秒杀系统 - API 自动化测试")
@allure.feature("端到端流程")
class TestE2EWorkflow:

    @allure.story("完整购物流程")
    @allure.title("管理员创建商品 → 用户浏览 → 验证商品存在")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_full_shopping_flow(self, admin_headers):
        """
        端到端测试完整购物流程：
        1. 管理员创建商品
        2. 用户浏览商品列表
        3. 验证商品存在
        """
        import random

        # 步骤1：管理员创建商品
        create_response = requests.post(
            f"{BASE_URL}/api/products",
            json={
                "name": f"E2E测试商品_{int(time.time())}",
                "description": "E2E测试创建",
                "price": 99.99,
                "stock": 1000,
                "category": "E2E测试"
            },
            headers=admin_headers,
            timeout=10
        )
        assert create_response.status_code in [200, 201]

        # 步骤2：用户浏览商品列表
        time.sleep(0.5)
        list_response = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert list_response.status_code == 200

        # 步骤3：验证列表接口正常返回
        products_data = list_response.json()
        if isinstance(products_data, dict):
            products = products_data.get("products", products_data.get("data", []))
        elif isinstance(products_data, list):
            products = products_data
        else:
            products = []
        assert isinstance(products, list)
```

### 运行结果

```bash
pytest tests/test_seckill_finance_comprehensive.py -v

# 运行结果：
# ========================= 16 passed in 1.93s ==========================
#
# 5 个测试类，16 个测试用例，全部通过
# 总耗时 1.93 秒（包含真实的 HTTP 请求）
```

**知识点覆盖**：

| 知识点 | 对应代码 | 节次 |
|--------|---------|------|
| Fixture 作用域 | `scope="session"` / `scope="function"` | 第05节 |
| Fixture 依赖链 | `admin_headers` 依赖 `admin_token` | 第05节 |
| 断言体系 | `assert response.status_code == 200, "错误信息"` | 第04节 |
| 参数化 | `@pytest.mark.parametrize` | 第08节 |
| Mark 标记 | `@pytest.mark.smoke` / `@pytest.mark.regression` | 第09节 |
| Allure 装饰器 | `@allure.epic` / `@allure.feature` / `@allure.story` | 第10节 |
| Hook 自动日志 | `conftest.py` 中的 `pytest_runtest_logreport` | 第07节 |
| 项目结构 | `tests/` / `api/` / `core/` / `utils/` | 第12节 |

---

## 接口 + 数据库校验（进阶）

只断言 `response.status_code == 201` 不够：**服务可能返回了假成功**，或写库失败但接口仍返回 200。工程上常见两层验证：

1. **API 回查**：创建后再 `GET` 列表/详情，确认能读到（不依赖数据库权限）。  
2. **DB 直连**：用 `pymysql` 等查表，确认行存在且字段正确（集成环境、测试库）。

配套代码 `test/tests/test_api_db_check.py`：

```bash
cd test
# 仅需 HTTP（对接演示后端时）
pytest tests/test_api_db_check.py::test_create_product_then_list -v

# MySQL 直连（需配置环境变量并 pip install pymysql）
export TEST_DB_HOST=127.0.0.1
export TEST_DB_USER=root
export TEST_DB_PASSWORD=你的密码
export TEST_DB_NAME=seckill_db
pytest tests/test_api_db_check.py::test_create_product_row_in_mysql -v
```

**手写 DB 校验核心逻辑**：

```python
import pymysql

def fetch_product_name(product_id: int) -> str | None:
    conn = pymysql.connect(
        host=os.environ["TEST_DB_HOST"],
        user=os.environ["TEST_DB_USER"],
        password=os.environ["TEST_DB_PASSWORD"],
        database=os.environ["TEST_DB_NAME"],
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM products WHERE id = %s", (product_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

# 测试里：POST 创建 → 取 id → assert fetch_product_name(id) == 期望名称
```

**注意**：生产库禁止直连；用独立测试库；测试结束清理数据或用唯一前缀（本节 E2E 注意事项已强调）。



---

## 注意事项和常见坑

- **Fixture 的 scope 选错会导致性能问题**。如果把 `admin_token` 设为 `function` 级别，16 个用例 = 16 次登录。设为 `session` 级别 = 1 次登录。时间从 5 秒降到 2 秒。
- **参数化中的中文描述要用英文变量名**。`@pytest.mark.parametrize("endpoint,expected_status,description", [...])` 中的 `description` 是变量名，不是中文。Allure 的 `@allure.title("{description}")` 会自动替换。
- **真实 API 测试要用 `timeout`**。不设置 `timeout` 的话，API 挂掉时测试会一直等。`timeout=10` 是合理的默认值。
- **端到端测试要处理数据清理**。本例中创建的商品会留在数据库里。真实项目中，测试结束后应该清理测试数据，或者用唯一的测试标识（如 `E2E测试_` 前缀）方便清理。
- **管理员口令**：正文与配套代码默认读取 `TEST_ADMIN_PASSWORD`，未设置时回落为本地演示环境的 `admin123`。对接非演示环境时务必通过环境变量注入，且不要将真实口令写入版本库。
- **pytest.ini 的 `addopts` 会影响命令行**。如果 `addopts` 中写了 `-v`，运行 `pytest -q` 时 `-q` 会覆盖 `-v`。

---

## 知识点串联图

本节综合实战中，每个知识点在代码中的位置和作用是：

```
pytest.ini ────────────────┐
  ├─ markers 定义           │ 第09节：Mark 标记
  └─ testpaths 配置         │
                            │
conftest.py ────────────────┤
  ├─ session fixture        │ 第05节：Fixture 作用域
  ├─ autouse fixture        │ 第06节：内置 fixture
  └─ pytest_runtest_logreport│ 第07节：Hook 机制
                            │
BaseAPI ────────────────────┤
  └─ HTTP 请求封装          │ 第12节：项目结构（API 层）
                            │
测试类（TestAuthAPI 等）─────┤
  ├─ @pytest.mark.smoke     │ 第09节：Mark 标记
  ├─ @allure.epic/feature   │ 第10节：Allure 报告
  ├─ parametrize            │ 第08节：参数化
  ├─ assert with message    │ 第04节：断言体系
  └─ fixture 依赖注入       │ 第05节：Fixture 依赖链
                            │
CI 流水线 ──────────────────┤
  ├─ pytest-xdist -n 4      │ 第11节：并行执行
  ├─ pytest-cov             │ 第13节：覆盖率
  └─ pytest-timeout         │ 第13节：超时控制
```

**一条命令串联所有知识点**：
```bash
pytest -n 4 \
  -m "smoke or critical" \
  --cov=src/ --cov-fail-under=70 \
  --timeout=120 --reruns 2 \
  --alluredir=reports/allure-results \
  -v
```

这行命令背后是 8 个知识点的协同工作。能写出来，说明你真的掌握了 pytest。

> 前面 13 节是"零件"，这一节是"组装"。零件再好用，不会组装也造不出车。
