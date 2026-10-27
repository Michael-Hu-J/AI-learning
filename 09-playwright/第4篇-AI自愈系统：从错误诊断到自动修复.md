# 第 4 篇：AI自愈系统：从错误诊断到自动修复
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

> 选择器失效之后呢？三层定位降级策略把所有候选都试过了，还是找不到元素。这时候测试直接失败，用户看到一堆红色错误日志，然后手动修改选择器、重新运行——这个循环我们经历过太多次。自愈系统要解决的就是这个问题：让系统自己诊断错误、自己尝试修复，而不是每次都等人工介入。

## 一、自愈系统的架构设计

### 1.1 为什么需要自愈系统？

**传统测试的痛点**：

```python
# 传统测试：选择器失效 → 测试失败 → 人工修复
page.click("#login-btn")  #  Element not found

# → 测试失败
# → 人工查看错误日志
# → 手动修改选择器
# → 重新运行测试
```

**自愈系统的价值**：

```python
# 自愈系统：选择器失效 → 自动诊断 → 自动修复 → 测试继续
page.click("#login-btn")  #  Element not found
# → 自动诊断：元素定位错误
# → 自动修复：尝试备选选择器
# → page.click("button:has-text('登录')")  #  成功！
# → 测试继续
```

### 1.2 自愈架构总览

```
┌─────────────────────────────────────────────────────────┐
│  UI Worker (ui_worker.py)                               │
│  - 步骤执行失败                                          │
│  - 捕获异常                                              │
└────────────────────┬────────────────────────────────────┘
                     │ invoke_healing_subgraph_sync()
                     ▼
┌─────────────────────────────────────────────────────────┐
│  自愈子图（诊断-规划-执行编排）（教学版用策略模式实现）                   │
│                                                         │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│  │ diagnose │────▶│  plan    │────▶│ execute  │        │
│  │ (诊断)   │     │ (规划)   │     │ (执行)   │        │
│  └──────────┘     └──────────┘     └────┬─────┘        │
│       │                                  │              │
│       │    ┌──────────────┐              │              │
│       └───▶│ should_retry?│◄─────────────┘              │
│            └──────────────┘                             │
│              │        │                                 │
│         retry │        │ done                            │
│              ▼        ▼                                 │
│          diagnose    END                                │
└─────────────────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────┐          ┌──────────────┐
│ healer_skill │          │ MCP 工具调用  │
│ (healer.py)  │          │ (healing_mcp) │
└──────────────┘          └──────────────┘
```

### 1.3 自愈触发时机

```python
# ui_worker.py - 步骤执行失败时触发自愈
try:
    if action == "点击元素":
        page.click(selector, timeout=timeout_ms)
except Exception as e:
    stats["failed"] += 1
    step_result["status"] = "failed"
    step_result["error"] = str(e)
    
    # 触发自愈
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
    
    if sg.get("healed"):
        stats["repaired"] += 1
        _push_log(logs, f" [步骤{idx}] 自愈成功", "success")
```

## 二、诊断节点（Diagnose）：错误分类与根因分析

### 2.1 正则模式匹配（第一层诊断）

```python
# healer.py - 错误分类
import re
from typing import Tuple

class HealerSkill:
    def __init__(self):
        self.error_patterns = {
            "network": [
                r"connection\s+refused",
                r"timeout",
                r"network\s+error",
                r"503\s+service\s+unavailable",
            ],
            "element": [
                r"element\s+not\s+found",
                r"no\s+such\s+element",
                r"element\s+not\s+interactable",
                r"stale\s+element",
                r"waiting for locator",
                r"could not find element",
                r"selector.*not found",
            ],
            "assertion": [
                r"assertion\s+failed",
                r"expected.*but\s+got",
                r"mismatch",
            ],
            "authentication": [
                r"401\s+unauthorized",
                r"403\s+forbidden",
                r"token\s+expired",
                r"session\s+expired",
            ],
        }
    
    def _classify_error(self, error_message: str) -> Tuple[str, float]:
        """分类错误类型并返回置信度"""
        error_lower = error_message.lower()
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    return error_type, 0.9
        
        return "unknown", 0.4
```

**实战案例**：

```python
# 错误信息
error = "Timeout: waiting for locator('#login-btn'): Element not found"

# 分类结果
error_type = "element"
confidence = 0.9
```

### 2.2 LLM 兜底诊断（第二层诊断）

> 以下 LLM 诊断为生产版功能，教学版使用纯规则实现。

当正则匹配失败或置信度低时，使用 LLM 进行兜底诊断：

