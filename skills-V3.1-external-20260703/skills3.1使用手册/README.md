# 测试技能包 V3.0 使用手册

> 版本：V3.0  
> 发布日期：2026-06  
> 适用对象：测试工程师、SDET、质量保障团队、自动化测试初学者  
> 说明：本手册为对外交付文档，面向实际使用场景编写。所有操作步骤均可直接复制执行，无需额外配置。

---

## 目录

1. 产品简介
2. 环境准备
3. 快速上手（3 分钟跑通第一个用例）
4. 核心功能详细指南
   4.1 需求分析与用例生成
   4.2 API 自动化测试
   4.3 UI自动化测试
   4.4 数据工厂（造数据与清理）
   4.5 性能压测（JMeter + k6）
   4.6 测试计划与方案生成
5. AI 增强能力详解
   5.1 RAG知识库（检索增强生成）
   5.2 故障自愈引擎
   5.3 CI门禁（质量关卡）
   5.4 失败分析与缺陷去重
   5.5 覆盖率分析与交互式报告
   5.6 规划中能力（尚未有一键脚本）
6. AI 编辑器集成指南（Cursor / Windsurf / VS Code）
7. 常用命令速查表
8. 完整案例：给一个登录功能做完整测试
9. 常见问题与排错（FAQ）
10. 附录：目录结构说明

---

## 1. 产品简介

测试技能包 V3.0 是一套开箱即用的 AI测试工具集。它将测试工程师从写用例、造数据、跑脚本、看报告的重复劳动中解放出来，通过 AI 自动生成、自动执行、自动分析，覆盖 API测试、UI 测试、性能压测、CI门禁等核心场景。

核心特点：
- 21 个技能目录，覆盖测试全流程（见包内 README「技能目录」状态表）
- 133 份文档 + 15 个可执行 Python 脚本
- 支持 AI 编辑器直接读取，也可命令行独立执行
- 内置依赖图推断、变量池自动传递、故障自愈、RAG知识库、CI门禁等企业级能力
- 零配置启动，Python 3.8+ 即可运行（无后端可 `verify_all.sh` + `--collect-only`）

**能力状态**（与包内 README 一致）：**可执行** / **需联调** / **AI 辅助** / **规划中** — 并非每一项都是「一行命令开箱即跑」，AI 型 Skill 与 roadmap 项已在 README 标明。

---

## 2. 环境准备

### 2.1 基础环境
- 操作系统：Linux / macOS / Windows（WSL）
- Python 版本：3.8 或以上
- 终端：系统自带终端或命令行工具

### 2.2 验证 Python
打开终端，执行：
```bash
python3 --version
```
输出包含 `Python 3.8` 或更高版本即满足要求。

### 2.3 安装依赖
进入技能包根目录后，按需安装依赖：
```bash
# 基础功能（必须）
pip install PyYAML

# API测试（必须）
pip install pytest requests

# UI 测试（可选）
pip install pytest-playwright
playwright install chromium

# 性能测试（可选）
pip install locust
```

---

## 3. 快速上手（3 分钟跑通第一个用例）

本章节指导你完成首次运行。全程无需修改代码，直接复制命令即可。

### 步骤 1：进入目录
```bash
cd skills-专业版V3.0
```

### 步骤 2：赋予执行权限并生成脚本
```bash
chmod +x generate.sh
./generate.sh templates/api_smoke.md
```
执行成功后，终端会显示：`已生成: .../output/api_smoke.py`

### 步骤 3：收集用例（不发包）
```bash
cd output
python3 -m pytest api_smoke.py --collect-only -q
```
终端输出 `N tests collected`（无报错即可；条数随内置模板扩展，以终端为准），表示环境配置正确，脚本已就绪。

### 步骤 4：对接真实服务（可选）

**演示后端（进销存）**：文档示例用的 `seckill_finance_system` **不在 zip 内**，**联系交付方获取**（详见包内 `README.md`、`LICENSE.txt` 与手册 `14-FAQ`）。

如果你有后端服务（演示进销存或自有项目），设置环境变量后执行全量测试：
```bash
export TEST_BASE_URL=http://你的服务地址:端口
python3 -m pytest api_smoke.py -v
```

> 注意：`--collect-only` 仅收集用例列表，不发送 HTTP 请求。首次验证请使用此参数，避免网络超时。

---

## 4. 核心功能详细指南

### 4.1 需求分析与用例生成

