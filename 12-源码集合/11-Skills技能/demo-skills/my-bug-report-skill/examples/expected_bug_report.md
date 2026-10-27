# 缺陷报告草稿 — BUG-demo-001

> 状态：Draft，需人工 triage 后提交工单

## 基本信息

| 字段 | 值 |
|------|-----|
| 缺陷编号 | BUG-demo-001 |
| 标题 | 登录接口：合法凭证返回 401 invalid credentials |
| 严重程度 | High |
| 缺陷类型 | 功能 |
| 当前状态 | Draft |
| 优先级 | P1 |
| 分流 | 产品待确认（非连接类错误） |

## 发现信息

- 发现时间：（生成时填写）
- 发现人：自动化测试
- 发现方式：自动化 pytest
- 关联用例：SM-001 / TC-API-001
- pytest nodeid：`output/login_api_smoke.py::test_tc_api_001`

## 问题描述

**接口类缺陷（草稿）**

```
接口地址：POST /api/auth/login
请求体：{"phone": "13800138000", "password": "ValidPass123"}

预期返回：200，登录成功
实际返回：401，{"error":"invalid credentials"}
```

## 环境信息

| 字段 | 值 |
|------|-----|
| TEST_BASE_URL | http://127.0.0.1:8080 |

## 失败摘要

```
AssertionError: {"error":"invalid credentials"}
assert 401 == 200
output/login_api_smoke.py:28: AssertionError
```

## 建议下一步

- 核对测试账号是否在环境中存在、密码是否与环境一致
- 若数据无误，转开发排查认证逻辑

## 附件（请补充）

- [ ] 完整请求/响应 curl
- [ ] 测试数据准备说明
