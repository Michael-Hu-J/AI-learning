# 第 5 篇：视觉语义定位——当 CSS/XPath 失效时
> **代码说明**：本文中的代码示例来自完整版系统，配套代码（`配套代码/` 目录）提供了功能一致的简化版——去掉了 LLM API、LangGraph、数据库等外部依赖，替换为纯规则实现 + JSON 文件 + 内置演示应用。文章讲原理，配套代码可本地跑通，两相对照效果更好。

语义定位示例中的占位邮箱等字段，可与「电商秒杀与财务一体化」注册/登录表单（`http://127.0.0.1:5000`）中的真实控件含义对应。演示用户见 `demo_app/app.py` 中的 `USERS`；若联调独立部署的外部项目，演示数据以该项目为准。

> **函数名说明**：正文中函数名为 `build_semantic`，配套代码（`配套代码/locator/visual_repair.py`）中简化为 `build_semantic`，功能一致。

## 一、为什么需要视觉语义定位？

### 1.1 传统选择器的局限性

```html
<!-- 场景 1：动态生成的 Class -->
<div class="css-1a2b3c">
  <button class="btn-primary css-4d5e6f">登录</button>
</div>
<!-- 每次构建，class 都不同 -->

<!-- 场景 2：无 ID 的表单 -->
<form>
  <input type="email" placeholder="请输入邮箱" />
  <input type="password" placeholder="请输入密码" />
  <button type="submit">登录</button>
</form>
<!-- 没有 ID，只能用 placeholder 定位 -->

<!-- 场景 3：国际化页面 -->
<button>Login</button>  <!-- 英文 -->
<button>登录</button>    <!-- 中文 -->
<button>ログイン</button> <!-- 日文 -->
<!-- text= 选择器依赖语言 -->
```

### 1.2 视觉语义定位的优势

| 定位方式 | 稳定性 | 适用场景 |
|---------|--------|---------|
| CSS 选择器 |  低 | 前端稳定时 |
| XPath |  低 | DOM 结构固定时 |
| data-testid |  高 | 需要前端配合 |
| text= |  中 | 文本不变时 |
| role= |  中 | ARIA 角色稳定时 |
| 视觉语义 |  高 | 任何场景 |

## 二、语义选择器生成

### 2.1 关键词提取

```python
# visual_repair.py - 从步骤中提取关键词
def _keywords(raw_step: Dict, target: str, value: Any) -> List[str]:

    hints = raw_step.get("locator_hints") or {}
    if not isinstance(hints, dict):
        hints = {}
    
    parts = []
    
    # 从 hints 提取
    for key in ("text", "label", "aria", "placeholder"):
        v = hints.get(key)
        if v and isinstance(v, str):
            parts.append(v.strip())
    
    # 从 value 提取
    if value and isinstance(value, str) and value.strip():
        parts.append(value.strip())
    
    # 从 target 提取（如果不是选择器格式）
    t = (target or "").strip()
    if t and not t.startswith(("#", ".", "/", "[", "xpath", "text=", "role=")):
        parts.append(t)
    
    # 去重
    seen = set()
    out = []
    for p in parts:
        if not p or len(p) > 120:
            continue
        low = p.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(p)
    
    return out[:12]
```

### 2.2 语义选择器生成

```python
def build_semantic(
    raw_step: Dict,
    target: str,
    value: Any,
    *,
    latency_anomaly: bool = False,
) -> List[str]:
    """
    生成 Playwright 引擎可识别的选择器串（与现有 page.click 兼容）。
    latency_anomaly 为 True 时优先插入文案/角色锚点（预测性维护路径）。
    """
    kws = _keywords(raw_step, target, value)
    candidates = []
    
    for kw in kws:
        safe = kw.replace("'", "\\'")
        candidates.extend([
            f"text={kw}",
            f"button:has-text('{safe}')",
            f"div:has-text('{safe}')",
            f"a:has-text('{safe}')",
            f"[aria-label*='{safe}']",
            f"[placeholder*='{safe}']",
            f"role=button[name='{safe}']",
        ])
    
    # 延迟异常时：文案锚点前置
    if latency_anomaly and kws:
        for kw in reversed(kws[:5]):
            candidates.insert(0, f"text={kw}")
    
    # 去重
    seen = set()
    dedup = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    
    return dedup[:24]
```

