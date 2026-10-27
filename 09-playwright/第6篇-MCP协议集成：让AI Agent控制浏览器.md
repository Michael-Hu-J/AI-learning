# 第 6 篇：MCP协议集成：让 AI Agent 控制浏览器
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

文中 `navigate` / `fill` / `click` 的 URL 与选择器默认对应 Flask 演示系统（`http://127.0.0.1:5000`，登录页 `#username` / `#password` / `#loginForm button[type=submit]`）。示例项目演示账号在 `demo_app/app.py` 的 `USERS` 中（如 `admin`/`admin123` 或 `testuser`/`test123`）；若使用外部仓库项目，账号与初始化以该项目文档为准（常见含 `init_data.py`）。与 `配套代码/tests/test_browser_api.py` 等 Playwright 用例可对照阅读。

## 一、MCP协议是什么，为什么用它

MCP（Model Context Protocol）解决的是一个具体问题：AI 模型（Claude、GPT、Qwen）需要调用外部工具时，工具接口五花八门，没有统一标准。MCP 定义了一套基于 JSON-RPC 的协议，让 AI 模型通过标准接口调用浏览器控制、API 请求、文件操作等工具。

### 1.1 架构概览

```
┌─────────────────────────────────────────────────┐
│  AI 模型（Claude/GPT/Qwen）                      │
│  - 理解自然语言指令                              │
│  - 决定调用哪个工具                              │
└────────────────────┬────────────────────────────┘
                     │ MCP协议（JSON-RPC over stdio/HTTP）
                     ▼
┌─────────────────────────────────────────────────┐
│  MCP Server                                      │
│  - 注册工具列表                                  │
│  - 接收工具调用请求                              │
│  - 执行工具并返回结果                            │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  实际工具（Playwright/Selenium/API）             │
│  - 浏览器控制                                    │
│  - API 调用                                      │
│  - 文件操作                                      │
└─────────────────────────────────────────────────┘
```

### 1.2 核心概念速览

| 概念 | 说明 | 示例 |
|------|------|------|
| Tool | 工具定义（名称、描述、参数） | navigate(url: str) |
| Resource | 资源定义（URI、内容） | file:///test/result.json |
| Prompt | 提示模板 | "分析错误日志：{error}" |
| Client | MCP 客户端 | AI 模型 |
| Server | MCP 服务端 | Playwright Server |

### 1.3 JSON-RPC 协议示例

MCP 底层使用 JSON-RPC 2.0 协议，所有通信都是 JSON 格式的请求/响应。一个真实的工具调用流程如下：

**客户端发起请求：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**服务端返回工具列表：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "navigate",
        "description": "导航到指定 URL",
        "inputSchema": {
          "type": "object",
          "properties": {
            "url": {"type": "string", "description": "目标 URL"}
          },
          "required": ["url"]
        }
      },
      {
        "name": "click",
        "description": "点击元素",
        "inputSchema": {
          "type": "object",
          "properties": {
            "selector": {"type": "string", "description": "CSS 选择器"}
          },
          "required": ["selector"]
        }
      }
    ]
  }
}
```

**客户端调用工具：**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "navigate",
    "arguments": {
      "url": "http://127.0.0.1:5000/login"
    }
  }
}
```

**服务端返回执行结果：**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"url\": \"http://127.0.0.1:5000/login\", \"title\": \"登录\"}"
      }
    ]
  }
}
```

**错误响应示例：**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32603,
    "message": "Navigation failed: net::ERR_CONNECTION_REFUSED"
  }
}
```

### 1.4 传统方式 vs MCP 方式

**传统方式的问题**——硬编码工具调用，每个场景都要写 if-else：

```python
def run_test(task: str):
    if "登录" in task:
        page.fill("#username", "testuser")
        page.fill("#password", "test123")
        page.click('#loginForm button[type="submit"]')
    elif "搜索" in task:
        page.fill("#search", "test")
        page.click("#search-btn")
    # ... 需要预先编写所有逻辑
```

**MCP 方式**——AI 自动选择工具，无需预判场景：

