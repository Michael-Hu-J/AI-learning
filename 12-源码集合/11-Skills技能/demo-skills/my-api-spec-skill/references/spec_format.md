# api_pytest spec 格式（demo 版）

## Frontmatter 必填

```yaml
---
kind: api_pytest          # 固定值
base_url: http://...      # 或 ${TEST_BASE_URL}
cases:
  - id: TC-API-001        # 唯一，建议与测试点追溯
    method: POST          # GET POST PUT DELETE PATCH
    path: /api/auth/login
    json_body:            # 可选
      phone: "13800138000"
      password: "ValidPass123"
    expect_status: 200
---
```

## cases 常用字段

| 字段 | 说明 |
|------|------|
| `id` | 用例编号 |
| `method` | HTTP 方法 |
| `path` | 路径，可含 `{id}` |
| `json_body` | POST/PUT  body |
| `headers` | 额外请求头 |
| `expect_status` | 期望 HTTP 状态码 |
| `expect_json` | 可选 JSON 子集断言 |

## 与专业版 generate.sh 的关系

本 demo 只生成 spec 文件。有 `skills-专业版V2.0` 时：

```bash
cd skills-专业版V2.0
./generate.sh /path/to/login_api_smoke.md
cd output && pytest --collect-only login_api_smoke.py
```

## 编号约定（demo）

- 前缀 `TC-API-`，三位数字
- 与冒烟测试点 `SM-xxx` 在正文追溯表中关联
