# 第14节-断言与验证 — Validator 的设计

> 对应代码：`core/validator.py`、`testcases/yaml/login_test_cases.yaml`
>
> 说明：本节所有代码示例均来自一个真实的移动端自动化测试项目，业务名称和API路径已做模糊化处理。

---

验证逻辑如果散落在每个测试函数里，改一个验证规则就要改 N 个地方。`Validator` 把验证抽象成规则引擎：测试用例只传数据 + 规则，`Validator` 返回 `(passed, message)` 元组。配套代码见 `core/validator.py`。

## Validator 接口总览

`Validator` 提供三个静态方法：

```python
# API 响应验证
Validator.validate_api_response(response_data, expected)

# UI 元素验证
Validator.validate_ui_element(driver, element_locator, expected)

# 预期结果格式解析
Validator.parse_expected(expected)
```

每个方法都返回 `tuple[bool, str]`：第一个元素表示是否通过，第二个是详细错误信息。

## validate_api_response — API 响应验证

```python
@staticmethod
def validate_api_response(response_data: Any, expected: Dict[str, Any]) -> tuple[bool, str]:
```

### 参数说明

`response_data` 可以是 dict、JSON 字符串或原始响应对象。内部会尝试 `json.loads()` 解析字符串。`expected` 字典支持三种验证方面：

1. **`status_code`** — 验证 HTTP 状态码
2. **`contains`** — 验证响应体包含指定文本
3. **`fields`** — 字段级精确/规则验证

```python
# core/validator.py 中的使用示例
from core.validator import Validator

response = {
    "status_code": 200,
    "response": {
        "code": "SUCCESS",
        "message": "注册成功",
        "data": {
            "userId": "u_12345",
            "count": 1
        }
    }
}

expected = {
    "status_code": 200,
    "contains": "成功",
    "fields": {
        "code": "SUCCESS",
        "message": {"contains": "成功"},
        "data.userId": {"exists": True},
        "data.count": {"gte": 1}
    }
}

passed, msg = Validator.validate_api_response(response, expected)
assert passed, msg

### 字段路径支持嵌套和数组索引

`_get_nested_field` 方法支持用点号分隔的路径，以及数组索引语法 `items[0]`：

```python
# data.items[0].name → response["data"]["items"][0]["name"]
```python

路径层级没有硬性限制，但建议不超过 4 层，否则调试报错时追踪路径很麻烦。比如 `data.items[0].order.detail` 还能接受，再深就该考虑重构响应结构了。

### 字段验证规则对照表

| 规则 | 示例 | 说明 |
|------|------|------|
| 精确匹配 | `"code": "SUCCESS"` | expected 不是 dict 时走简单相等比较 |
| `exists` | `{"exists": True}` | 字段是否存在，不关心值 |
| `contains` | `{"contains": "成功"}` | 字符串包含匹配 |
| `gt` / `gte` | `{"gte": 1}` | 数值比较，内部 `float()` 转换 |
| `lt` / `lte` | `{"lt": 100}` | 数值比较 |
| `regex` | `{"regex": "^test.*"}` | 正则匹配，使用 `re.match` |
| `type` | `{"type": "int"}` | Python 类型名比较 |

## validate_ui_element — UI 元素验证

```python
@staticmethod
def validate_ui_element(driver, element_locator: Dict[str, str], expected: Dict[str, Any]) -> tuple[bool, str]:
```python

`element_locator` 格式为 `{"type": "id", "value": "com.example:id/btn_login"}`。底层调用 `BasePage.find_element`。支持的验证方面：

- **`exists`** — 布尔值，控制元素是否存在
- **`text`** — 精确文本匹配
- **`text_contains`** — 文本包含匹配
- **`enabled`** — 是否可点击
- **`displayed`** — 是否可见
- **`attribute`** — 任意属性验证，如 `{"attribute": {"content-desc": "登录"}}`

```python
from core.validator import Validator

locator = {"type": "accessibility_id", "value": "btn_login"}
expected = {
    "exists": True,
    "text": "登录",
    "displayed": True,
    "enabled": True
}

passed, msg = Validator.validate_ui_element(driver, locator, expected)

## parse_expected — 灵活格式适配

如果从 YAML 或配置中读到的 `expected` 字段是纯字符串（比如只用文本包含验证），`parse_expected` 会自动包装成字典格式：