**关于 `latency_anomaly` 参数**：当系统检测到页面响应延迟异常（如接口超时、资源加载缓慢）时，元素可能还没渲染完成。此时将文案锚点（`text=`）前置到候选列表头部，优先尝试最简单的文本匹配——因为即使页面没完全加载，已渲染的文本内容通常已经可用。这在预测性维护场景（提前发现页面异常）中特别有用。

**关于 `div:has-text()` 和 `a:has-text()` 的区分**：虽然 `div:has-text()` 覆盖面最广（绝大多数元素都是 div 的后代），但 `a:has-text()` 专门针对链接元素。当操作目标是链接（如"点击下一页"）时，`a:has-text()` 的精确度更高，不会误匹配到包含相同文本的按钮或 div 容器。同理 `button:has-text()` 专门针对按钮。生成候选时按宽到窄排列，Playwright 会按顺序尝试，精确度高的选择器自然排在后面作为兜底。

### 2.3 实战案例：登录表单定位

```python
# 输入
raw_step = {
    "action": "输入文本",
    "target": "#email-input",  # 已失效
    "value": "buyer@seckill.demo",
    "locator_hints": {
        "placeholder": "请输入邮箱",
        "label": "邮箱地址",
    }
}

# 关键词提取
kws = ["请输入邮箱", "邮箱地址", "buyer@seckill.demo"]

# 语义选择器生成
candidates = [
    "text=请输入邮箱",
    "button:has-text('请输入邮箱')",
    "div:has-text('请输入邮箱')",
    "a:has-text('请输入邮箱')",
    "[aria-label*='请输入邮箱']",
    "[placeholder*='请输入邮箱']",  #  成功！
    "role=button[name='请输入邮箱']",
    "text=邮箱地址",
    "button:has-text('邮箱地址')",
    "[aria-label*='邮箱地址']",
    "[placeholder*='邮箱地址']",
    "role=button[name='邮箱地址']",
    "text=buyer@seckill.demo",
    # ...
]
```

## 三、OpenCV 颜色检测定位

### 3.1 原理

当页面出现异常（如红色高亮错误提示）时，通过 OpenCV 检测红色区域，定位到异常元素：

```
┌─────────────────────────────────────────┐
│  1. 页面截图                              │
│     page.screenshot(type="png")         │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  2. 转换为 HSV 色彩空间                   │
│     cv2.cvtColor(img, COLOR_BGR2HSV)    │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  3. 检测红色区域                          │
│     cv2.inRange(hsv, (0,60,50), (10,255,255)) │
│     cv2.inRange(hsv, (170,60,50), (180,255,255)) │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  4. 查找轮廓                              │
│     cv2.findContours(mask, ...)         │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  5. 计算形心                              │
│     cx = x + bw/2, cy = y + bh/2       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  6. 坐标映射到 DOM                        │
│     document.elementFromPoint(cx, cy)   │
└─────────────────────────────────────────┘
```

### 3.2 代码实现

