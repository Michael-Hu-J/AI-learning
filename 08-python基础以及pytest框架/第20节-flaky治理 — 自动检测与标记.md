# 20-flaky 治理 — 自动检测与标记

> 对应代码：`test/self_healing/flaky_detector.py`、`test/conftest.py`（集成部分）

---

先说个真实经历。

前年我带一个中大型项目，CI 上有个测试用例——`test_order_flow`——经常"跳"。

怎么说呢？你今天触发构建，它绿了。明天什么都没改，它红了。你再 rerun 一次，又绿了。你以为修好了，第三天它又红了。

团队里三个测试轮流排查了三天。有人怀疑是数据库并发写入冲突，有人觉得是订单号重复生成，还有人说是 CI 节点的时钟不同步。最后发现：**是一个毫秒级的时间戳拼接逻辑——某次生成唯一订单号时，恰好两次调用落入了同一毫秒，导致唯一性约束冲突。**

三天，三个人，就为了一个"时红时绿"的问题。

这就是 flaky 测试的典型症状——**它不总是失败，但也从来不总是成功。它就像测试界的幽灵，来无影去无踪，每次出现都让你怀疑人生。**

今天我们就来聊聊怎么系统性地治理 flaky 测试：自动检测、自动标记、自动出报告。

---

## 概念讲解

### 什么是 flaky 测试？

**Flaky 测试**指的是同一个测试用例，在代码和环境完全不变的情况下，多次执行得到不一致的结果——有时候过，有时候不过。

大白话就是：**这个测试"神经质"。**

```python
# 典型 flaky 测试
def test_create_order():
    order_id = generate_order_id()  # 依赖毫秒级时间戳
    result = create_order(order_id)
    assert result["status"] == "success"  # 有时唯一性冲突就失败
    # 第1次跑：通过
    # 第2次跑：失败（同一毫秒，id 冲突）
    # 第3次跑：通过（毫秒变了）
```

注意区分 flaky 和"不稳定环境"导致的失败：

| 类型 | 表现 | 根因 |
|------|------|------|
| 环境抖动 | 整个套件都挂 | 网络、服务不可用 |
| Flaky 测试 | 个别用例时红时绿 | 代码设计问题 |
| 真实 bug | 稳定失败 | 逻辑有缺陷 |

**Flaky 测试最大的迷惑性在于：它看起来像环境问题（偶尔挂），但根因在代码本身。**

### flaky 测试的危害

#### 1. 浪费排查时间

刚才那个例子三天排查不说。就算只花半小时，乘以团队人数和频率，时间成本惊人。每个 flaky 测试平均需要 **2-4 小时**才能定位根因，而且很多最终不了了之。

#### 2. 降低 CI 信任度

这可能是最严重的后果。当一个 CI 管道经常"无缘无故"变红，团队会逐渐形成条件反射：

- "哦，又红了？rerun 一下就好了。"
- "不用看报告，大概率是 flaky。"
- "那个测试本来就不稳定，忽略它。"

**一旦 CI 失去了"变红就意味着有 bug"的信任，它的存在价值就崩塌了。** 真正的 bug 被淹没在 flaky 的噪声中，可能要几个小时甚至几天才会被发现。

#### 3. 掩盖真实 bug

更可怕的是：一个 flaky 测试被忽略惯了，某天它真的报了一个 bug，大家也以为是 flaky。我亲眼见过一个生产事故——一个支付接口的返回值从 `200` 改成了 `201`，测试报了 `AssertionError`。但因为那个用例之前就偶尔"flaky"，开发看了一眼说"重试一下吧"，结果就跳过去了。两天后线上出了问题才被发现。

---

### flaky 测试的常见原因

#### 1. 共享状态

测试之间共享数据库、文件、全局变量等状态。一个测试改了数据，影响另一个测试的结果。

```python
# 共享状态导致 flaky
test_data = {"count": 0}

def test_increment():
    test_data["count"] += 1  # 并发运行时顺序不确定
    assert test_data["count"] == 1  # 有时 1，有时 2
```

#### 2. 时间依赖

依赖系统时间、随机数、毫秒级唯一 ID 生成等。时间戳在毫秒级精度下很容易碰撞。

#### 3. 网络波动