```python
from urllib import request as urllib_request
import json

def _llm_diagnose(self, error_message: str, context: Dict) -> Optional[Dict]:
    """使用 LLM 进行软判决诊断（兜底）。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        return None
    
    prompt = (
        "你是资深测试架构师，请根据错误日志和上下文做诊断。\n"
        "请严格输出 JSON："
        '{"error_type":"network|element|authentication|assertion|business|unknown",'
        '"root_cause":"...",'
        '"suggested_fix":"...",'
        '"confidence":0.0,'
        '"auto_repairable":true}\n\n'
        f"错误日志:\n{error_message}\n\n"
        f"上下文:\n{json.dumps(context or {}, ensure_ascii=False)}"
    )
    
    # 调用 DashScope API
    payload = json.dumps({
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "你是测试故障诊断专家。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 400,
    }).encode("utf-8")
    
    req = urllib_request.Request(
        url=f"{self.llm_base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    
    with urllib_request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        return self._extract_json(content)
```

**LLM 诊断示例**：

输入：

```json
{
  "error_message": "AssertionError: expected '登录成功' but got '用户名或密码错误'",
  "context": {
    "url": "http://127.0.0.1:5000/login",
    "action": "验证文本",
    "selector": ".message"
  }
}
```

LLM 输出：

```json
{
  "error_type": "assertion",
  "root_cause": "登录失败，可能是用户名或密码错误",
  "suggested_fix": "检查测试数据或业务逻辑是否变更",
  "confidence": 0.85,
  "auto_repairable": false
}
```

### 2.3 诊断结果结构

```python
diagnosis = {
    "error_type": "element",              # 错误类型
    "confidence": 0.9,                    # 置信度 (0-1)
    "root_cause": "元素不存在或选择器错误",  # 根本原因
    "suggested_fix": "尝试使用更稳定的选择器", # 修复建议
    "auto_repairable": True,              # 是否可自动修复
    "repair_strategy": "element_locator_repair",  # 修复策略
    "diagnosis_source": "regex",          # 诊断来源：regex/llm
}
```

## 三、规划节点（Plan）：修复策略选择

### 3.1 策略模式设计

```python
# healer.py - 策略接口
class RepairStrategy(ABC):
    """修复策略接口（策略工厂模式）。"""
    
    name: str = "base"
    
    @abstractmethod
    def match(self, diagnosis: Dict) -> bool:
        """判断是否匹配该策略"""
        pass
    
    @abstractmethod
    def execute(self, error_message: str, context: Dict) -> Dict:
        """执行修复"""
        pass
```

### 3.2 四种核心策略

**策略 1：元素定位修复**

```python
class ElementRepairStrategy(RepairStrategy):
    name = "element_locator_repair"
    
    def match(self, diagnosis: Dict) -> bool:
        return diagnosis.get("error_type") == "element"
    
    def execute(self, error_message: str, context: Dict) -> Dict:
        from locator.visual_repair import (
            build_semantic,
            opencv_to_selectors,
        )
        
        original_selector = context.get("selector", "")
        alternatives = []
        
        # ID → XPath 转换
        if original_selector.startswith("#"):
            id_value = original_selector[1:]
            alternatives.append(f"//*[@id='{id_value}']")
        
        # Class → XPath 转换
        if original_selector.startswith("."):
            class_value = original_selector[1:]
            alternatives.append(f"//*[@class*='{class_value}']")
        
        # 语义选择器生成
        raw_step = context.get("raw_step", {})
        target = context.get("selector", "")
        value = context.get("value")
        alternatives.extend(
            build_semantic(raw_step, target, value)
        )
        
        # 视觉修复（可选）
        page = context.get("page")
        if page is not None:
            alternatives.extend(opencv_to_selectors(page))
        
        # 去重
        seen = set()
        dedup = [s for s in alternatives if s and s not in seen and not seen.add(s)]
        
        return {
            "action": "retry_with_alternatives",
            "original_selector": original_selector,
            "alternative_selectors": dedup[:40],
            "success": len(dedup) > 0,
        }
```

**策略 2：认证刷新**

```python
class AuthRefreshStrategy(RepairStrategy):
    name = "auth_refresh"
    
    def match(self, diagnosis: Dict) -> bool:
        return diagnosis.get("error_type") == "authentication"
    
    def execute(self, error_message: str, context: Dict) -> Dict:
        return {
            "action": "refresh_token",
            "success": True,
            # mock_token_ 为模拟实现，实际项目中使用真实的 Token 刷新接口
            "new_token": "mock_token_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "expires_in": 3600,
        }
```

