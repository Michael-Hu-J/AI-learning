# 14 年测试工程师拆分：UI 自动化测试引擎到底在跑什么
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

> 在 AI测试系统中，一个 UI 测试从"JSON 步骤定义"到"浏览器实际操作"，中间经历了怎样的流程？下面逐行拆分 `ui_worker.py` 的执行主循环，看看 Playwright 是怎么被集成进来的，以及结果收集和停止机制的设计。  
> **增补**：路径二声明式 spec 见 `配套代码/examples/ui_login_spec_example.md`。

## 一、步骤定义：JSON 格式的测试步骤

### 1.1 为什么使用 JSON 格式？

传统的 Playwright 测试需要编写 Python 代码：

```python
# 传统方式：需要编写 Python 代码
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    page.goto("http://127.0.0.1:5000/login")
    page.fill("#username", "testuser")
    page.fill("#password", "admin123")
    page.click('#loginForm button[type="submit"]')
    page.wait_for_url("**/products")
    
    browser.close()
```

**问题**：
- 需要编写代码，门槛高
- 无法在前端界面中编辑
- 无法动态生成（AI 生成）
- 无法版本控制（代码文件 vs 数据库记录）

**我们的解决方案：JSON 步骤定义**

```json
{
  "steps": [
    {"action": "打开页面", "target": "http://127.0.0.1:5000/login", "value": ""},
    {"action": "输入文本", "target": "#username", "value": "testuser"},
    {"action": "输入文本", "target": "#password", "value": "admin123"},
    {"action": "点击元素", "target": "#loginForm button[type=submit]", "value": ""},
    {"action": "等待元素", "target": "#product-table", "value": ""}
  ]
}
```

**优势**：
- 前端可以直接编辑（表单界面）
- AI 可以生成（自然语言 → JSON）
- 数据库可以存储（JSON 字段）
- 版本控制方便（API 管理）

### 1.2 步骤格式详解

每个步骤包含三个核心字段：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `action` | string | 操作类型 | "打开页面"、"点击元素"、"输入文本"、"等待元素"、"验证文本" |
| `target` | string | 目标选择器/URL | "#username"、"http://127.0.0.1:5000/login" |
| `value` | string/number | 输入值/期望值 | "testuser"、199.99 |

**可选字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `locator_hints` | object | 定位提示（testid、role、label、text） |
| `timeout` | number | 超时时间（ms） |
| `retry` | number | 重试次数 |

### 1.3 步骤生成方式

在我们的系统中，步骤可以通过三种方式生成：

**方式 1：前端表单手动创建**
```javascript
// frontend/src/views/uitest/index.vue
this.newScript.stepsList.push({
  action: '点击元素',
  target: '#login-btn',
  value: ''
})
```

**方式 2：自然语言 AI 生成**
```python
# backend/app/api/ui_fastapi.py
@router.post("/scripts/parse-steps")
async def parse_steps_from_natural_language(payload):
    """使用 LLM 将自然语言转换为测试步骤"""
    prompt = f"""
    你是一个 UI 自动化测试专家。将以下自然语言描述转换为测试步骤 JSON 数组。
    每个步骤包含: action (打开页面/点击元素/输入文本/等待元素/验证文本), 
    target (CSS 选择器或 URL), value (输入值或期望文本)。
    
    自然语言描述: {payload.get('description')}
    """
    # 调用 LLM 生成步骤
    steps = await call_llm(prompt)
    return {"code": 200, "data": {"steps": steps}}
```

**方式 3：录制回放生成**
```javascript
// 用户在前端操作浏览器，系统自动记录步骤
this.currentSteps.push({
  action: '点击元素',
  target: elementSelector,
  value: ''
})
```

## 二、执行引擎：ui_worker.py 的主循环

### 2.1 Worker 进程启动

Worker 进程由主服务通过 `subprocess.Popen` 启动：

```python
# ui_execution_service.py - 启动子进程
proc = subprocess.Popen(
    [sys.executable, WORKER_SCRIPT, 
     paths["config"], paths["result"], paths["stop_flag"]],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
```

Worker 进程接收三个文件路径作为参数：

| 参数 | 说明 | 内容 |
|------|------|------|
| `config_path` | 配置文件路径 | 测试步骤、浏览器配置、超时设置 |
| `result_path` | 结果文件路径 | 执行结果、步骤详情、定位记录、自愈记录 |
| `stop_flag_path` | 停止标志路径 | 空文件，存在表示需要停止 |

