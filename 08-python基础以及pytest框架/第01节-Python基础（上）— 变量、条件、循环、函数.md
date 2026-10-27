# 01-Python基础（上）— 变量、条件、循环、函数

> **配套代码与环境**：请先阅读同级目录 [`test/README.md`](test/README.md) 与 [`test/requirements.txt`](test/requirements.txt)，按其中说明创建虚拟环境并安装依赖，再对照正文运行示例代码。

> 对应代码：`test/tests/test_login_data_driven_example.py`、`test/base/base_page.py`、`test/api/base_api.py`
>

---

## 概念讲解

测试工程师学Python，不需要成为Python专家。

一个中型自动化测试项目（接口+UI），Python代码通常3000-5000行。其中80%的代码只用到最基础的语法：变量、条件、循环、函数。剩下的20%才会涉及类、装饰器、异常处理等进阶内容。

**问题是，很多测试工程师花大量时间学元类、描述符、协程，结果写测试用例的时候连字典取值都写不对。**

方向错了。测试代码的核心诉求不是"写得优雅"，而是"写得清楚"。任何人接手你的测试代码，30秒内应该能看懂这个测试在干什么。

本节只讲最实用的部分。学完这节，你能看懂项目中80%的Python代码。

---

## 测试数据构造要点

### 1. 字符串、列表、字典 — 测试数据的三件套

测试的本质是什么？是**构造输入数据 → 执行操作 → 验证输出结果**。这三步都离不开字符串、列表、字典。

**字符串**用于构造请求参数、验证响应内容、拼接URL。

**列表**用于存储多个测试数据、遍历页面元素、批量断言。

**字典**用于组织结构化数据——请求体、响应体、测试用例配置，几乎全是字典。

来看一个真实项目中的测试数据构造。这是一个数据驱动的登录测试，测试数据从YAML文件加载后变成Python字典列表：

```python
# 从YAML加载的测试数据，每个字典代表一组登录用例
test_data_list = [
    {
        "name": "正常登录",
        "username": "user001@example.com",
        "password": "ValidPass123!",
        "expected_result": "success",
        "error_message": ""
    },
    {
        "name": "密码错误",
        "username": "user001@example.com",
        "password": "wrong_password",
        "expected_result": "fail",
        "error_message": "密码不正确，请重试"
    },
    {
        "name": "账号不存在",
        "username": "nobody@fake.com",
        "password": "AnyPass123!",
        "expected_result": "fail",
        "error_message": "该账号未注册"
    }
]

# 遍历每组数据，执行登录测试
for test_data in test_data_list:
    username = test_data.get("username", "")       # 取字典值，默认空字符串
    password = test_data.get("password", "")
    expected = test_data.get("expected_result", "success")
    
    print(f"执行用例: {test_data['name']}, 用户名: {username}")
    # 接下来会调用登录接口或UI操作...
```

**关键语法点**：
- `dict.get(key, default)` 比 `dict[key]` 安全——键不存在时返回默认值而不是抛异常
- `dict["key"]` 适合确定存在的键（如循环内的 `test_data["name"]`）
- f-string 格式化：`f"文本{变量}"` 是Python 3.6+最推荐的字符串拼接方式

### 2. 条件判断 if/else — 测试验证的分支逻辑

测试用例不是只测"成功"这一条路。一个完整的测试要覆盖：成功路径、失败路径、边界情况。

**if/else 就是用来处理这些分支的。** 来看真实项目中数据驱动测试的验证逻辑：

```python
# 根据预期结果选择不同的验证方式
if expected_result == "success":
    # 成功路径：验证是否跳转到主页
    assert page.is_on_home_page(), "登录应该成功，但跳转失败"
    logger.info(" 验证登录成功")
else:
    # 失败路径：验证是否显示错误提示
    error_text = page.get_error_message()
    assert error_message in error_text, \
        f"应该显示'{error_message}'，实际显示'{error_text}'"
    logger.info(f" 验证登录失败，错误信息正确")
```

**这里有个实战技巧**：断言信息要写得"出了问题一眼就能看出原因"。

```python
#  不好的写法——失败了不知道哪里出了问题
assert page.is_on_home_page()

#  好的写法——失败了直接告诉你预期和实际
assert page.is_on_home_page(), "登录应该成功但跳转失败"
```

### 3. 循环 for/while — 批量处理测试数据

测试中用到循环的场景非常多：

- 遍历一组测试数据，每组执行一次测试
- 遍历页面上的多个元素，逐个验证
- 重试机制：失败后等待重试，直到成功或达到最大次数

**遍历测试数据**是最常见的用法。上面字典示例中已经展示了 `for test_data in test_data_list`。

**遍历页面元素**的场景也很常见。真实项目中有一个"智能元素定位"功能，按优先级尝试多种定位方式：

