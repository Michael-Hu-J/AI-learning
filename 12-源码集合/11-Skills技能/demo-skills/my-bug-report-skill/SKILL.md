---
name: my-bug-report-skill
description: 从 pytest 失败日志、接口响应或手工复现步骤生成标准 Markdown 缺陷报告，含严重级别、环境信息与证据摘要。在用户提到缺陷报告、提 bug、测试失败、pytest 红了、报工单时使用。
---

# 缺陷报告 Skill（demo 版）

从 **失败证据** 生成 **可指派、可复现** 的 Markdown 缺陷单。本 Skill **只写 Markdown**，不调用 Jira/禅道 API，不修复代码。

## 快速使用

```text
@demo-skills/my-bug-report-skill/SKILL.md
@demo-skills/my-bug-report-skill/examples/sample_pytest_failure.txt

按 Skill 生成缺陷报告草稿，输出 demo-skills/my-bug-report-skill/output/BUG-demo-001.md
```

---

## 适用范围

| 项 | 说明 |
|----|------|
| 输入 | pytest 堆栈、接口请求/响应摘录、手工复现步骤 |
| 输出 | 单条 `output/BUG-*.md`，可选追加 `output/bug_list.md` |
| 不做 | 自动建工单、改代码、判断「是不是环境问题」的最终结论 |

---

## 输入检查

**必需**：至少一种可复现证据（堆栈 / 请求响应 / 带步骤的现象描述）。

**若只有「这里有问题」**：
1. 列出 ≤3 个追问（环境、复现步骤、期望/实际）
2. 禁止编造接口路径、错误码、截图内容

---

## 工作流程

### Step 1：分类

判断缺陷类型：**接口 / 界面 / 数据 / 环境疑似**（见 `references/severity_guide.md`）。

### Step 2：填模板

按《输出模板》写入，严重级别对照 `references/severity_guide.md`。

### Step 3：证据摘要

从输入提取 **失败摘要**（≤30 行），保留关键断言行，不整段粘贴无关日志。

### Step 4：自检

对照 `references/field_checklist.md` 改稿；状态固定 **Draft**。

---

## 输出模板

```markdown
# 缺陷报告草稿 — BUG-YYYYMMDD-NNN

> 状态：Draft，需人工 triage 后提交工单

## 基本信息
| 字段 | 值 |
| 缺陷编号 | |
| 标题 | |
| 严重程度 | Critical/High/Medium/Low |
| 缺陷类型 | |
| 当前状态 | Draft |

## 发现信息
- 发现方式：
- 关联用例：
- pytest nodeid：（如有）

## 问题描述
（接口类写请求/预期/实际；界面类写操作路径与现象）

## 环境信息
| 字段 | 值 |

## 失败摘要
```

---

## 禁止

- 不要输出 Python 修复补丁
- 不要把「MySQL 连不上」直接标 Critical 产品缺陷（标 Draft + 环境疑似）
- 不要删除堆栈中的关键断言行

---

## references 索引

| 文件 | 何时加载 |
|------|----------|
| `references/severity_guide.md` | Step 2 定级 |
| `references/field_checklist.md` | Step 4 自检 |

## 版本

- v1.0.0 — 单条 Markdown 缺陷草稿
