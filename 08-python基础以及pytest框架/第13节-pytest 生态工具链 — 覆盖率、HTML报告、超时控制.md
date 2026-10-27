# 13-pytest 生态工具链 — 覆盖率、HTML报告、超时控制

> 对应代码：pytest 生态插件，补充示例

---

## 概念讲解

pytest 本身已经很强了，但生态插件让它更强。

**其他事情——覆盖率统计、HTML报告、超时控制、失败重试——都靠插件完成。**

pytest 的插件生态非常丰富，PyPI 上搜索 `pytest-` 有上千个插件。但实际项目中常用的就那几个。本节介绍5个最实用的插件。

---

## 覆盖率统计与工具集成

### 1. pytest-cov — 测试覆盖率统计

`pytest-cov` 统计测试代码覆盖了哪些代码行，生成覆盖率报告。

**安装**：

```bash
pip install pytest-cov
```

**基本用法**：

```bash
# 生成终端覆盖率报告
pytest --cov=src/ --cov-report=term

# 生成HTML覆盖率报告
pytest --cov=src/ --cov-report=html

# 生成XML覆盖率报告（CI集成用）
pytest --cov=src/ --cov-report=xml

# 设置覆盖率门槛（低于这个值pytest返回非零退出码）
pytest --cov=src/ --cov-fail-under=80
```

**报告示例**：

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
src/base_page.py                 85      12    86%
src/api/base_api.py              45       5    89%
src/utils/logger.py              20       3    85%
src/utils/screenshot.py          15       8    47%
-------------------------------------------------
TOTAL                           165      28    83%
```

**覆盖率的意义和局限**：

- **有意义**：覆盖率低说明有很多代码没被测试到，潜在 bug 多。
- **有局限**：覆盖率高不代表测试质量好。`assert True` 也能覆盖代码，但没有任何验证价值。

**实际项目中的建议**：
- 核心业务代码：覆盖率目标 80%+
- 工具类代码：覆盖率目标 60%+
- 配置文件/YAML：不需要覆盖率

### 2. pytest-html — 轻量级 HTML 报告

`pytest-html` 生成独立的 HTML 报告，不需要 Allure 和 Java 环境。

**安装**：

```bash
pip install pytest-html
```

**基本用法**：

```bash
# 生成HTML报告
pytest --html=reports/report.html --self-contained-html

# --self-contained-html：把所有资源（CSS、JS）内嵌到一个HTML文件中
# 方便通过邮件或飞书发送
```

**Allure vs pytest-html 的选择**：

| 特性 | Allure | pytest-html |
|------|--------|-------------|
| 报告质量 | 高（三级分类、步骤、附件） | 中（表格+基本信息） |
| 依赖 | 需要 Java | 无需额外依赖 |
| 生成速度 | 较慢 | 快 |
| 适用场景 | 正式报告、对外展示 | 快速查看、CI附件 |

**建议**：对外展示用 Allure，内部快速查看用 pytest-html。

### 3. pytest-timeout — 单个用例超时控制

`pytest-timeout` 为每个测试用例设置超时时间，防止某个用例卡死导致整个测试套件挂住。

**安装**：

```bash
pip install pytest-timeout
```

**基本用法**：

```bash
# 所有用例超时60秒
pytest --timeout=60

# 用装饰器设置单个用例超时
@pytest.mark.timeout(30)
def test_slow_operation():
    ...
```

**适用场景**：
- UI 自动化测试中，元素定位可能永远等不到（页面卡死）
- API测试中，请求可能永远不返回（网络问题）
- 数据驱动测试中，某个数据组合可能导致死循环

**超时 vs 重试**：
- 超时是"超过时间就失败"
- 重试是"失败了再试几次"
- 两者可以组合使用：`@pytest.mark.timeout(30)` + `@pytest.mark.flaky`（失败重试）

### 4. pytest-rerunfailures — 失败自动重试

`pytest-rerunfailures` 让失败的测试用例自动重试 N 次。

**安装**：

```bash
pip install pytest-rerunfailures
```

**基本用法**：

```bash
# 每个失败用例重试2次
pytest --reruns 2

# 每次重试间隔5秒
pytest --reruns 2 --reruns-delay 5
```

**用装饰器控制单个用例**：

```python
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_flaky_ui_operation():
    """UI操作可能偶发性失败，自动重试3次"""
    login_page = LoginPage(driver)
    login_page.click_login_button()
    assert login_page.is_on_home_page()
```

**适用场景**：
- UI 自动化测试：元素定位偶发性超时（页面加载慢）
- 网络请求：偶发性连接超时
- 不适用范围：逻辑错误导致的失败（重试100次也会失败）

### 5. pytest-ordering — 控制执行顺序

pytest 默认按文件扫描顺序执行用例。`pytest-ordering` 允许你控制执行顺序。

**生态说明**：`pytest-ordering` 在 PyPI 上更新不算活跃；**新建项目**选型前建议对比 **pytest-order** 等同类的最近发布时间与 issue 情况，再决定依赖，避免无人维护的插件锁死版本。

**安装**：

```bash
pip install pytest-ordering
```

**基本用法**：

```python
import pytest

@pytest.mark.run(order=1)
def test_step1_setup():
    """第一步：初始化"""
    ...

@pytest.mark.run(order=2)
def test_step2_use_result():
    """第二步：使用第一步的结果"""
    ...

