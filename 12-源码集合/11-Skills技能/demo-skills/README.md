# demo-skills 使用说明

本目录提供 **可直接 @ 的三套 Skill 示例**，覆盖 Skill 族分工：测试点 → 接口 spec → 缺陷报告。

## 目录

```
demo-skills/
├── my-first-testcase-skill/   # PRD → 冒烟测试点
├── my-api-spec-skill/         # 测试点 → api_pytest spec（不写 Python）
├── my-bug-report-skill/       # pytest 失败 → 缺陷 Draft
└── scripts/
    └── validate_all_skills.sh # 一键校验示例产出（可进 CI）
```

## 1. 测试点 Skill

```text
@demo-skills/my-first-testcase-skill/SKILL.md
@demo-skills/my-first-testcase-skill/examples/sample_prd_login.md

按 Skill 生成冒烟测试点，输出 demo-skills/my-first-testcase-skill/output/smoke_testcases.md
```

校验：

```bash
python3 demo-skills/my-first-testcase-skill/scripts/validate_testcase_output.py \
  demo-skills/my-first-testcase-skill/output/smoke_testcases.md
```

## 2. API Spec Skill

```text
@demo-skills/my-api-spec-skill/SKILL.md
@demo-skills/my-first-testcase-skill/output/smoke_testcases.md
@demo-skills/my-api-spec-skill/examples/mini_openapi_login.md

只生成 api_pytest spec，输出 demo-skills/my-api-spec-skill/output/login_api_smoke.md
```

校验：

```bash
python3 demo-skills/my-api-spec-skill/scripts/validate_spec.py \
  demo-skills/my-api-spec-skill/output/login_api_smoke.md
```

有专业版时：

```bash
cd skills-专业版V2.0
./generate.sh /绝对路径/demo-skills/my-api-spec-skill/output/login_api_smoke.md
```

## 3. 缺陷报告 Skill

```text
@demo-skills/my-bug-report-skill/SKILL.md
@demo-skills/my-bug-report-skill/examples/sample_pytest_failure.txt

按 Skill 生成缺陷草稿，输出 demo-skills/my-bug-report-skill/output/BUG-demo-001.md
```

## 一条龙（推荐两个 Chat）

**Chat 1**：testcase → 人审 → **Chat 2**：api-spec → validate →（可选）generate.sh → pytest → bug-report

详见 [07-多Skill串联与scripts和CI.md](../07-多Skill串联与scripts和CI.md)。

## 一键校验全部示例

```bash
bash demo-skills/scripts/validate_all_skills.sh
```

## 复制为个人 Skill

```bash
cp -r demo-skills/my-first-testcase-skill ~/.cursor/skills/
```

复制后改 `SKILL.md` 内 output 路径与 description。

## 负向验收

| 场景 | 话术 | 期望 |
|------|------|------|
| 无 PRD | `@testcase Skill` +「写登录用例」 | 待澄清，不编造 OAuth |
| 要 pytest | `@api-spec Skill` +「直接给 Python」 | 只出 spec，引用 forbidden_outputs |
| 无堆栈 | `@bug-report Skill` +「这里有问题」 | 追问，不编造接口 |

路由矩阵见 [06-Skill路由与回归怎么测.md](../06-Skill路由与回归怎么测.md)。

## 进阶

- 裁剪团队版：[05-如何把专业版Skill改成团队版.md](../05-如何把专业版Skill改成团队版.md)
- 专业版意图路由：`skills-专业版V2.0/配套文章/05-意图路由-先派活.md`