```python
def opencv_red_regions_to_selectors(page: Any, max_regions: int = 4) -> List[str]:
    """
    在视口截图上检测偏红色高亮区域，取形心映射回 DOM，生成 xpath= 备选。
    未安装 OpenCV 或失败时返回空列表。
    """
    try:
        import numpy as np
        import cv2
    except Exception:
        return []
    
    try:
        # 1. 截图
        png = page.screenshot(type="png")
        arr = np.frombuffer(png, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        
        if img is None:
            return []
        
        # 2. 转换为 HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 3. 检测红色区域（红色在 HSV 中有两个区间）
        m1 = cv2.inRange(hsv, (0, 60, 50), (10, 255, 255))
        m2 = cv2.inRange(hsv, (170, 60, 50), (180, 255, 255))
        mask = cv2.bitwise_or(m1, m2)
        
        # 4. 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []
        
        h, w = img.shape[:2]
        
        # 5. 按面积排序，取最大的几个
        scored = sorted(contours, key=cv2.contourArea, reverse=True)[:15]
        out = []
        
        for cnt in scored:
            area = cv2.contourArea(cnt)
            if area < (w * h) * 0.0001:  # 过滤太小的区域
                continue
            
            x, y, bw, bh = cv2.boundingRect(cnt)
            cx = int(x + bw / 2)
            cy = int(y + bh / 2)
            
            # 6. 坐标映射到 DOM
            alt = selector_from_point(page, cx, cy)
            if alt:
                out.append(alt)
            
            if len(out) >= max_regions:
                break
        
        return out
    except Exception:
        return []
```

### 3.3 坐标映射到 DOM

```python
def selector_from_point(page: Any, cx: int, cy: int) -> Optional[str]:
    """在浏览器内由视口坐标得到 Playwright 可用选择器（id / text= / 标签）。"""
    try:
        sel = page.evaluate(
            """([x, y]) => {
            const el = document.elementFromPoint(x, y);
            if (!el || el.nodeType !== 1) return null;
            if (el.id) return '#' + el.id;
            const txt = (el.innerText || '').trim().slice(0, 80);
            if (txt) return 'text=' + txt;
            return el.tagName.toLowerCase();
          }""",
            [cx, cy],
        )
        if sel and isinstance(sel, str) and sel.strip():
            return sel.strip()
    except Exception:
        return None
    return None
```

### 3.4 实战案例：错误提示定位

```python
# 场景：表单提交后出现红色错误提示
# <div class="error-message" style="color: red;">用户名或密码错误</div>

# OpenCV 检测
selectors = opencv_red_regions_to_selectors(page)
# → ['.error-message', 'text=用户名或密码错误']

# 验证文本
body = page.content()
assert "用户名或密码错误" in body  #  成功
```

## 四、视觉语义定位的集成

### 4.1 在定位解析器中的集成

```python
# ui_locator_resolver.py - 视觉语义定位集成
def resolve(self, page, step):
    target = step.get("target", "")
    value = step.get("value", "")
    hints = step.get("locator_hints", {})
    action = step.get("action", "")
    page_url = page.url
    
    # 先查缓存
    cached = self._resolve_cache(page_url, action, target)
    if cached:
        return {"found": True, "selector": cached, "level": "CACHE"}
    
    # L0_SEM: 视觉语义定位（可选）
    if isinstance(hints, dict) and hints.get("prefer_visual_semantic"):
        from .visual_repair import build_semantic
        
        sem = build_semantic(step, target, value, latency_anomaly=True)
        selector0, attempts0 = self._first_working_selector(page, sem, "L0_SEM")
        if selector0:
            return {
                "found": True,
                "selector": selector0,
                "level": "L0_SEM",
                "attempts": attempts0,
            }
    
    # L1, L2, L3 ...
    # ...
```

### 4.2 在自愈系统中的集成

```python
# healer.py - ElementRepairStrategy
class ElementRepairStrategy(RepairStrategy):
    def execute(self, error_message: str, context: Dict) -> Dict:
        from ..services.visual_repair import (
            build_semantic,
            opencv_red_regions_to_selectors,
        )
        
        original_selector = context.get("selector", "")
        alternatives = []
        
        # 语义选择器生成
        raw_step = context.get("raw_step") or {}
        target = str(context.get("selector") or "")
        value = context.get("value")
        
        if isinstance(raw_step, dict):
            alternatives.extend(
                build_semantic(
                    raw_step, target, value
                )
            )
        
        # 视觉修复（可选）
        page = context.get("page")
        if page is not None:
            try:
                alternatives.extend(opencv_to_selectors(page))
            except Exception:
                pass
        
        # 去重
        seen = set()
        dedup = [s for s in alternatives if s and s not in seen and not seen.add(s)]
        
        return {
            "action": "retry_with_alternatives",
            "original_selector": original_selector,
            "alternative_selectors": dedup[:40],
            "success": len(dedup) > 0,
            "visual_path_used": bool(page) and prefer_visual,
        }
```

