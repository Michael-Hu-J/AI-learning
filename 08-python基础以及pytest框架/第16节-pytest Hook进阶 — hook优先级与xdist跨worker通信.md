# 16-pytest Hook 进阶 — hook 优先级与 xdist 跨 worker 通信

> 对应代码：`test/conftest.py`（自愈系统 hook 集成）、整个 `test/self_healing/` 目录

---

有一次我写了一个重试插件，跑单进程的时候好好的。上线第一天跑了 `pytest -n 4`（4 个 worker），结果发现重试计数器乱了——A worker 重试了 3 次，B worker 重试了 0 次，C worker 重试了 10086 次。

查了半天，原因是 `retry_count` 是个全局变量，而 xdist 下每个 worker 是独立进程，全局变量根本不共享。

这时候我才真正理解了：**hook 不是你想象的那么简单，尤其是在分布式场景下。**

第 07 节讲了 hook 的基础用法——怎么注册、怎么用 `tryfirst/trylast` 控制顺序、怎么用 `hookwrapper` 包裹执行过程。这一节是它的进阶版，解决三个核心问题：

1. **hook 的执行顺序到底怎么定的？** `tryfirst` 是不是绝对优先？
2. **多个 conftest.py 都写了同一个 hook，谁覆盖谁？**
3. **xdist 开了多进程，hook 怎么在 worker 之间同步状态？**

这三个问题搞清楚了，你写自愈系统就不会踩我踩过的坑。

---

## hookwrapper 深入 — yield 前后到底怎么执行的

### yield 前后是两段代码

先看一个最简单的 hookwrapper：

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    print("1. hookwrapper 开始")
    outcome = yield          # <-- 这里让出控制权
    print("3. hookwrapper 结束")
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
```

执行顺序是：`1` → pytest 内部的 report 生成逻辑 → `3`。

`yield` 前面的代码在原始逻辑**之前**执行，`yield` 后面的代码在原始逻辑**之后**执行。

**这就是 hookwrapper 的核心：它把你写的函数分成了"前处理"和"后处理"两段，中间是原始逻辑。**

### outcome 对象是什么

`yield` 返回的 `outcome` 不是报告结果，而是一个 `_Result` 对象。它有三个属性：

- `outcome.get_result()` — 获取原始 hook 的执行结果（report 对象）
- `outcome.excinfo` — 如果原始逻辑抛了异常，这里存着异常信息
- `outcome.force_result()` — 强制修改返回结果（慎用，容易翻车）

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    # 如果原始逻辑抛异常了
    if outcome.excinfo:
        exc_type, exc_value, tb = outcome.excinfo
        logger.error(f"report 生成异常: {exc_value}")
        # 这时候 get_result() 会重新抛出异常
        # 所以一般先检查 excinfo
    rep = outcome.get_result()  # 正常情况获取 report
```

### 多个 hookwrapper 的洋葱模型

当多个 conftest.py 或者多个插件都注册了 `hookwrapper`，它们会像洋葱一样嵌套执行。

假设有 3 个 hookwrapper：

```python
# hookwrapper A（最外层）
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    print("A 前处理")
    yield
    print("A 后处理")

# hookwrapper B（中间层）
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    print("B 前处理")
    yield
    print("B 后处理")

# hookwrapper C（最内层）
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    print("C 前处理")
    yield
    print("C 后处理")
```

执行顺序：

```
A 前处理 → B 前处理 → C 前处理 → 原始逻辑 → C 后处理 → B 后处理 → A 后处理
```

这就是洋葱模型。**最外层的 hookwrapper 最先进入、最后退出。**

如果你想象不出来，想想电视剧里大将军穿盔甲：最外层的锁子甲先穿上，然后是中层的铁甲片，最里层是软甲。脱的时候反过来——先脱最里层的软甲。

**这个模型在自愈系统中非常重要。** 比如你可能想在最外层做"失败截图"（保证截图不被其他 hook 干扰），然后在中间层做"结果收集"，最内层做"重试判断"。

---

## 多个 conftest.py 的 hook 优先级

### 项目根目录 > 子目录

现在假设你的项目结构是这样的：

```
project/
├── conftest.py           # 根目录 conftest
├── tests/
│   ├── conftest.py       # 子目录 conftest
│   └── test_login.py
└── tests/api/
    └── conftest.py       # 更深的子目录 conftest
```

三个 conftest 都定义了 `pytest_runtest_makereport`，执行顺序是：

1. 根目录 `conftest.py`（最外层）
2. `tests/conftest.py`（中间层）
3. `tests/api/conftest.py`（最内层）

**说白了：离测试用例越近的 conftest，越先执行，越在洋葱的最内层。**

这个规则和 Python 的导入顺序其实是一个道理——pytest 会先加载根目录的配置，再加载子目录的配置。子目录的 conftest 可以覆盖或者扩展根目录的行为。

