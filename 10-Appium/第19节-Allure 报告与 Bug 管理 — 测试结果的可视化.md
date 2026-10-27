# 第19节-Allure 报告与 Bug 管理 — 测试结果的可视化

> **对应代码**：`utils/allure_helper.py`、`utils/bug_reporter.py`、`utils/bug_allure_helper.py`
>
> **说明**：本节代码来自一个真实的移动端自动化测试项目，已做模糊化处理，可直接复用。

---

## 1. 为什么需要报告体系？

测试跑完之后，终端输出了一堆 `PASS` / `FAIL`。但——

- **产品经理**想知道哪些功能崩了
- **开发**需要精确的错误信息和截图
- **老板**只看通过率百分比

终端文本满足不了这些需求。你需要一套 **分级报告体系**：

| 报告类型 | 面向角色 | 用途 |
|---|---|---|
| **Allure 报告** | 测试 / 开发 | 可视化展示，含截图、步骤、层级分类 |
| **Bug 清单报告** | 开发 / PM | Markdown / JSON 格式，列明每条失败详情 |
| **执行概览报告** | 管理者 | 通过率 / 失败率一张表 |

原项目实现了上述三层体系。下面逐一拆分。

---

## 2. AllureHelper — 附件的统一封装

Allure 原生支持图片、文本、JSON、HTML 等附件类型。每次手动调 `allure.attach` 容易写散，封装一个工具类集中处理。

**代码**：`utils/allure_helper.py`

```python
import json
import allure
from loguru import logger


class AllureHelper:
    """Allure 报告辅助工具类，提供静态方法高效附加各类附件。"""

    @staticmethod
    def attach_screenshot(driver, name: str = "截图") -> None:
        """附加当前页面截图到 Allure 报告。"""
        try:
            screenshot = driver.get_screenshot_as_png()
            allure.attach(
                screenshot,
                name=name,
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as e:
            logger.warning(f"附加截图失败: {e}")

    @staticmethod
    def attach_text(text: str, name: str = "文本") -> None:
        """附加纯文本到 Allure 报告。"""
        allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)

    @staticmethod
    def attach_json(data: dict | list, name: str = "JSON") -> None:
        """附加 JSON 数据到 Allure 报告（自动美化格式）。"""
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        allure.attach(
            formatted,
            name=name,
            attachment_type=allure.attachment_type.JSON,
        )

    @staticmethod
    def attach_html(html: str, name: str = "HTML") -> None:
        """附加 HTML 片段到 Allure 报告。"""
        allure.attach(html, name=name, attachment_type=allure.attachment_type.HTML)
```

### 关键设计

- **静态方法**：无需实例化，`AllureHelper.attach_screenshot(driver)` 一行调用
- **异常保护**：`attach_screenshot` 捕获 WebDriver 异常，不影响用例继续执行
- **类型明确**：每个方法对应一种 Allure attachment_type，方便后续扩展

---

## 3. BugReporter — 自动记录 + 多格式导出

失败的用例不能只活在终端日志里。`BugReporter` 负责：

1. 记录每条失败用例的上下文（错误信息、截图路径、环境等）
2. 在测试会话结束时导出为 **Markdown** 和 **JSON** 格式
3. 生成 **执行概览报告**（通过率、失败率统计）

**代码**：`utils/bug_reporter.py`