外部请求偶尔超时、连接重置、DNS 解析延迟。这类 flaky 通常可以用重试缓解（参考第17节的条件重试）。

#### 4. 异步操作

等待异步任务完成时，有时快有时慢。如果等待时间固定（如 `time.sleep(3)`），在 CI 负载高时可能不够。

```python
# 异步操作导致 flaky
def test_async_job():
    submit_job()          # 提交异步任务
    time.sleep(3)         # 固定等 3 秒
    result = check_result()
    assert result["status"] == "completed"
    # CI 负载高时：3 秒不够，失败
    # CI 空闲时：3 秒够了，通过
```

---

## FlakyDetector 实现

治理 flaky 的第一步：**量化它**。你连哪些测试是 flaky 都不知道，怎么治理？

`FlakyDetector` 的核心功能就是：记录每次执行结果 → 根据历史数据判断哪些是 flaky → 自动标记处理。

### record_result() — 每次执行记录

每次用例执行完，把结果记录下来：

```python
def record_result(self, nodeid: str, outcome: str):
    """
    记录一个用例的执行结果。
    outcome 取值：'passed', 'failed', 'skipped'
    """
    self._results.append((
        nodeid,
        outcome,
        datetime.now().isoformat(),
    ))
```

这里只做了三件事：谁（nodeid）、什么结果（outcome）、什么时候（timestamp）。这三个字段就够了。

### save_history() / load_history() — 持久化到 JSON

记录在内存里没用——进程一退出就没了。需要持久化到文件，让**跨会话**的历史数据积累下来。