### 2.2 主执行循环

Worker 的主循环可以拆成 4 个阶段来看。

**阶段一：加载配置 + 初始化容器**

```python
# ui_worker.py - 主执行入口
def run(config_path, result_path, stop_flag_path):
    # 1. 加载配置
    config = _load_config(config_path)
    exec_id = config.get("exec_id", "unknown")
    base_steps = config.get("steps", [])
    headless = bool(config.get("headless", True))
    browser_name = str(config.get("browser", "chromium")).lower()
    timeout_ms = int(config.get("timeout", 15000))
    enable_l3_ai = bool(config.get("enable_l3_ai", False))
    
    # 2. 初始化数据容器
    logs = []
    stats = {"total": 0, "passed": 0, "failed": 0, "repaired": 0}
    step_results = []
    locator_resolution = []
    self_healing_plans = []
    
    _push_log(logs, f" Worker 启动，exec_id={exec_id}", "info")
```

配置来自上一节说的 JSON 文件，容器用来收集执行过程的所有数据。

**阶段二：启动 Playwright + 浏览器**

```python
    # 3. 启动 Playwright
    try:
        from playwright.sync_api import sync_playwright
        from app.services.ui_locator_resolver import UILocatorResolver
        
        resolver = UILocatorResolver(enable_l3_ai=enable_l3_ai)
        
        with sync_playwright() as p:
            # 选择浏览器
            browser_launcher = {
                "chrome": p.chromium,
                "chromium": p.chromium,
                "firefox": p.firefox,
                "webkit": p.webkit,
                "edge": p.chromium,
            }.get(browser_name, p.chromium)
            
            browser = browser_launcher.launch(headless=headless)
            page = browser.new_page()
            
            _push_log(logs, f" 浏览器已启动: {browser_name}", "info")
            abort = False
```

注意两点：一是用 `with` 语句包裹，保证异常时浏览器也能正常关闭；二是初始化了 `UILocatorResolver`，这是下一篇要讲的三层定位降级策略的核心组件。

**阶段三：执行步骤循环（核心逻辑）**

```python
            # 4. 执行步骤循环
            for idx, step in enumerate(base_steps, start=1):
                # 检查停止标志
                if os.path.exists(stop_flag_path):
                    _push_log(logs, " 收到停止信号", "warning")
                    abort = True
                    break
                
                # 解析步骤
                action = str(step.get("action") or "").strip()
                target = str(step.get("target") or "").strip()
                value = step.get("value")
                stats["total"] += 1
                
                # 执行步骤
                step_result = {
                    "index": idx,
                    "action": action,
                    "target": target,
                    "status": "passed",
                    "duration_ms": 0,
                    "error": "",
                }
                t0 = time.time()
                
                try:
                    if action == "打开页面":
                        page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
                    elif action in ["点击元素", "输入文本", "等待元素", "验证文本"]:
                        # 使用定位解析器
                        resolution = resolver.resolve(page, step)
                        locator_resolution.append({
                            "action": action,
                            "original_selector": target,
                            "resolved_selector": resolution.get("selector", ""),
                            "level": resolution.get("level", "NONE"),
                            "attempts": resolution.get("attempts", []),
                        })
                        
                        if not resolution.get("found"):
                            raise RuntimeError(f"element not found: {target}")
                        
                        selector = resolution["selector"]
                        if action == "点击元素":
                            page.click(selector, timeout=timeout_ms)
                        elif action == "输入文本":
                            page.fill(selector, str(value or ""), timeout=timeout_ms)
                        elif action == "等待元素":
                            page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
                        elif action == "验证文本":
                            body = page.text_content("body")
                            expected = str(value or "")
                            if expected and expected not in body:
                                raise AssertionError(f"AssertionError: expected contains '{expected}'")
                    else:
                        step_result["status"] = "skipped"
                        stats["total"] -= 1
                    
                    # 成功
                    stats["passed"] += 1
                    step_result["duration_ms"] = int((time.time() - t0) * 1000)
                    _push_log(logs, f" [步骤{idx}] {action} 成功", "success")
                
                except Exception as e:
                    # 失败
                    stats["failed"] += 1
                    step_result["status"] = "failed"
                    step_result["error"] = str(e)
                    step_result["duration_ms"] = int((time.time() - t0) * 1000)
                    _push_log(logs, f" [步骤{idx}] {action} 失败: {e}", "error")
                    
                    # 尝试自愈（注：以下为生产版 LangGraph 实现，教学版配套代码使用策略模式实现，见 healer/strategies.py）
                    try:
                        from app.graphs.healing_graph import invoke_healing_subgraph_sync
                        
                        sg = invoke_healing_subgraph_sync(
                            str(e),
                            {
                                "entity": "ui_playwright",
                                "selector": target,
                                "action": action,
                                "url": page.url or "",
                                "session_id": exec_id,
                                "scope": "ui_playwright",
                            },
                            step={"index": idx, "target": target, "action": action},
                            run_name="ui-worker-healing",
                        )
                        
                        self_healing_plans.append({
                            "test": f"step_{idx}",
                            "diagnosis": sg.get("diagnosis") or {},
                            "repair": sg.get("repair_result") or {},
                            "healed": bool(sg.get("healed")),
                            "heal_log": sg.get("heal_log") or [],
                            "tool_calls": sg.get("tool_calls") or [],
                        })
                        
                        _push_log(
                            logs,
                            f" [步骤{idx}] 已走 healing_subgraph（healed={bool(sg.get('healed'))}）",
                            "info",
                        )
                    except Exception:
                        pass
                
                step_results.append(step_result)
```