### 实际场景：根 conftest 做通用处理，子 conftest 做特定处理

```python
# 根目录 conftest.py — 通用处理
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)         # 通用：设置 rep_* 属性

# tests/api/conftest.py — API 测试专用处理
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.failed:
        # API 测试失败了，自动保存请求/响应体
        save_api_payload(item)
```

这样，根 conftest 保证所有测试都有 `rep_call` 属性，API 子目录的 conftest 额外做 API 特定的现场保存。互相不冲突。

---

## tryfirst / trylast 的真正作用

### "尝试"优先，不是绝对优先

这个点很多人理解错了，包括当年的我。

```python
@pytest.hookimpl(tryfirst=True)     # 尝试优先执行
def my_hook():
    pass

@pytest.hookimpl(trylast=True)      # 尝试延后执行
def my_hook():
    pass
```

你以为 `tryfirst=True` 的 hook 一定在 `trylast=True` 之前执行？

**答案是：在同优先级的情况下是的。但如果遇到 conftest 目录层级不同，不一定。**

tryfirst/trylast 的完整生效规则：

1. **同类 hook 之间**：tryfirst > 普通 > trylast，一定优先。
2. **不同 conftest 层级之间**：根 conftest 的 trylast 仍然可能在子 conftest 的 tryfirst**之后**（不是绝对的）。

为啥？因为 conftest 的层级优先级高于 tryfirst/trylast。**目录层级是第一优先级，tryfirst/trylast 是第二优先级。**

举个例子：

```
project/
├── conftest.py               # trylast=True
└── tests/deep/
    └── conftest.py           # tryfirst=True
```

`tests/deep/conftest.py` 的 hook **一定在** `project/conftest.py` 之前执行，不管有没有 tryfirst/trylast。因为子目录的 conftest 离测试用例更近。

**所以 tryfirst 和 trylast 的正确理解是：在同级 conftest 中，tryfirst 比同级的其他 hook 先执行。它不能跨目录层级穿透。**

### 踩坑记录

我之前犯过一个低级错误：

我在项目的两个 conftest 里都写了 `pytest_sessionfinish`：

```python
# project/conftest.py
@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    generate_report()     # 全局报告

# project/sub/conftest.py
@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    save_sub_report()     # 子模块报告
```

我以为 `tryfirst=True` 会让它在全局报告的 hook 之前执行。结果发现执行顺序完全不按我想的来——因为子目录 conftest 的 `pytest_sessionfinish` 跟根目录是**同级调用**（`sessionfinish` 是 session 级别，所有 conftest 共享同一个 hook 调用链），它们的顺序是：

1. 项目根 conftest 的 `trylast` hook
2. 子目录 conftest 的 `tryfirst` hook

**因为根目录 conftest 在 trylast 组里是最先加载的，而 tryfirst/trylast 只在同一加载顺序下生效。**

后来我学乖了：**同一种 hook 尽量只在一个地方写。非要分散在多个 conftest，一定要测试执行顺序。**

---

## xdist 跨 worker 的 hook 特性

### 每个 worker 是独立进程

这是 xdist 最容易被忽视的点。

当你运行 `pytest -n 4`，pytest 会启动 4 个 Python 进程。**每个进程都独立加载 conftest、独立执行 hook、独立创建 fixture。**

这意味着：

- 进程 A 的全局变量 `retry_count = 3`，进程 B 不知道
- 进程 A 的 flaky_detector 记录了 100 条结果，进程 B 不知道
- 进程 A 的 `scene_collector` 收集了截图，进程 B 不知道

### pytest_configure 在每个 worker 中独立执行

```python
def pytest_configure(config):
    # 这行代码会在主进程和每个 worker 中各执行一次
    logger.info(f"pytest_configure 执行，worker={os.getenv('PYTEST_XDIST_WORKER')}")
    config.option.alluredir = f"reports/allure-{worker_id}"
```

如果你在 `pytest_configure` 里做了全局初始化（比如清空目录），xdist 下你要小心：

```python
def pytest_configure(config):
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is not None:
        # 是 worker 进程，不要清空目录
        return
    # 只有主进程才清空
    clean_allure_dir()
```

### pytest_sessionfinish 在每个 worker 中独立执行

同理，`pytest_sessionfinish` 在每个 worker 也都执行一次。

```python
@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    
    # 每个 worker 保存自己的 flaky 历史
    flaky_detector.save_history()  # 每个 worker 的数据是独立的
    
    # 如果想合并统计，需要额外处理
    logger.info(f"[{worker_id}] 会话结束")
```

### 跨 worker 共享状态的坑

先看反面教材：

