---
name: my-first-testcase-skill
description: 从简短 PRD 或用户故事生成 5～15 条冒烟测试点 Markdown，含 SM 编号、检查点与待澄清清单。在用户提到冒烟用例、快速测试点、需求转用例、PRD 转测试点时使用。
---

# 我的第一个测试用例 Skill（冒烟版）

从需求片段生成 **可 PASS/FAIL 判定** 的冒烟测试点。本 Skill 只交付 Markdown，不写自动化脚本。

## 快速使用

```text
@demo-skills/my-first-testcase-skill/SKILL.md
@demo-skills/my-first-testcase-skill/examples/sample_prd_login.md

按 Skill 生成冒烟测试点，输出 demo-skills/my-first-testcase-skill/output/smoke_testcases.md
```

---

## 适用范围

| 项 | 说明 |
|----|------|
| 输入 | PRD 片段、用户故事、功能说明（Markdown / 纯文本） |
| 输出 | Markdown 测试点，默认 `demo-skills/my-first-testcase-skill/output/smoke_testcases.md` |
| 不做 | 不写 pytest / Playwright；不编造 PRD 未提及的功能 |

---

## 输入检查

**必需**：至少一段可测的功能描述（谁、做什么、规则/边界之一）。

**若用户只给一句话**（如「测一下登录」）且无细节：
1. 列出 ≤3 个待澄清问题
2. 禁止编造验证码、OAuth、图形验证码等未提及能力
3. 可基于合理假设生成 ≤5 条冒烟点，但必须在《待澄清清单》标注假设

---

## 工作流程

### Step 1：提取功能点

从输入提取：
- **模块名**（用于输出标题）
- **3～8 个可测行为**（动词开头，如「输入错误密码」「连续失败第 5 次」）

有 OpenAPI / 接口文档时：只记录端点列表，**本 Skill 不展开接口用例**（交给 api-spec 类 Skill）。

---

### Step 2：生成冒烟测试点

每条必须包含：
- **编号**：`SM-001` 递增
- **标题**：一句话
- **检查点**：可客观判定 PASS/FAIL（见 `references/checkpoint_format.md`）
- **优先级**：冒烟默认 **P0**

覆盖建议（按 PRD 有则写，无则待澄清）：
- 1 条正向主流程
- ≥1 条反向（错误输入 / 非法操作）
- ≥1 条边界（长度、次数、时间阈值）

---

### Step 3：写入输出文件

按下方《输出模板》写入默认路径。目录不存在则创建。

---

### Step 4：自检（必须改稿）

对照 `references/checkpoint_format.md`：
- [ ] 消灭「系统正常」「体验良好」等不可判定句
- [ ] 无 PRD 未出现的接口、字段、页面
- [ ] 《待澄清清单》已汇总所有假设与缺失信息
- [ ] 编号连续无跳号

---

## 输出模板

```markdown
# [模块名] 冒烟测试点

## 文档信息
- 依据需求：
- 生成规则：my-first-testcase-skill v1.0.0
- 测试范围：冒烟
- 待澄清条数：

## 测试点

### SM-001 [标题]
- 检查点：
- 优先级：P0

## 待澄清清单

| # | 问题 | 关联编号 |
```

---

## 禁止

- 不要输出 Python / pytest / Playwright 代码
- 不要用「前置条件 / 操作步骤 / 预期结果」三列表格（本 Skill 用检查点句式）
- 不要删除或重排 PRD 原有章节（若输入是完整 PRD，保持结构可追溯）
- 不要编造 PRD 未出现的业务规则

---

## references 索引

| 文件 | 何时加载 |
|------|----------|
| `references/checkpoint_format.md` | Step 4 自检必加载 |
| `references/delivery_standard.md` | 需要编号/优先级说明时 |
| `references/clarification_rules.md` | 输入不足、写待澄清时 |

---

## 版本

- v1.0.0 — 冒烟测试点，SM 编号，待澄清机制