**功能说明**  
根据需求文档或自然语言描述，自动拆解功能点、核心流程、边界值，并按 8 个维度生成完整测试用例。

**8 维度覆盖矩阵**
| 维度 | 全称 | 含义 | 示例 |
|------|------|------|------|
| N | Normal 正常 | 合法参数，期望成功 | 正确账号密码登录成功 |
| B | Boundary 边界 | 极限值测试 | 密码为空、密码 129 字符（上限 128） |
| T | Type 类型 | 类型错误测试 | 手机号传数字、密码传布尔值 |
| E | Exception 异常 | 业务异常流程 | 密码错误 5 次触发账号锁定 |
| A | Auth 权限 | 越权访问测试 | 普通用户调用管理员接口返回 403 |
| D | Dependency 依赖 | 顺序错误测试 | 未登录调用下单接口返回 401 |
| I | Idempotent 幂等 | 重复操作测试 | 连续点击支付 3 次仅生成 1 个订单 |
| S | Security 安全 | 恶意输入测试 | SQL 注入、XSS 脚本、无 Token 访问 |

**操作步骤**
1. 准备需求文档（Markdown 或 TXT 格式）
2. 在 AI 编辑器中打开技能包目录
3. 在 Chat 中输入：
   ```
   @testcase-skills/生成/SKILL.md
   @你的需求文档.md

   生成测试用例，输出 output/login_testcases.md
   ```
4. AI 将自动输出完整用例表，包含用例编号、标题、步骤、预期结果、优先级。

> 💡 **没有 AI 编辑器？** 直接用命令行（见下方"命令行替代方案"），效果一样。

**命令行替代方案**
```bash
# 复制模板，按需修改
cp templates/testcase_template.md my_testcase.md
# 用任意编辑器打开 my_testcase.md，按注释填写你的需求
# 然后生成
./generate.sh my_testcase.md
cd output && python3 -m pytest testcase_template.py --collect-only -q
```

---

### 4.2 API 自动化测试

**功能说明**  
将接口文档（OpenAPI/Swagger）或一句话需求转化为可执行的 pytest 脚本。内置智能依赖分析与自动传参能力。

**核心机制**
1. 依赖图推断：自动识别接口调用顺序（如先登录→再下单→查订单）
2. 变量池传递：登录返回的 token 自动存入变量池，后续接口通过 `${token}` 引用
3. 失败跳过：某步失败时，自动跳过依赖它的后续步骤，避免无效报错

**操作步骤**
1. 在 AI 编辑器 Chat 中输入：
   ```
   @api-skills/执行/SKILL.md

   帮我测 POST /api/login，admin/admin123，错误密码要 401
   ```
2. AI 生成 `api_spec.md` 并调用 `./generate.sh` 输出 `api_spec.py`
3. 执行测试：
   ```bash
   cd output
   python3 -m pytest api_spec.py -v
   ```

> 💡 **没有 AI 编辑器？** 直接复制内置模板，改改就能用（见下方"命令行替代方案"）。

**命令行替代方案**
```bash
# 复制 API 模板
cp templates/api_smoke.md my_api_test.md
# 编辑 my_api_test.md，把 base_url、接口路径、参数改成你的
# 生成脚本
./generate.sh my_api_test.md
cd output && python3 -m pytest my_api_test.py -v
```

**变量池使用示例**
```json
// 步骤1 登录响应
{"data": {"token": "abc123", "user_id": 42}}

// 步骤2 创建订单（自动注入）
POST /api/orders
Headers: { "Authorization": "Bearer ${token}" }
Body:    { "user_id": "${user_id}", "sku": "BOOK-001" }
```

---

### 4.3 UI自动化测试

**功能说明**  
将自然语言描述（如"打开登录页，输入账号密码，点击登录"）转化为 Playwright 脚本，自动驱动浏览器执行。

**核心机制：UI 自愈定位**  
当页面元素选择器变更时（如 `#login-btn` 变为 `#submit`），脚本不会失败。系统按以下优先级自动尝试定位：
ID → data-testid → CSS 选择器 → role+name → label → placeholder → 文本匹配

**操作步骤**
1. 在 AI 编辑器 Chat 中输入：
   ```
   @UI-skills/执行/SKILL.md

   帮我生成登录页的 Playwright 脚本，base_url 是 http://127.0.0.1:5000
   ```