**策略 3：网络重试**

```python
class NetworkRetryStrategy(RepairStrategy):
    name = "network_retry"
    
    def match(self, diagnosis: Dict) -> bool:
        return diagnosis.get("error_type") == "network"
    
    def execute(self, error_message: str, context: Dict) -> Dict:
        max_retries = int(context.get("max_retries", 2))
        current_retry = int(context.get("current_retry", 0))
        
        if current_retry >= max_retries:
            return {
                "action": "retry_request",
                "success": False,
                "reason": "已达到最大重试次数",
            }
        
        return {
            "action": "retry_request",
            "success": True,
            "retry_count": current_retry + 1,
            "delay_seconds": 5 * (current_retry + 1),
        }
```

**策略 4：断言调整**

```python
class AssertionAdjustStrategy(RepairStrategy):
    name = "assertion_adjust"
    
    def match(self, diagnosis: Dict) -> bool:
        return diagnosis.get("error_type") == "assertion"
    
    def execute(self, error_message: str, context: Dict) -> Dict:
        # 断言失败通常意味着业务逻辑变了，而不是选择器的问题
        # 因此我们不自动修复，只给出建议并标记为不可自动修复
        return {
            "action": "adjust_assertion",
            "success": False,
            "auto_repairable": False,
            "reason": "断言失败通常意味着业务逻辑变更，需要人工确认",
            "suggestions": [
                "使用模糊匹配代替精确匹配",
                "添加容差范围",
                "检查测试数据是否稳定",
            ],
        }
```

### 3.3 策略选择逻辑

```python
def _select_strategy(self, diagnosis: Dict) -> Optional[RepairStrategy]:
    """根据诊断结果选择修复策略"""
    for strategy in self.strategies:
        if strategy.match(diagnosis):
            return strategy
    return None

# 策略列表（按优先级）
self.strategies = [
    ElementRepairStrategy(),      # 元素定位修复
    AuthRefreshStrategy(),        # 认证刷新
    NetworkRetryStrategy(),       # 网络重试
    AssertionAdjustStrategy(),    # 断言调整
]
```

## 四、执行节点（Execute）：修复执行与重试

### 4.1 修复执行流程

```python
# healing_graph.py - 执行节点
async def _heal_execute_node(state: HealingSubState) -> Dict[str, Any]:
    diagnosis = state.get("diagnosis", {})
    context = dict(state.get("context", {}))
    context["current_retry"] = state.get("current_attempt", 0)
    context["max_retries"] = state.get("max_retries", 2)
    context["error_message"] = state.get("error_message", "")
    
    # 1. 调用 MCP 工具（可选）
    planned_tools = (state.get("repair_plan") or {}).get("tool_actions") or []
    tool_calls = []
    for t in planned_tools:
        tool_name = t.get("tool_name", "").strip()
        if tool_name:
            tool_result = await safe_call_tool(tool_name, t.get("arguments") or {})
            tool_calls.append(tool_result)
    
    # 2. 执行修复策略
    repair_result = healer_skill.execute_repair(diagnosis, context)
    
    # 3. 判断是否修复成功
    tool_success = any(x.get("success") for x in tool_calls)
    healed = repair_result.get("success") or tool_success
    
    return {
        "repair_result": repair_result,
        "tool_calls": tool_calls,
        "healed": healed,
        "current_attempt": state.get("current_attempt", 0) + 1,
        "heal_log": state.get("heal_log", []) + [
            f"execute:{repair_result.get('action', 'none')}:{healed}",
            f"tool_success:{sum(1 for x in tool_calls if x.get('success'))}/{len(tool_calls)}",
        ],
    }
```

### 4.2 条件重试逻辑

```python
def _heal_should_retry(state: HealingSubState) -> str:
    """判断是否应该重试"""
    # 已修复 → 结束
    if state.get("healed"):
        return "done"
    
    # 达到最大重试次数 → 结束
    if state.get("current_attempt", 0) >= state.get("max_retries", 2):
        return "done"
    
    # 不可自动修复 → 结束
    if not state.get("repair_plan", {}).get("auto_repairable", False):
        return "done"
    
    # 重试
    return "retry"
```

### 4.3 自愈流程图

```
测试步骤失败
     │
     ▼
┌──────────┐
│ diagnose │ ← diagnose:{error_type}:{confidence}
└────┬─────┘
     │
     ▼
┌──────────┐
│  plan    │ ← plan:{strategy}
└────┬─────┘
     │
     ▼
┌──────────┐
│ execute  │ ← execute:{action}:{healed}
└────┬─────┘
     │
     ▼
┌──────────────┐
│ should_retry?│
└──────┬───────┘
       │
  ┌────┴────┐
  │         │
healed?  max_retries?
  │         │
  ▼         ▼
 END      retry → diagnose
```