这是整个 Worker 最核心的部分。每一步执行后，成功就记 `passed`，失败就记 `failed` 并触发自愈。失败不会中断循环，默认继续执行下一步——这个设计让单次测试能暴露更多问题。

**阶段四：确定状态 + 保存结果**

```python
            # 5. 确定最终状态
            if not abort:
                status = "completed" if stats["failed"] == 0 else "failed"
            else:
                status = "stopped"
            
            browser.close()
    
    except Exception as e:
        status = "failed"
        error_detail = traceback.format_exc()
        _push_log(logs, f" 执行器异常: {e}", "error")
        _push_log(logs, error_detail, "error")
    else:
        error_detail = ""
    
    # 6. 计算成功率
    total = max(stats["total"], 1)
    success_rate = round((stats["passed"] / total) * 100, 2)
    _push_log(
        logs,
        f" 执行结束: total={stats['total']}, passed={stats['passed']}, "
        f"failed={stats['failed']}, repaired={stats['repaired']}, success_rate={success_rate}%",
        "info",
    )
    
    # 7. 保存结果
    result = {
        "exec_id": exec_id,
        "status": status,
        "stats": stats,
        "step_results": step_results[:200],
        "locator_resolution": locator_resolution,
        "self_healing": {
            "summary": {
                "total": len(self_healing_plans),
                "repaired": sum(1 for p in self_healing_plans if p.get("healed")),
                "auto_repairable": sum(
                    1 for p in self_healing_plans if (p.get("diagnosis") or {}).get("auto_repairable")
                ),
            },
            "plans": self_healing_plans[:100],
        },
        "logs": logs,
        "end_time": datetime.now().isoformat(),
        "error": error_detail,
    }
    _save_result(result_path, result)
```

结果文件中 `step_results` 最多保留 200 条、`self_healing_plans` 最多 100 条，防止文件过大。完整的执行结果数据结构见第三节的详细说明。

### 2.3 执行流程图

```
┌─────────────────────────────────────────────────────────┐
│  启动 Worker 进程                                         │
│  python ui_worker.py <config> <result> <stop_flag>       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  1. 加载配置文件                                           │
│  - exec_id、steps、browser、headless、timeout            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  2. 启动 Playwright                                       │
│  - sync_playwright()                                     │
│  - browser.launch(headless=True)                         │
│  - browser.new_page()                                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  3. 执行步骤循环                                           │
│  for step in steps:                                      │
│    ├─ 检查停止标志                                         │
│    ├─ 解析 action/target/value                            │
│    ├─ 执行操作 (goto/click/fill/wait/verify)              │
│    ├─ 成功 → stats.passed++                               │
│    └─ 失败 → stats.failed++ → 尝试自愈                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  4. 确定最终状态                                           │
│  - completed (无失败)                                     │
│  - failed (有失败)                                        │
│  - stopped (收到停止信号)                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  5. 保存结果到 JSON 文件                                    │
│  - exec_id、status、stats                                 │
│  - step_results、locator_resolution                       │
│  - self_healing、logs                                     │
└─────────────────────────────────────────────────────────┘
```

## 三、结果收集：三大核心数据结构

### 3.1 step_results：步骤执行结果

每个步骤的执行结果包含：