2. AI 生成 `ui_spec.py`
3. 执行测试：
   ```bash
   cd output
   python3 -m pytest ui_spec.py -v
   ```
4. 支持视频录制与失败截图，默认保存在 `output/videos/` 与 `output/screenshots/`

> 💡 **没有 AI 编辑器？** 直接复制 UI 模板：
> ```bash
> cp templates/ui_login.md my_ui_test.md
> ./generate.sh my_ui_test.md
> cd output && python3 -m pytest my_ui_test.py -v
> ```

---

### 4.4 数据工厂（造数据与清理）

**功能说明**  
测试前自动生成测试数据（用户、商品、订单等），测试完成后按依赖顺序自动清理，避免脏数据残留。

**核心机制**
- 字段名自动映射：识别 `phone` 自动生成手机号，识别 `email` 自动生成邮箱
- 跨表关联：`ref("users.id")` 自动引用上游生成的 ID
- 边界数据：自动注入空值、超长文本、特殊字符
- 逆向清理：按创建相反顺序删除数据，防止外键约束报错

**操作步骤**
1. 编写数据 spec 文件 `data_spec.md`：
   ```yaml
   ---
   kind: data_factory
   tables:
     - name: users
       count: 50
       fields:
         username: "user_{i}"
         phone: auto
         email: "user{i}@test.com"
   ---
   ```
2. 生成并执行：
   ```bash
   ./generate.sh data_spec.md
   cd output && python data_spec.py
   ```
3. 清理数据（脚本已内置）：
   ```bash
   python data_cleanup.py
   ```

---

### 4.5 性能压测（JMeter + k6）

**功能说明**  
支持 JMeter 与 k6 双引擎，生成压测脚本，模拟多用户并发访问，验证系统性能指标。

**压测场景分类**
| 场景 | 目的 | 并发规模 | 持续时间 |
|------|------|----------|----------|
| 冒烟 | 验证脚本正确性 | 1-5 | 1-2 分钟 |
| 基线 | 单用户响应基准 | 1 | 3-5 分钟 |
| 负载 | 预期并发表现 | 50-200 | 5-15 分钟 |
| 压力 | 定位系统瓶颈 | 逐步递增 | 直至报错 |
| 稳定性 | 验证长时间运行 | 50-100 | 30 分钟-24 小时 |

**操作步骤**
1. 在 AI 编辑器 Chat 中输入：
   ```
   @load-testing/执行/SKILL.md

   帮我生成一个 k6 压测脚本，阶梯并发 10→100，持续 10 分钟，目标 P95 < 500ms
   ```
2. AI 生成 `load_test.js`
3. 执行压测：
   ```bash
   k6 run output/load_test.js
   ```

---

### 4.6 测试计划与方案生成

**功能说明**  
根据项目背景与上线时间，自动生成标准测试计划文档，包含测试范围、策略、环境、资源、里程碑、风险评估。

**操作步骤**
1. 在 AI 编辑器 Chat 中输入：
   ```
   @test-plan/SKILL.md

   帮我生成一个秒杀系统的测试计划，上线时间 7 月 15 日
   ```
2. AI 输出 `test_plan.md`，可直接用于评审或汇报。

> 💡 **没有 AI 编辑器？** 复制内置示例，按需修改：
> ```bash
> cp examples/test-plan-example-seckill.md my_test_plan.md
> # 编辑 my_test_plan.md，改成你的项目信息
> ```

---

## 5. AI 增强能力详解

### 5.1 RAG知识库（检索增强生成）

**功能说明**  
AI 生成用例时，自动从团队历史用例、Bug 记录、最佳实践中找相关知识，注入到生成过程，实现"开卷考试"。

**检索流程**
1. 关键词匹配：从标题或内容中找含关键词的文档
2. 语义匹配：按意思相似度匹配（如"登录"能匹配到"鉴权/Token"相关文档）
3. 合并排序：把两路结果合并，按相关性打分，输出最相关的 Top 5

**命令行使用**
```bash
cd rag-engine/scripts

# 检索知识
python rag_search.py "登录模块测试" --top-k 3

# 添加知识
python rag_search.py "dummy" --add "改密后旧 Token 失效" --metadata "{'type': 'bug', 'title': '改密未踢下线'}"
```

**Python 调用**
```python
from service import create_rag_service
rag = create_rag_service()
rag.add_knowledge(["登录功能测试"], [{"type": "case", "title": "登录测试"}])
context = rag.get_context("Token 鉴权", top_k=3)
print(context)
```

