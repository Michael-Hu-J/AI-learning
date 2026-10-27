# 04-pytest 断言体系 — assert 不只是判断真假

> 对应代码：`test/tests/test_login_example.py`、`test/tests/test_login_data_driven_example.py`
>

---

## 概念讲解

Python 自带的 assert 和 pytest 的 assert，看起来一模一样，但失败时的表现天差地别。

**Python 原生 assert 失败时**：

```python
assert [1, 2, 3] == [1, 2, 4]
# 输出：AssertionError（就这五个字，没了）
```

**pytest assert 失败时**：

```python
assert [1, 2, 3] == [1, 2, 4]
# 输出：
# E   AssertionError: assert [1, 2, 3] == [1, 2, 4]
# E     At index 2 diff: 3 != 4
# E     Full diff:
# E       [
# E            1,
# E            2,
# E     -      4,
# E     +      3,
# E       ]
```

**看到了吗？pytest 直接告诉你哪里不同、第几个元素不同、完整 diff 长什么样。**

这就是 pytest 的 assert 重写（assertion rewriting）机制——它在字节码层面拦截了你的 assert 语句，替换成了能输出详细 diff 的版本。

**assert 失败后你不需要再去翻日志、截图、加 print 来定位问题。pytest 已经把答案摆在你面前了。**

---

## 常用断言模式

### 1. 常用断言写法

pytest 的断言就是 Python 的 `assert` 语句，加上 pytest 的自动 diff 能力。

**基本断言**：

```python
# 相等断言
assert response.status_code == 200
assert data["code"] == "SUCCESS"

# 不等断言
assert error_message != ""
assert result is not None

# 包含断言
assert "登录成功" in page.get_text()
assert "admin" in user_roles

# 布尔断言
assert page.is_on_home_page()
assert not page.has_error_message()

# 类型断言
assert isinstance(response.json(), dict)
assert isinstance(data["items"], list)
```

**这些和 Python 原生 assert 完全一样，但 pytest 会让失败信息更有用。**

来看一个真实项目中的验证逻辑：

```python
# 数据驱动测试中的验证
if expected_result == "success":
    # 成功路径：验证跳转到主页
    assert page.is_on_home_page(), "登录应该成功但跳转失败"
else:
    # 失败路径：验证错误提示
    error_text = page.get_error_message()
    assert error_message in error_text, \
        f"应该显示'{error_message}'，实际显示'{error_text}'"
```

**注意断言信息的写法**：`assert condition, "失败时的提示信息"`。这条信息会在断言失败时显示，帮助你快速定位问题。

### 2. 复杂断言 — 列表、字典的 diff 输出

pytest 最强大的地方在于复杂数据结构的 diff。

**列表比较**：

```python
expected_roles = ["user", "admin", "editor"]
actual_roles = ["user", "admin", "viewer"]

assert actual_roles == expected_roles

# 失败时输出：
# E   AssertionError: assert ['user', 'admin', 'viewer'] == ['user', 'admin', 'editor']
# E     At index 2 diff: 'viewer' != 'editor'
# E     Full diff:
# E       [
# E            'user',
# E            'admin',
# E     -      'editor',
# E     +      'viewer',
# E       ]
```

**字典比较**：

```python
expected_response = {
    "code": "SUCCESS",
    "message": "SUCCESS",
    "data": {
        "userId": "U123456",
        "nickname": "test_user",
        "status": "ACTIVE"
    }
}

actual_response = response.json()

assert actual_response == expected_response

# 失败时输出：
# E   AssertionError: assert {'code': 'FAILED', 'message': '...'} == {'code': 'SUCCESS', ...}
# E     Omitting 1 identical items, use -vv to show
# E     Differing items:
# E     {'code': 'FAILED'} != {'code': 'SUCCESS'}
# E     {'message': '...'} != {'message': 'SUCCESS'}
```

**实际测试中，你不需要断言整个响应体**。通常只断言关键字段：

```python
# 只断言关键字段，不关心 userId 这种动态生成的值
assert actual_response["code"] == "SUCCESS"
assert actual_response["message"] == "SUCCESS"
assert actual_response["data"]["status"] == "ACTIVE"
assert "userId" in actual_response["data"]  # 只要存在就行，值不重要
```