```python
step_result = {
    "index": 1,                    # 步骤序号
    "action": "点击元素",           # 操作类型
    "target": "#login-btn",        # 目标选择器
    "status": "passed",            # 状态：passed/failed/skipped
    "duration_ms": 125,            # 执行耗时（毫秒）
    "error": "",                   # 错误信息（失败时）
}
```

**用途**：
- 前端显示步骤执行详情
- 失败步骤高亮显示
- 性能分析（哪个步骤最慢）

### 3.2 locator_resolution：定位解析记录

每次元素定位的解析过程：

```python
locator_resolution.append({
    "action": "点击元素",                    # 操作类型
    "original_selector": "#login-btn",      # 原始选择器
    "resolved_selector": "button:has-text('登录')",  # 最终选择器
    "level": "L2",                          # 定位级别：L1/L2/L3/NONE
    "attempts": [                           # 尝试列表
        {"level": "L1", "selector": "#login-btn", "ok": False, "reason": "Timeout"},
        {"level": "L2", "selector": "button:has-text('登录')", "ok": True},
    ],
})
```

**用途**：
- 分析定位策略效果
- 优化选择器生成规则
- 定位失败原因分析

### 3.3 self_healing：自愈记录

每次自愈尝试的完整记录：

```python
self_healing_plans.append({
    "test": "step_3",
    "diagnosis": {
        "error_type": "element",
        "confidence": 0.9,
        "root_cause": "元素不存在或选择器错误",
        "auto_repairable": True,
    },
    "repair": {
        "action": "retry_with_alternatives",
        "alternative_selectors": [
            "button:has-text('登录')",
            "[role='button']",
        ],
        "success": True,
    },
    "healed": True,
    "heal_log": [
        "diagnose:element:0.9",
        "plan:element_locator_repair",
        "tools:2",
        "execute:retry_with_alternatives:True",
    ],
    "tool_calls": [
        {"tool_name": "get_page_content", "success": True},
    ],
})
```

**用途**：
- 自愈效果统计
- 修复策略优化
- LLM 诊断质量评估

**如何消费这些数据**：执行服务层读取 JSON 结果文件后，前端通过 SSE 推送实时状态，同时 DB 持久化记录供后续分析。`step_results` 用于前端展示步骤详情，`locator_resolution` 用于分析定位策略效果，`self_healing` 用于评估自愈系统的修复成功率。

## 四、停止机制：优雅停止的设计

### 4.1 为什么需要优雅停止？

**场景**：用户点击"停止执行"，系统需要：
1. 通知 Worker 进程停止
2. 保存已执行的步骤结果
3. 关闭浏览器
4. 更新执行状态为 "stopped"

**如果直接 kill 进程**：
- 结果文件可能不完整
- 浏览器可能未正常关闭
- 用户看不到已执行的结果

### 4.2 三级停止机制

**第一级：stop flag 文件（优雅停止）**

```python
# 主进程创建停止标志
def request_stop(self, exec_id):
    paths = _worker_paths(exec_id)
    with open(paths["stop_flag"], "w") as f:
        f.write("stop")

# Worker 进程检查停止标志
for idx, step in enumerate(base_steps, start=1):
    if os.path.exists(stop_flag_path):
        _push_log(logs, " 收到停止信号", "warning")
        abort = True
        break
```

**第二级：子进程 terminate（强制停止）**

```python
def _kill_process(self, exec_id):
    proc = self._processes.get(exec_id)
    if proc and proc.poll() is None:
        try:
            proc.terminate()  # 发送 SIGTERM
            proc.wait(timeout=5)
        except Exception:
            proc.kill()  # 发送 SIGKILL
```

**第三级：超时自动停止**

```python
try:
    returncode = proc.wait(timeout=600)  # 10 分钟超时
except subprocess.TimeoutExpired:
    self._push_log(exec_id, " 子进程超时，终止执行", "error")
    self._kill_process(exec_id)
    cache["status"] = "failed"
```

### 4.3 停止流程图

```
用户点击"停止"
       │
       ▼
┌─────────────────────────────────────────┐
│  创建 stop flag 文件                      │
│  /test_data/ui_worker_data/xxx_stop.flag │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Worker 进程检查 stop flag               │
│  if os.path.exists(stop_flag_path):      │
│      abort = True                        │
│      break                               │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  保存结果到 JSON 文件                      │
│  status = "stopped"                      │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  主进程读取结果，更新状态                   │
│  cache["status"] = "stopped"             │
└─────────────────────────────────────────┘
```

