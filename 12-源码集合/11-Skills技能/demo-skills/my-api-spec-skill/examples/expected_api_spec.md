---
kind: api_pytest
base_url: ${TEST_BASE_URL}
cases:
  - id: TC-API-001
    method: POST
    path: /api/auth/login
    json_body:
      phone: "13800138000"
      password: "ValidPass123"
    expect_status: 200
  - id: TC-API-002
    method: POST
    path: /api/auth/login
    json_body:
      phone: "13800138000"
      password: "WrongPassword"
    expect_status: 401
  - id: TC-API-003
    method: POST
    path: /api/auth/login
    json_body:
      phone: "1380013800"
      password: "ValidPass123"
    expect_status: 422
---

# 用户登录 API 冒烟 spec

依据：`smoke_testcases.md` P0 场景 + `mini_openapi_login.md`

| case id | 追溯 SM | 说明 |
|---------|---------|------|
| TC-API-001 | SM-001 | 正确手机号密码 → 200 |
| TC-API-002 | SM-002 | 密码错误 → 401 |
| TC-API-003 | SM-003 | 手机号 10 位 → 422 |

## 生成与运行（专业版包）

```bash
./generate.sh demo-skills/my-api-spec-skill/output/login_api_smoke.md
cd output && pytest login_api_smoke.py -v
```

## 待澄清

| # | 问题 |
|---|------|
| 1 | 422 vs 400：OpenAPI 未明确非法手机号状态码，当前按 422 |
