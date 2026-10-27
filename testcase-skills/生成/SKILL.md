---
name: testcase-generator
description: 从 PRD/OpenAPI 生成专业测试点。含通用覆盖矩阵、用例编号、评审表、待澄清清单。保持 PRD 结构、核心流程、边界 trio、Step6 自检修复。
---

# 测试用例生成（专业版）

从需求文档生成 **可判定 PASS/FAIL** 的测试点。本包仅此一种交付规格，按下列规则完整执行。

## 快速使用

```text
@testcase-skills/生成/SKILL.md
@需求文档.md
（可选）@openapi.yaml
生成测试用例，输出 output/模块名_testcases.md
```

---

## 核心原则

### 1. 测试点 ≠ 功能描述

见 `references/test_point_validation.md`。落笔前三问：验证行为？能 PASS/FAIL？有明确预期？

### 2. 层级适中

见 `references/hierarchy_patterns.md`（2/3/4 级）。

### 3. 检查点格式

见 `references/checkpoint_format.md`。不用「前置/操作/预期」标签。

### 4. PRD 与通用矩阵

| 来源 | 规则 |
|------|------|
| **PRD 明确写的** | 必须覆盖 |
| **通用矩阵触发的** | 必须有点 **或** `T-xx（待澄清）` 占位 |
| **PRD 未写且未触发矩阵** | 不编造功能 |

不臆测业务；不清楚写待澄清，见 `references/delivery_standard.md`。

### 5. 覆盖维度

正向、反向、边界、状态/时间、权限；另扫 `references/universal_coverage_matrix.md`。

---

## 工作流程

### Step 0：需求预分析（原始 PRD 必做）

已结构化 `func_list.md` 可跳过至 Step 1。

1. **结构**：保持 PRD 标题层级 → `references/structure_preservation.md`
2. **核心流程**：树形 10～15 步 → `references/core_flows.md`
3. **功能点**：`- 条件` + `预期：` → `references/requirement_patterns.md`
4. **阈值清单**：提取所有比较符/次数/时间 → 供 Step 4 边界与矩阵 E 维
5. **预分析自检**：PRD 节全覆盖、术语一致

有 OpenAPI 时：记录端点列表，供 Step 4 加载 `references/api_contract_supplement.md`。

---

### Step 1：分析需求

判断：核心流程有无、复杂度（2/3/4 级）、模块划分、矩阵哪些维度将触发。

---

### Step 2：核心流程测试

有核心流程则优先生成 → `references/core_flow_testing.md`
`### 流程N：` + 与 func_list 一致的树形结构；编号 `F-01`…

---

### Step 3：确定层级

| 类型 | 结构 |
|------|------|
| 简单 | H2 → H3 |
| 标准 | H2 → H3 → H4 |
| 复杂 | H2 → H3 → H4 → H5 |

---

### Step 4：生成详细测试点

对每个功能/场景：

1. 从 PRD 功能点写检查点（验证点句式）
2. **边界值**：PRD 阈值 → trio（`references/boundary_value_testing.md`）
3. **时间/状态**：→ `references/time_and_state.md`
4. **通用覆盖矩阵**：
   - 加载 `references/universal_coverage_matrix.md`
   - 对每个触发的维度 A～G 写检查点或 `T-xx 待澄清`
   - 有 OpenAPI 则叠加 H 维 `references/api_contract_supplement.md`
   - 需要安全/性能包则加载 `references/appendix_security.md` / `references/appendix_performance.md`
5. **编号与优先级**：按 `references/delivery_standard.md` 赋 `L-/D-/C-/V-/P-` 与 P0～P3

---

### Step 5：输出（符合交付标准）

```markdown
# [模块名] 测试用例

## 文档信息
- 依据需求：
- 生成版本：规则 1.2.0（skills-专业版V2.0 · testcase-skills/生成）
- 测试范围：
- 结构说明：
- 待澄清汇总：N 条

## 需求追溯表

| 需求段落 | 用例编号 | 说明 |

## 核心流程测试

### 流程1：…

## 详细功能点测试

## 用例评审表

| 编号 | 名称 | 优先级 | 类型 | 标签 |

## 通用覆盖矩阵自检

（复制矩阵打勾表，见 universal_coverage_matrix.md）

## 待澄清清单

| # | 问题 | 关联编号 |
```

默认路径：`skills-专业版V2.0/output/[模块名]_testcases.md`

---

### Step 6：自检并修复（必须改稿）

#### 检查 1：测试点格式

`references/test_point_validation.md` — 消灭「支持/需要通过」句式。

#### 检查 2：边界值

每个 PRD 阈值：-1 / 边界 / +1；时间窗三态。

#### 检查 3：PRD 覆盖

func_list 每功能点有对应用例编号。

#### 检查 4：核心流程结构

与 func_list 树一致。

#### 检查 5：通用覆盖矩阵

矩阵 A～I 打勾表填满；触发行无空白（须有点或 T-xx）。

#### 检查 6：交付标准

- 评审表完整
- 编号无重复
- P0 占比合理（≤20%）
- 待澄清已汇总

与 `testcase-skills/评审` 一致；评审 Skill 为发布前加强复核。

---

## 边界值速查

| 需求 | 必测 |
|------|------|
| X > N | N+1, N, N-1 |
| min～max | min-1,min,min+1,max-1,max,max+1 |
| N 次限制 | N-1, N, N+1 |

---

## 参考文档

| 文件 | 何时加载 |
|------|----------|
| **`references/universal_coverage_matrix.md`** | Step 4、6（必） |
| **`references/delivery_standard.md`** | Step 5、6（必） |
| `references/test_point_validation.md` | 写每条检查点 |
| `references/core_flow_testing.md` | Step 2 |
| `references/time_and_state.md` | 时间/状态/次数 |
| `references/api_contract_supplement.md` | 有 OpenAPI |
| `references/appendix_security.md` | 安全包 |
| `references/appendix_performance.md` | 性能包 |
| `references/requirement_patterns.md` | Step 0 |
| `references/core_flows.md` | Step 0 |
| `references/structure_preservation.md` | Step 0 |
| `references/hierarchy_patterns.md` | Step 3 |
| `references/checkpoint_format.md` | Step 4 |
| `references/boundary_value_testing.md` | 数值边界 |
| `references/examples.md` | 样例 |

---

## 质量清单（交付前）

- [ ] 矩阵自检表 + 评审表 + 待澄清清单齐全
- [ ] 测试点均可 PASS/FAIL
- [ ] PRD 追溯表完整
- [ ] 边界与矩阵触发行已覆盖
- [ ] 无 PRD 外的编造功能

---

## 流水线

| 环节 | Skill |
|------|-------|
| 规划 | `testcase-skills/规划` |
| 分析 | `testcase-skills/分析`（≈ Step 0） |
| **生成** | **本 Skill** |
| 评审 | `testcase-skills/评审` |

接口自动化：见 `api-skills/`、`generate.sh`（OpenAPI → pytest）。

## 已废弃

~~`testcase_generator.py`~~ — 勿用，统一使用本 Skill。
