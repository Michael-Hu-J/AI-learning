# 第 1 篇：Playwright 在测试系统中的架构定位
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

> 在 AI测试系统 v3.0 中，Playwright 不是简单地被"调用"，而是被嵌入到一个精心设计的架构中。下面从架构视角出发，聊聊为什么选 Playwright、执行引擎怎么设计，以及进程隔离和并发控制的实战经验。

`配套代码/tests/` 下提供可直接运行的 Playwright 示例（如 `test_browser_api.py`：登录成功跳转、错误密码提示等，依赖内置 `demo_app`）。**内置演示**：在 `配套代码/` 安装依赖并执行 `playwright install chromium`，终端 A 运行 `cd demo_app && python app.py`，终端 B 在 `配套代码/` 执行 `pytest tests/test_browser_api.py -v`。演示账号见 `demo_app/app.py` 中的 `USERS`（默认 `admin` / `admin123`，普通用户 `testuser` / `test123`）。**外部项目**：初始化与启动以该项目文档为准，再在配套目录按需修改 `tests/test_seckill_playwright.py` 的 `BASE_URL` 后执行 `pytest tests/test_seckill_playwright.py -v`。下文中的 `example.com` 仅作语法示意，实战请替换为实际基地址（如 `http://127.0.0.1:5000`）。

## 一、为什么选择 Playwright？

### 1.1 选型决策：我们为什么没选 Selenium 和 Cypress

市面上常见的 UI 自动化框架有三个：Selenium、Cypress、Playwright。网上到处都能查到对比表，这里不重复那些参数罗列，直接说我们当时的决策过程。

**Selenium**：我们最早用的就是它。问题不在 Selenium 本身——它生态成熟、支持浏览器多，这些都好。问题在于 Python 生态里的 Selenium 缺少自动等待，每个操作后面都要跟 `WebDriverWait`，代码越来越长。在我们的 FastAPI 后端里嵌入 Selenium 还需要额外处理线程和进程隔离，维护成本越来越高。

**Cypress**：体验确实好，自动等待、时间旅行调试都很舒服。但它的硬伤是只支持 JavaScript。我们的系统后端是 Python（FastAPI），如果选 Cypress 就需要跨语言通信——要么前端生成脚本后端调 Node 进程，要么把整个测试引擎拆成两个服务。架构复杂度陡增，直接 pass。

**Playwright**：最终选择它，核心原因只有一个——Python 原生 API。不需要跨语言，不需要额外进程，`pip install playwright` 就能用。自动等待、网络拦截、多浏览器支持这些是锦上添花。

如果你也在选型，我的建议很简单：
- 后端是 Python → 直接选 Playwright，没有犹豫空间
- 后端是 Node.js → Cypress 和 Playwright 都行，看团队偏好
- 需要支持 Safari 真机 → Playwright 的 webkit 是目前最靠谱的方案
- 已有大量 Selenium 脚本 → 不用急着换，Selenium 4 的 CDP 支持已经改善了很多

### 1.2 选择 Playwright 的核心理由

在我们的 AI测试系统中，选择 Playwright 基于以下考虑：

1. **Python 生态集成**：系统后端使用 Python（FastAPI），Playwright 提供原生 Python API，无需跨语言通信
2. **自动等待机制**：内置的自动等待减少了测试脚本中的 `time.sleep()`，提高了测试稳定性
3. **网络拦截能力**：可以拦截和修改网络请求，支持 API 测试和 UI 测试的统一
4. **并发执行**：原生支持多浏览器实例并发执行，适合大规模测试场景
5. **社区活跃**：微软维护，更新频繁，文档完善

### 1.3 代码对比：三种框架的登录测试

**Selenium**：
```python
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Chrome()
BASE = "http://127.0.0.1:5000"
driver.get(f"{BASE}/login")

# 需要显式等待
wait = WebDriverWait(driver, 10)

username = wait.until(EC.presence_of_element_located((By.ID, "username")))
username.send_keys("testuser")

password = driver.find_element(By.ID, "password")
password.send_keys("admin123")

login_btn = driver.find_element(By.CSS_SELECTOR, '#loginForm button[type="submit"]')
login_btn.click()

# 需要手动等待页面加载
time.sleep(2)
assert "/products" in driver.current_url
driver.quit()
```