```python
def save_history(self):
    """将本次会话的结果持久化到文件"""
    history_path = Path(self.history_file)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取已有历史
    existing = []
    if history_path.exists():
        try:
            existing = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            existing = []

    # 追加新结果
    existing.extend([
        {"nodeid": r[0], "outcome": r[1], "timestamp": r[2]}
        for r in self._results
    ])

    # 只保留最近 30 天的记录
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    existing = [
        r for r in existing
        if r.get("timestamp", "") >= thirty_days_ago
    ]

    history_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

有几个设计要点：

**追加而非覆盖**：每次保存时读取已有数据再追加，而不是直接写入。这样多轮测试的历史能累加起来。

**30 天自动清理**：flaky 是有"时效性"的。六个月前的 flaky 记录可能早就修好了，留着只会降低准确性。保留 30 天的数据已经足够判断一个测试是否 flaky。

**异常安全**：文件损坏时不会 crash，而是从空列表重新开始。

```python
def load_history(self) -> list:
    """从文件加载历史结果"""
    history_path = Path(self.history_file)
    if not history_path.exists():
        return []
    try:
        return json.loads(history_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        logger.warning(f"flaky 历史文件读取失败: {self.history_file}")
        return []
```

### get_flaky_tests() — 根据历史判断 flaky

核心判断逻辑来了：

```python
def get_flaky_tests(self, min_runs: int = 5,
                    fail_threshold: float = 0.2,
                    pass_threshold: float = 0.95) -> list:
    """
    检测 flaky 测试。

    参数：
    - min_runs: 最少执行次数（小于此数不判断 flaky）
    - fail_threshold: flaky 的失败率下限（低于此值视为稳定通过）
    - pass_threshold: pass 率低于此值视为稳定失败

    返回 flaky 用例列表：[{nodeid, pass_rate, total_runs, failed_runs, ...}]
    """
    history = self.load_history()

    # 按用例聚合
    stats = defaultdict(lambda: {"pass": 0, "fail": 0, "skip": 0, "total": 0})
    for record in history:
        nodeid = record["nodeid"]
        outcome = record["outcome"]
        stats[nodeid]["total"] += 1
        if outcome == "passed":
            stats[nodeid]["pass"] += 1
        elif outcome == "failed":
            stats[nodeid]["fail"] += 1
        else:
            stats[nodeid]["skip"] += 1

    # 判断 flaky
    flaky_tests = []
    for nodeid, s in stats.items():
        if s["total"] < min_runs:
            continue
        pass_rate = s["pass"] / s["total"] if s["total"] > 0 else 0

        # flaky 判断：既不是稳定通过也不是稳定失败
        is_flaky = pass_threshold > pass_rate > fail_threshold

        if is_flaky:
            flaky_tests.append({
                "nodeid": nodeid,
                "pass_rate": round(pass_rate, 2),
                "total_runs": s["total"],
                "passed_runs": s["pass"],
                "failed_runs": s["fail"],
                "skipped_runs": s["skip"],
            })

    # 按失败率降序排列
    flaky_tests.sort(key=lambda x: x["pass_rate"])
    return flaky_tests
```

**判断逻辑详解：**

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `min_runs` | 5 | 至少要跑 5 次才有统计意义。只跑了两三次就判断 flaky，样本太小不靠谱 |
| `fail_threshold` | 0.2 | 失败率低于 20%，视为稳定通过 |
| `pass_threshold` | 0.95 | 通过率低于 95%（即失败率高于 5%），视为 flaky |

**实际判断就是一句话**：一个用例跑满了 `min_runs` 次，它的通过率在 `fail_threshold` 和 `pass_threshold` 之间——既不是稳定通过（通过率 >= 95%），也不是稳定失败（通过率 <= 20%），那就是 flaky。

举个例子：

| 用例 | 跑了几次 | 通过次数 | 通过率 | 判断结果 |
|------|---------|---------|-------|---------|
| test_a | 10 | 10 | 100% | 稳定通过 |
| test_b | 10 | 1 | 10% | 稳定失败（这是 bug） |
| test_c | 10 | 7 | 70% | flaky |
| test_d | 3 | 2 | 67% | 跑满 5 次再说 |
| test_e | 10 | 9 | 90% | flaky（通过率 90%，在 20%-95% 之间）|

---

### 踩坑记录

> 第一次写 `get_flaky_tests` 的时候，我忘记对历史记录按 nodeid 聚合了。结果同一个用例的历史记录被当成 N 个独立记录，每个的记录都可能不完整。后来发现 flaky 判断全是错的——因为每个记录只有一两条数据，全都因为"样本不足"被跳过了。
>
> **一定要先聚合（`defaultdict`），再判断。**

---

## flaky 标记策略

检测到 flaky 之后怎么办？不能让它继续"污染" CI 结果。

### 自动标记为 xfail(strict=False)

pytest 提供了一个绝佳的机制：**`xfail` 标记**。

```python
pytest.mark.xfail(reason="flaky: 通过率不稳定", strict=False)
```

加上这个标记后，这个用例即使失败，pytest 也不会将其计为"失败"，而是计为"预期失败（xfailed）"。`strict=False` 意味着：通过了算惊喜，失败了不扣分。

```python
def mark_skipped_flaky(self, nodeid: str, session) -> bool:
    """
    将 flaky 测试标记为 xfail（预期失败）。
    返回 True 表示标记成功。
    """
    try:
        # 尝试找到该用例并标记
        for item in session.items:
            if item.nodeid == nodeid:
                item.add_marker(pytest.mark.xfail(
                    reason="flaky: 通过率不稳定",
                    strict=False,
                ))
                logger.info(f"已将 flaky 用例标记为 xfail: {nodeid}")
                return True
    except Exception as e:
        logger.warning(f"标记 flaky 用例失败: {e}")
    return False
```

### 标记后不阻塞 CI

核心价值就在这里：**一个已知的 flaky 测试不应该阻塞整个 CI 管道。**

`xfail(strict=False)` 的效果：

| 场景 | 结果 | CI 是否阻塞 |
|------|------|------------|
| Flaky 测试这次过了 | xpassed（意外通过） | 不阻塞 |
| Flaky 测试这次失败了 | xfailed（预期失败） | 不阻塞 |
| 稳定测试失败了 | failed | 阻塞 |
| Flaky 测试通过了但被标注 | 算通过 | 不阻塞 |

说白了就是：**把 flaky 降级了。** 它不再是"一等公民"的失败，而是被标记为"已知问题"，不影响 CI 的绿/红灯判断。

### 需要人工确认后再修复

标记只是临时措施，不是终点。标记的目的有两个：

1. **止损**——立刻不让 flaky 影响 CI
2. **留痕**——为后续修复提供数据

建议的修复流程：

```
检测 flaky → 自动标记 xfail → 生成报告
    ↓
轮值测试查看报告 ← 每周一次
    ↓
确认根因 → 修复 → 移除 xfail 标记
    ↓
如果无法修复 → 继续标记，下个迭代再评估
```

**千万不要标记了就不管了。** 我见过有些团队的 flaky 列表越来越长，最后几百个用例全是 xfail，等于把整个测试套件废了。

---

## Flaky 报告

光检测和标记还不够——你需要**一个报告来驱动治理**。

### generate_report() — 生成 Markdown 报告

```python
def generate_report(self) -> str:
    """生成 flaky 报告 Markdown 文本"""
    flaky_tests = self.get_flaky_tests()

    if not flaky_tests:
        return "# Flaky 检测报告\n\n未检测到 flaky 测试用例，所有用例运行稳定。\n"

    lines = [
        "# Flaky 检测报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"检测到 **{len(flaky_tests)}** 个 flaky 测试用例。",
        "",
        "| 用例名称 | 通过率 | 总执行次数 | 通过 | 失败 |",
        "|---------|--------|-----------|------|------|",
    ]

    for t in flaky_tests:
        lines.append(
            f"| {t['nodeid'][:60]} | {t['pass_rate']:.0%} "
            f"| {t['total_runs']} | {t['passed_runs']} | {t['failed_runs']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "**建议**：",
        "- 通过率在 50-80% 之间的用例优先排查",
        "- 检查是否有共享状态导致的不稳定",
        "- 考虑添加显式等待或重试机制",
    ])

    return "\n".join(lines)