```python
# 按优先级尝试多种定位方式，直到找到元素为止
locators = [
    ("accessibility_id", "login_button"),      # 第一优先：无障碍ID
    ("resource-id", "com.app:id/login_btn"),   # 第二优先：Android resource-id
    ("id", "login_btn"),                        # 第三优先：通用ID
    ("xpath", "//*[@text='登录']"),             # 最后备选：XPath
]

last_exception = None
for idx, (locator_type, locator_value) in enumerate(locators):
    try:
        element = find_element(locator_type, locator_value, timeout=10)
        logger.info(f" 成功使用 {locator_type} 定位到元素")
        return element  # 找到了，直接返回
    except Exception as e:
        last_exception = e
        logger.debug(f"定位方式 {locator_type} 失败，尝试下一个")
        continue  # 没找到，尝试下一个定位方式

# 所有方式都失败了
raise TimeoutException(f"无法定位元素，最后错误: {last_exception}")
```

**这个模式的核心思想**：优雅降级。优先用最稳定的定位方式（accessibility_id），失败了再退而求其次（XPath）。这在UI自动化中非常实用——页面改版后，只要有一种定位方式还有效，测试就不会挂。

**重试循环**用 `while` 实现：

```python
# 重试机制：最多尝试3次，每次间隔2秒
max_attempts = 3
delay = 2.0
attempt = 0

while attempt < max_attempts:
    try:
        result = click_login_button()  # 可能偶发性失败的操作
        return result  # 成功了，直接返回
    except Exception as e:
        attempt += 1
        if attempt >= max_attempts:
            raise  # 达到最大次数，抛出异常
        logger.warning(f"第{attempt}次尝试失败，{delay}秒后重试: {e}")
        time.sleep(delay)
```

### 4. 函数定义 — 测试工具函数的封装

测试代码中大量重复的操作，应该封装成函数。**判断该不该封装的标准很简单：同一个操作写了两次以上，就该封装。**

来看真实项目中API请求的封装。这是一个HTTP请求的通用方法，所有接口测试都调用它：

```python
def send_request(
    method: str,           # HTTP方法：GET / POST / PUT / DELETE
    endpoint: str,         # API端点：如 "/api/auth/login"
    json_data=None,        # 请求体（JSON格式）
    headers=None,          # 自定义请求头
    timeout=30             # 超时时间（秒）
) -> dict:
    """
    发送HTTP请求的通用方法
    
    返回：
    - 响应体的JSON字典
    """
    # 拼接完整URL
    base_url = "https://api.example.com"
    url = f"{base_url}/{endpoint.lstrip('/')}"
    
    # 合并默认请求头和自定义请求头
    default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if headers:
        default_headers.update(headers)
    
    logger.info(f"发送{method}请求: {url}")
    
    # 发送请求（这里用requests库）
    response = requests.request(
        method=method.upper(),
        url=url,
        json=json_data,
        headers=default_headers,
        timeout=timeout
    )
    
    logger.info(f"响应状态码: {response.status_code}")
    
    # 返回JSON响应
    return response.json()
```

**函数封装的好处**：
1. **统一处理**：所有请求都经过同一个方法，日志、超时、错误处理统一管控
2. **减少重复**：不用在每个测试用例里重复写 `requests.request(...)`
3. **方便修改**：如果要加认证、改超时、加重试，只改这一个函数

---

## 实战案例

以"电商商品管理"为场景，把上面四个知识点串起来。

**场景描述**：电商系统的商品管理流程包含多个步骤——创建商品 → 查询商品列表 → 更新商品信息 → 验证库存变化。每个步骤都是一个API调用，后一步依赖前一步的返回数据。

**测试目标**：用Python基础语法完成整个商品管理流程的测试数据构造和验证。