**Cypress**：
```javascript
cy.visit('http://127.0.0.1:5000/login')
cy.get('#username').type('testuser')
cy.get('#password').type('admin123')
cy.get('#loginForm button[type=submit]').click()
cy.url().should('include', '/products')
```

**Playwright**（与配套代码 `tests/test_browser_api.py` 所用登录页一致：`#username`、`#password`、`#loginForm`）：
```python
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"  # 内置 demo：先启动 demo_app；外部项目则按其文档初始化

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f"{BASE}/login")
    page.fill("#username", "testuser")
    page.fill("#password", "admin123")
    page.click('#loginForm button[type="submit"]')
    page.wait_for_url("**/products")

    browser.close()
```

代码量上看，Playwright 比 Selenium 少了一半，功能却不输 Cypress。

## 二、系统架构总览

### 2.1 四层架构设计

在 AI测试系统中，Playwright 被嵌入到一个四层架构中：

```
┌─────────────────────────────────────────────────────────────┐
│  第 1 层：API 层 (ui_fastapi.py)                            │
│  - POST /scripts/{id}/run          启动测试执行              │
│  - GET  /scripts/stream/{id}       SSE 实时日志推送          │
│  - GET  /scripts/status/{id}       轮询状态查询              │
│  - POST /scripts/{id}/stop         停止执行                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ BackgroundTasks
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  第 2 层：执行服务层 (ui_execution_service.py)              │
│  - asyncio.Semaphore         并发控制 (默认 4 个浏览器)      │
│  - DB 持久化                 ExecutionRecord 表             │
│  - 内存缓存                  SSE 实时读取 logs              │
│  - 进程管理                  subprocess.Popen 映射          │
└──────────────────────────┬──────────────────────────────────┘
                           │ subprocess.Popen
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  第 3 层：Worker 进程层 (ui_worker.py)                      │
│  - sync_playwright()         启动浏览器                      │
│  - UILocatorResolver         三层定位降级                    │
│  - healing_subgraph          自愈诊断编排（教学版使用策略模式）              │
│  - 步骤执行循环              action/target/value             │
└──────────────────────────┬──────────────────────────────────┘
                           │ Playwright API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  第 4 层：Playwright 浏览器层                               │
│  - chromium/firefox/webkit   多浏览器支持                    │
│  - page.goto/click/fill      元素操作                        │
│  - page.screenshot()         截图取证                        │
│  - page.evaluate()           JS 执行                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 为什么需要四层架构？

**问题场景**：用户在前端点击"执行测试"，后端需要：
1. 接收请求，返回执行 ID
2. 启动浏览器，执行测试步骤
3. 实时推送日志到前端
4. 持久化执行结果到数据库
5. 支持并发执行（多个用户同时测试）
6. 支持优雅停止（用户点击停止按钮）

**如果只用一层**：
```python
# 反模式：所有逻辑写在一起
@app.post("/run")
def run_test(config):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for step in config["steps"]:
            page.click(step["selector"])
        browser.close()
        return {"result": "done"}
```

**问题**：
- 请求会阻塞 30 秒到几分钟（测试执行时间）
- 无法实时推送日志
- 无法并发执行（浏览器进程独立运行，线程方案下内存泄漏和崩溃会互相影响）
- 无法优雅停止
- 结果不持久化

**四层架构的优势**：
- API 层高效返回，不阻塞
- 执行服务层管理并发和资源
- Worker 进程隔离，崩溃不影响主服务
- 前端可以实时看到日志

## 三、进程隔离设计：为什么不用线程？

### 3.1 线程 vs 进程的对比

最初，我们尝试使用线程来执行 Playwright 测试：

```python
# 反模式：使用线程
import threading

def run_test_in_thread(config):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # ... 执行测试

thread = threading.Thread(target=run_test_in_thread, args=(config,))
thread.start()
```

**遇到的问题**：

1. **GIL 限制**：Python 的全局解释器锁（GIL）导致多线程无法真正并行，CPU 密集型任务性能差
2. **内存泄漏**：Playwright 浏览器实例在线程中可能无法正常释放，导致内存持续增长
3. **崩溃传播**：一个线程崩溃可能导致整个进程崩溃
4. **调试困难**：线程间的状态共享导致调试复杂

### 3.2 进程隔离方案

我们改为使用 `subprocess.Popen` 启动独立进程：

```python
# ui_execution_service.py - 进程隔离
import subprocess
import sys

