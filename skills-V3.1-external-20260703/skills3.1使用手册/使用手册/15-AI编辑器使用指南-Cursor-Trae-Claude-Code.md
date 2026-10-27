# AI 编辑器怎么用我们的 Skills？Cursor / Trae / Claude Code 全指南

## 一、先搞懂一件事

我们的 Skills 本质上是**一堆 Markdown 文档**，放在目录里。

不同的 AI 编辑器，只是**读取这些文档的方式不同**：

| 编辑器 | 读取方式 | 难度 |
|--------|---------|------|
| Cursor | 自动加载 `.cursor/rules/` + 手动 `@` 引用 | ⭐ 最简单 |
| Trae | 手动 `@` 引用文件 | ⭐⭐ 简单 |
| Claude Code | 命令行 `/read` + 自然语言 | ⭐⭐⭐ 稍复杂 |

**不管用哪个编辑器，核心逻辑都一样：**
1. 打开技能包目录
2. 让 AI 读 SKILL.md
3. 告诉 AI 你要做什么
4. AI 生成 spec → 调用 generate.sh → 出脚本

---

## 二、Cursor（推荐，最简单）

### 为什么推荐 Cursor？

**技能包已经内置了 Cursor 配置。**

解压后，`skills-专业版V3.0/.cursor/rules/` 目录下有 3 个 `.mdc` 文件：

```
.cursor/rules/
├── professional-testing-skills.mdc  ← 总规则（自动加载）
├── testing-skills.mdc               ← 技能包说明（自动加载）
└── ui-l1-l23.mdc                    ← UI 定位策略（按需加载）
```

**这意味着：你打开技能包目录时，Cursor 会自动读取这些规则，不需要你手动配置。**

### 使用步骤

**第 1 步：安装 Cursor**

下载地址：https://cursor.sh（免费）

安装后打开。

**第 2 步：打开技能包目录**

```
File → Open Folder → 选择 skills-专业版V3.0 目录
```

**打开后，Cursor 会自动加载 `.cursor/rules/` 下的规则。**

你会看到右下角提示："Rules loaded: 2 files"。

**第 3 步：在 Chat 中使用**

按 `Ctrl+L`（Mac: `Cmd+L`）打开 Chat 面板。

**方式 A：直接说需求（推荐新手）**

```
帮我生成一个登录接口的测试脚本，接口是 POST /api/auth/login，
管理员账号 admin/admin123，错误密码要返回 401
```

Cursor 会自动读取 `professional-testing-skills.mdc` 规则，按 SKILL 流程执行。

**方式 B：显式引用 SKILL（推荐进阶）**

```
@api-skills/执行/SKILL.md

帮我生成登录接口的测试脚本
```

`@` 符号告诉 Cursor：先读这个文件的内容，再回答我的问题。

**方式 C：引用多个文件**

```
@testcase-skills/生成/SKILL.md
@examples/prd_mini_seckill_auth.md

按专业版规则生成测试用例，输出 output/seckill_auth_testcases.md
```

**第 4 步：让 AI 执行生成**

AI 读完了 SKILL，会问你一些澄清问题。回答后，AI 会：

1. 生成 spec 文件（如 `output/login_test.md`）
2. 调用终端执行 `./generate.sh output/login_test.md`
3. 输出 pytest 脚本

**你只需要复制 AI 给的命令，在终端跑就行。**

### Cursor 的 3 个快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+L` | 打开 Chat 面板 |
| `Ctrl+K` | 在当前文件 inline 提问 |
| `@` | 引用项目中的文件 |

### Cursor 常见问题

**Q：打开目录后 Chat 没反应？**

A：确认你打开的是**技能包根目录**（含 `generate.sh` 的那层），不是子目录。

**Q：`@` 了但 AI 没读文件？**

A：检查路径是否正确。`@api-skills/执行/SKILL.md` 是相对于根目录的路径。

**Q：AI 生成的代码不对？**

A：在 Chat 里说："按 professional-testing-skills.mdc 的规则重新生成"。

---

## 三、Trae

### Trae 是什么？

Trae 是字节跳动推出的 AI 编辑器，和 Cursor 类似，但**没有 `.cursor/rules/` 自动加载机制**。

**这意味着：你需要手动引用文件。**

### 使用步骤

**第 1 步：安装 Trae**

下载地址：https://www.trae.com.cn（免费）

安装后打开。

**第 2 步：打开技能包目录**

```
File → Open Folder → 选择 skills-专业版V3.0 目录
```

**第 3 步：在 Chat 中引用文件**

按 `Ctrl+L`（Mac: `Cmd+L`）打开 Chat 面板。

**关键：Trae 不会自动加载规则，你必须用 `@` 显式引用。**

**方式 A：引用 SKILL + 需求**

```
@api-skills/执行/SKILL.md
@templates/api_smoke.md

参考这个模板，帮我生成登录接口的测试脚本。
接口：POST /api/auth/login
参数：username=admin, password=admin123
预期：成功返回 200，错误密码返回 401
```

**方式 B：引用多个 SKILL**

```
@testcase-skills/生成/SKILL.md
@testcase-skills/生成/references/universal_coverage_matrix.md
@examples/prd_mini_seckill_auth.md

生成用户认证模块的测试用例，覆盖 8 维度矩阵。
```

**方式 C：直接说需求（不引用 SKILL，效果差一些）**

```
帮我生成一个 pytest 测试脚本，测试登录接口。
POST /api/auth/login，admin/admin123，错误密码返回 401。
用 requests 库，支持 Token 自动传递。
```