```python
# ===== 第一步：构造商品测试数据（字典） =====
product_data = {
    "name": f"测试商品_{int(time.time())}",  # 动态生成唯一商品名
    "price": 99.99,
    "stock": 100,
    "description": "自动化测试商品",
    "category": "electronics"
}

# ===== 第二步：定义商品管理流程的步骤（列表） =====
product_steps = [
    {
        "name": "创建商品",
        "method": "POST",
        "endpoint": "/api/products",
        "body": {
            "name": product_data["name"],
            "price": product_data["price"],
            "stock": product_data["stock"],
            "description": product_data["description"]
        },
        "expected_status": 201,
        "validate_fields": ["id", "name", "price"],
        "extract_fields": {
            "product_id": "id"  # 需要提取的商品ID
        }
    },
    {
        "name": "查询商品列表",
        "method": "GET",
        "endpoint": "/api/products",
        "params": {"status": "active"},
        "expected_status": 200,
        "validate_fields": ["name", "price", "stock"]
    },
    {
        "name": "更新商品价格",
        "method": "PUT",
        "endpoint": "/api/products/{product_id}",
        "body": {
            "price": 79.99,
            "stock": 150
        },
        "expected_status": 200,
        "validate_fields": ["id", "name", "price", "stock"]
    },
    {
        "name": "验证库存查询",
        "method": "GET",
        "endpoint": "/api/products/{product_id}/inventory",
        "expected_status": 200,
        "validate_fields": ["product_id", "total_stock"]
    }
]

# ===== 第三步：遍历执行每一步（循环） =====
context = {}  # 用于存储步骤间传递的数据

for step in product_steps:
    logger.info(f"执行步骤: {step['name']}")
    
    # 构造请求体（替换上下文占位符）
    body = step.get("body", {})
    if body:
        for key, value in body.items():
            if isinstance(value, str) and value.startswith("{context:"):
                field_name = value.strip("{}").replace("context:", "")
                body[key] = context.get(field_name, "")
    
    # 替换路径中的动态参数（如 {product_id}）
    endpoint = step["endpoint"]
    for var_name, var_value in context.items():
        endpoint = endpoint.replace("{" + var_name + "}", str(var_value))
    
    # 发送请求
    response = send_request(
        method=step["method"],
        endpoint=endpoint,
        json_data=body if body else None
    )
    
    # ===== 第四步：验证响应（条件判断） =====
    if response.get("code") == "SUCCESS" or response.get("id"):
        logger.info(f" {step['name']} 成功")
        
        # 提取需要传递给下一步的数据
        if "extract_fields" in step:
            for target_key, source_path in step["extract_fields"].items():
                # 从响应中提取数据（如 id、product_id）
                value = response
                for part in source_path.split("."):
                    value = value.get(part, {})
                context[target_key] = value
                logger.info(f"提取字段 {target_key} = {value}")
    else:
        logger.error(f" {step['name']} 失败: {response.get('error', '未知错误')}")
        raise AssertionError(f"步骤 '{step['name']}' 失败")
```

**这个案例展示了什么**：
- 字典组织测试数据 → 列表存储流程步骤 → 循环遍历执行 → 条件判断验证结果
- 四个基础语法点串成了一个完整的测试流程
- `context` 字典实现了步骤间的数据传递（后一步依赖前一步的返回值）
- 路径参数替换（如 `{product_id}`）实现了接口关联

---

## 注意事项和常见坑

- **不要用 `eval()` 或 `exec()` 处理测试数据。** 有些测试框架允许用字符串表达式动态计算值，这有安全风险。用 `dict.get()` 和简单的字符串替换就够了。
- **字典取值优先用 `.get()` 而不是 `[]`。** 测试数据经常有可选字段，`dict["optional_field"]` 在字段缺失时会直接抛异常，`.get("optional_field", default)` 更健壮。
- **循环中的 `continue` 和 `break` 要写清注释。** 别人看你代码时，不知道 `continue` 是"跳过这个继续"还是"出错了跳过"。一行注释就能省别人10分钟。
- **函数参数不要太多（超过5个就该重构）。** 如果函数参数超过5个，考虑用字典或配置对象打包。上面 `send_request()` 的5个参数已经接近上限了。
- **f-string 是Python 3.6+ 特性。** 如果你的测试环境还是Python 2.7（不太可能但万一），需要用 `.format()` 代替。

---

## 总结与思考

> 测试代码的第一目标是"写得清楚"，不是"写得优雅"。能用if/else说清楚的事，不要用装饰器；能用字典存下的数据，不要搞个类。

**思考题**：你在写测试用例时，有没有遇到过"同一个操作写了三次以上"的情况？当时是怎么处理的？有没有封装成函数？


---

## 面试题模块

### 1. 字符串与字典

**Q1：`dict.get(key, default)` 和 `dict[key]` 的区别是什么？测试代码中应该用哪个？**

A：`dict[key]` 在键不存在时抛 `KeyError` 异常，`dict.get(key, default)` 返回默认值而不抛异常。测试代码中优先用 `.get()`，因为测试数据经常有可选字段，用 `[]` 取值在字段缺失时会直接报错，用 `.get()` 更健壮。

### 2. 循环与重试

**Q2：写一个带重试机制的循环，最多重试3次，每次间隔2秒。**

```python
import time

max_attempts = 3
delay = 2.0
for attempt in range(max_attempts):
    try:
        result = do_something_unstable()
        break
    except Exception as e:
        if attempt < max_attempts - 1:
            print(f"第{attempt + 1}次失败，{delay}秒后重试: {e}")
            time.sleep(delay)
        else:
            raise
```

### 3. 函数封装

**Q3：什么情况下应该把代码封装成函数？判断标准是什么？**

A：同一个操作写了两次以上就该封装。测试代码中，重复的 API 请求、元素定位、数据构造都应该封装成函数。封装的好处是统一处理、减少重复、方便修改。

---