## 五、实战案例：一次完整的登录测试

### 5.1 测试步骤

```json
{
  "steps": [
    {"action": "打开页面", "target": "http://127.0.0.1:5000/login", "value": ""},
    {"action": "输入文本", "target": "#username", "value": "testuser"},
    {"action": "输入文本", "target": "#password", "value": "admin123"},
    {"action": "点击元素", "target": "#loginForm button[type=submit]", "value": ""},
    {"action": "等待元素", "target": "#product-table", "value": ""}
  ]
}
```

### 5.2 执行日志

```
16:30:01  Worker 启动，exec_id=ui_exec_20260504163001_abc123
16:30:01  浏览器已启动: chromium
16:30:02  [步骤 1] 打开页面 成功
16:30:02  [步骤 2] 输入文本 成功
16:30:03  [步骤 3] 输入文本 成功
16:30:03  [步骤 4] 点击元素 成功
16:30:04  [步骤 5] 等待元素 成功
16:30:04  执行结束: total=5, passed=5, failed=0, repaired=0, success_rate=100.0%
```

### 5.3 执行结果

```json
{
  "exec_id": "ui_exec_20260504163001_abc123",
  "status": "completed",
  "stats": {
    "total": 5,
    "passed": 5,
    "failed": 0,
    "repaired": 0
  },
  "step_results": [
    {"index": 1, "action": "打开页面", "target": "http://127.0.0.1:5000/login", "status": "passed", "duration_ms": 850},
    {"index": 2, "action": "输入文本", "target": "#username", "status": "passed", "duration_ms": 120},
    {"index": 3, "action": "输入文本", "target": "#password", "status": "passed", "duration_ms": 95},
    {"index": 4, "action": "点击元素", "target": "button[type=submit]", "status": "passed", "duration_ms": 200},
    {"index": 5, "action": "等待元素", "target": "#product-table", "status": "passed", "duration_ms": 1050}
  ],
  "locator_resolution": [
    {"action": "输入文本", "original_selector": "#username", "resolved_selector": "#username", "level": "L1", "attempts": []},
    {"action": "输入文本", "original_selector": "#password", "resolved_selector": "#password", "level": "L1", "attempts": []},
    {"action": "点击元素", "original_selector": "button[type=submit]", "resolved_selector": "button[type=submit]", "level": "L1", "attempts": []},
    {"action": "等待元素", "original_selector": "#product-table", "resolved_selector": "#product-table", "level": "L1", "attempts": []}
  ],
  "self_healing": {
    "summary": {"total": 0, "repaired": 0, "auto_repairable": 0},
    "plans": []
  },
  "logs": [...],
  "end_time": "2026-05-04T16:30:04.123456",
  "error": ""
}
```

## 附一、两条 UI 自动化路径怎么选

本课 **路径一（主路径）**：`worker/ui_worker.py` + JSON 步骤 `action/target/value` —— 适合平台编排、NL 解析结果、进程内执行（下文全文）。

**路径二（声明式 spec）**：Markdown frontmatter 写 `kind: ui_pytest_playwright` + `steps` / `expect`，由 **`generate.sh` 渲染 pytest**（本仓库 **不包含** 生成器，示例见 `配套代码/examples/ui_login_spec_example.md`）。

```
                    URL / 需求 / 截图意图
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
   路径一：JSON 步骤表                  路径二：ui_pytest spec
   ui_worker / step_parser              generate.sh → test_*.py
   本课配套代码完整实现
           │                               │
           └───────────────┬───────────────┘
                           ▼
              第 3 篇定位 + 第 4 篇自愈 + pytest 报告
```

| 维度 | 路径一（本课） | 路径二（Skill） |
|------|----------------|-----------------|
| 典型产出 | `steps[]` JSON | `ui_login.md` 等 spec |
| 谁改起来顺手 | 平台、NL 引擎 | 测试工程师、CI 评审 |
| 定位字段 | `target` 常为 CSS | `l1_label`、`l1_role` 等 |

---

## 附二、本课引擎 ↔ Agent 四段（认知图）

**本课教的是各段背后的代码**：

| Agent 阶段（Skill） | 本课对应 |
|---------------------|----------|
| 分析（元素 / 截图意图） | 第 3 篇 `resolver`；第 5 篇 `page_intent_example.md` |
| 规划（范围、冒烟集） | 第 1～2 篇架构与步骤设计 |
| 执行（Playwright 脚本） | `ui_worker.py`；路径二 spec 见 Skill |
| 自愈（失败收敛） | 第 4 篇 `healer/`；脚本级补丁见 Skill `UI-skills/自我修复` |

