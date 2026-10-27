---
kind: api_pytest
base_url: http://127.0.0.1:5000
auth:
  type: bearer_login
  login_path: /api/auth/login
  username_field: username
  password_field: password
  username_env: TEST_USERNAME
  password_env: TEST_PASSWORD
cases:
  - id: API-001
    method: GET
    path: /api/products
    no_auth: true
    expect_status: 200
  - id: API-002
    method: POST
    path: /api/products
    json_body:
      name: "声明式商品"
      price: 19.9
      stock: 5
    expect_status: 201
---

# 声明式 API 冒烟（教学示例）

本文件是 **第 22 节路径二** 的最小 spec 示例，用于理解 `kind: api_pytest` 的结构。

**本课程仓库不包含 `generate.sh`**。

运行前（对接秒杀演示系统时）：

```bash
export TEST_USERNAME=admin
export TEST_PASSWORD=admin123
export TEST_BASE_URL=http://127.0.0.1:5000
```