## 五、实战：语义定位在真实项目中的表现

### 5.1 场景：前端用了 CSS Modules

CSS Modules 会把 `.btn-primary` 编译成 `.btn-primary__abc123`，每次构建都不一样。这时候 CSS 选择器完全失效。

我们的处理方式：

```python
# 不用 CSS class，用 text= 定位
page.click("text=登录")  # 不管 class 怎么变，"登录"这两个字不变

# 或者用 placeholder
page.fill("[placeholder='请输入邮箱']", "test@example.com")
```

**实际效果**：在我们项目中，CSS Modules 导致的选择器失效占了所有定位问题的 40%。换成 text= 和 placeholder 定位后，这部分问题降到了 0。

### 5.2 场景：动态表单

秒杀系统的购物车表单是动态生成的——用户添加商品后才出现对应的输入框。测试时如果直接用 `#cart-item-1` 这种带序号的选择器，每次商品顺序一变就失效。

处理方式：

```python
# 不用序号定位
# page.fill("#cart-item-1-quantity", "2")  # 商品顺序一变就失效

# 用上下文定位
page.locator("tr:has-text('iPhone 15') input[type='number']").fill("2")
# "找到包含 'iPhone 15' 的那一行，填里面的数量输入框"
```

**关键思路**：用"内容 + 结构"代替"序号 + ID"。商品顺序会变，但"iPhone 15 旁边有个数量输入框"这个关系不会变。

### 5.3 场景：国际化页面

如果产品面向多语言用户，按钮文字会随语言变化：

```python
# 不好：依赖具体语言
page.click("text=登录")   # 中文环境有效
page.click("text=Login")  # 英文环境有效

# 好：用 role + 语义
page.click("role=button[name='登录']")  # 中文
page.click("role=button[name='Login']") # 英文
```

更好的做法是让前端加上 `data-testid`：

```html
<button data-testid="login-btn">登录</button>
<button data-testid="login-btn">Login</button>
```

```python
page.click("[data-testid='login-btn']")  # 语言无关
```

**这是最稳定的方案**，但需要前端配合。如果前端不配合，text= 和 role= 就是最佳替代。

### 5.4 场景：表单验证错误定位

表单提交后的验证错误提示，一般有固定的 DOM 结构（比如 `class="error-message"` 的 div）。但前端重构后，class 名字可能会变。这时用语义定位更可靠：

```python
# 重构前
error = page.locator(".error-message.has-error")  # class 会变

# 重构后——用文本定位，改不了
page.wait_for_selector("text=用户名不能为空")

# 或者用 role + 描述
page.wait_for_selector("[role='alert']")
```

**注意**：text= 选择器是"包含"匹配，不是"精确"匹配。`text=用户名` 会匹配到"用户名"和"用户名不能为空"两个元素。如果你要精确匹配，用引号包裹：`text='用户名不能为空'`。

### 5.5 场景：弹窗/Modal 定位

Modal 组件通常是页面加载完成后动态创建的，普通选择器可能找不到。因为 Modal 可能有透明遮罩层挡住后面的元素：

```python
# 场景：点击"确认删除"后弹出 Modal
# <div class="modal-backdrop"></div>  # 透明遮罩
# <div class="modal">
#   <p>确认删除此商品？</p>
#   <button id="confirm-delete">确认</button>
# </div>

# 用语义定位，绕过遮罩层直接找到按钮
page.locator(".modal button:has-text('确认')").click()

# 或者用 role
page.locator("role=button[name='确认']").click()
```