> 💡 **小白提示**：这个功能主要给团队用。个人用户不需要配置，直接用就行。

---

### 5.2 故障自愈引擎

**功能说明**  
接口测试失败时，自动分类处理。环境类问题（401/500/429/超时/断连）自动重试，不重复报缺陷。

**自愈策略表**
| 错误类型 | 处理策略 | 重试次数 | 延迟策略 |
|----------|----------|----------|----------|
| 401 | 刷新 Token | 最多 5 次 | 固定 0.5 秒 |
| 500 | 指数退避重试 | 最多 3 次 | 1秒 × 2^尝试次数 + 随机抖动 |
| 429 | 等待后重试 | 最多 3 次 | 2^尝试次数 + 随机抖动 |
| 超时 | 延长超时时间 | 最多 2 次 | 每次 +10 秒，上限 120 秒 |
| 连接失败 | 指数退避重试 | 最多 3 次 | 2秒 × 2^尝试次数 + 随机抖动 |

**随机抖动说明**  
多请求同时重试时，加入 0.5~1.5 倍随机系数错开重试时间，避免"惊群效应"导致服务端再次过载。

---

### 5.3 CI门禁（质量关卡）

**功能说明**  
代码合并或部署前，自动执行四维度质量检查。全部通过则放行，任一失败则拦截（可配置自动回滚）。

**四维度阈值（生产环境）**
| 维度 | 参数 | 阈值 | 说明 |
|------|------|------|------|
| 性能 | P95 响应时间 | ≤ 500ms | 95% 请求在此时间内完成 |
| 安全 | 严重漏洞 | 0 | 生产环境零容忍 |
| 质量 | 代码覆盖率 | ≥ 90% | 测试覆盖的代码比例 |
| 断言 | 关键断言通过率 | 100% | 核心业务逻辑必须全通过 |

**命令行使用**
```bash
cd ci-gate/scripts

# 执行检查
python ci_gate.py --env prod --metrics metrics.json

# 开启自动回滚
python ci_gate.py --env prod --auto-rollback

# 输出 Markdown 报告
python ci_gate.py --env prod --output markdown
```

---

### 5.4 失败分析与缺陷去重

**功能说明**  
测试失败后，AI 自动分析根因，按 5 大类分类（环境/数据/代码/测试设计/未知），并生成置信度分级。同一问题多次出现仅报一次缺陷。

**置信度分级**
| 置信度 | 条件 | 处理方式 |
|--------|------|----------|
| 高（≥0.8） | 明确错误模式 + AI 确认 | 自动创建缺陷单 |
| 中（0.5-0.8） | 可能原因 + 需确认 | 创建缺陷，标注待确认 |
| 低（<0.5） | AI 无法判断 | 标记未知，人工排查 |

**缺陷去重机制**  
缺陷指纹 = MD5(接口路径 + 状态码 + 错误信息前 50 字符)。指纹相同视为重复缺陷，自动合并。

---

### 5.5 覆盖率分析与交互式报告

**覆盖率分析**  
比对 OpenAPI 文档与实际测试记录，计算端点覆盖率。自动输出未覆盖端点列表（Gap 分析），按优先级排序。

**交互式报告**  
测试报告支持层级钻取：总览（通过率）→ 技能层（按模块统计）→ 用例层（请求/响应/断言详情）→ 一键报缺陷。非静态文本，支持对比两次回归结果。

---

### 5.6 规划中能力（尚未有一键脚本）

以下能力在 Skill 文档中有说明，**暂不能像 `./generate.sh` 一样本地一键跑**；需在 AI 编辑器 Chat 中 `@` 对应 Skill，或等待后续版本：

| 能力 | 入口 | 说明 |
|------|------|------|
| 安全扫描 / UI 规范审查 / 代码质量门禁 | `@special-testing/SKILL.md` | Skill 内「规划中」章节 |
| 数据工厂环境重置 | `@data-factory/SKILL.md` | truncate / migrate / seed 由 AI 生成脚本 |
| UI L2.5 Scrapling / L3 AI 定位 | `UI-skills/自我修复` | roadmap；当前以七种 Playwright 策略 + L2 DOM 为准 |
| 压测报告 HTML（截图分析） | `@load-testing/报告/SKILL.md` | **AI 辅助**，非固定 CLI |

