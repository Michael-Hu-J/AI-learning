# 11-pytest 并行执行 — pytest-xdist 让测试速度翻倍

> 对应代码：`test/并行执行测试使用指南.md`、`test/tests/test_seckill_finance_comprehensive.py`

---

## 概念讲解

单核跑 pytest，4 核 CPU 闲着看戏——直到你发现 pytest-xdist 能让速度翻倍。

串行执行的话，每个用例平均30秒，1000个用例 = 500分钟 = 8小时。

**CI 环境中，8小时意味着：早上提交代码，晚上才能看到测试结果。这个反馈周期太长了。**

`pytest-xdist` 是 pytest 最流行的并行执行插件。一行命令 `pytest -n 4`，把测试用例分配到4个 worker 进程并行执行。1000个用例从8小时降到2小时。

**但并行执行不是银弹。共享状态的测试会互相干扰，fixture 的作用域在并行模式下行为不同，Allure 报告需要特殊处理。**

---

## 并行执行配置

### 1. 安装与基本用法

```bash
# 安装 pytest-xdist
pip install pytest-xdist

# 基本用法：-n 指定 worker 数量
pytest -n 4              # 4个进程并行执行
pytest -n auto           # 自动检测CPU核心数
pytest -n 4 -v           # 并行 + 详细输出
```

**worker 数量的选择**：
- `-n auto`：自动等于 CPU 核心数。适合 CPU 密集型测试（如数据处理）。
- `-n 4` 或 `-n 8`：固定数量。适合 I/O 密集型测试（如网络请求、UI 操作），因为瓶颈不在 CPU。
- 不要设太大。worker 数量 > CPU 核心数 × 2 时，上下文切换开销会抵消并行收益。

### 2. 并行的陷阱 — 共享状态

**并行执行最大的坑：共享状态的测试会互相干扰。**

来看一个会出问题的例子：

```python
#  这段代码在并行模式下会出问题
shared_counter = 0  # 全局变量——所有worker共享

@pytest.mark.parametrize("i", range(10))
def test_increment(i):
    global shared_counter
    shared_counter += 1
    assert shared_counter == i + 1  # 并行时这个断言会失败！
```

**为什么会失败**：4个 worker 同时修改 `shared_counter`，值是不可预测的。worker A 读到 3，worker B 也读到 3，两个都加1变成4，但预期应该是4和5。

**解决方案**：测试用例之间不要共享状态。每个用例用独立的数据、独立的资源。

```python
#  正确的写法：每个用例独立
@pytest.mark.parametrize("i", range(10))
def test_increment(i):
    local_counter = 0
    local_counter += 1
    assert local_counter == 1  # 每个worker有自己的local_counter
```

**真实项目中的常见共享状态陷阱**：

| 共享状态 | 问题 | 解决方案 |
|---------|------|---------|
| 全局变量 | 多个worker同时修改 | 改用 fixture 返回独立实例 |
| 同一个测试账号 | 多个用例同时登录同一账号 | 每组数据用不同的测试账号 |
| 同一个文件 | 多个worker同时写文件 | 用 `tmp_path` 创建独立临时目录 |
| 同一个数据库记录 | 多个用例修改同一条记录 | 每个用例创建独立的测试数据 |

### 3. fixture 在并行模式下的变化

**session 级别的 fixture 在每个 worker 中独立初始化一次。**

```python
@pytest.fixture(scope="session")
def driver_setup():
    """session级fixture"""
    driver = create_driver()
    yield driver
    driver.quit()
```

**串行模式**：整个测试会话只初始化1次 driver。

**并行模式（-n 4）**：4个 worker 各初始化1次 driver，共4次。

**这不是 bug，是设计如此**。每个 worker 是独立的 Python 进程，无法共享同一个 driver 实例。

**如果你的 fixture 初始化很慢（如启动 Appium），并行模式下总初始化时间 = worker 数 × 初始化时间。4个 worker × 30秒 = 2分钟。但测试执行时间从8小时降到2小时，总体还是划算的。**

### 4. 负载均衡

pytest-xdist 自动分配用例到各个 worker。分配策略是"按文件分组"：同一个文件中的用例尽量分配到同一个 worker。

**手动控制分配**：用 `--dist loadfile` 按文件分组，或用 `--dist worksteal` 动态负载均衡（空闲 worker 可以从忙 worker 那里"偷"用例）。

```bash
# 按文件分组（同一个文件的用例在同一个worker）
pytest -n 4 --dist loadfile

# 动态负载均衡（空闲worker自动领取新用例）
pytest -n 4 --dist worksteal
```

### 5. 与 Allure 报告的兼容性