```python
# 错误的做法 — 全局变量不共享
_test_results = []  # 全局列表

@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        _test_results.append({
            "nodeid": report.nodeid,
            "outcome": report.outcome,
        })

@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    # 这里的 _test_results 只包含当前 worker 的数据
    # 其他 worker 的数据看不到
    print(f"结果数量: {len(_test_results)}")  # 只有 1/4 的数据！
```

**解决方案有三种：**

#### 方案 1：文件持久化（最简单，适合测试报告、flaky 历史）

```python
import json
from pathlib import Path

@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
        # 每个 worker 写入自己的结果文件
        result = {
            "nodeid": report.nodeid,
            "outcome": report.outcome,
            "duration": report.duration,
            "worker": worker_id,
        }
        result_file = Path(f"reports/results_{worker_id}.jsonl")
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, "a") as f:
            f.write(json.dumps(result) + "\n")

@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    if worker_id != "master":
        return  # 只有主进程做合并
    
    # 主进程读取所有 worker 的结果
    all_results = []
    for f in Path("reports/").glob("results_*.jsonl"):
        with open(f) as fh:
            for line in fh:
                all_results.append(json.loads(line))
    
    # 现在 all_results 包含所有 worker 的数据
    print(f"总结果: {len(all_results)}")
```

flaky_detector 就是这么干的——每个 worker 往同一个 `flaky_history.json` 文件追加数据，`pytest_sessionfinish` 时读取合并。

#### 方案 2：Redis / 共享缓存（适合实时共享状态）

```python
import redis

r = redis.Redis(host="localhost", port=6379, db=0)

@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    if report.when == "call":
        # 实时写入 Redis
        r.rpush("test:results", json.dumps({
            "nodeid": report.nodeid,
            "outcome": report.outcome,
        }))
        # 原子计数器
        r.incr(f"test:count:{report.outcome}")
```

**优点**：实时，跨进程，不会丢失。  
**缺点**：多了 Redis 依赖，不适合所有团队。

#### 方案 3：wait/poll 机制（主进程等待所有 worker 完成）

这个方案稍微复杂一点。xdist 本身会在所有 worker 完成后才调用主进程的 `pytest_sessionfinish`，但如果你需要在**执行过程中**汇总数据，可以用文件锁或者命名管道。

```python
import fcntl
import json

def safe_append_to_shared_file(file_path, data):
    """带文件锁的追加写入，防止多个 worker 同时写冲突"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # 加锁
        try:
            f.write(json.dumps(data) + "\n")
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)  # 解锁
```

**我们的自愈系统选择了方案 1（文件持久化）**，原因很简单：
1. flaky 历史本身就是持久化数据，写到文件是天然的需求
2. Redis 增加了运维成本，不是所有测试环境都有 Redis
3. 文件锁的方案虽然没有 Redis 优雅，但对于测试报告级别的并发量完全够用

---

## 自愈系统中的 hook 协作 — 5 个模块的数据流

现在我们把所有知识串起来，看看自愈系统的 5 个模块是怎么通过 hook 串联的。

### 模块一览

| 模块 | 文件 | 职责 |
|------|------|------|
| 智能重试引擎 | `self_healing/retry_engine.py` | 条件重试、指数退避 |
| 失败诊断 | `self_healing/diagnostic.py` | 错误分类、根因分析 |
| 现场收集器 | `self_healing/scene_collector.py` | 截图、日志、响应体 |
| Flaky 检测器 | `self_healing/flaky_detector.py` | 历史记录、flaky 判断 |
| 健康检查器 | `self_healing/health_checker.py` | 环境预检 |

### hook 数据流

```
pytest 启动
  │
  ▼
pytest_configure ───> HealthChecker.run_all_checks()
  │                      ├── ping 服务端口
  │                      ├── 检查依赖命令
  │                      └── 不通过 → pytest.exit()
  │
  ▼
pytest_sessionstart ───> 清空 Allure 目录（主进程）
  │
  ▼
每个测试用例执行：
  │
  ├── pytest_runtest_makereport (tryfirst=True, hookwrapper=True)
  │     │
  │     ├── yield 前：无操作
  │     │
  │     ├── yield 后（用例执行完）：
  │     │     ├── setattr(item, f"rep_{rep.when}", rep)   ← 通用
  │     │     ├── classify_failure(rep)                    ← Diagnostic
  │     │     ├── extract_root_cause(rep)                  ← Diagnostic
  │     │     ├── scene_collector.collect(...)             ← SceneCollector
  │     │     ├── scene_collector.attach_to_allure(...)    ← SceneCollector (Allure)
  │     │     └── flaky_detector.record_result(...)         ← FlakyDetector
  │     │
  │     └── 失败时输出诊断信息:
  │           "失败分类: timeout"
  │           "   根因: Connection timed out"
  │           "   建议: 检查网络..."
  │
  ├── pytest_runtest_logreport (trylast=True)
  │     └── record_result(nodeid, outcome)   ← FlakyDetector
  │     └── record_attempt(nodeid, ...)      ← RetryTracker
  │
  └── fixture（自动截图）
        └── if request.node.rep_call.failed:
              → take_screenshot(driver)
  │
  ▼
pytest_sessionfinish (tryfirst=True)
  │
  ├── flaky_detector.save_history()       ← 持久化到 JSON 文件
  ├── flaky_detector.save_report()        ← 生成 Markdown 报告
  │
  └── retry_tracker.get_summary()         ← 打印重试统计
        "总用例: 120"
        "重试用例: 15"
        "重试救回: 12"
        "重试后仍失败: 3"
```