```python
# MCP 方式：AI 自动选择工具
user: "帮我登录系统，用户名 testuser，密码 test123"

AI: 调用 navigate(url="http://127.0.0.1:5000/login")
AI: 调用 fill(selector="#username", value="testuser")
AI: 调用 fill(selector="#password", value="test123")
AI: 调用 click(selector="#loginForm button[type=submit]")
AI: 调用 screenshot(name="login_result")
```

## 二、Playwright MCP Server 设计

### 2.1 架构设计

```
┌─────────────────────────────────────────────────┐
│  MCP Client (AI Agent)                          │
│  - 理解用户指令                                  │
│  - 选择并调用工具                                │
└────────────────────┬────────────────────────────┘
                     │ MCP协议
                     ▼
┌─────────────────────────────────────────────────┐
│  Playwright MCP Server                          │
│  (mcp_servers/playwright/main.py)               │
│                                                 │
│  注册工具：                                      │
│  - navigate(url)       页面导航                  │
│  - click(selector)     点击元素                  │
│  - fill(selector, val) 填充输入框                │
│  - screenshot(name)    页面截图                  │
│  - get_text(selector)  获取文本                  │
│  - find_elements(sel)  查找元素                  │
│  - get_page_content()  获取页面内容              │
└────────────────────┬────────────────────────────┘
                     │ Playwright API
                     ▼
┌─────────────────────────────────────────────────┐
│  Playwright Browser Pool                        │
│  - 管理多个浏览器实例                            │
│  - 按需创建、用完回收                            │
│  - chromium/firefox/webkit                      │
└─────────────────────────────────────────────────┘
```

### 2.2 工具注册与 BrowserPool

实际生产环境中，多个 AI Agent 可能同时调用 MCP Server。如果只用一个全局浏览器实例，状态会互相干扰。这里引入 `BrowserPool` 来管理浏览器实例的生命周期：

```python
# mcp_servers/playwright/main.py
from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright, Page, Browser
from typing import Dict
import threading

mcp = FastMCP("Playwright Server")

class BrowserPool:
    """浏览器实例池，避免多 Agent 共享同一实例导致状态冲突。"""
    def __init__(self, max_browsers: int = 5):
        self._pool: list = []
        self._lock = threading.Lock()
        self._max = max_browsers
        self._playwright = sync_playwright().start()
    
    def acquire(self) -> Browser:
        with self._lock:
            if self._pool:
                return self._pool.pop()
            return self._playwright.chromium.launch(headless=True)
    
    def release(self, browser: Browser):
        with self._lock:
            if len(self._pool) < self._max:
                self._pool.append(browser)
            else:
                browser.close()
    
    def shutdown(self):
        with self._lock:
            for b in self._pool:
                b.close()
            self._pool.clear()

# 全局 Pool 实例
_pool = BrowserPool(max_browsers=5)
```

每个工具函数通过 Pool 获取独立浏览器实例，避免状态交叉污染。

### 2.3 工具实现

**工具 1：页面导航**