## 五、实战案例：一次完整的自愈流程

### 5.1 场景：登录按钮选择器失效

```python
# 测试步骤
step = {
    "action": "点击元素",
    "target": "#login-btn",  # 前端重构后失效
    "value": ""
}

# 执行失败
error = "Timeout: waiting for locator('#login-btn'): Element not found"
```

### 5.2 自愈流程

```python
# 1. 诊断
diagnosis = {
    "error_type": "element",
    "confidence": 0.9,
    "root_cause": "元素不存在或选择器错误",
    "auto_repairable": True,
    "repair_strategy": "element_locator_repair"
}

# 2. 规划
repair_plan = {
    "strategy": "element_locator_repair",
    "auto_repairable": True,
    "tool_actions": []
}

# 3. 执行
repair_result = {
    "action": "retry_with_alternatives",
    "original_selector": "#login-btn",
    "alternative_selectors": [
        "//*[@id='login-btn']",
        "button:has-text('登录')",
        "[role='button']",
    ],
    "success": True
}

# 4. 重试
healed = True  #  使用备选选择器成功
```

### 5.3 自愈记录

```python
self_healing_plans.append({
    "test": "step_4",
    "diagnosis": {
        "error_type": "element",
        "confidence": 0.9,
        "root_cause": "元素不存在或选择器错误",
        "auto_repairable": True,
    },
    "repair": {
        "action": "retry_with_alternatives",
        "alternative_selectors": [
            "//*[@id='login-btn']",
            "button:has-text('登录')",
        ],
        "success": True,
    },
    "healed": True,
    "heal_log": [
        "diagnose:element:0.9",
        "plan:element_locator_repair",
        "tools:0",
        "execute:retry_with_alternatives:True",
    ],
    "tool_calls": [],
})
```

### 5.4 实际运行日志

下面是自愈系统在实际项目中的一次完整运行日志，可以看到从错误发生到自愈成功的全过程：

```
[步骤3] 点击 #login-btn → 失败: Timeout: waiting for locator('#login-btn'): Element not found
[自愈] 触发自愈子图，session_id=exec_20260515_001
[自愈] diagnose: element (confidence=0.90, source=regex)
[自愈]   root_cause: 元素不存在或选择器错误
[自愈]   repair_strategy: element_locator_repair
[自愈] plan: element_locator_repair
[自愈]   生成备选选择器:
[自愈]     [1] //*[@id='login-btn']
[自愈]     [2] button:has-text('登录')
[自愈]     [3] [role='button']
[自愈]     [4] a:has-text('登录')
[自愈] execute: retry_with_alternatives
[自愈]   尝试 [1] //*[@id='login-btn'] → 失败: 元素不存在
[自愈]   尝试 [2] button:has-text('登录') → 成功!
[自愈] 自愈成功，耗时 2.3s
[步骤3] 自愈成功，继续执行后续步骤...
```

可以看到整个自愈过程在 2.3 秒内完成，读者可以直观地看到系统是如何一步步诊断、生成备选方案、最终找到可用选择器的。

## 六、踩坑经验

### 6.1 坑 1：同步/异步混用导致事件循环冲突

**问题**：UI Worker 是同步环境，但 LangGraph 子图是异步的。

**解决**：提供同步入口，在独立线程中运行 asyncio.run()。

```python
def invoke_healing_subgraph_sync(...):
    async def _run():
        return await invoke_healing_subgraph_async(...)
    
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())
    
    # 已有事件循环，在独立线程中运行
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(asyncio.run, _run())
        return fut.result(timeout=180)
```

### 6.2 坑 2：LLM 诊断延迟过高

**问题**：LLM 调用需要 1-3 秒，影响测试性能。

**解决**：正则匹配优先，LLM 仅作为兜底。

```python
# 正则匹配优先
error_type, confidence = self._classify_error(error_message)

# 仅在必要时使用 LLM
if error_type == "unknown" or confidence < 0.8:
    llm_result = self._llm_diagnose(error_message, context)
```

### 6.3 坑 3：策略匹配顺序影响修复效果

**问题**：多个策略可能同时匹配，顺序影响结果。

**解决**：按优先级排序策略列表。

