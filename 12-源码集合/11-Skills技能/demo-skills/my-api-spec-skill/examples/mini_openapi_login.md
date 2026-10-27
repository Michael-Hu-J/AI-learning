# 登录接口 OpenAPI 片段（demo）

> 配合 testcase 冒烟点生成 api spec

## POST /api/auth/login

- 描述：手机号 + 密码登录
- Request body:
  - `phone`: string, 11 位手机号
  - `password`: string, 8～20 位
- Responses:
  - `200`: 登录成功，返回 token
  - `401`: 凭证错误
  - `422`: 参数校验失败

## POST /api/auth/register（可选，本期可不写 case）

- 201 注册成功

## 环境

- base_url 测试环境：`${TEST_BASE_URL}`
