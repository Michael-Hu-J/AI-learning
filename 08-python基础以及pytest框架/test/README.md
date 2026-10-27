# 配套代码 — 使用说明

> **课程总览**（文章列表、和 09/Skill 关系）：请先看上一级 [`../README.md`](../README.md)  
> **本目录**：所有 `pytest` / 脚本命令的 **工作目录**（先 `cd` 到这里再执行下文命令）。

---

## 本目录能干什么（一张表）

| 你想做的事 | 要不要业务后端 | 命令 / 文件 |
|------------|----------------|-------------|
| 学 pytest 基础（无后端） | 否 | `pytest tests/test_self_healing.py -v` |
| 商品接口实战 | 是（秒杀演示后端） | `pytest tests/test_product_api.py -v` |
| OpenAPI 批量生成接口测试 | 可选（生成后需地址才能全绿） | `python scripts/test_generator.py ../openapi-example.yaml -o output/` |
| 看声明式 API spec 长什么样 | 否 | `cat examples/api_smoke_spec_example.md` |
| 对比两版 OpenAPI 是否破坏性变更 | 否 | `python scripts/schema_drift_demo.py examples/openapi_mini_v1.json examples/openapi_mini_v2.json` |
| 接口创建后 DB/列表校验 | 是（:5000 演示后端） | `pytest tests/test_api_db_check.py -v` |
| 综合 API 实战 | 是 | `pytest tests/test_seckill_finance_comprehensive.py -v` |
| API 运行时自愈演示 | 否（mock） | `python scripts/demo_self_healing.py` |
| flaky / 健康检查 / 智能重试 | 视用例而定 | 见 `self_healing/`，第 17～21 节 |

---

## 快速开始

```bash
# 进入本目录（重要）
cd test

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 推荐第一步：不依赖任何后端
pytest tests/test_self_healing.py -v
```

---

## 路径一：OpenAPI → 大量 pytest 文件（第 22 节主路径）

```bash
cd test
python scripts/test_generator.py ../openapi-example.yaml --output output/

cd output
pytest -v -m h          # 只跑 Happy Path
pytest -v -m x          # 只跑异常
```

**产出**：按模块拆分的 `test_api_*.py`、安全/边界/E2E 等（详见第 22 节）。

---

## 路径二：声明式 spec（本仓库只有示例）

本课 **不包含** `generate.sh`。只提供结构示例，方便和 Skill 包对照：

```bash
cat examples/api_smoke_spec_example.md
```



数据流说明见 **第 22 节 §22.4～22.5**。

---

## 契约漂移（第 22 节附录 A）

```bash
cd test
python scripts/schema_drift_demo.py examples/openapi_mini_v1.json examples/openapi_mini_v2.json
```

输出含 `[BREAKING]` / `[COMPAT]`。完整版工具在 Skill 包 `api_schema_drift_detector.py`。

---

## 接口 + 数据库校验（第 14 节增补）

```bash
export TEST_BASE_URL=http://127.0.0.1:5000
export TEST_ADMIN_PASSWORD=admin123

# 仅 HTTP：创建商品后在列表里能查到
pytest tests/test_api_db_check.py::test_create_product_then_list -v

# MySQL 直连（可选，需 pip install pymysql）
export TEST_DB_HOST=127.0.0.1
export TEST_DB_USER=root
export TEST_DB_PASSWORD=***
export TEST_DB_NAME=你的库名
pytest tests/test_api_db_check.py::test_create_product_row_in_mysql -v
```

---

## 没有业务系统怎么学？
**方案 A（推荐）**：只跑不依赖后端的用例  

```bash
pytest tests/test_self_healing.py -v
python scripts/schema_drift_demo.py examples/openapi_mini_v1.json examples/openapi_mini_v2.json
python scripts/demo_self_healing.py
```

**方案 B**：有自己的系统 → 改 `BASE_URL`、登录 path、token 字段（见下一节）。

---

## 适配你自己的系统（改 3 处）

```python
BASE_URL = "http://你的地址:端口"

# 登录
resp = requests.post(f"{BASE_URL}/你的登录路径", json={...})
token = resp.json()["你的token字段"]

# 业务接口
resp = requests.post(f"{BASE_URL}/你的业务路径", json={...}, headers={"Authorization": f"Bearer {token}"})
```

或用环境变量：`export SECKILL_BASE_URL=...`（部分脚本已支持，以代码为准）。

---

## 目录结构

```
test/
├── README.md
├── conftest.py / pytest.ini / requirements.txt / env.example
├── openapi-example.yaml / openapi.yaml
├── examples/                    # spec 示例、契约漂移 mini OpenAPI
├── scripts/
│   ├── test_generator.py
│   ├── schema_drift_demo.py
│   ├── demo_self_healing.py
│   └── run_seckill_api_test.py
├── tests/                       # 4 个 pytest 用例文件
├── core/                        # openapi_parser、api_self_healing
├── self_healing/                # 重试、诊断、flaky、健康检查
├── utils/                       # backend_check、test_data_generator
└── output/                      # 本地生成（勿打包，见 .gitignore）
```

---

## 对应课程章节

| 章节 | 主题 |
|------|------|
| 01～09 | pytest 基础 |
| 10～13 | Allure、并行、结构、生态 |
| 14 | 综合实战 + **接口 DB 校验** |
| 17～21 | 重试、诊断、现场、flaky、健康检查 |
| **22** | OpenAPI 生成、双路径、契约漂移、自愈对照、三件套路线 |

正文文件在上一级目录：`第01节-....md` … `第22节-....md`。

---

## 依赖（按需安装）

```bash
pip install -r requirements.txt

# 可选
pip install pymysql              # test_api_db_check MySQL 用例
pip install pytest-xdist allure-pytest pytest-timeout pytest-cov
```

---

## 环境排错

若收集阶段报错 `AttributeError: 'Package' object has no attribute 'obj'`：

```bash
pip install "pytest>=7.4,<9"   # 按 requirements.txt
# 或
pytest -p no:asyncio tests/test_self_healing.py -v
```

---

## 对外打包说明（勿随课包外发）

与上一级 [`../README.md`](../README.md#对外打包说明勿随课包外发) 相同。本目录额外注意：**不要**打包 `output/`、`.pytest_cache/`、`reports/`、`.venv/`、`.env`。

---

**作者**：测试员周周 · 公众号：测试员周周