@pytest.mark.run(order=3)
def test_step3_cleanup():
    """第三步：清理"""
    ...
```

**注意事项**：
- **测试用例之间不应该有顺序依赖**。如果B依赖A的结果，说明你的测试设计有问题。
- `pytest-ordering` 只在"确实需要顺序"的场景下使用，如：集成测试中的多步骤流程。
- 并行执行时，`order` 标记失效（多个 worker 同时跑，无法保证顺序）。

---

## 实战案例

以"CI 流水线中的工具链组合"为场景，展示这些插件如何组合使用。

**场景描述**：某移动App的 CI 流水线，每次代码提交后自动运行测试。

**CI 配置（GitHub Actions 示例）**：

```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pytest-html pytest-timeout pytest-rerunfailures pytest-xdist allure-pytest
      
      - name: Run tests with coverage
        run: |
          pytest -n 4 \
            --cov=src/ \
            --cov-report=xml:reports/coverage.xml \
            --cov-report=term \
            --cov-fail-under=70 \
            --html=reports/report.html \
            --self-contained-html \
            --timeout=120 \
            --reruns 2 \
            --alluredir=reports/allure-results \
            -v
      
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: reports/coverage.xml
      
      - name: Upload HTML report
        uses: actions/upload-artifact@v4
        with:
          name: html-report
          path: reports/report.html
      
      - name: Generate Allure report
        if: always()
        uses: simple-elf/allure-report-action@v1
        with:
          allure_results: reports/allure-results
          allure_report: reports/allure-report
```

**这条 CI 流水线做了什么**：
1. **并行执行**（`-n 4`）：4个 worker 并行跑测试
2. **覆盖率统计**（`--cov`）：覆盖率低于70%时 CI 失败
3. **超时控制**（`--timeout=120`）：单个用例超过120秒自动失败
4. **失败重试**（`--reruns 2`）：偶发性失败的用例自动重试2次
5. **HTML报告**（`--html`）：生成独立的 HTML 报告
6. **Allure报告**（`--alluredir`）：生成 Allure 报告用于详细分析
7. **上传产物**：覆盖率报告、HTML报告、Allure报告都作为 CI 产物保存

---

## 其他常用插件速查

| 插件 | 作用 | 安装命令 |
|------|------|---------|
| `pytest-mock` | mock 第三方依赖 | `pip install pytest-mock` |
| `pytest-asyncio` | 异步测试支持 | `pip install pytest-asyncio` |
| `pytest-django` | Django 项目测试 | `pip install pytest-django` |
| `pytest-selenium` | Selenium 集成 | `pip install pytest-selenium` |
| `pytest-bdd` | BDD 测试框架 | `pip install pytest-bdd` |
| `pytest-lazy-fixture` | fixture 懒加载 | `pip install pytest-lazy-fixture` |

---

## 注意事项和常见坑

- **覆盖率不是越高越好**。80% 是合理目标，超过90%的投入产出比很低。为了覆盖那最后10%的代码，你可能要写大量边界测试用例，但实际 bug 大多在前80%的代码里。
- **`--cov-fail-under` 在 CI 中很有用**。它防止有人提交代码后不写测试，导致覆盖率下降。但门槛要设得合理，70-80% 比较合适。
- **`--timeout` 和 `--reruns` 不要混用**。超时后 pytest 会标记为失败，`--reruns` 会重试。但如果超时是因为死循环，重试100次也会超时。
- **并行执行时 `order` 标记失效**。这是 `pytest-ordering` 的已知限制。如果需要顺序执行，不要用 `-n` 并行。
- **插件不是越多越好**。每个插件都增加了依赖和维护成本。只装你真正需要的插件。

---

## 插件速查表

| 插件 | 解决什么问题 | 一行命令 | 什么时候用 |
|------|------------|---------|-----------|
| `pytest-cov` | 测试覆盖率统计 | `pytest --cov=src/` | CI 中设覆盖率门槛 |
| `pytest-html` | 轻量 HTML 报告 | `pytest --html=report.html` | 快速查看、邮件发送 |
| `pytest-timeout` | 防止用例卡死 | `pytest --timeout=60` | UI 自动化、网络请求 |
| `pytest-rerunfailures` | 失败自动重试 | `pytest --reruns 2` | 偶发性失败的 UI 测试 |
| `pytest-xdist` | 并行执行 | `pytest -n 4` | 用例数 > 100 时 |
| `pytest-mock` | mock 第三方依赖 | `mocker.patch(...)` | 单元测试中隔离外部依赖 |
| `pytest-asyncio` | 异步测试支持 | `@pytest.mark.asyncio` | 测试 async/await 代码 |
| `pytest-ordering` | 控制执行顺序 | `@pytest.mark.run(order=1)` | 集成测试多步骤流程 |

**选型建议**：
- 每个插件都增加依赖和维护成本，只装你真正需要的
- 安装前在 PyPI 上看最后更新时间，超过 1 年未更新的插件谨慎使用
- CI 环境优先装：`pytest-cov`、`pytest-xdist`、`pytest-timeout`
- 本地开发可以按需装其他插件

> pytest 的强大不在于它本身，而在于它的插件生态。覆盖率、HTML 报告、超时控制、失败重试——这些功能 pytest 本身不提供，但通过插件可以无缝集成。先搞清楚自己要什么，再去 PyPI 上找对应的插件，比什么都自己写效率高得多。