### 3. pytest.approx() — 浮点数比较

性能测试中经常需要比较浮点数（如响应时间、吞吐量）。浮点数有精度问题，不能直接用 `==`。

```python
import pytest

#  错误写法——浮点数精度问题导致断言失败
response_time = 0.30000000000000004
assert response_time == 0.3  # 失败！

#  正确写法——用 approx 指定容差
assert response_time == pytest.approx(0.3, rel=0.01)  # 相对误差1%
assert response_time == pytest.approx(0.3, abs=0.01)  # 绝对误差0.01
```

**参数说明**（与 pytest 官方 `approx` 行为一致，勿按字面误解）：
- `rel`：相对容差（默认 `1e-6`）
- `abs`：绝对容差（默认 `0`）
- 做 `==` 比较时，判定可直观理解为：**「实际与期望之差的绝对值」不超过 `rel × |期望| + abs`**（`rel` 与 `abs` 都传时也是这一条合成公式，而不是「rel、abs 各判一遍、两个都要单独成立」）。

**性能测试中的实用场景**：

```python
# 验证响应时间在预期范围内
avg_response_time = calculate_avg_time(response_times)
assert avg_response_time == pytest.approx(0.5, rel=0.2)  # 预期0.5秒，允许±20%波动

# 验证多个响应时间都在合理上界（上界 3 秒，允许 +0.5 秒抖动；语义比拿 approx 做 < 更清晰）
for rt in response_times:
    assert rt <= 3.0 + 0.5, f"单次响应时间超过上界: {rt}s"
```

### 4. pytest.raises() — 验证异常是否被正确抛出

有些测试场景需要验证"应该抛出异常"。比如传入无效参数时，函数应该 raise ValueError。

```python
import pytest

# 验证特定异常被抛出
with pytest.raises(ValueError):
    parse_config("invalid_yaml_content")

# 验证异常信息
with pytest.raises(ValueError, match="无效的YAML格式"):
    parse_config("invalid_yaml_content")

# 验证异常对象（可以进一步检查异常属性）
with pytest.raises(ValueError) as exc_info:
    parse_config("invalid_yaml_content")

assert "line 3" in str(exc_info.value)  # 检查异常信息中包含行号
```

**真实项目中的场景**：验证 API 基类在连接失败时正确抛出异常。

```python
def test_api_connection_error():
    """验证API连接失败时抛出ConnectionError"""
    api = BaseAPI(base_url="http://nonexistent-host:9999")
    
    with pytest.raises(requests.exceptions.ConnectionError):
        api.get("/api/some-endpoint")
```

### 5. 自定义断言失败信息

`assert condition, "失败信息"` 的第二个参数是自定义失败信息。

**好的失败信息应该包含**：
- 预期是什么
- 实际是什么
- 在什么场景下失败

```python
#  不好的失败信息——看不出哪里出了问题
assert response.status_code == 200

#  好的失败信息——失败了直接告诉你原因
assert response.status_code == 200, \
    f"注册接口应该返回200，实际返回{response.status_code}，" \
    f"响应体: {response.text[:200]}"
```

---

## 实战案例

以"商品管理接口测试"为场景，展示多种断言的综合使用。

**场景描述**：商品管理流程包含多个API调用，每个调用都需要验证响应状态码、响应结构、关键字段。