**踩过的坑**：用 `page.click("text=确认")` 可能会点到遮罩层而不是 Modal 里的按钮。因为遮罩层在 Modal 上面，它可能也有"确认"文本。解决方法是加上上下文限定——只查找 Modal 内部的"确认"按钮。

---

## 附一、先写测试意图，再写定位（截图 / 原型）

第 3 篇解决 **怎么点得到**；在点之前要先回答 **测什么**。只有截图、没有稳定 URL 时，建议先产出「给人看的测试意图表」，再写 JSON 步骤或 pytest。

示例（本仓库，非 Agent 实现）：

```bash
cat 配套代码/examples/page_intent_example.md
```

流程：

```
截图/原型 → page_intent（意图表）→ locator_tiers JSON（第3篇附）→ worker 步骤 / pytest
```

---

## 附二、两种「视觉」：语义定位 vs 像素回归

| 类型 | 本篇重点 | 何时用 | 本课 demo | Skill 模板 |
|------|----------|--------|-----------|------------|
| **语义 / 关键词** | `build_semantic`、OpenCV 红字 | DOM 不稳、仍有可见文案 | `test_visual.py` | — |
| **像素截图回归** | 整页 PNG 与基线 diff | 改版怕「布局挤歪」 | `test_snapshot_demo.py` | `visual_regression.md` |

语义定位 **不能替代** 像素回归：文案不变但 CSS 把按钮挤出视口时，语义仍可能「成功」。像素回归成本高，只覆盖 **少数关键页**。

```bash
cd 配套代码
# 需 demo_app；首次生成基线
pytest tests/test_snapshot_demo.py --update-snapshots -v
pytest tests/test_snapshot_demo.py -v
```

本课只掌握 **概念 + 上面命令**。

---

## 六、踩坑经验

### 6.1 坑 1：OpenCV 依赖问题

**问题**：OpenCV 体积大（~50MB），不是所有环境都安装。

**解决**：可选依赖，未安装时自动跳过。

```python
try:
    import numpy as np
    import cv2
except Exception:
    return []  # 未安装 OpenCV，返回空列表
```

### 6.2 坑 2：颜色检测误判

**问题**：页面中红色元素很多（如红色按钮、红色图标），导致误判。

**解决**：过滤面积太小的区域，只保留显著的红色区域。

```python
area = cv2.contourArea(cnt)
if area < (w * h) * 0.0001:  # 至少占页面 0.01%
    continue
```

### 6.3 坑 3：坐标映射失败

**问题**：视口坐标可能映射到不可见元素或遮挡元素。

**解决**：使用 `elementFromPoint` 获取最顶层可见元素。

```python
const el = document.elementFromPoint(x, y);
if (!el || el.nodeType !== 1) return null;
```

### 6.4 坑 4：语义选择器过长

**问题**：关键词提取过多，生成大量候选选择器。

**解决**：限制关键词数量（最多 12 个），候选选择器数量（最多 24 个）。

```python
return out[:12]  # 关键词限制
return dedup[:24]  # 候选限制
```

## 七、总结

视觉语义定位的核心思路是：当 DOM 结构不可靠时，退回到"页面上能看到什么"这个最直接的方面。文本内容、ARIA 标签、placeholder 这些属性比 CSS class 稳定得多——前端重构时 class 会变，但"请输入邮箱"这个提示文字不会随便改。

实际使用中，视觉语义定位不是要替代 CSS/XPath，而是作为降级策略的兜底层。正常的 L1（data-testid）→ L2（contains）→ L3（语义）三级降级已经覆盖了 95% 以上的场景，OpenCV 颜色检测属于锦上添花，在错误提示定位这种特定场景下才有价值。

配套代码中函数名简化为 `build_semantic`，与正文的 `build_semantic` 功能完全一致，见 `配套代码/locator/visual_repair.py`。

---