```python
@mcp.tool()
def navigate(url: str) -> Dict:
    """
    导航到指定 URL
    
    Args:
        url: 目标 URL
    
    Returns:
        导航结果
    """
    browser = _pool.acquire()
    try:
        page = browser.new_page()
        # 注意：wait_until="networkidle" 在 Playwright 1.47+ 已标记为 deprecated
        # 新版推荐使用 "load" 或 "domcontentloaded"，配合 page.wait_for_load_state()
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return {
            "success": True,
            "url": page.url,
            "status": response.status,
            "title": page.title()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

**工具 2：点击元素**

```python
@mcp.tool()
def click(selector: str) -> Dict:
    """
    点击元素
    
    Args:
        selector: CSS 选择器
    
    Returns:
        操作结果
    """
    browser = _pool.acquire()
    try:
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.click(selector, timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        return {"success": True, "selector": selector}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

**工具 3：填充输入框**

```python
@mcp.tool()
def fill(selector: str, value: str) -> Dict:
    """
    填充输入框
    
    Args:
        selector: CSS 选择器
        value: 要填充的值
    
    Returns:
        操作结果
    """
    browser = _pool.acquire()
    try:
        page = browser.new_page()
        page.fill(selector, value, timeout=10000)
        return {"success": True, "selector": selector, "value": value}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

**工具 4：页面截图**

```python
import base64

@mcp.tool()
def screenshot(name: str = "screenshot") -> Dict:
    """
    页面截图
    
    Args:
        name: 截图文件名
    
    Returns:
        截图结果 (Base64)
    """
    browser = _pool.acquire()
    try:
        page = browser.new_page()
        data = page.screenshot(full_page=True)
        base64_img = base64.b64encode(data).decode('utf-8')
        
        filepath = f"/tmp/{name}.png"
        with open(filepath, 'wb') as f:
            f.write(data)
        
        return {
            "success": True,
            "filepath": filepath,
            "base64": base64_img[:100] + "..."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

**工具 5：获取文本**

```python
@mcp.tool()
def get_text(selector: str) -> Dict:
    """获取元素文本"""
    browser = _pool.acquire()
    try:
        page = browser.new_page()
        text = page.text_content(selector)
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

**工具 6：查找元素**

```python
@mcp.tool()
def find_elements(selector: str) -> Dict:
    """查找元素"""
    browser = _pool.acquire()
    try:
        page = browser.new_page()
        elements = page.query_selector_all(selector)
        return {
            "success": True,
            "count": len(elements),
            "elements": [
                {"text": el.text_content(), "visible": el.is_visible()}
                for el in elements[:10]
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

**工具 7：获取页面内容**

```python
@mcp.tool()
def get_page_content() -> Dict:
    """获取页面内容"""
    browser = _pool.acquire()
    try:
        page = browser.new_page()
        html = page.content()
        text = page.text_content()
        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "html_length": len(html),
            "text_length": len(text),
            "text_preview": text[:500] + "..." if len(text) > 500 else text
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

## 三、AI Agent 调用 MCP 工具

### 3.1 调用流程

```
用户: "帮我登录系统，用户名 testuser，密码 test123"
  │
  ▼
AI 模型: 分析指令，决定调用工具
  │
  ├─ 调用 navigate(url="http://127.0.0.1:5000/login")
  │    → {"success": True, "url": "...", "title": "登录"}
  │
  ├─ 调用 fill(selector="#username", value="testuser")
  │    → {"success": True, "selector": "#username"}
  │
  ├─ 调用 fill(selector="#password", value="test123")
  │    → {"success": True, "selector": "#password"}
  │
  ├─ 调用 click(selector="#loginForm button[type=submit]")
  │    → {"success": True, "selector": "#loginForm button[type=submit]"}
  │
  └─ 调用 screenshot(name="login_result")
       → {"success": True, "filepath": "/tmp/login_result.png"}
```

### 3.2 工具选择逻辑

AI 模型根据工具描述自动选择最合适的工具：

```python
# 工具描述（AI 模型可见）
tools = [
    {
        "name": "navigate",
        "description": "导航到指定 URL",
        "parameters": {"url": {"type": "string", "description": "目标 URL"}}
    },
    {
        "name": "click",
        "description": "点击元素",
        "parameters": {"selector": {"type": "string", "description": "CSS 选择器"}}
    },
    {
        "name": "fill",
        "description": "填充输入框",
        "parameters": {
            "selector": {"type": "string", "description": "CSS 选择器"},
            "value": {"type": "string", "description": "要填充的值"}
        }
    },
    # ...
]
```

### 3.3 错误处理

```python
# 以下代码为伪代码示意，展示 AI 模型收到错误后的处理流程
# call_tool() 是 MCP 客户端的标准调用方法
# generate_alternatives() 来自第3篇的三层定位降级策略
try:
    result = call_tool("click", {"selector": "#login-btn"})
    if not result["success"]:
        # 尝试备选选择器（generate_alternatives 来自第3篇的三层定位降级策略，
        # 基于 LRU 缓存和语义选择器生成备选列表）
        alternatives = generate_alternatives("#login-btn")
        for alt in alternatives:
            try:
                result = call_tool("click", {"selector": alt})
                if result["success"]:
                    break
            except:
                continue
except Exception as e:
    # 截图记录错误
    call_tool("screenshot", {"name": "error"})
    raise
```

## 四、实战案例：自然语言登录测试

### 4.1 用户指令

```
用户: "帮我测试一下登录功能，用户名 testuser，密码 test123，登录成功后截图"
```

### 4.2 AI 执行过程

```json
{
  "thought": "用户要求测试登录功能，我需要：\n1. 导航到登录页面\n2. 输入用户名\n3. 输入密码\n4. 点击登录按钮\n5. 验证登录成功\n6. 截图",
  "tool_calls": [
    {"tool": "navigate", "arguments": {"url": "http://127.0.0.1:5000/login"}},
    {"tool": "fill", "arguments": {"selector": "#username", "value": "testuser"}},
    {"tool": "fill", "arguments": {"selector": "#password", "value": "test123"}},
    {"tool": "click", "arguments": {"selector": "#loginForm button[type=submit]"}},
    {"tool": "get_text", "arguments": {"selector": "#product-table"}},
    {"tool": "screenshot", "arguments": {"name": "login_success"}}
  ]
}
```

### 4.3 执行结果

```json
{
  "success": true,
  "steps": [
    {"tool": "navigate", "result": {"success": true, "url": "http://127.0.0.1:5000/login"}},
    {"tool": "fill", "result": {"success": true, "selector": "#username"}},
    {"tool": "fill", "result": {"success": true, "selector": "#password"}},
    {"tool": "click", "result": {"success": true, "selector": "#loginForm button[type=submit]"}},
    {"tool": "get_text", "result": {"success": true, "text": "商品A-手机"}},
    {"tool": "screenshot", "result": {"success": true, "filepath": "/tmp/login_success.png"}}
  ]
}
```

## 五、踩坑经验

### 5.1 坑 1：浏览器实例状态混乱

**问题**：多个工具调用共享同一个浏览器实例时，cookie、localStorage、页面状态会互相干扰。

**解决**：用 BrowserPool 管理实例，每个工具调用 acquire/release 独立实例。

```python
browser = _pool.acquire()
try:
    page = browser.new_page()
    # ... 执行操作
finally:
    _pool.release(browser)
```

### 5.2 坑 2：工具超时处理

**问题**：页面加载慢时，工具调用超时。

**解决**：设置合理的超时时间，配合 `wait_until` 参数控制加载策略。

```python
# wait_until="networkidle" 在 Playwright 1.47+ 已 deprecated
# 推荐做法：先用 "domcontentloaded" 等待 DOM 就绪，再单独等待网络空闲
page.goto(url, wait_until="domcontentloaded", timeout=30000)
page.wait_for_load_state("networkidle")
page.click(selector, timeout=10000)
page.fill(selector, value, timeout=10000)
```

### 5.3 坑 3：选择器动态变化

**问题**：前端生成的动态选择器导致工具调用失败。

**解决**：结合第3篇的三层定位降级策略，原始选择器失效时自动生成备选列表。

```python
# generate_alternatives 来自第3篇的三层定位降级策略
# 基于 LRU 缓存的历史选择器 + 语义选择器生成 + OpenCV 视觉定位
# 详见第3篇《定位降级策略：从硬编码到智能自愈》
try:
    page.click(selector)
except:
    alternatives = generate_alternatives(selector)
    for alt in alternatives:
        try:
            page.click(alt)
            break
        except:
            pass
```

### 5.4 坑 4：为什么需要 BrowserPool 而不是全局单例

**问题**：很多教程示例用一个全局 `_browser` 变量，看起来简单，但在多 Agent 并发场景下问题严重：

1. **状态污染**：Agent A 登录后，Agent B 的 `new_page()` 会继承 A 的 cookie，导致权限混乱
2. **并发冲突**：两个 Agent 同时操作同一个 page 对象，Playwright 会抛 `Target closed` 错误
3. **资源泄漏**：一个 Agent 调用了 `browser.close()`，其他 Agent 的后续操作全部失败

**解决**：BrowserPool 的核心价值是隔离。每个工具调用从池中获取独立实例，用完后归还（或关闭），互不影响。池的大小根据服务器资源限制（通常 3-5 个），超出时等待释放。

```python
class BrowserPool:
    def __init__(self, max_browsers=5):
        self._pool = []
        self._lock = threading.Lock()
        self._max = max_browsers
    
    def acquire(self):
        with self._lock:
            if self._pool:
                return self._pool.pop()
            return create_browser()  # 新建
    
    def release(self, browser):
        with self._lock:
            if len(self._pool) < self._max:
                self._pool.append(browser)  # 归还到池
            else:
                browser.close()  # 池已满，直接关闭
```

## 六、总结

MCP协议让 AI 模型调用浏览器工具时不再需要硬编码 if-else，而是通过标准接口动态选择。实际集成时，BrowserPool 是绕不开的——全局单例在单 Agent 场景下没问题，但多 Agent 并发时状态冲突会让你排查到怀疑人生。

配套代码见 `配套代码/mcp/playwright_server.py`，与正文的工具注册逻辑一致，使用全局单例（适合单 Agent 演示场景）。生产环境建议按这篇 2.2 节改为 BrowserPool。

`wait_until="networkidle"` 在 Playwright 1.47+ 已标记为 deprecated，正文工具实现中已改用 `domcontentloaded` + `wait_for_load_state("networkidle")` 的组合方式。

### 6.1 实战：MCP 在测试系统中的实际效果

我们在项目中把 MCP 集成到测试编排层之后，最明显的变化是"测试脚本的编写方式"变了。

**之前**：每个测试场景都要写一套 Playwright 代码——打开页面、找元素、填数据、点按钮、断言结果。一个登录测试就要 20 行代码，100 个场景就是 2000 行。

**之后**：用户用自然语言描述测试场景，AI 自动调用 MCP 工具完成操作。"帮我登录系统，用户名 testuser，密码 test123，然后截图"——一行指令，AI 自动拆分成 navigate → fill → fill → click → screenshot 五个工具调用。

**实际数据**：集成 MCP 后，新测试场景的创建时间从平均 15 分钟（写代码+调试）降到了 2 分钟（写指令+验证）。当然，AI 不是万能的——大约 30% 的场景需要人工调整选择器，但剩下的 70% 确实是一次就跑通了。

### 6.2 实战：MCP 与三层定位降级的配合

MCP 的 `click` 和 `fill` 工具接收选择器参数。如果选择器失效了怎么办？我们在 MCP Server 里集成了第 3 篇的三层定位降级策略：

```python
@mcp.tool()
def click(selector: str) -> Dict:
    """点击元素（支持自动降级）"""
    browser = _pool.acquire()
    try:
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.click(selector, timeout=10000)
        return {"success": True, "selector": selector}
    except Exception as e:
        # 选择器失效，尝试降级
        alternatives = generate_alternatives(selector)  # 来自第3篇
        for alt in alternatives[:5]:  # 最多尝试5个备选
            try:
                page.click(alt, timeout=3000)
                return {"success": True, "selector": alt, "fallback": True}
            except:
                continue
        return {"success": False, "error": str(e)}
    finally:
        _pool.release(browser)
```

这样 AI 调用 `click` 工具时，即使选择器失效了，MCP Server 也会自动尝试备选方案，不需要 AI 重新决策。

### 6.3 实战：什么时候不该用 MCP

MCP 不是银弹。以下场景不建议用 MCP：

1. **高性能要求的场景**——MCP 的 JSON-RPC 通信有额外开销（每次调用约 50-100ms），如果需要每秒执行 100 次点击，直接用 Playwright API 更快。
2. **确定性强的场景**——如果测试流程固定不变（比如每天跑一次的回归测试），写死 Playwright 脚本比让 AI 决策更可靠。
3. **需要精确控制的场景**——MCP 的工具粒度是"点击""输入""导航"，如果你需要精细控制鼠标移动轨迹、模拟触摸手势，MCP 的抽象层次不够。

**MCP 最适合的场景**：探索性测试、用户指令推动的测试、需要 AI 理解页面内容后做决策的场景。

---