class UIExecutionService:
    def __init__(self):
        self._processes = {}  # exec_id -> subprocess.Popen
    
    async def _run_subprocess(self, exec_id):
        # 准备配置文件
        paths = _worker_paths(exec_id)
        with open(paths["config"], "w") as f:
            json.dump(config, f)
        
        # 启动子进程
        proc = subprocess.Popen(
            [sys.executable, WORKER_SCRIPT, 
             paths["config"], paths["result"], paths["stop_flag"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # 行缓冲
        )
        self._processes[exec_id] = proc
        
        # 监控子进程输出
        def _read_output():
            for line in proc.stdout:
                self._push_log(exec_id, line.strip(), "info")
        
        reader = threading.Thread(target=_read_output, daemon=True)
        reader.start()
        
        # 等待子进程完成
        returncode = proc.wait(timeout=600)
        
        # 读取结果
        if os.path.exists(paths["result"]):
            with open(paths["result"]) as f:
                result = json.load(f)
```

**进程隔离的优势**：

1. **真正的并行**：每个进程有独立的 Python 解释器，不受 GIL 限制
2. **崩溃隔离**：一个进程崩溃不影响其他进程和主服务
3. **资源可控**：可以监控每个进程的内存和 CPU 使用
4. **优雅停止**：可以通过 `proc.terminate()` 或 `proc.kill()` 停止进程

### 3.3 进程间通信：JSON 文件 + 管道

进程间如何通信？我们使用了两种方式：

**方式 1：JSON 文件（配置和结果）**
```python
# 主进程写入配置
with open(paths["config"], "w") as f:
    json.dump(config, f)

# Worker 进程读取配置
config = json.load(open(config_path))

# Worker 进程写入结果
with open(result_path, "w") as f:
    json.dump(result, f)

# 主进程读取结果
result = json.load(open(result_path))
```

**方式 2：管道（实时日志）**
```python
# Worker 进程输出日志
print(f" [步骤 1] 打开页面成功")

# 主进程读取日志
for line in proc.stdout:
    self._push_log(exec_id, line.strip(), "info")
```

**方式 3：文件标志（停止信号）**
```python
# 主进程创建停止标志
with open(paths["stop_flag"], "w") as f:
    f.write("stop")

# Worker 进程检查停止标志
if os.path.exists(stop_flag_path):
    print(" 收到停止信号")
    break
```

## 四、DB 持久化 + 内存缓存的双层架构

### 4.1 为什么需要双层架构？

**问题场景**：
- 前端需要实时看到日志（SSE 推送）
- 后端需要持久化执行记录（DB 存储）
- 如果每次日志都写 DB，性能太差
- 如果只写内存，服务重启后数据丢失

**解决方案**：DB 持久化 + 内存缓存

```python
# ui_execution_service.py - 双层架构
class UIExecutionService:
    def __init__(self):
        self._cache = {}  # 内存缓存
    
    def _push_log(self, exec_id, message, level="info"):
        """推送日志到内存缓存 + DB"""
        # 1. 写入内存缓存
        cache = self._get_or_create_cache(exec_id)
        cache["logs"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "level": level,
        })
        
        # 限制内存中的日志数量
        if len(cache["logs"]) > 500:
            cache["logs"] = cache["logs"][-500:]
        
        # 2. 同步到 DB
        self._update_record(exec_id, logs=cache["logs"])
    
    def _sync_cache_to_db(self, exec_id):
        """执行结束时，将完整结果同步到 DB"""
        cache = self._cache.get(exec_id)
        if not cache:
            return
        
        self._update_record(
            exec_id,
            status=cache.get("status"),
            stats=cache.get("stats"),
            logs=cache.get("logs"),
            end_time=datetime.fromisoformat(cache["end_time"]),
            result_data={
                "step_results": cache.get("step_results", []),
                "locator_resolution": cache.get("locator_resolution", []),
                "self_healing": cache.get("self_healing", {}),
            },
        )
```

### 4.2 数据流图

```
┌─────────────┐
│  Worker 进程 │
│  (ui_worker) │
└──────┬──────┘
       │ stdout 管道
       ▼
┌─────────────────────────────────────────────┐
│  UIExecutionService                         │
│                                             │
│  _push_log() ─────────────────────────────┐ │
│       │                                   │ │
│       ▼                                   │ │
│  ┌─────────────┐    ┌─────────────┐      │ │
│  │  内存缓存    │    │  DB 持久化   │      │ │
│  │  _cache     │    │  DB 写入     │      │ │
│  └─────────────┘    └─────────────┘      │ │
│       │                                   │ │
│       │ SSE 读取                          │ │
│       ▼                                   │ │
│  ┌─────────────┐                         │ │
│  │  SSE 端点   │◄────────────────────────┘ │
│  │  (实时日志) │                           │
│  └─────────────┘                           │
└─────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  前端浏览器  │
│  EventSource │
└─────────────┘
```

### 4.3 为什么限制 500 条日志？

内存中的日志数量限制为 500 条，原因：

1. **内存保护**：每个执行可能产生数千条日志，不限制会导致内存溢出
2. **SSE 推送效率**：前端只需要最近的日志，历史日志可以通过 DB 查询
3. **用户体验**：前端滚动显示日志，500 条足够覆盖一次执行的全过程

```python
if len(cache["logs"]) > 500:
    cache["logs"] = cache["logs"][-500:]
```

## 五、实战案例：一次完整的测试执行

### 5.1 用户操作流程

1. 用户在前端点击"执行测试"
2. 前端调用 `POST /api/ui/scripts/6/run`
3. 后端返回 `exec_id`，前端开始订阅 SSE
4. Worker 进程启动，执行测试步骤
5. 前端实时显示日志
6. 执行完成，前端显示结果

### 5.2 代码执行流程

```python
# 1. 前端调用 API
fetch('http://localhost:8888/api/ui/scripts/6/run', {
  method: 'POST',
  body: JSON.stringify({
    browser: 'chromium',
    headless: true,
    steps: [
      {action: '打开页面', target: 'http://127.0.0.1:5000/login', value: ''},
      {action: '输入文本', target: '#username', value: 'testuser'},
      {action: '输入文本', target: '#password', value: 'admin123'},
      {action: '点击元素', target: '#loginForm button[type=submit]', value: ''},
    ]
  })
})

# 2. 后端 API 处理
@app.post("/scripts/{script_id}/run")
async def run_ui_script(script_id, payload):
    # 获取脚本内容
    script = db.query(UIScript).filter(UIScript.id == script_id).first()
    
    # 启动执行（后台任务）
    exec_id = ui_execution_service.start_execution({
        "steps": payload.get("steps", []),
        "browser": payload.get("browser", "chromium"),
        "headless": payload.get("headless", True),
    })
    
    return {"code": 200, "data": {"exec_id": exec_id}}

# 3. 执行服务启动子进程
def start_execution(self, config):
    exec_id = f"ui_exec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    # 创建 DB 记录
    self._create_record(exec_id, config)
    
    # 启动后台线程
    t = threading.Thread(target=self._run_execution, args=(exec_id,))
    t.start()
    
    return exec_id

# 4. Worker 进程执行测试
def run(config_path, result_path, stop_flag_path):
    config = json.load(open(config_path))
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for step in config["steps"]:
            action = step.get("action", "")
            target = step.get("target", "")
            value = step.get("value", "")
            if action == "打开页面":
                page.goto(target, wait_until="domcontentloaded")
            elif action == "输入文本":
                page.fill(target, value)
            elif action == "点击元素":
                page.click(target)
        
        browser.close()
    
    # 保存结果
    json.dump(result, open(result_path, "w"), ensure_ascii=False, indent=2)
```

### 5.3 时间线

```
T+0s    用户点击"执行测试"
T+0.1s  后端返回 exec_id
T+0.2s  前端开始订阅 SSE
T+0.5s  Worker 进程启动
T+1.0s  浏览器启动，打开登录页
T+1.5s  输入用户名
T+2.0s  输入密码
T+2.5s  点击登录按钮
T+3.0s  等待页面加载
T+3.5s  测试完成，保存结果
T+3.6s  Worker 进程退出
T+3.7s  前端显示完成状态
```

## 六、踩坑经验

### 6.1 坑 1：subprocess 的 stdout 缓冲问题

**问题**：子进程的 stdout 默认是块缓冲，导致日志延迟推送。

**解决**：使用 `bufsize=1`（行缓冲）或 `PYTHONUNBUFFERED=1` 环境变量。

```python
proc = subprocess.Popen(
    [sys.executable, WORKER_SCRIPT, ...],
    stdout=subprocess.PIPE,
    text=True,
    bufsize=1,  # 行缓冲
    env={**os.environ, "PYTHONUNBUFFERED": "1"},
)
```

### 6.2 坑 2：线程中读取 stdout 导致阻塞

**问题**：在主线程中直接读取 `proc.stdout` 会阻塞，无法同时等待进程结束。

**解决**：使用独立线程读取 stdout。

```python
def _read_output():
    for line in proc.stdout:
        self._push_log(exec_id, line.strip(), "info")

reader = threading.Thread(target=_read_output, daemon=True)
reader.start()

returncode = proc.wait(timeout=600)
reader.join(timeout=5)
```

### 6.3 坑 3：子进程崩溃导致主进程卡死

**问题**：子进程崩溃时，`proc.wait()` 可能永远阻塞。

**解决**：设置超时时间，超时后 kill 子进程。

```python
try:
    returncode = proc.wait(timeout=600)
except subprocess.TimeoutExpired:
    self._push_log(exec_id, " 子进程超时，终止执行", "error")
    self._kill_process(exec_id)
    cache["status"] = "failed"
```

### 6.4 坑 4：内存缓存与 DB 不一致

**问题**：服务重启后，内存缓存丢失，DB 中的数据不完整。

**解决**：执行结束时同步缓存到 DB，启动时从 DB 恢复缓存。

```python
def _get_or_create_cache(self, exec_id):
    if exec_id not in self._cache:
        # 从 DB 恢复
        record = self._get_record(exec_id)
        if record:
            self._cache[exec_id] = {
                "status": record.status,
                "logs": record.logs or [],
                # ...
            }
    return self._cache[exec_id]
```

## 七、写在最后

这篇文章比较长，但核心想说的其实就一件事：**UI 自动化不是写脚本，而是设计系统**。

我们在 v1.0 的时候也犯过错误——把所有逻辑塞进一个 Flask 路由里，`@app.post("/run")` 里面直接调 `sync_playwright()`。跑起来没问题，直到用户开始并发执行，GIL 锁住了整个服务，浏览器进程泄漏，日志丢失。踩了这些坑之后才意识到，UI 自动化测试系统本质上是一个**分布式任务调度系统**，只是它的"任务"恰好是浏览器操作。

四层架构不是设计出来的，是踩坑踩出来的。进程隔离是因为线程扛不住，双层存储是因为纯内存不靠谱，优雅停止是因为用户真的会点那个按钮。

如果你正在搭建自己的 UI 自动化系统，我的建议是：先跑通最小可用版本（一个路由 + sync_playwright），然后逐步加入进程隔离、结果持久化、并发控制。别一开始就搞四层架构，那会拖慢你的迭代速度。但当你遇到并发问题的时候，别用线程打补丁——直接上进程。

---

## 八、总结

这篇从选型讲到架构，核心就三个决策点：

**第一，为什么选 Playwright 不选 Selenium。** 不是 Selenium 不好，是 Python 生态里 Selenium 的等待机制太繁琐。每个操作后面跟 `WebDriverWait`，代码长度翻倍。Playwright 的自动等待不是"更好用"，是"不用写"——这在一千个测试用例的规模下，差异是 2000 行代码和 0 行代码的区别。

**第二，为什么用进程不用线程。** Python 的 GIL 不是理论问题，是实际问题。一个浏览器实例占 200-300MB 内存，3 个同时跑就接近 1GB。线程共享内存，一个浏览器崩溃可能把整个进程带崩。进程隔离虽然启动慢一点（多 2-3 秒），但稳定性提升是数量级的。我们线上跑了半年，进程隔离方案零次全系统崩溃，之前线程方案一周崩两次。

**第三，为什么做双层存储。** 纯内存缓存快，但服务重启就丢。纯数据库持久化稳，但 SSE 实时读取太慢（每次查库）。双层存储——内存做实时读取，数据库做持久化——看起来复杂，实际上代码量只增加了 30%，可靠性提升了 10 倍。

配套代码里的 `配套代码/worker/ui_worker.py` 和 `配套代码/worker/execution_service.py` 是这套架构的简化版，去掉了 FastAPI 和数据库，用 JSON 文件代替。先跑通配套代码，再看原文理解架构，会更容易。

---