---

## 六、踩坑经验

### 6.1 坑 1：Playwright 的同步/异步混用

**问题**：`sync_playwright()` 是同步 API，但某些操作（如网络拦截）需要异步 API。

**解决**：根据场景选择 API 类型。UI Worker 使用同步 API，MCP Server 使用异步 API。

```python
# 同步 API（UI Worker）
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)

# 异步 API（MCP Server）
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto(url)
```

### 6.2 坑 2：步骤执行失败后的状态恢复

**问题**：步骤 3 失败后，步骤 4 是否继续执行？

**解决**：默认继续执行，但可以通过配置控制。

```python
# 当前实现：失败后继续执行
except Exception as e:
    stats["failed"] += 1
    # 不 break，继续执行下一步
```

### 6.3 坑 3：结果文件大小控制

**问题**：大量日志和步骤结果导致 JSON 文件过大。

**解决**：限制日志数量和步骤结果数量。

```python
# 限制日志数量
if len(logs) > 500:
    logs[:] = logs[-500:]

# 限制步骤结果数量
"step_results": step_results[:200],
"self_healing_plans": self_healing_plans[:100],
```

### 6.4 坑 4：浏览器未正常关闭导致资源泄漏

**问题**：Worker 进程异常退出时，浏览器进程可能未关闭。

**解决**：使用 `with` 语句保证浏览器关闭。

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=headless)
    page = browser.new_page()
    # ... 执行测试
    # browser.close()  # with 块退出时自动关闭，这行可省略
```

## 七、写在最后

这篇拆分了 `ui_worker.py` 的执行主循环。核心逻辑其实不复杂：加载配置 → 启动浏览器 → 遍历步骤 → 收集结果 → 保存 JSON。真正有坑的地方在细节里。

我在写这个 Worker 的时候犯过的一个错误是：把 `browser.close()` 放在 `with` 块外面，结果异常路径下浏览器没关闭，服务器上堆了一堆 headless chromium 进程。后来统一用 `with sync_playwright()` 包裹，靠上下文管理器自动清理，省心多了。

另一个容易被忽略的点是结果文件大小。一次完整的测试执行可能产生几千行日志、几十个步骤结果，JSON 文件轻松超过 10MB。限制日志条数和步骤结果数量不是优化，是必须。

下一篇会讲三层定位降级策略，这是整个系统里我最满意的设计之一——用缓存 + 三层候选 + LLM 兜底，把选择器失效的痛点解决了大半。

---

## 八、总结

这篇把测试引擎的执行流程拆了一遍，核心就四个要点：

**第一，步骤格式决定了系统的扩展性。** JSON 格式的 `action/target/value` 三元组看起来简单，但它能表达任何浏览器操作——打开页面、点击、输入、等待、断言。更重要的是，这个格式可以被 AI 生成、被前端编辑、被数据库存储。我们后来做的"无代码测试编排"功能，底层就是这套步骤格式。

**第二，同步代码跑在异步环境里是最容易踩的坑。** `ui_worker.py` 本身是同步的（`sync_playwright`），但它是被 `asyncio` 的子进程调度器调用的。同步代码里不能直接 `await`，异步代码里不能直接调同步函数。解决方案很简单：子进程用 `asyncio.create_subprocess_exec` 启动，Worker 内部用同步代码，两者通过 JSON 文件通信。

**第三，结果文件会爆炸。** 一次测试执行产生 10MB 的 JSON 不是夸张，是常态。每个步骤的日志、每个定位器的尝试记录、每次自愈的诊断信息，都会往文件里写。限制日志条数（最多 500 条）、限制步骤结果数量（最多 200 个）、限制自愈记录（最多 100 条），不是优化，是必须。

**第四，`with` 语句不是可选的，是必须的。** `with sync_playwright() as p:` 保证无论正常结束还是异常退出，浏览器进程都会被关闭。我们线上曾经因为一个未捕获的异常导致浏览器没关闭，服务器上堆了 20 多个 headless chromium 进程，内存耗尽。从那以后，所有浏览器操作必须包裹在 `with` 语句里，成了铁律。

配套代码里的 `worker/ui_worker.py` 是这套执行流程的简化版，去掉了数据库和 FastAPI，用 JSON 文件做持久化。先跑通配套代码，再看原文理解完整架构。

---
