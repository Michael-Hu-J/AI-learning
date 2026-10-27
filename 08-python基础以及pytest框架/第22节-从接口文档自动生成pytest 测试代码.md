# 第22节 — 从接口文档自动生成pytest 测试代码

> 对应代码：`test/scripts/test_generator.py`、`test/core/openapi_parser.py`  
> 本节增补：`test/examples/api_smoke_spec_example.md`、`test/scripts/schema_drift_demo.py`  
> 接口 + DB 校验见：**第 14 节**、`test/tests/test_api_db_check.py`

---

## 概念讲解

前面 21 节讲的都是"人写测试代码"。这一节讲"机器写测试代码"。

**场景**：你接手一个已有系统，50+ 个接口，接口文档是 OpenAPI YAML。你要在一天内写出基础测试覆盖。

**传统做法**：逐条看文档，手动写 `test_xxx.py`。50 个接口，每个 20 行代码，就是 1000 行。一天写不完。

**本节做法**：把 `openapi-example.yaml` 丢给生成器，3 秒出 200+ 条测试函数。每个接口覆盖 5 个维度：正常请求、边界值、异常拒绝、响应时间、安全测试。不是完美测试，但能立刻跑起来，覆盖基本路径。

**生成器不替代你写复杂测试**。它做的是"从 0 到 1"——把接口文档变成可运行的 pytest 文件。你在这个基础上加业务断言、加数据校验、加异常场景。

---

## 覆盖维度

每个接口自动生成 4-8 条测试，覆盖 5 个维度：

| 代号 | 维度 | 内容 | 举例 |
|------|------|------|------|
| **H** | Happy Path | 主路径成功 | 正常创建商品返回 201 |
| **E** | Edge | 契约边界 | 空值、超长字符串、最大/最小值、特殊字符 |
| **X** | Exception | 协议/业务拒绝 | 缺少必填字段、类型错误、无效枚举 |
| **P** | Performance | 响应时间量级 | 单次请求 < 5s |
| **S** | Security | 安全 sanity | 匿名访问、过期Token、无效 Token |

**底线**：对外真正会打的接口，至少 **H + X**；钱相关的多加 **S**。

---

## 22.1 两层用例：功能测试点 vs 接口契约

H/E/X/P/S 解决的是「**一个接口怎么测全**」，没解决「**谁负责写哪类用例**」。

| 类型 | 典型问题 | 谁写 | 本课程路径 |
|------|----------|------|------------|
| **功能测试点** | 页面流程、业务规则、权限故事、异常文案 | 测试设计 / 用例评审 | 第 14 节综合实战、手工用例 |
| **接口契约测试** | 状态码、字段、鉴权、边界、契约是否漂移 | 自动化（生成或 spec） | 本节 `test_generator` / 声明式 spec |

**接口自动化擅长**：`POST /api/products` 返回 201、缺字段返回 422、无 Token 返回 401。  
**不擅长替代**：「秒杀库存为 0 时按钮置灰」「支付失败 3 次锁定账户」——这类应写在功能用例里，必要时用 UI 或复杂场景脚本补。

| 做 | 不做 |
|----|------|
| 从契约生成 H/E/X/P/S、冒烟、安全 sanity | 替代完整 PRD 功能测试点 |
| 多步 API 流程（注册→登录→下单） | 替代页面交互与视觉验收 |
| 契约变更时回归接口层 | 修服务端业务逻辑 bug |


---

## 22.2 两条生成路径怎么选

```
                    OpenAPI / 需求
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
   路径一：test_generator              路径二：声明式 spec
   一次生成 N 个 .py 文件              Markdown/YAML → 少量 pytest
   适合：全量铺底、63 接口              适合：冒烟集、评审后增量、CI 小集
           │                               │
           └───────────────┬───────────────┘
                           ▼
              手动补业务断言 / DB 校验 / 复杂流程
                           ▼
                    pytest + 第 17～21 节工程化
```

| 维度 | 路径一 `test_generator.py` | 路径二 声明式 `api_pytest` spec |
|------|---------------------------|--------------------------------|
| 产出 | 20+ 文件、200+ 条用例 | 通常 1 个 spec → 1 个 pytest 文件 |
| 评审 |  diff 大，适合首次铺底 | diff 小，适合 PR 评审 |
|| 工具 | **本仓库已包含** | 示例见 `test/examples/api_smoke_spec_example.md`；需配套渲染工具生成 pytest 文件 |
| OpenAPI 导入 | 直接解析生成 py | 可先 `openapi → spec.md` 再生成（Skill 提供 `--import-openapi`） |

