---
name: my-api-spec-skill
description: 从 OpenAPI 片段或测试点列表生成 api_pytest 声明式 spec（YAML frontmatter + Markdown），供 generate.sh 生成 pytest。在用户提到接口 spec、api_pytest、OpenAPI 转脚本、接口自动化规格时使用。不直接输出 Python 代码。
---

# API Spec Skill（demo 版）

从 **契约或测试点** 生成 **`kind: api_pytest` spec 文件**。本 Skill **只写 spec Markdown**，不输出 `def test_xxx` Python。

## 快速使用

```text
@demo-skills/my-api-spec-skill/SKILL.md
@demo-skills/my-first-testcase-skill/output/smoke_testcases.md
@demo-skills/my-api-spec-skill/examples/mini_openapi_login.md

从冒烟测试点挑 P0 接口场景，生成 spec，输出 demo-skills/my-api-spec-skill/output/login_api_smoke.md
```

---

## 适用范围

| 项 | 说明 |
|----|------|
| 输入 | OpenAPI 片段、已评审测试点、接口清单 |
| 输出 | 带 YAML frontmatter 的 `.md` spec |
| 不做 | 写 pytest 代码；不跑测试；不做 UI spec |

---

## 输入检查

**必需**：`base_url`（或占位 `${TEST_BASE_URL}`）+ 至少 1 个可测 endpoint。

**缺 base_url**：写入《待澄清》，用 `${TEST_BASE_URL}` 占位，禁止猜生产地址。

---

## 工作流程

### Step 1：映射测试点 → cases

从输入提取 P0 场景，每条对应 spec 里一个 `cases[]` 项（见 `references/spec_format.md`）。

### Step 2：写 frontmatter

```yaml
---
kind: api_pytest
base_url: ${TEST_BASE_URL}
cases:
  - id: TC-API-001
    method: POST
    path: /api/...
    expect_status: 201
---
```

### Step 3：写 Markdown 说明

正文列出 case id 与业务含义，便于人审。

### Step 4：自检

- [ ] `kind: api_pytest` 存在
- [ ] 每个 case 有 `id`、`method`、`path`、`expect_status`
- [ ] 无 Python 代码块
- [ ] 运行 `scripts/validate_spec.py <输出文件>` 通过

---

## 输出路径

默认：`demo-skills/my-api-spec-skill/output/login_api_smoke.md`

---

## 禁止

- 不要输出 `.py` 文件或 `def test_` 代码块
- 不要编造 OpenAPI 里不存在的 path
- 不要在本 Skill 里写 Playwright / UI 步骤

---

## 与 testcase Skill 的分工

| Skill | 产出 |
|-------|------|
| my-first-testcase-skill | 测试点 Markdown（SM-xxx） |
| **my-api-spec-skill（本 Skill）** | api_pytest spec |
| 专业版 generate.sh | spec → pytest |

---

## references 索引

| 文件 | 何时加载 |
|------|----------|
| `references/spec_format.md` | Step 2 写 frontmatter |
| `references/forbidden_outputs.md` | Step 4 自检 |

## 版本

- v1.0.0 — api_pytest spec only