```python
import os, json
from datetime import datetime
from typing import Optional
from loguru import logger


class BugReporter:
    """Bug 报告工具，单例模式。"""

    _instance: Optional["BugReporter"] = None

    def __new__(cls) -> "BugReporter":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.bugs = []
        return cls._instance

    def record_failure(
        self,
        test_name: str,
        error_message: str,
        screenshot_path: Optional[str] = None,
        api_request: Optional[dict] = None,
        api_response: Optional[dict] = None,
        test_steps: Optional[list] = None,
        environment: Optional[dict] = None,
    ) -> None:
        """记录一条失败用例的 Bug 信息。"""
        bug = {
            "test_name": test_name,
            "error_message": error_message[:500],
            "screenshot_path": screenshot_path,
            "api_request": api_request,
            "api_response": api_response,
            "test_steps": test_steps or [],
            "environment": environment or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.bugs.append(bug)

    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式的 Bug 清单报告。"""
        if not self.bugs:
            return ""
        lines = ["# Bug 清单报告\n"]
        lines.append(f"**失败用例数**: {len(self.bugs)}\n---\n")
        for idx, bug in enumerate(self.bugs, 1):
            lines.append(f"## Bug #{idx}: {bug['test_name']}\n")
            lines.append(f"- **错误信息**: {bug['error_message']}\n")
            if bug.get("screenshot_path"):
                lines.append(f"- **截图**: `{bug['screenshot_path']}`\n")
            if bug.get("environment"):
                env = bug["environment"]
                lines.append(f"- **环境**: {env.get('platform', '?')} {env.get('device_name', '')}\n")
            lines.append("")
        os.makedirs("reports", exist_ok=True)
        report_path = "reports/bug_list.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return report_path

    def generate_json_report(self) -> str:
        """生成 JSON 格式的 Bug 清单报告。"""
        os.makedirs("reports", exist_ok=True)
        report_path = "reports/bug_list.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({"total": len(self.bugs), "bugs": self.bugs},
                      f, indent=2, ensure_ascii=False)
        return report_path

    def generate_summary_report(self, total: int, passed: int, failed: int) -> str:
        """生成 Markdown 格式的执行概览报告。"""
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        lines = [
            "# 执行概览报告\n",
            f"**总用例**: {total}  |   通过: {passed} ({pass_rate:.1f}%)  "
            f"|   失败: {failed} ({100 - pass_rate:.1f}%)\n",
        ]
        os.makedirs("reports", exist_ok=True)
        report_path = "reports/execution_summary.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
        return report_path

    def clear(self) -> None:
        self.bugs.clear()


# 全局单例获取函数
_reporter_instance: Optional[BugReporter] = None


def get_bug_reporter() -> BugReporter:
    global _reporter_instance
    if _reporter_instance is None:
        _reporter_instance = BugReporter()
    return _reporter_instance
```

### 关键设计

| 设计 | 解释 |
|---|---|
| **单例模式** | `get_bug_reporter()` 保证所有 fixture 和 hook 操作同一个实例 |
| **信息截断** | `error_message[:500]` 防止超大日志撑爆报告文件 |
| **多格式导出** | Markdown 给人读，JSON 给 CI/CD 工具消费 |
| **环境记录** | `environment` 字典记录平台、设备名，方便复现 |

---

## 4. BugAllureHelper — 把 Bug 写入 Allure

光有独立报告不够——开发者查看 Allure 报告时，希望直接看到每个失败用例的错误信息和截图。`BugAllureHelper` 把这些信息**写进 Allure 测试用例的附件里**。

**代码**：`utils/bug_allure_helper.py`

```python
import os, json
import allure
from loguru import logger


class BugAllureHelper:
    """将 Bug 信息附加到当前 Allure 测试用例。"""

    @staticmethod
    def attach_bug_info(
        error_message: str,
        screenshot_path: str | None = None,
        api_request: dict | None = None,
        api_response: dict | None = None,
        test_steps: list[str] | None = None,
    ) -> None:
        """将 Bug 详细信息附加到当前 Allure 测试用例。"""
        # 1. 错误信息
        allure.attach(
            error_message[:2000],
            name="错误信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        # 2. 截图（先检查文件是否存在）
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                allure.attach.file(
                    screenshot_path,
                    name="失败截图",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception as e:
                logger.warning(f"附加截图失败: {e}")

        # 3. API 请求
        if api_request:
            allure.attach(
                json.dumps(api_request, indent=2, ensure_ascii=False),
                name="API 请求",
                attachment_type=allure.attachment_type.JSON,
            )

        # 4. API 响应
        if api_response:
            allure.attach(
                json.dumps(api_response, indent=2, ensure_ascii=False),
                name="API 响应",
                attachment_type=allure.attachment_type.JSON,
            )

        # 5. 执行步骤
        if test_steps:
            steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(test_steps))
            allure.attach(steps_text, name="执行步骤",
                          attachment_type=allure.attachment_type.TEXT)
```

---

## 5. 在 conftest.py 中串联起来

前面的工具类只是积木。真正的"自动化"发生在 `conftest.py` 的 fixture 和 hook 中：