### 关键协作点

1. **`pytest_runtest_makereport` 是核心枢纽** — 所有 5 个模块都在这里被调用。失败诊断、现场收集、flaky 记录，全部串在同一个 hook 里。`tryfirst=True` 保证这里先执行完，后面的 fixture 才能读到 `rep_call`。

2. **`pytest_runtest_logreport` 做兜底记录** — 无论 pass/fail/skip，都记录到 flaky 检测器和重试跟踪器。`trylast=True` 保证所有其他 hook 都跑完了它再跑。

3. **`pytest_sessionfinish` 做持久化和报告** — 每个 worker 独立调用。flaky 历史写入 JSON 文件，后续读取时自动合并所有 worker 的数据。

4. **文件是跨 worker 的桥梁** — worker 各自写 `flaky_history.json`，主进程在 `sessionfinish` 时读取合并。

---

## 总结与思考

这一节的核心就三件事：

1. **hookwrapper 是洋葱模型** — yield 前是前处理，yield 后是后处理，多个 hookwrapper 嵌套执行。最外层最先进入、最后退出。

2. **hook 优先级：目录层级 > tryfirst/trylast** — 子目录 conftest 的 hook 永远比根目录优先执行。tryfirst/trylast 只在同级 conftest 中生效。

3. **xdist 下 hook 在独立进程执行** — 不能用全局变量共享状态。用文件持久化、Redis、或带锁的共享文件来解决。

**思考题**：
- 你在项目里有没有碰到过"单进程没问题，多进程就乱"的情况？是怎么排查和解决的？
- 如果让你设计一个跨 worker 的"测试进度共享"方案（A worker 跑完了告诉其他人），你会怎么实现？

---

## 面试题模块

### 1. hookwrapper 机制

**Q1：`hookwrapper=True` 和普通 hook 有什么区别？**

A：普通 hook 只接收参数执行逻辑。hookwrapper 用 `yield` 把函数分成"前处理"和"后处理"两段——`yield` 之前在前，`yield` 之后在后。中间插入原始 hook 逻辑。yield 返回一个 `outcome` 对象，通过 `outcome.get_result()` 获取执行结果。

**Q2：多个 hookwrapper 同时注册同一个 hook，执行顺序是什么？**

A：洋葱模型。最外层的 hookwrapper 最先执行前处理代码（进入洋葱），最后执行后处理代码（退出洋葱）。目录层级越远的 conftest 越外层，子目录的 conftest 越内层。

### 2. 优先级控制

**Q3：`tryfirst=True` 和 `trylast=True` 什么情况下不生效？**

A：跨 conftest 目录层级时。子目录 conftest 的 hook 永远在根目录之前执行，不管有没有 tryfirst/trylast。因为目录层级的优先级高于 tryfirst/trylast。tryfirst/trylast 只在同一个 conftest 层级内的同类 hook 之间有效。

### 3. xdist 和 hook

**Q4：xdist 模式下，pytest 的 hook 有什么特殊行为？**

A：每个 worker 是独立进程，hook 在每个 worker 中独立执行。具体来说：
- `pytest_configure` 在主进程和每个 worker 中都执行一次
- `pytest_sessionfinish` 在每个 worker 中都执行一次
- 全局变量不跨 worker 共享

**Q5：xdist 下如何汇总各个 worker 的测试结果？**

A：三种方案：
1. **文件持久化** — 每个 worker 写入各自文件，主进程读取合并（最简单）
2. **Redis** — 各个 worker 写入 Redis，实时共享（需依赖）
3. **文件锁** — 带 `fcntl.flock` 的共享文件写入（避免并发写冲突）

### 4. hook 实战

**Q6：你在项目中遇到过 hook 执行顺序导致的 bug 吗？怎么解决的？**

A：（开放题，参考文章开头的例子）hook 执行顺序问题多出现在"多个 conftest 写同一个 hook"或"hook 和 fixture 配合"的场景。解决方法是：明确每个 hook 的职责边界，尽量只在根 conftest 定义关键 hook，子 conftest 只做扩展。必要时加日志输出确认执行顺序。

---