**本课默认主路径仍是路径一**（学会批量铺底）；路径二用于理解业界「可评审的 spec」工作流，避免和 Skill 包重复交付整套生成器。

---

## 22.3 路径一：批量生成（test_generator）

### 生成所有接口的测试

```bash
cd test
python scripts/test_generator.py ../openapi-example.yaml --output output/
```

**输出**：
```
解析完成: 63 个接口, 31 个 Schema
已生成 22 个测试文件:
   - test_api_认证.py (55KB)
   - test_api_商品管理.py (107KB)
   - test_api_秒杀功能.py (11KB)
   - test_security.py (3.4KB)
   - test_boundary.py (35KB)
   - test_functional_flows.py (2.6KB)
   - test_e2e_seckill_flow.py (2.4KB)
   ...
```

### 只生成指定模块

```bash
python scripts/test_generator.py ../openapi-example.yaml --tag 认证 --output output/
```

### 按维度运行

```bash
cd output
pytest -v              # 全部
pytest -v -m h         # 只跑 Happy Path
pytest -v -m e         # 只跑边界值
pytest -v -m x         # 只跑异常
pytest -v -m p         # 只跑性能
pytest -v -m s         # 只跑安全
```

---

## 22.4 路径二：声明式 spec（概念 + 最小示例）

**声明式**：用 Markdown/YAML 的 frontmatter 描述 `method`、`path`、`expect_status`，由生成器渲染成 pytest，而不是手写 200 行 `requests.post`。

本仓库提供 **结构示例**（不附带 `generate.sh`）：

```bash
cat test/examples/api_smoke_spec_example.md
```

节选结构：

```markdown
---
kind: api_pytest
base_url: http://127.0.0.1:5000
cases:
  - id: API-001
    method: GET
    path: /api/products
    expect_status: 200
  - id: API-002
    method: POST
    path: /api/products
    json_body:
      name: "示例商品"
      price: 9.9
    expect_status: 201
---
```

**自然语言拆 API 用例**（「帮我测登录，错误密码要 401」→ `cases[]`）依赖 LLM 与提示词；本课用 **参数化 + YAML**（第 8 节）覆盖多场景输入即可。

---

## 22.5 OpenAPI → spec → pytest（数据流）

路径二在工程上常多一层 **中间 spec**，便于评审和增量 CI：

```
openapi.json / swagger.yaml
        │
        ├─► 路径一：test_generator.py ──► output/test_api_*.py（本课已学）
        │
        └─► 路径二：import-openapi（Skill: generate.sh）
                    │
                    ▼
              imported_api.md    ← 人可改 cases、删不必测的端点
                    │
                    ▼
              api_smoke.py       ← pytest 可执行文件
```

**为什么不总是路径一「一次 22 个文件」？**

1. **可控**：冒烟只保留 10 条，CI 更快。  
2. **可评审**：改 spec 的 diff 比改 3000 行生成代码清晰。  
3. **与 Agent 协作**：spec 即「用例表」，适合 `@api-skills` 迭代。

完整 `--import-openapi` 与模板库可自行实现；本课掌握数据流即可。

---

## 22.6 多步场景：`cases[]` vs `scenarios[]`

| 结构 | 含义 | 典型场景 |
|------|------|----------|
| `cases[]` | 单步请求，彼此独立 | 冒烟、单接口 H/X |
| `scenarios[]` | 多步 + `capture` 上下文 | 注册→拿 token→创建资源 |

路径一里类似能力见 `test_e2e_seckill_flow.py`（多个 `test_0x_*` 顺序执行）。路径二用 **一张表** 维护流程（Skill 模板 `api_scenario_register.md` 同构，此处简化）：

```yaml
scenarios:
  - name: register_then_profile
    steps:
      - method: POST
        path: /api/auth/register
        no_auth: true
        json_body:
          username: "flow_user"
          password: "Passw0rd!"
          email: "flow@example.com"
        expect_status: 201
        capture:
          token: data.token
      - method: GET
        path: /api/auth/profile
        headers:
          Authorization: "Bearer {token}"
        expect_status: 200
```

`capture` 把响应 JSON 写入上下文，后续步骤用 `{token}` 占位替换。复杂状态机仍建议用 **Python 代码**（路径一里的 `test_functional_flows.py`）。

---

## 生成的代码长什么样

以认证模块为例，每个接口生成 4 条测试：

