# 第13节-混合测试执行器 — API + UI 的协同执行

> 对应代码：`配套代码/test/core/hybrid_test_executor.py`
>
> 说明：本节讲解当一个测试用例需要同时使用接口测试和 UI 测试时，如何协调执行。

---

## 这节讲什么

有些测试用例，光靠接口测试或 UI 测试都不够。

比如"验证用户注册后能登录"这个用例：
1. 需要先通过接口创建用户（数据准备）
2. 再通过 UI 验证登录流程（用户体验）

如果只用接口测试：验证不了 UI 层面的问题（比如按钮没响应、页面跳转错误）
如果只用 UI 测试：数据准备太慢（需要通过 UI 手动填写注册表单）

**混合测试**就是为了解决这个问题：接口负责数据准备，UI 负责体验验证。两者协同，各取所长。

---

## 核心思路

混合测试的执行流程：

```yaml
测试用例
  ↓
步骤 1: 接口准备数据（高效、稳定）
  ↓
步骤 2: UI 验证功能（覆盖用户体验）
  ↓
汇总结果
```

### 为什么需要混合测试？

| 场景 | 纯接口测试 | 纯 UI 测试 | 混合测试 |
|------|-----------|-----------|---------|
| 数据准备 |  快 |  慢 |  接口准备 |
| 用户体验验证 |  覆盖不了 |  全覆盖 |  UI 验证 |
| 执行时间 | 1-2 秒 | 30-60 秒 | 15-30 秒 |
| 稳定性 | 高 | 低（依赖设备） | 中 |

混合测试折中了时间和覆盖度：用接口高效准备数据，用 UI 验证核心体验。

---

## 实战案例

### 案例：用户注册后登录

```yaml
name: "验证用户注册后能成功登录"
test_type: hybrid  # 明确指定混合测试

# 接口步骤：准备测试数据
api_steps:
  - action: "post"
    path: "/api/register"
    json:
      username: "testuser"
      password: "test123"
    expect_status: 201

# UI 步骤：验证登录体验
steps:
  - action: "click"
    target: "login_button"
  - action: "input"
    target: "username_field"
    value: "testuser"
  - action: "input"
    target: "password_field"
    value: "test123"
  - action: "click"
    target: "submit_button"
  - action: "verify"
    target: "welcome_text"
    expect: "欢迎，testuser"
```

执行流程：
1. **接口阶段**：调用 `/api/register` 创建用户（1 秒）
2. **UI 阶段**：打开登录页面，输入账号密码，点击登录，验证欢迎文本（15 秒）
3. **汇总**：两个阶段都通过才算通过

---

## 代码实现

核心代码在 `core/hybrid_test_executor.py`：

```python
class HybridTestExecutor:
    def execute(self, test_case, driver=None, api_client=None):
        test_type = TestRouter.determine_test_type(test_case)
        
        if test_type == TestType.HYBRID:
            return self._execute_hybrid_test(test_case, driver, api_client)
    
    def _execute_hybrid_test(self, test_case, driver, api_client):
        result = {
            "test_case": test_case["name"],
            "test_type": "hybrid",
            "api_result": {},
            "ui_result": {}
        }
        
        # 步骤 1: 接口准备数据
        api_steps = test_case.get("api_steps", [])
        if api_steps and api_client:
            api_result = self._execute_api_test(
                {"name": "数据准备", "steps": api_steps}, 
                api_client
            )
            result["api_result"] = api_result
            
            # 接口失败则直接返回
            if api_result["status"] == "failed":
                result["status"] = "failed"
                result["message"] = "接口数据准备失败"
                return result
        
        # 步骤 2: UI 验证
        ui_steps = test_case.get("steps", [])
        if ui_steps and driver:
            ui_result = self._execute_ui_test(
                {"name": test_case["name"], "steps": ui_steps}, 
                driver
            )
            result["ui_result"] = ui_result
            
            if ui_result["status"] == "failed":
                result["status"] = "failed"
                result["message"] = "UI 验证失败"
                return result
        
        # 都通过
        result["status"] = "passed"
        result["message"] = "混合测试通过"
        return result

---

## 注意事项

### 1. 接口失败的处理

如果接口数据准备失败，**不要继续执行 UI 步骤**。因为 UI 验证依赖接口准备的数据，数据没准备好，UI 验证必然失败。

**建议**：接口失败时立即返回，记录错误信息，方便排查是接口问题还是环境问题。

### 2. UI 失败的截图

UI 验证失败时，**一定要截图**。因为 UI 问题往往是视觉层面的（比如元素没显示、布局错乱），光看日志看不出问题。

**建议**：在 `_execute_ui_test` 的 except 块中调用 `driver.get_screenshot_as_file()`，保存失败时的页面状态。

### 3. 数据清理

混合测试完成后，**需要清理接口创建的数据**。否则多次执行会积累大量测试数据，影响后续测试。

**建议**：在测试用例的 `teardown` 阶段添加清理步骤，或者使用唯一用户名（如 `testuser_12345`）避免冲突。

### 4. 执行顺序

**必须先接口后 UI**，不能反过来。因为 UI 验证依赖接口准备的数据。如果先执行 UI，数据还没准备好，验证必然失败。

---

## 混合测试的适用场景

混合测试不是万能药，它适合特定的场景。以下是判断"该不该用混合测试"的参考标准：

**适合用混合测试的场景：**

- **注册→登录→下单**：数据准备用接口（快），核心流程用 UI 验证（全）
- **后台配置→前端展示**：接口修改配置，UI 验证展示效果
- **批量数据准备→单点验证**：接口批量创建 100 条数据，UI 验证分页/搜索/筛选
- **跨系统协作**：接口调用外部系统触发事件，UI 验证本系统响应

**不适合用混合测试的场景：**

- **纯 UI 交互验证**：比如动画效果、手势操作、拖拽排序——这些跟接口无关，纯 UI 测试就行
- **纯接口压力测试**：比如并发 1000 请求——不需要 UI，接口测试更合适
- **用例数量少的项目**：混合测试增加了用例设计的复杂度，小项目用不上

**判断标准**：如果一个测试场景满足"数据准备耗时 > UI 验证耗时"或者"数据准备步骤 > 3 步"，就值得考虑混合测试。否则，选纯 API 或纯 UI 更简单。