```python
self.strategies = [
    ElementRepairStrategy(),      # 最常用，优先匹配
    AuthRefreshStrategy(),        # 认证问题
    NetworkRetryStrategy(),       # 网络问题
    AssertionAdjustStrategy(),    # 断言问题
]
```

### 6.4 坑 4：自愈循环导致无限重试

**问题**：修复失败后重试，可能无限循环。

**解决**：设置最大重试次数。

```python
def _heal_should_retry(state):
    if state.get("current_attempt", 0) >= state.get("max_retries", 2):
        return "done"
    return "retry"
```

## 七、写在最后

自愈系统的核心逻辑就三步：诊断 → 规划 → 执行。听起来简单，但每一步都有坑。

诊断阶段最容易翻车的是误判。我们一开始把 "timeout" 只归入 network 类，结果一个 "waiting for locator" 的错误被诊断成网络超时，走了重试策略而不是备选选择器策略。后来加了 Playwright 特有的错误模式（`waiting for locator`、`selector.*not found`），让 element 类优先匹配定位器超时，误判率明显下降了。

规划阶段的问题是策略优先级。ElementRepairStrategy 必须排在最前面，因为元素定位错误是最常见的。如果 AuthRefreshStrategy 排在前面，一个 "401" 错误可能先被当成认证问题处理，但实际上只是某个按钮的选择器不对。

执行阶段最需要注意的是重试上限。我们一开始没设 max_retries，结果一个定位失败 → 修复失败 → 重试 → 再失败的循环跑了 10 多分钟。后来加了 `max_retries=2`，超过两次就放弃，直接标记失败。

基于我们的实际项目经验，元素定位类错误的自愈成功率在 85% 左右——这意味着绝大多数选择器失效问题可以自动解决。但断言失败的自愈成功率只有 50%，因为断言失败往往意味着业务逻辑变了，而不是选择器的问题。

下一篇讲视觉语义定位，这是三层定位和自愈系统都失败之后的最后一道防线。

---

## 附：运行时自愈 vs 脚本自愈

本篇 `healer/strategies.py` 解决的是 **跑的时候救**（备选选择器、网络重试、Token 刷新）。**脚本自愈** 解决的是 **跑完后改 pytest 源码**（定位器字符串、断言文案）。二者互补。

| 类型 | 典型手段 | 失败示例 | 本课 | Skill |
|------|----------|----------|------|-------|
| **运行时自愈** | 备选 selector、重试、刷新 Token | `#login-btn` 找不到 | **第 4 篇** | 弱 |
| **脚本自愈** | 改 `test_*.py`、更新 expect | 业务文案从「登录」改成「Sign in」 | 概念 | **UI-skills/自我修复** |

```
步骤执行失败
    │
    ├─ Element not found ──► 本篇：ElementRepairStrategy 换备选 selector
    │
    └─ 断言文案/URL 预期变了 ──► 多半要改脚本；可 @ Skill 做最小补丁
```



---

## 八、总结

这篇把自愈系统的架构和实现走了一遍，核心就四个要点：

**规则引擎比 LLM 更适合做自愈主体。** 我们最开始想用 LLM 做自愈，后来发现正则模式匹配 + 策略模式已经能覆盖 80% 的场景。"element not found" → 换选择器，"401" → 刷新 Token，"timeout" → 重试。这些规则比 LLM 更快、更准、更便宜。LLM 只作为兜底，处理规则覆盖不到的边缘情况。

**策略模式是自愈系统的核心。** 每种错误类型对应一个修复策略，策略之间互不依赖。新增一种错误类型，只需要加一个新策略类，不需要改现有代码。这就是开闭原则——对扩展开放，对修改关闭。我们项目里有 7 个策略类，从写第一个到写第七个，每个的复杂度都一样，没有因为数量增加而变复杂。

**重试上限是保命符。** 没有上限的重试就是死循环。我们踩过这个坑——定位失败 → 修复失败 → 重试 → 再失败，跑了 10 多分钟。加 `max_retries=2` 之后，最多尝试 3 次就放弃。失败不可怕，可怕的是失败之后还不停地在失败。

**自愈成功率不是 100%。** 元素定位类错误的自愈成功率在 85% 左右，断言失败的自愈成功率只有 50%。剩下的 15-50% 怎么办？答案是：标记失败，通知人工。说白了，自愈不是为了炫技，是为了让我少加班。

配套代码里的 `healer/diagnostic.py` 和 `healer/strategies.py` 是这套系统的简化版，去掉了 LangGraph，用策略模式 + 工厂模式替代。`tests/test_healer.py` 有 19 个测试用例覆盖所有策略。先跑通测试，再看代码理解逻辑。

---