```python
# H: Happy Path
@pytest.mark.h
def test_register_happy_path():
    """H: 用户注册 — 正常请求"""
    body = {"username": "testuser", "password": "password123", "email": "test@example.com"}
    resp = requests.post(f"{BASE_URL}/api/auth/register", json=body, timeout=10)
    assert resp.status_code == 201

# E: 边界值
@pytest.mark.e
def test_register_boundary():
    """E: 用户注册 — 边界值测试"""
    body_empty = {"username": "", "password": "password123", "email": "test@example.com"}
    resp = requests.post(f"{BASE_URL}/api/auth/register", json=body_empty, timeout=10)
    assert resp.status_code in (400, 422)

# X: 异常
@pytest.mark.x
def test_register_exception():
    """X: 用户注册 — 异常请求测试"""
    body_partial = {"password": "password123", "email": "test@example.com"}
    resp = requests.post(f"{BASE_URL}/api/auth/register", json=body_partial, timeout=10)
    assert resp.status_code in (400, 422)

# P: 性能
@pytest.mark.p
def test_register_perf():
    """P: 用户注册 — 响应时间检查"""
    start = time.time()
    resp = requests.post(f"{BASE_URL}/api/auth/register", json=body, timeout=10)
    elapsed = time.time() - start
    assert elapsed < 5.0, f"响应时间 {elapsed:.2f}s 超过 5s 阈值"
```

---

## 额外生成的测试文件

除了按 tag 分组的 API测试，生成器还会额外产出：

### test_security.py — 安全测试

```python
class TestSecurity:
    def test_anonymous_access_protected(self):
        """S: 未登录访问受保护接口"""
        resp = requests.get(f"{BASE_URL}/api/auth/profile", timeout=10)
        assert resp.status_code == 401

    def test_expired_token(self):
        """S: 过期Token 访问"""
        headers = {"Authorization": "Bearer expired_token_12345"}
        resp = requests.get(f"{BASE_URL}/api/products", headers=headers, timeout=10)
        assert resp.status_code in (401, 403)
```

### test_boundary.py — 边界值专项测试

按字段逐个测试边界：空值、超长字符串、特殊字符、Unicode、无效枚举值。

### test_functional_flows.py — 功能流程测试

```python
class TestAuthFlow:
    def test_register_then_login(self):
        """流程：注册 → 登录 → 获取用户信息"""
        # 1. 注册
        resp1 = requests.post(f"{BASE_URL}/api/auth/register", ...)
        assert resp1.status_code in (200, 201)
        # 2. 登录
        resp2 = requests.post(f"{BASE_URL}/api/auth/login", ...)
        assert resp2.status_code == 200
        # 3. 获取用户信息
        resp3 = requests.get(f"{BASE_URL}/api/auth/profile", ...)
        assert resp3.status_code == 200
```

### test_e2e_seckill_flow.py — 端到端测试

```python
class TestSeckillE2E:
    def test_01_register(self):   # 注册
    def test_02_login(self):      # 登录
    def test_03_list_products(self):  # 查询商品
    def test_04_product_detail(self): # 商品详情
    def test_05_seckill_activities(self): # 秒杀活动
    def test_06_orders(self):     # 订单列表
    def test_07_unauthorized(self): # 未登录访问
```

---

## 实际工作流

**路径一（首次接手系统）**：

```
1. 拿到 openapi.yaml
   ↓
2. python scripts/test_generator.py openapi.yaml -o output/
   ↓
3. cd output && pytest -v
   ↓
4. 补充业务断言、DB 校验（第 14 节）、数据依赖
   ↓
5. 接入第 17～21 节（重试、flaky、健康检查）
```

**路径二（已有铺底，维护冒烟集）**：

```
1. openapi 变更 → 对比漂移（附录 A）
   ↓
2. 更新 spec.md 中的 cases / scenarios
   ↓
3. generate.sh → pytest（Skill 包）→ CI
```

**时间对比（路径一）**：
- 手动写 50 个接口测试（含 H/E/X/P/S）：4-6 小时
- 生成器 + 手动补充：约 30 分钟

---

## 生成结果统计

以秒杀系统 63 个接口为例：

| 维度 | 数量 | 说明 |
|------|------|------|
| H (Happy Path) | 62 条 | 每个接口一条正常请求 |
| E (边界值) | 28 条 | 空值/超长/特殊字符/无效枚举 |
| X (异常) | 62 条 | 缺少必填/类型错误/无效枚举 |
| P (性能) | 62 条 | 响应时间 < 5s |
| S (安全) | 3 条 | 匿名/过期Token/无效Token |
| 功能流 | 2 条 | 注册→登录、商品CRUD |
| E2E | 7 条 | 完整秒杀流程 |
| **总计** | **204 条** | 22 个文件，343KB |

---

## 生成器的能力边界

