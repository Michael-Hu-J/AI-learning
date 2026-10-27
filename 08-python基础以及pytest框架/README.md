# Python 基础 & pytest 自动化测试

> **你买到的是什么**：一套能跟着写的 **pytest 系统课** + 可运行的 **示例工程**（接口生成、自愈、flaky、健康检查等）。  
> **示例代码目录**：本文件夹下的 [`test/`](test/README.md)（所有命令默认在 `test/` 里执行）。

---

## 课程目录（文章在哪里）

所有正文为 **Markdown**，文件名即节次，与 `test/` 代码一一对应：

| 块 | 节次 | 主题 |
|----|------|------|
| 基础 | 01～02 | Python 变量、类、装饰器 |
| pytest 核心 | 03～09 | 入门、断言、Fixture、Hook、Mark、参数化 |
| 工程化 | 10～13 | Allure、xdist 并行、项目结构、覆盖率/超时 |
| 实战 | 14 | 真实业务 API 综合实战（含 **接口+DB 校验** 增补） |
| 面试 | 15 | pytest 面试题 |
| 进阶 Hook | 16 | xdist 跨 worker |
| 自愈体系 | 17～21 | 智能重试、诊断、现场收集、flaky、健康检查 |
| 接口生成 | **22** | OpenAPI→pytest（**路径一**批量 + **路径二** spec 概念、契约漂移、自愈对照） |

**第 22 节是接口自动化主线**，建议学完 17 节后阅读（附录 A/B 与 17 节呼应）。

---

## 怎么开始（选一条路径）

### 路径 A：只想先学会 pytest（30 分钟）

```bash
cd test
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_self_healing.py -v
```

不需要业务系统（自愈引擎单元测试）。详见 [`test/README.md`](test/README.md)。

### 路径 B：有 OpenAPI，想批量生成接口测试

```bash
cd test
python scripts/test_generator.py ../openapi-example.yaml --output output/
cd output && pytest -v -m h    # 先跑 Happy Path
```

详见 **第 22 节**、`test/README.md` 第二节。

### 路径 C：跟完整实战（需自建/秒杀演示后端）

```bash
cd test
export TEST_BASE_URL=http://127.0.0.1:5000
export TEST_ADMIN_PASSWORD=admin123
pytest tests/test_seckill_finance_comprehensive.py -v
pytest tests/test_api_db_check.py::test_create_product_then_list -v
```

---

## 本课增补能力（相对旧版目录）

| 能力 | 文档 | 代码/命令 |
|------|------|-----------|
| 功能用例 vs 接口契约分工 | 第 22 节 §22.1 | — |
| 声明式 API spec（示例，无 generate.sh） | 第 22 节 §22.4 | `test/examples/api_smoke_spec_example.md` |
| 契约漂移检测（教学版） | 第 22 节附录 A | `test/scripts/schema_drift_demo.py` |
| 运行时自愈 vs 改脚本 | 第 17 节 + 第 22 节附录 B | `test/self_healing/` |
| 接口 + DB 校验 | 第 14 节增补 | `test/tests/test_api_db_check.py` |
| 进阶三件套 | 第 22 节文末 | 联读 `09-playwright/附录-进阶路线与三件套分工.md` |

---

## 文件夹结构（顶层）

```
08-python基础以及pytest框架/
├── README.md                 ← 你正在看的总说明
├── 第01节-....md ～ 第22节-....md
├── openapi-example.yaml      ← 生成器示例契约
└── test/                     ← 全部可运行代码（必读 test/README.md）
```

---

## 对外打包说明（勿随课包外发）

以下内容**仅本地开发产生**，打 zip / 上传网盘前请删除或不要收录：

| 类型 | 路径 / 说明 |
|------|-------------|
| 缓存与报告 | `.pytest_cache/`、`reports/`、`test/reports/`、`test/.pytest_cache/`、`allure-results/` |
| 生成物 | `test/output/`（`test_generator.py` 本地生成，可让读者自行生成） |
| 虚拟环境 | `.venv/`、`venv/` |
| 私密配置 | `.env`、真实数据库口令、公司内网 URL |

**本课包不包含**（需读者自行获取或另购）：完整「电商秒杀与财务一体化」后端仓库、AI 测试专业版 Skill 全套 `generate.sh`、生产环境执行平台前后端源码。正文会引用其概念，以外链或 Skill 产品说明为准。

---

## 常见问题

**Q：没有秒杀系统能学吗？**  
能。`test_self_healing.py`、第 03～13 节、`schema_drift_demo.py` 均不依赖外部系统。`test_product_api.py` 需秒杀演示后端（`/api/auth/login`），未启动时会自动 skip。

**Q：和 09 重复吗？**  
不重复。本课偏 **HTTP/pytest/CI**；09 偏 **浏览器引擎**。09 里少量 API 用例是联调演示。

**Q：`pytest` 收集报错 `Package object has no attribute obj`？**  
多为本机已装 `pytest-asyncio` 且版本与 pytest 9 不兼容。可在课包 venv 内 `pip install -r requirements.txt`（已限制 `pytest<9`），或临时：`pytest -p no:asyncio tests/...`。

---

**作者**：测试员周周 · 公众号：测试员周周