```

报告结构很直观：

```
# Flaky 检测报告

生成时间：2026-05-14 11:07
检测到 **6** 个 flaky 测试用例。

| 用例名称 | 通过率 | 总执行次数 | 通过 | 失败 |
|---------|--------|-----------|------|------|
| tests/test_order.py::test_create_order | 70% | 10 | 7 | 3 |
| tests/test_api.py::test_user_login | 85% | 20 | 17 | 3 |
| tests/test_async.py::test_job_status | 60% | 15 | 9 | 6 |
| tests/test_db.py::test_unique_constraint | 40% | 5 | 2 | 3 |

---

**建议**：
- 通过率在 50-80% 之间的用例优先排查
- 检查是否有共享状态导致的不稳定
- 考虑添加显式等待或重试机制
```

### 按通过率排序，优先排查通过率低的

注意报告中的排序方式：`flaky_tests.sort(key=lambda x: x["pass_rate"])` 是按通过率**升序**排列。

通过率最低的排在最前面——这些是"最 flaky"的用例。比如通过率 40% 的那个，5 次里失败 3 次，波动非常大，应该优先排查。

通过率 85% 的虽然也是 flaky，但相对稳定，可以排在后面。

**这个排序的意义**：给团队一个明确的"优先级"——从最不稳定的开始修，收益最高。

### 保存到文件

```python
def save_report(self, output_path: str = "reports/flaky_report.md"):
    """保存 flaky 报告到文件"""
    report = self.generate_report()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    logger.info(f"Flaky 报告已生成: {output_path}")
```

报告生成在 `reports/flaky_report.md`，可以直接在 CI 的 artifacts 里查看，或者定期发到团队群里。

---

## Hook 集成

最后一步：把 `FlakyDetector` 接入 pytest 的生命周期。

### 在 pytest_runtest_logreport 中记录

`pytest_runtest_logreport` 这个 hook 在每个用例的每个阶段（setup/call/teardown）都会触发。我们只关注 `call` 阶段（"1. 测试被调用了、执行了"）的结果：

```python
@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    """记录所有结果（pass/fail/skip）到 flaky 检测器"""
    if report.when == "call":
        # 记录到 flaky 检测器
        flaky_detector.record_result(report.nodeid, report.outcome)
