# 交付标准（冒烟版）

## 编号规则

| 前缀 | 含义 | 示例 |
|------|------|------|
| SM- | Smoke 冒烟测试点 | SM-001 |

编号三位数字，从 001 递增，不跳号。

## 优先级（冒烟默认）

| 级别 | 含义 | 本 Skill 默认 |
|------|------|---------------|
| P0 | 主流程 / 阻断发布 | 冒烟全部 P0 |
| P1 | 重要分支 | 扩展版 Skill 使用 |
| P2 | 一般 | 扩展版 Skill 使用 |
| P3 | 低 | 扩展版 Skill 使用 |

## 输出路径

默认：`demo-skills/my-first-testcase-skill/output/smoke_testcases.md`

复制到个人目录后改为：`output/smoke_testcases.md` 或团队约定路径。

## 版本号

输出《文档信息》中写：`my-first-testcase-skill v1.0.0`

大改规则时递增 minor：`v1.1.0`
