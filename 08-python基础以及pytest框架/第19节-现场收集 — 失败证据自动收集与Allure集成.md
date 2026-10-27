# 19-现场收集 — 失败证据自动收集与 Allure 集成

> 对应代码：`test/self_healing/scene_collector.py`（SceneCollector 类）、`test/conftest.py`（失败时自动调用收集）

---

## 概念讲解

有一次，测试跑了 8 小时，生产环境出了事故，所有人急着翻测试报告。

QA 问："谁有截图？"

沉默。

"那日志呢？有谁存了日志？"

还是沉默。

"至少告诉我请求参数是什么吧？"

所有人都知道测试跑了、红了，但没有任何现场证据。等于白跑。

**失败的痛苦不在于失败本身，而在于失败后你没有任何信息可以排查。**

手动收集现场的问题：

| 方式 | 问题 |
|------|------|
| 用人盯着跑 | 人不可能 24 小时盯着 |
| 跑完后手动截图 | 已经错过了，driver 都 quit 了 |
| 看控制台输出 | 被截断了，看不到完整的错误信息 |

解决方案？**自动收集**。失败瞬间自动截全：截图、日志、响应体，全部附加到 Allure 报告。排查人员打开报告就能看到一切。

---

## 现场收集到底要收集什么

很多人的第一反应是"截图就够了"。截图确实有用，但远远不够：

**1. 截图** — 页面在失败时的状态。UI 自动化必备。

**2. 日志** — 测试执行过程中的 debug 信息。能回答"之前做了什么操作"。

**3. 请求/响应体** — API 测试中，能回答"刚才发了什么请求，服务器返回了什么"。很多时候截图看不出问题，但一看响应体就发现状态码是 500。

**4. 系统状态** — CPU、内存、网络延迟（高级选项，通常只在性能测试中需要）。

我们的 SceneCollector 前三个是标配，第四个按需添加。

---

## SceneCollector 实现

先看核心接口：

```python
from self_healing.scene_collector import scene_collector

# 失败时调用
collected = scene_collector.collect(
    nodeid="test_login.py::test_login_success",
    driver=driver,           # 移动端/浏览器 driver（用于截图）
    response='{"code":500}', # 响应体
    extra_logs='...',        # 调试日志
    category="timeout",      # 失败分类
)
```

### collect() 做了什么

它做了 4 件事：

1. 生成场景目录名（`test_login_test_login_success_143022/` — 用例名_时间戳）
2. 截图（如果提供了 driver）
3. 保存响应体（如果提供了 response）
4. 保存日志（如果提供了 extra_logs）

### 场景目录结构

```
reports/scenes/
  test_login_test_login_success_143022/
    failure.png       # 截图
    response.txt      # 响应体
    debug.log         # 日志
  test_api_user_143110/
    failure.png
    response.txt
    debug.log
```

**为什么按用例分目录？** 因为 CI 中多个失败用例同步收集，如果不分开会互相覆盖。

### _take_screenshot — 自动截图

```python
def _take_screenshot(self, driver, scene_dir, nodeid):
    try:
        screenshot_path = str(scene_dir / "failure.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"失败截图已保存: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.warning(f"截图失败: {e}")
        return None
```

**截图失败时不会中断收集**。driver 可能已经 quit 了，这种情况很常见。吞掉异常，继续收集其他证据。

---

## Allure 集成

截图和日志存在文件系统里还不够——排查人员还得自己找文件。**把证据附加到 Allure 报告，打开 Allure 就能看到一切。**

```python
def attach_to_allure(self, collected, nodeid):
    """将收集的证据附加到 Allure 报告"""
    try:
        import allure
        for file_type, file_path in collected.get("files", []):
            if file_type == "screenshot" and os.path.exists(file_path):
                allure.attach.file(
                    file_path,
                    name=f"失败截图 - {nodeid}",
                    attachment_type=allure.attachment_type.PNG,
                )
            elif file_type == "response" and os.path.exists(file_path):
                content = Path(file_path).read_text(encoding="utf-8")
                allure.attach(
                    content,
                    name=f"响应体 - {nodeid}",
                    attachment_type=allure.attachment_type.TEXT,
                )
    except ImportError:
        logger.debug("未安装 allure-pytest，跳过 Allure 附件")
```

**关键设计**：