```

为什么不直接用 `pytest_runtest_makereport`？因为那个 hook 是在**报告生成时**触发的，而 `pytest_runtest_logreport` 是在**报告被记录后**触发，更适合做"记录型"的工作。

注意这里记录的是所有结果（pass 和 fail 都记），因为 flaky 的判断需要完整的执行历史。

### 在 pytest_sessionfinish 中保存和生成报告

测试会话结束时，做两件事：保存历史数据到文件、生成 flaky 报告。

```python
@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后持久化 flaky 历史和生成报告"""
    # 保存 flaky 历史
    try:
        flaky_detector.save_history()
    except Exception as e:
        logger.debug(f"保存 flaky 历史失败: {e}")

    # 生成 flaky 报告
    try:
        flaky_detector.save_report()
    except Exception as e:
        logger.debug(f"生成 flaky 报告失败: {e}")
```

两个操作都用 `try/except` 包裹——**保存失败不应该影响测试结果本身**。

### 完整的数据流

```
每次用例执行完成
  ↓
pytest_runtest_logreport hook
  ↓
flaky_detector.record_result(nodeid, outcome)  ← 记录到内存
  ↓
... 多次运行（跨多轮 CI）...
  ↓
pytest_sessionfinish hook
  ↓
save_history() → 持久化到 JSON 文件（追加 + 30天清理）
  ↓
generate_report() → 判断 flaky → 生成 Markdown 报告
  ↓
save_report() → 写入 reports/flaky_report.md
```

---

## 总结与思考

Flaky 测试是自动化测试中最烦人的问题之一，但你不可能手工追踪——因为数据量太大，人工根本盯不过来。

**一条龙治理方案**：

1. **记录**：每次执行都记录结果，积累历史数据
2. **检测**：用通过率 + 最小样本数判断哪些是 flaky
3. **标记**：自动标记为 `xfail(strict=False)`，不阻塞 CI
4. **报告**：生成定期报告，驱动人工修复
5. **修复**：找到根因，彻底解决，移除标记

**核心原则**：

1. **先量化，后治理**——没有数据，你都不知道哪些测试在"捣乱"
2. **标记不是终点**——xfail 只是止损，修复才是目的
3. **样本要充分**——跑个两三次就判断 flaky？不靠谱，至少 5 次起步
4. **时效性**——30 天前的 flaky 可能已修复，定期清理历史数据

**思考题**：你的项目里，如果今天开始记录所有用例的执行历史，一个月后打开 flaky 报告，你觉得会有多少个 flaky 测试？里面有多少是你早就"凭感觉"知道的，又有多少是"你没想到它居然不稳定"的？

---

## 面试题模块

### 1. Flaky 概念

**Q1：什么是 flaky 测试？它和环境不稳定导致的失败有什么区别？**

A：Flaky 测试是指同一个测试在代码和环境不变的情况下，多次执行得到不同的结果（时过时不过）。它与环境不稳定导致的失败的区别在于：环境问题通常影响整个套件（所有测试都失败），而 flaky 只影响个别测试，且根因在代码设计本身（如共享状态、时间依赖、异步等待不足）。环境抖动通过重试可以解决，flaky 需要修改代码逻辑。

### 2. Flaky 检测算法

**Q2：如何设计一个 flaky 检测算法？核心参数有哪些？**

A：核心思路是：积累历史执行数据 → 按用例聚合计算通过率 → 根据阈值判断。

核心参数三个：
- `min_runs`（最少执行次数）：默认 5，样本不足时不判断
- `fail_threshold`（失败率下限）：默认 0.2，通过率低于 20% 视为稳定失败（可能是 bug）
- `pass_threshold`（通过率上限）：默认 0.95，通过率高于 95% 视为稳定通过

判断条件：`pass_threshold > pass_rate > fail_threshold`，在此范围内的视为 flaky。

### 3. Flaky 标记策略

**Q3：检测到 flaky 后应该怎么处理？为什么用 `xfail(strict=False)` 而不是 skip？**

A：检测到 flaky 后自动标记为 `xfail(strict=False)`。理由是：
- `xfail` 表示"预期失败"——我们知道这个测试不稳定，但不希望它阻塞 CI
- `strict=False` 意味着：通过就是惊喜，失败也不扣分
- 不用 `skip` 是因为 skip 会跳过执行，而 flaky 测试仍需要继续执行以积累更多数据（也许下个月就修好了）

标记只是临时手段，目的是止损 + 留痕。需要配合定期报告，由人工确认根因后真正修复。

### 4. 报告设计

**Q4：Flaky 报告应该包含哪些信息？数据怎么组织对排查最有帮助？**

A：报告应包含：生成时间、flaky 用例总数、每个用例的通过率/执行次数/通过次数/失败次数。数据按通过率升序排列（通过率最低的排在最前面），这样团队能优先排查最不稳定的用例。

有价值的额外信息：通过率在 50-80% 之间的用例是"高优先级"，因为这些测试的不确定性最大，对 CI 的干扰最强。