完整状态表见包内 **`README.md` → 技能目录**。

---

## 6. AI 编辑器集成指南（Cursor / Windsurf / VS Code）

### 6.1 打开项目
1. 启动 AI 编辑器
打开技能包根目录（解压后的 skills-专业版V3.0 目录）

### 6.2 引用技能
在 Chat 面板输入：
```
@技能目录/SKILL.md

你的需求描述
```
示例：
```
@api-skills/执行/SKILL.md

帮我测 POST /api/login，admin/admin123，错误密码要 401
```

### 6.3 生成与执行
AI 会自动：
1. 读取 SKILL.md 规则
2. 生成 spec 文件
3. 调用 `./generate.sh` 输出可执行脚本
4. 提供运行命令

### 6.4 推荐编辑器
- Cursor：原生支持项目级 SKILL 读取
- Windsurf：支持自然语言转测试脚本
- VS Code + GitHub Copilot：配合 `@` 引用正常工作

---

## 7. 常用命令速查表

| 场景 | 命令 |
|------|------|
| 生成 API 脚本 | `./generate.sh templates/api_smoke.md` |
| 收集用例（不发包） | `cd output && python3 -m pytest xxx.py --collect-only -q` |
| 执行全量测试 | `export TEST_BASE_URL=http://服务:端口 && python3 -m pytest xxx.py -v` |
| 生成测试数据 | `./generate.sh data_spec.md && cd output && python data_spec.py` |
| 清理测试数据 | `cd output && python data_cleanup.py` |
| RAG 检索 | `cd rag-engine/scripts && python rag_search.py "查询" --top-k 3` |
| RAG 添加知识 | `cd rag-engine/scripts && python rag_search.py "dummy" --add "文本" --metadata "{'type':'case'}"` |
| CI门禁检查 | `cd ci-gate/scripts && python ci_gate.py --env prod` |
| CI门禁自动回滚 | `cd ci-gate/scripts && python ci_gate.py --env prod --auto-rollback` |
| JMeter 压测 | `./generate.sh templates/perf_test.md && cd output && locust -f perf_test.py --headless -u 10 -r 2 -t 30s` |
| k6 压测 | `k6 run output/load_test.js` |

---

## 8. 完整案例：给一个登录功能做完整测试

> 本节演示从需求文档到测试报告的完整流程。不需要 AI 编辑器，纯命令行操作。

### 场景：测试一个用户登录功能

**需求：**
- 正确账号密码 → 登录成功，返回 Token
- 错误密码 → 返回 401
- 无 Token 访问受保护接口 → 返回 401

### 步骤 1：准备需求文档

```bash
# 复制内置示例
cp examples/prd_mini_seckill_auth.md my_prd.md
```

编辑 `my_prd.md`，改成你的需求（或直接使用内置示例）。

### 步骤 2：生成测试用例

**有 AI 编辑器：**
```
@testcase-skills/生成/SKILL.md
@my_prd.md
生成测试用例，输出 output/login_testcases.md
```

**没有 AI 编辑器：**
```bash
# 手动写 spec（复制模板）
cp templates/testcase_generation.md my_testcase.md
# 编辑 my_testcase.md，按注释填写
./generate.sh my_testcase.md
```

**输出：** `output/login_testcases.md`，包含 10+ 条用例，覆盖登录成功、失败、权限等场景。

### 步骤 3：生成 API 测试脚本

```bash
# 复制 API 模板
cp templates/api_auth.md my_api_test.md
# 编辑 my_api_test.md，把 base_url 改成你的服务地址
./generate.sh my_api_test.md
```

**输出：** `output/my_api_test.py`，包含登录、Profile 查询、错误密码等测试。

### 步骤 4：运行测试

```bash
cd output

# 先收集用例（不发包）
python3 -m pytest my_api_test.py --collect-only -q
# 应看到 "X tests collected"

# 设置后端地址
export TEST_BASE_URL=http://127.0.0.1:5001
export TEST_USERNAME=admin
export TEST_PASSWORD=admin123

# 执行全量测试
python3 -m pytest my_api_test.py -v
```

**预期输出：**
```
my_api_test.py::test_tc_auth_001 PASSED
my_api_test.py::test_tc_auth_002 PASSED
my_api_test.py::test_tc_auth_003 PASSED
...
============================== X passed in 0.5s ===============================
```

### 步骤 5：查看结果