```python
Validator.parse_expected("成功")    # → {"contains": "成功"}
Validator.parse_expected(200)       # → {"equals": 200}
Validator.parse_expected({"status_code": 200})  # → 原样返回
```

## 常见踩坑记录

### 坑 1：`_validate_field` 中 `exists=False` 的处理

当 `expected` 中写 `{"exists": False}` 时，代码里的逻辑是：

```python
if "exists" in expected:
    should_exist = expected["exists"]
    actually_exists = actual_value is not None
    if should_exist != actually_exists:
        return False, ...
    return True, ""

如果你期望字段**不存在**，但响应里字段值为 `None`，`_get_nested_field` 返回 `None`，`actually_exists` 为 `False`，所以 `should_exist=False` 且 `actually_exists=False`，验证通过。但如果你期望字段不存在，而字段实际有值，会报错：

```
字段 data.id 存在性不匹配: 期望 不存在, 实际 存在
```python

### 坑 2：数值比较抛 ValueError

```python
if "gt" in expected:
    try:
        if float(actual_value) <= float(expected["gt"]):
            return False, ...
    except (ValueError, TypeError):
        return False, f"字段 {field_path} 无法比较大小, 实际值: {actual_value}"

字段值是字符串 `"abc"` 或者 `None` 时，`float()` 直接抛异常，错误信息形如：

```python
字段 data.count 无法比较大小, 实际值: None
```

所以数值类型的字段要先确认值不是 `None`，或者用 `type` 规则先验证类型。

### 坑 3：`_validate_field` 中 expected 是 dict 时的短路逻辑

看这段代码：

```python
if isinstance(expected, dict):
    if "exists" in expected:
        ...
        return True, ""    # ← 早期 return
    if actual_value is None:
        return False, f"字段 {field_path} 不存在"
```

如果 rules 里有 `exists` 且验证通过，就直接 `return True`，**不会继续验证 contains/gt/regex 等**。换句话说 `{"exists": True, "regex": "^test"}` 这种配置，exists 通过后 regex 根本不执行。想同时验证存在性和内容，只能用两条独立规则或者分两次调 `_validate_field`。

### 坑 4：`validate_api_response` 中 `contains` 是对整个响应体做字符串匹配

```python
if "contains" in expected:
    expected_text = str(expected["contains"]).lower()
    actual_text = str(actual_data).lower()
    if expected_text not in actual_text:
        return False, f"响应中不包含预期文本: {expected['contains']}"

注意 `actual_data` 可能是从 `response_data["response"]` 提取的，也可能是整个 `response_data`。如果你传入了包含 `status_code` 和 `response` 的完整字典，`contains` 检查的是 `response` 子字段的内容。如果传的是裸 JSON，则检查整个 dict 的字符串表示。这会导致一种隐蔽的问题：大响应体被 `str()` 后可能误匹配到意料之外的子串。建议用 `fields` 里的 `contains` 做字段级匹配，更精确。

### 坑 5：UI 元素验证超时不一致

`validate_ui_element` 内部对 `exists` 检查用了 `timeout=3`，但后续获取元素用了 `timeout=5`。如果元素加载较慢（超过 3 秒但不超过 5 秒），`exists` 检测会认为元素不存在：

```
元素存在性不匹配: 期望 存在, 实际 不存在
```

而如果你跳过 `exists` 直接验证 `text`，反而不超时。所以在慢速页面上要么统一调大 `BasePage.find_element` 的默认超时，要么先等元素稳定再传给 Validator。

## 配合 YAML 用例的使用模式

测试用例在 YAML 中定义 `expected` 字段，框架调用 `Validator.parse_expected` 解析后传入 `validate_api_response`：

```yaml
# 注册接口测试用例
- name: register-step1
  api: /api/auth/register/step1
  method: POST
  body:
    email: "test@example.com"
    recommendTag: "FRIEND_REF"
  expected:
    status_code: 200
    fields:
      code: SUCCESS
      message:
        contains: 成功
      data.email:
        exists: true
        regex: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      data.userId:
        type: str
      data.count:
        gte: 1

YAML 中的 `expected` 直接对应 `Validator.validate_api_response` 的第二个参数。改验证规则改 YAML 即可，`Validator` 不需要改动。