### 能做的
- 从 OpenAPI 3.0 文档提取所有接口
- 生成 5 维度测试覆盖（H/E/X/P/S）
- 自动处理认证接口（生成 Token fixture）
- 自动生成示例请求参数
- 按 tag 分组输出
- 生成安全/边界/功能流/E2E 专项测试
- 支持 `pytest -m` 按维度运行

### 不能做的（需要你手动补充）
- 复杂的业务断言（如"库存扣减后等于原库存-1"）
- 数据依赖（如"先创建商品才能秒杀"）
- 异常场景（如"密码错误3次后锁定"）
- 性能测试（如"100并发下响应时间<2s"）

**生成器是起点，不是终点**。它帮你跨过"从文档到代码"的第一道坎。

---

## 附录 A：契约漂移检测

接口文档会变：**新增必填字段、删路径、改状态码** 都会让旧测试「突然全红」。CI 里应在跑 pytest 前 **对比两版 OpenAPI**。

### 破坏性变更（Breaking）示例

- 删除 `/api/products` 或删除 `POST` 方法  
- `POST` 请求体 **新增必填** 字段 `stock`（旧客户端未传则失败）  
- 响应里业务依赖字段被删  

### 教学演示（本仓库）

```bash
cd test
python scripts/schema_drift_demo.py examples/openapi_mini_v1.json examples/openapi_mini_v2.json
```

**预期输出（节选）**：

```
对比: openapi_mini_v1.json → openapi_mini_v2.json
--------------------------------------------------
[BREAKING] /api/products POST 新增必填字段: ['stock']
[COMPAT] 新增路径: /api/orders
--------------------------------------------------
共 2 项变更，其中破坏性 1 项。
```

完整检测（响应体字段、导出报告）可自行实现扩展；本课掌握 **为何要比对 + 如何读 BREAKING** 即可。

---

## 附录 B：运行时自愈 vs 脚本自愈

第 17 节教的是 **运行时自愈**（跑的时候救）。二者互补，不要混为一谈。

| 类型 | 典型手段 | 何时有效 | 本课程 |
|------|----------|----------|--------|
| **运行时自愈** | 智能重试、指数退避、状态轮询、前置失败 skip | 网络抖动、服务短暂 5xx | **第 17 节**、`api_self_healing.py` |
| **脚本自愈** | 契约变了改 path/断言、LLM 最小补丁 | 字段改名、状态码约定变更 | **概念**（第 22 节）；完整 Healer 提示词在 **Skill `api-skills/自我修复`** |

```
测试失败
    │
    ├─ ConnectionError / Timeout / 5xx  ──► 运行时重试（第 17 节）
    │
    └─ AssertionError（200 变 404、字段缺失）──► 先查附录 A 是否契约漂移
                                              └──► 再改脚本或走 Skill 脚本自愈
```

---

## 附录 C：与 Agent 四段流水线（认知图）

本课 **不展开** AI 编辑器 Skill 正文（分析→规划→执行→自愈）。只需知道业界常这样分工：

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│  分析   │ → │  规划   │ → │  执行   │ → │  自愈   │
│ 解析契约│   │ 范围优先│   │ 生成脚本│   │ 失败补丁│
│ 依赖关系│   │ 样本数据│   │ 跑 pytest│  │ 或登记缺陷│
└─────────┘   └─────────┘   └─────────┘   └─────────┘
     ↑ 本课：你学会手写与改 pytest，不被黑盒绑死
```

---

---

## 要点回顾

接口文档自动生成测试不是"AI 黑科技"，就是 YAML 解析 + 字符串拼接（或 spec 渲染）。但它的价值在于：

1. **消除重复劳动**：路径一一次生成 200+ 条；路径二用 spec 维护冒烟小集
2. **分工清晰**：功能测试点 vs 接口契约（22.1）；不与页面用例混写
3. **保持同步**：文档变更 → 附录 A 看漂移 → 再生成或改 spec
4. **自愈分层**：运行时重试（第 17 节）≠ 脚本改断言（附录 B）
5. **覆盖全面**：H/E/X/P/S；钱相关多加 S；DB 校验见第 14 节

**适用场景**：
- 接手已有系统，快速建立测试覆盖
- 接口数量多（20+），手写成本高
- 需要保持测试和文档同步
- 需要多维度测试覆盖（正常/异常/边界/安全）

**不适用场景**：
- 接口数量少（5 个以内），手写更快
- 需要复杂的业务逻辑测试
- 接口文档本身就不准确

---

**作者**：测试员周周（14 年测试老兵，专注 AI测试与安全）
**公众号**：测试员周周