# driver_setup 在第03节定义，此处复用
```python
@pytest.fixture(scope="function")
def driver(request, driver_setup):
    driver = driver_setup
    yield driver

    # ── 用例失败时自动收集信息 ──
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        from utils.screenshot import ScreenshotHelper
        from utils.bug_reporter import get_bug_reporter
        from utils.bug_allure_helper import BugAllureHelper

        # 1 截图
        screenshot_helper = ScreenshotHelper(driver)
        screenshot_path = screenshot_helper.take_screenshot(
            f"failure_{request.node.name}"
        )

        # 2 提取错误信息
        error_message = ""
        if hasattr(request.node.rep_call, "longreprtext"):
            error_message = request.node.rep_call.longreprtext

        # 3 记录到 BugReporter
        bug_reporter = get_bug_reporter()
        bug_reporter.record_failure(
            test_name=request.node.name,
            error_message=error_message[:2000],
            screenshot_path=screenshot_path,
        )

        # 4 附加到 Allure 报告
        BugAllureHelper.attach_bug_info(
            error_message=error_message[:2000],
            screenshot_path=screenshot_path,
        )

### 数据流

```
测试失败
   │
   ▼
fixture 检测 rep_call.failed
   │
   ├─① ScreenshotHelper 截图 → screenshots/failure_xxx.png
   │
   ├─② BugReporter.record_failure() → 存入全局 bugs 列表
   │
   ├─③ BugAllureHelper.attach_bug_info() → 写入 Allure 附件
   │
   ▼
pytest_sessionfinish hook
   │
   ├─④ BugReporter.generate_markdown_report() → reports/bug_list.md
   │
   ├─⑤ BugReporter.generate_json_report() → reports/bug_list.json
   │
   └─⑥ BugReporter.generate_summary_report() → reports/execution_summary.md
```

`pytest_sessionfinish` hook 示例：

```python
def pytest_sessionfinish(session):
    """测试会话结束后生成报告。"""
    from utils.bug_reporter import get_bug_reporter

    reporter = get_bug_reporter()
    if reporter.bugs:
        reporter.generate_markdown_report()
        reporter.generate_json_report()
        # 总用例数、通过数可从 session 统计取得
        total = session.testscollected
        passed = total - len(reporter.bugs)
        reporter.generate_summary_report(total, passed, len(reporter.bugs))

---

## 6. 实战案例：登录失败后的完整 Bug 记录

场景：`test_login_with_wrong_password` 执行失败，断言"密码不正确"未出现，实际显示"网络错误"。

### 生成的 Bug 清单报告

```markdown
# Bug 清单报告

**失败用例数**: 2

---

## Bug #1: test_login_with_wrong_password

- **错误信息**: AssertionError: 期望显示'密码不正确'，实际显示'网络错误'
- **截图**: `screenshots/failure_test_login_with_wrong_password_20250101.png`
- **环境**: Android Android Emulator

## Bug #2: test_register_with_invalid_email

- **错误信息**: TimeoutException: 无法定位元素 accessibility_id=email_error
- **截图**: `screenshots/failure_test_register_with_invalid_email_20250101.png`
- **环境**: Android Android Emulator

### Allure 报告中的效果

在 Allure 报告中，点击 `test_login_with_wrong_password` 用例，你会在 **Attachments** 区域看到：

-  `错误信息.txt` — 完整异常的 traceback
-  `失败截图.png` — 失败时的页面快照
-  `执行步骤.txt` — 操作步骤流水（如果有传入）

开发人员不必找测试人员"要截图要日志"，Allure 报告里全都有。

---

## 7. 注意事项与常见坑

| 坑 | 解决方案 |
|---|---|
| **错误信息过长**撑爆 Allure | `error_message[:2000]` 截断后再附加 |
| **截图失败后附件为空** | 调用 `os.path.exists(screenshot_path)` 检查后再 attach |
| **Bug 清单不完整** | 用 `pytest_sessionfinish` 替代每个 fixture 内导出，保证收集完 |
| **Allure 需要 Java** | `allure serve` / `allure generate` 依赖 Java 8+，CI 环境提前安装 |
| **BugReporter 对象不唯一** | 使用 `get_bug_reporter()` 单例函数，避免 `import` 不同模块产生多个实例 |
| **同一轮测试中重复记录** | 每个 `request.node.name` 只记录一次，可用 set 去重 |

---

## 8. 总结与思考

### 三层报告体系的价值

1. **Allure 报告** — 开发/测试自查，截图+步骤+日志统一查看
2. **Bug 清单报告** — 产品经理/报告会，Markdown 格式可嵌入 Wiki、CI 输出
3. **执行概览报告** — 管理者看板，通过率一目了然

### 核心原则

- **自动化收集**：失败时自动截图、记录、附加，零人工干预
- **分级展示**：不同角色看不同报告，信息不过载
- **可追溯**：每条失败都有截图 + 错误信息 + 环境信息，复现成本降到最低