**第 4 步：执行生成**

Trae 会生成 spec 文件。然后在终端执行：

```bash
cd skills-专业版V3.0
./generate.sh output/生成的文件.md
cd output && python3 -m pytest 生成的文件.py -v
```

### Trae 和 Cursor 的区别

| 特性 | Cursor | Trae |
|------|--------|------|
| 自动加载规则 | ✅ `.cursor/rules/` | ❌ 需要手动 `@` |
| `@` 引用文件 | ✅ | ✅ |
| 终端集成 | ✅ | ✅ |
| 价格 | 免费 | 免费 |

**建议：** 如果你同时装了 Cursor 和 Trae，**用 Cursor**（自动加载规则，省心）。

### Trae 常见问题

**Q：`@` 找不到文件？**

A：确认你打开的是技能包根目录。`@` 路径是相对于打开的根目录的。

**Q：AI 生成的代码不符合 SKILL 规范？**

A：Trae 没有自动加载规则，你必须每次都 `@SKILL.md`。忘记引用就会这样。

**Q：能用 `.cursor/rules/` 吗？**

A：Trae 不识别 `.cursor/` 目录。需要手动引用。

---

## 四、Claude Code

### Claude Code 是什么？

Claude Code 是 Anthropic 推出的**命令行 AI 编程助手**。不是图形界面，是在终端里用的。

**这意味着：操作方式完全不同。**

### 使用步骤

**第 1 步：安装 Claude Code**

```bash
# 需要 Node.js 18+
npm install -g @anthropic-ai/claude-code

# 登录（需要 Anthropic API Key）
claude login
```

**第 2 步：进入技能包目录**

```bash
cd skills-专业版V3.0
```

**第 3 步：启动 Claude Code**

```bash
claude
```

进入交互式对话。

**第 4 步：引用文件 + 说需求**

Claude Code 用 `/read` 命令读取文件，或者直接引用路径。

**方式 A：用 `/read` 读取 SKILL**

```
/read api-skills/执行/SKILL.md
/read templates/api_smoke.md

参考这两个文件，帮我生成登录接口的测试脚本。
```

**方式 B：直接引用路径**

```
请按照 api-skills/执行/SKILL.md 的规则，
参考 templates/api_smoke.md 的格式，
生成一个测试 POST /api/auth/login 的 pytest 脚本。
admin/admin123，错误密码返回 401。
```

**方式 C：用 `@` 引用（Claude Code 也支持）**

```
@api-skills/执行/SKILL.md
@templates/api_smoke.md

生成登录接口测试脚本
```

**第 5 步：让 AI 执行命令**

Claude Code 可以直接在终端执行命令。

```
生成 spec 后，执行 ./generate.sh output/login.md
然后 cd output && python3 -m pytest login.py -v
```

Claude Code 会自动执行这些命令，并把结果返回给你。

### Claude Code 的常用命令

| 命令 | 功能 |
|------|------|
| `/read <文件>` | 读取文件内容 |
| `/clear` | 清空对话历史 |
| `/help` | 查看帮助 |
| `@<文件>` | 引用文件（同 Cursor/Trae） |

### Claude Code 和 Cursor/Trae 的区别

| 特性 | Claude Code | Cursor/Trae |
|------|-------------|-------------|
| 界面 | 命令行 | 图形界面 |
| 自动加载规则 | ❌ 需要手动引用 | ✅ Cursor 自动加载 |
| 执行命令 | ✅ 直接在终端执行 | ✅ 可以复制命令 |
| 适合人群 | 熟悉命令行的开发者 | 所有用户 |

**建议：** 如果你习惯命令行，Claude Code 很强。如果你是测试工程师，**推荐 Cursor**。

### Claude Code 常见问题

**Q：API Key 怎么获取？**

A：登录 https://console.anthropic.com → API Keys → 创建 Key。

**Q：`/read` 报文件不存在？**

A：确认你在技能包根目录下执行 `claude`。路径是相对于当前工作目录的。

**Q：能不能自动加载 `.cursor/rules/`？**

A：不能。Claude Code 不识别 `.cursor/` 目录。需要手动 `/read`。

---

## 五、三种编辑器对比

| 维度 | Cursor | Trae | Claude Code |
|------|--------|------|-------------|
| 上手难度 | ⭐ 最低 | ⭐⭐ 低 | ⭐⭐⭐ 中等 |
| 自动加载规则 | ✅ | ❌ | ❌ |
| 图形界面 | ✅ | ✅ | ❌ |
| 终端执行 | 复制命令 | 复制命令 | 直接执行 |
| 价格 | 免费 | 免费 | 按 API 用量收费 |
| 适合人群 | 所有测试工程师 | 字节生态用户 | 命令行爱好者 |

## 六、推荐方案

**新手/测试工程师：** 用 Cursor

- 打开目录就能用
- 规则自动加载
- 图形界面友好
- 免费

**进阶/测开：** Cursor + Claude Code 混用

- 日常用 Cursor（方便）
- 复杂任务用 Claude Code（推理能力强）

**团队负责人：** 统一用 Cursor

- 降低新人上手门槛
- 统一 SKILL 引用方式
- `.cursor/rules/` 可以团队共享

---

## 七、不管用哪个编辑器，记住这 3 句话

1. **先打开技能包根目录**（含 `generate.sh` 的那层）
2. **先引用 SKILL.md，再说需求**（`@SKILL.md` + 你的需求）
3. **AI 生成 spec 后，跑 `./generate.sh`**（复制命令，终端执行）

**学会这 3 步，用哪个编辑器都一样。**