pytest-xdist 并行执行时，每个 worker 独立生成 allure-results。需要特殊处理才能合并成一份报告。

**方式一：合并结果目录**

```bash
# 并行执行
pytest -n 4 --alluredir=reports/allure-results

# Allure 结果会自动合并到 alluredir
allure serve reports/allure-results
```

**方式二：使用 pytest-xdist 的 alluredir 插件**

```bash
pip install pytest-xdist allure-pytest

# 并行执行，每个worker独立生成结果
pytest -n 4 --alluredir=reports/allure-results

# 合并并生成报告
allure generate reports/allure-results -o reports/allure-report --clean
```

---

## 实战案例

以"全量回归测试"为场景，展示并行执行的完整流程。

**场景描述**：某移动App有500个回归测试用例，串行执行需要约4小时。引入并行执行后，目标是将执行时间降到1小时以内。

```bash
# ===== 步骤1：评估并行可行性 =====
# 检查测试用例之间是否有共享状态
# 关键检查点：
# 1. 是否有全局变量？
# 2. 是否多个用例共用同一个测试账号？
# 3. 是否多个用例写同一个文件？
# 4. fixture 是否有副作用？

# ===== 步骤2：小规模并行测试 =====
# 先用 -n 2 测试，确认没有并发问题
pytest -n 2 -v --tb=short

# ===== 步骤3：全量并行执行 =====
# 确认无误后，用 -n 4 全量执行
pytest -n 4 -v --tb=short --alluredir=reports/allure-results

# ===== 步骤4：生成报告 =====
allure generate reports/allure-results -o reports/allure-report --clean
```

**并行执行 vs 串行执行的性能对比**（模糊化数据）：

| 指标 | 串行（-n 0） | 并行（-n 2） | 并行（-n 4） |
|------|-------------|-------------|-------------|
| 用例数 | 500 | 500 | 500 |
| 执行时间 | ~4小时 | ~2小时 | ~1小时 |
| 失败用例 | 12 | 12 | 12 |
| 误报率 | 0% | 0% | 0% |

**关键发现**：
- 并行执行的结果与串行执行完全一致（失败用例数量和具体用例相同）
- 没有发现因并发导致的误报
- 4个 worker 时 CPU 利用率约 80%，还有提升空间

---

## 注意事项和常见坑

- **并行执行前先用串行跑一遍**。确认所有用例在串行模式下都通过，再开并行。否则出了问题分不清是用例本身的 bug 还是并发问题。
- **session 级 fixture 在并行模式下会初始化多次**。如果你的 fixture 初始化很慢（如启动 WebDriver），并行模式下总初始化时间 = worker 数 × 初始化时间。
- **不要并行执行有顺序依赖的用例**。如果用例B依赖用例A的结果，并行执行时两个用例可能同时跑，B 拿不到 A 的结果。
- **worker 数量不是越大越好**。I/O 密集型测试（网络请求、UI操作）可以设大一点（4-8），CPU 密集型测试（数据处理、加密）设小一点（2-4）。
- **并行执行的日志会混在一起**。4个 worker 同时输出日志，终端里看起来乱七八糟。建议用 `--log-file` 把日志写到文件，或者用 Allure 报告的步骤信息代替日志。

---

## 性能对比数据

以下是真实项目中并行执行的性能数据（模糊化处理）：

| 配置 | 用例数 | 执行时间 | 加速比 | CPU 利用率 |
|------|--------|---------|--------|-----------|
| 串行（-n 0） | 500 | ~4 小时 | 1× | ~25% |
| 2 worker（-n 2） | 500 | ~2 小时 | 2× | ~50% |
| 4 worker（-n 4） | 500 | ~1 小时 | 4× | ~80% |
| 8 worker（-n 8） | 500 | ~45 分钟 | 5.3× | ~95% |

**关键发现**：
- 并行执行的结果与串行完全一致（失败用例数量和具体用例相同）
- 没有发现因并发导致的误报
- 4 worker 时 CPU 利用率约 80%，还有提升空间
- 8 worker 时加速比接近线性，但 CPU 几乎满载，不建议再增加

**I/O 密集型 vs CPU 密集型**：
- UI 自动化测试（I/O 密集）：worker 数量可以设到 CPU 核心数的 1.5-2 倍
- 数据处理测试（CPU 密集）：worker 数量等于 CPU 核心数即可
- API测试（I/O 密集）：-n 4 到 -n 8 都有明显收益

> 并行执行不是"开了就行"。先确认测试用例之间没有共享状态，再从小规模（-n 2）开始验证，最后再全量并行。省下的时间值得你花 30 分钟排查并发问题。