```python
import pytest
import requests
from api.base_api import BaseAPI


class TestProductAPI:
    """商品接口测试"""
    
    def test_product_crud_flow(self, api_client):
        """完整的商品管理流程测试"""
        
        # ===== 步骤1：创建商品 =====
        response = api_client.post("/api/products", json_data={
            "name": "测试商品",
            "price": 99.99,
            "stock": 100,
            "description": "自动化测试商品"
        })
        
        # 断言1：状态码
        assert response.status_code == 201, \
            f"创建商品接口应该返回201，实际返回{response.status_code}"
        
        # 断言2：响应结构
        data = response.json()
        assert "id" in data, "响应必须包含id字段"
        assert "name" in data, "响应必须包含name字段"
        assert "price" in data, "响应必须包含price字段"
        
        # 断言3：验证字段值
        assert data["name"] == "测试商品", \
            f"商品名称应该匹配，实际是{data['name']}"
        assert data["price"] == 99.99, \
            f"商品价格应该是99.99，实际是{data['price']}"
        
        product_id = data["id"]
        
        # ===== 步骤2：查询商品列表 =====
        response = api_client.get("/api/products")
        data = response.json()
        assert response.status_code == 200
        assert isinstance(data, list), "商品列表应该是数组类型"
        assert len(data) > 0, "商品列表不应为空"
        
        # ===== 步骤3：更新商品价格 =====
        response = api_client.put(f"/api/products/{product_id}", json_data={
            "price": 79.99,
            "stock": 150
        })
        
        data = response.json()
        assert response.status_code == 200
        assert data["price"] == 79.99, \
            f"更新后价格应该是79.99，实际是{data['price']}"
        assert data["stock"] == 150, \
            f"更新后库存应该是150，实际是{data['stock']}"
        
        # 断言4：验证库存查询
        response = api_client.get(f"/api/products/{product_id}/inventory")
        data = response.json()
        assert response.status_code == 200
        assert "total_stock" in data, "库存查询应该返回total_stock字段"
        assert data["total_stock"] >= 0, \
            f"库存数量不应为负数，实际是{data['total_stock']}"
```

**这个案例展示了什么**：
- 状态码断言：`assert response.status_code == 200`
- 类型断言：`assert isinstance(data, list)`
- 值相等断言：`assert data["price"] == 79.99`
- 范围断言：`assert data["total_stock"] >= 0`
- 自定义失败信息：每个 assert 都附带了失败时的提示信息

---

## 注意事项和常见坑

- **不要用 `assert True` 当占位符**。有些测试用例写到最后忘了加真正的断言，就写 `assert True` 凑数。这等于没测——永远通过，没有任何验证价值。
- **断言不要太多**。一个测试用例 3-5 个断言比较合理。超过10个说明这个测试做的事情太多了，应该拆成多个测试。
- **`pytest.raises` 的 `match` 参数用正则匹配**。`match="无效"` 会匹配任何包含"无效"的异常信息。如果需要精确匹配，用 `match="^无效参数$"`。
- **浮点数比较一定要用 `approx`**。直接 `assert 0.1 + 0.2 == 0.3` 会失败（浮点数精度问题），这是很多测试工程师踩过的第一个坑。
- **断言失败信息不要写太长**。超过200字符的信息在终端里显示不全，反而影响阅读。关键信息放前面，详细数据放日志里。

---

## 总结与思考

> pytest 的 assert 重写机制让断言失败从"猜谜游戏"变成了"看图说话"。diff 信息已经摆在你面前了，别再写 `assert True` 糊弄自己。

**思考题**：你遇到过最"难排查"的断言失败是什么样的？最后是怎么定位到问题的？


---

## 面试题模块

### 1. 断言重写

**Q1：pytest 的 assert 和 Python 原生 assert 失败时的表现有什么区别？**

A：Python 原生 assert 失败只输出 `AssertionError`（就五个字）。pytest 会输出详细的 diff 信息——哪个元素不同、完整列表对比。这是因为 pytest 在字节码层面重写了 assert 语句（assertion rewriting）。

### 2. 断言信息

**Q2：`assert page.is_on_home_page()` 和 `assert page.is_on_home_page(), "登录应该成功但跳转失败"` 有什么区别？**

A：前者失败时只告诉你"断言失败了"，后者失败时直接告诉你"预期是什么、实际是什么"。在 CI 日志中，后者能让你 3 秒定位问题，前者需要翻日志、截图、加 print。

### 3. 复杂断言

**Q3：怎么断言两个字典相等但忽略某些字段？**

A：pytest 没有内置的"忽略字段"断言。常用做法是：
1. 手动比较需要的字段：`assert data["code"] == 0 and data["message"] == "success"`
2. 用第三方库：`pytest-assume` 支持多个独立断言
3. 用 `dict.items()` 比较：`assert expected.items() <= actual.items()`（检查 expected 的所有键值对都在 actual 中）

---