- 用 `try/except` 包裹 `import allure`，没装 allure 时不报错
- 截图用 `allure.attach.file`（附加文件），响应体用 `allure.attach`（附加文本）
- 检查文件是否真的存在再附加，避免 Allure 报告里出现"无法找到文件"的空白附件

---

## Hook 集成

在 `pytest_runtest_makereport` 中自动触发收集：

```python
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

    # 只在 call 阶段处理失败收集
    if rep.when == "call" and rep.failed:
        nodeid = item.nodeid

        # 失败分类诊断（第 19 节的内容）
        category = classify_failure(rep)

        # 获取 driver（如果有）
        driver_instance = None
        try:
            if "driver" in item.funcargs:
                driver_instance = item.funcargs["driver"]
        except Exception:
            pass

        # 收集现场
        collected = scene_collector.collect(
            nodeid=nodeid,
            driver=driver_instance,
            category=category,
        )

        # 附加到 Allure
        scene_collector.attach_to_allure(collected, nodeid)
```

**注意只处理 `rep.when == "call"`**。setup 和 teardown 阶段失败不收集（通常是 fixture 启动失败，driver 还没初始化，截图也没意义）。

---

## 踩坑记录

### 坑 1：截图时 driver 已经 quit

这是最常遇到的。有些 fixture 在 teardown 中先 quit 了 driver，然后才发现测试失败了。这时候 driver.save_screenshot() 会抛异常。

**解决方法**：在 `_take_screenshot` 中用 try/except 包裹，截图失败不影响其他证据收集。

```python
try:
    driver.save_screenshot(screenshot_path)
except Exception:
    pass  # driver 可能已经 quit 了，不阻塞收集
```

### 坑 2：响应体包含敏感信息

保存响应体时，注意可能包含密码、token、身份证号等敏感信息。如果 Allure 报告要对外分享，需要做脱敏处理。

**建议**：在 `_save_response` 中加入简单的脱敏逻辑：

```python
def _mask_sensitive(self, text):
    """脱敏处理"""
    text = re.sub(r'"password":\s*"[^"]*"', '"password": "***"', text)
    text = re.sub(r'"token":\s*"[^"]*"', '"token": "***"', text)
    return text
```

### 坑 3：日志文件太大

如果一个用例跑了几千行日志，加上截图和响应体，一次失败可能产生几 MB 的现场数据。100 个失败用例就是几百 MB。

**建议**：
- 日志只保留最后 100 行（大多数情况下，失败时的上下文就够了）
- 定期清理 `reports/scenes/` 目录（超过 7 天的可以删掉）
- `.gitignore` 中加入 `reports/scenes/`

---

## 总结与思考

> 现场收集是最简单也最容易被忽视的自动化环节。截图 + 日志 + 响应体，三件套齐了，排查效率提升 80%。

**思考题**：你在排查失败测试时，最常缺什么信息？是截图、日志、还是请求参数？如果用自动收集能节省你多少时间？

---

## 面试题模块

### 1. 现场收集

**Q：失败现场收集一般收集哪些信息？为什么？**

A：三类：截图（页面状态）、日志（操作过程）、响应体（API 交互）。这三类信息相互补充，截图看表象，日志看过程，响应体看数据。缺任何一类，排查时都可能需要反复跑测试重现场景。

### 2. 收集时机

**Q：在 pytest 的哪个阶段收集现场证据？为什么不是所有阶段都收集？**

A：在 `pytest_runtest_makereport` 的 call 阶段。setup 阶段 driver 可能还没初始化，截图无意义；teardown 阶段 driver 可能已经 quit。只有在 call 阶段（测试函数执行时），driver 才处于可用状态。同时，只失败时收集（`report.failed`），通过时收集浪费 IO。

### 3. Allure 附件

**Q：怎么把截图和日志附加到 Allure 报告？**

A：用 `allure.attach.file()` 附加文件（截图），用 `allure.attach()` 附加文本（日志/响应体）。注意用 try/except 包裹，因为不是所有项目都装了 allure-pytest。截图类型用 `allure.attachment_type.PNG`，文本用 `allure.attachment_type.TEXT`。

### 4. 异常处理

**Q：截图失败会中断整个现场收集吗？应该怎么处理？**

A：不应该中断。截图失败常见原因（driver 已 quit、WebDriver 连接断开）不影响其他证据（日志、响应体）的收集。用 try/except 包裹每个证据收集步骤，单个失败不影响其他步骤。