- **通过的用例：** 终端显示绿色 PASSED
- **失败的用例：** 自动在 `output/bugs/` 生成缺陷草稿
- **测试进度：** `output/reports/progress.md`

### 总结

| 步骤 | 耗时 | 产出 |
|------|------|------|
| 准备需求 | 2 分钟 | my_prd.md |
| 生成用例 | 3 分钟 | login_testcases.md |
| 生成脚本 | 1 分钟 | my_api_test.py |
| 运行测试 | 30 秒 | 测试报告 |
| **合计** | **约 7 分钟** | **完整测试流程** |

---

## 9. 常见问题与排错（FAQ）

**Q1：我不懂 Python，能使用吗？**  
能。核心操作仅为 `./generate.sh` 与 `python3 -m pytest`，复制命令即可。AI 编辑器中直接输入自然语言，系统自动生成脚本。

**Q2：没有后端服务，能跑吗？**  
能。使用 `--collect-only` 参数仅收集用例，不发送请求。后端就绪后设置 `TEST_BASE_URL` 再执行全量。

**Q3：RAG 和 CI门禁需要安装数据库吗？**  
不需要。RAG 内置 FAISS（轻量级，使用本地 JSON 文件），CI门禁为纯 Python 逻辑。开箱即用，零外部依赖。

**Q4：脚本执行失败怎么办？**  
1. 检查 `output/bugs/` 目录，失败用例会自动生成缺陷草稿
2. 查看终端日志，401/500/429 会自动重试
3. 确认真实服务地址与端口正确
4. 检查接口路径与请求体字段名是否匹配

**Q5：如何对接我的项目？**  
修改 `base_url` 与接口路径。模板中的占位符替换为真实接口，执行 `./generate.sh` 重新生成即可。

**Q6：pytest 提示 command not found？**  
使用 `python3 -m pytest` 替代 `pytest`，不依赖 PATH 环境变量。

**Q7：权限不足或 Permission denied？**  
执行 `chmod +x generate.sh` 添加执行权限，或使用 `bash generate.sh xxx.md` 显式调用。

**Q8：终端输出空白但文件已更新？**  
执行 `cat output/.last_run_message.txt` 查看完整生成日志。此为部分 IDE 终端显示问题，不影响实际执行。

---

## 10. 附录：目录结构说明

| 目录 | 用途 | 状态 |
|------|------|------|
| api-skills/ | API测试（分析→规划→执行→自愈） | 可执行 + AI 辅助 |
| UI-skills/ | 网页自动化（Playwright + 自愈定位） | 可执行；L2.5/L3 **规划中** |
| mobile-skills/ | Appium 移动端 | 需联调 |
| testcase-skills/ | 用例生成（8 维度矩阵 + 评审） | AI 辅助 |
| testplan-skills/ / test-plan/ | 测试方案与计划 | AI 辅助 |
| testcase-data-generator/ | 用例驱动数据设计 | AI 辅助 |
| data-factory/ | 数据工厂（注入 + 清理） | 可执行；环境重置 **规划中** |
| load-testing/ | 性能压测（JMeter + k6） | 可执行；报告 **AI 辅助** |
| special-testing/ | Locust 冒烟、视觉回归 | 部分可执行；安全/UI审查 **规划中** |
| screenshot-skills/ | 全站截图 | 需联调 |
| requirement-modeling/ | 需求建模 | AI 辅助 |
| rag-engine/ | RAG知识库 | 可执行 |
| ci-gate/ | CI门禁 | 可执行 |
| bug-reporter/ / defect-analysis/ / defect-sync/ | 缺陷与失败分析 | 可执行（同步推送需联调） |
| intent-router/ / progress-reporter/ | 路由与进度 | 可执行 |
| templates/ / codegen/ / examples/ / prompts/ | 模板、引擎、示例、话术 | 配套资源 |
| output/ | 生成产物（首次运行后自动产生，**勿打入交付 zip**） | 运行时目录 |

---

## 版本记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V3.0 | 2026-06 | 对外正式版：21 技能目录、能力状态表、verify_all、RAG/CI/自愈/8 维矩阵 |
| V1.0 | 2026-04 | 初始版本（API / UI / 用例 / 数据基础能力） |

---

## 反馈与支持

如有使用问题或改进建议，欢迎提交 Issue 或联系项目维护者。  
**演示后端（进销存）** `seckill_finance_system` 不在技能包 zip 内，**联系交付方获取**。
