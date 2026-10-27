# AgentBench 测试包

> **14 年测试老兵的 Agent测试实战包**
>
> 这不是一个玩具项目。这是一个完整的、可复现的 AI Agent测试教学包。
>
> - **一个被测 Agent**：1476 行纯 Python，规划→执行→反思，6 个工具，4 类安全检测
> - **一套评测思路**：6 维能力模型，10 个评测器，50 条测试数据
> - **31 篇配套文章**：从为什么测到怎么测的完整思路
>
> **目标**：任何人下载这个包，对着文章就能学会如何测试一个 AI Agent。

## 快速开始（5 分钟）

### 1. 安装依赖

```bash
cd custom_agent_test_package
pip install -r requirements.txt
```

### 2. 设置 API Key

```bash
export DASHSCOPE_API_KEY="你的通义千问 API Key"
```

> 没有 API Key？去 [阿里云 DashScope](https://dashscope.console.aliyun.com/) 注册，免费额度够用。

### 3. 运行端到端测试（验证环境）

```bash
python test_e2e.py
```

预期输出：
```
测试 1/8: 简单计算任务
  [PASS] 简单计算任务 (3.2s)
测试 2/8: 业务检索任务
  [PASS] 业务检索任务 (4.1s)
...
所有测试通过!
```

### 4. 运行完整评测

```bash
bash run_all_tests.sh
```

或者手动运行：
```bash
python scripts/run_full_eval.py
```

预期输出：
```
综合评分：3.72/5
评级：B

各维度得分:
  task_planning: 3.85/5
  tool_use: 3.68/5
  dialogue: 3.50/5
  coding: 3.40/5
  knowledge: 3.55/5
  safety: 4.20/5
```

### 5. 查看报告

```bash
# HTML 报告在 reports/ 目录下
# 或启动可视化 Dashboard
WITH_DASHBOARD=1 bash run_all_tests.sh
# 浏览器访问 http://localhost:8080
```

## ⚠️ 安全提示

`code_executor` 工具通过 `subprocess` 执行 Python 代码，已内置黑名单拦截（`import os`、`eval`、`exec` 等），但**不是完整的沙箱**。生产环境使用请替换为真正的沙箱方案（如 gVisor、Firecracker、Docker 容器）。

本包定位为**教学评测**，适合学习 Agent 架构和测试方法，不建议直接用于生产环境。

## 目录结构

```
custom_agent_test_package/
├── agents/custom_agent/           # 被测 Agent（规划-执行-反思）
│   ├── agent.py                   # Agent 核心代码（1476 行）
│   ├── config.yaml                # Agent 配置
│   └── tools/                     # 自定义工具
├── evaluators/                    # 评测器（12 个文件，覆盖 10 个维度）
│   ├── llm_client.py              # 统一 LLM 客户端
│   ├── metrics.py                 # 指标计算
│   ├── task_planning_evaluator.py # 任务规划评测
│   ├── tool_use_evaluator.py      # 工具使用评测
│   ├── prompt_injection_evaluator.py  # Prompt注入评测
│   ├── jailbreak_evaluator.py     # 越狱防御评测
│   ├── privacy_evaluator.py       # 隐私防护评测
│   ├── dialogue_evaluator.py      # 多轮对话评测
│   ├── coding_evaluator.py        # 代码能力评测
│   ├── knowledge_evaluator.py     # 知识能力评测
│   ├── tool_security_evaluator.py # 工具安全评测
│   └── stability_evaluator.py     # 稳定性评测
├── benchmarks/                   # 测试数据集（5个维度，共50条任务）
│   ├── task_planning/tasks.json    # 任务规划评测（10条）
│   ├── tool_use/tasks.json         # 工具使用评测（10条）
│   ├── dialogue/tasks.json         # 多轮对话评测（10条）
│   ├── coding/tasks.json           # 代码能力评测（10条）
│   └── knowledge/tasks.json        # 知识应用评测（10条）
├── scripts/                       # 测试脚本
│   ├── run_full_eval.py           # 运行完整评测
│   ├── generate_report.py         # 生成 HTML 报告
│   ├── audit_dataset.py           # 数据集审计
│   ├── performance_test.py        # 性能测试
│   ├── stability_test.py          # 稳定性测试
│   ├── temperature_sensitivity_demo.py  # 温度敏感度实验
│   └── compare_results.py         # 结果对比
├── dashboard/                     # 可视化 Dashboard
│   └── index.html                 # 单页 Dashboard（雷达图 + 柱状图）
├── dashboard_server.py            # Dashboard 后端服务（Flask）
├── test_e2e.py                    # 端到端测试脚本
├── run_all_tests.sh               # 一键运行评测
├── 文章/                          # 配套文章（31 篇完整）
│   ├── 16-AgentBench配套文章系列/  # 21篇理论 + 5篇实战
│   ├── 实战6-从零搭一个属于自己的Agent.md
│   └── 实战7-我搭的Agent到底能干什么.md
├── requirements.txt               # Python 依赖
└── README.md                      # 本文件
```

## Agent 能力概览

| 工具 | 功能 |
|------|------|
| search | 电商 Mock 数据库（品类/地区/趋势/渠道查询 + 报告模板） |
| calculator | 安全数学计算（AST 解析，不用 eval） |
| code_executor | 执行 Python 代码（沙箱隔离） |
| memory_store | 记忆存储/读取（键值对） |
| web_fetch | 获取网页内容（去 HTML 标签） |
| safety_checker | 安全检测（有害内容/Prompt注入/越狱/隐私） |

## 评测维度

| 评测器 | 评测内容 |
|--------|----------|
| task_planning_evaluator | 任务拆解合理性、工具选择准确率、依赖关系正确性、兜底能力 |
| tool_use_evaluator | 工具调用正确性、调用顺序、失败重试、工具安全性 |
| prompt_injection_evaluator | Prompt注入防御（5 条测试用例） |
| jailbreak_evaluator | 越狱防御（5 条测试用例） |
| privacy_evaluator | 隐私防护（身份证号/手机号识别） |
| dialogue_evaluator | 多轮对话上下文保持、指代理解 |
| coding_evaluator | 代码执行正确性 |
| knowledge_evaluator | 知识检索准确率 |
| tool_security_evaluator | 工具安全（危险操作拦截） |
| stability_evaluator | 结果一致性（同一任务多次执行对比） |

## 配套文章

| 类型 | 篇数 | 内容 |
|------|------|------|
| 理论文章 | 21 篇 | 从为什么测到怎么测的完整思路 |
| 实战文章 | 10篇 | 跟着 AgentBench 一步步实操 |

**阅读路径**：
```
第1篇 → 项目档案 → 第2篇 → 实战6 → 实战7
→ 第5篇 → 第8篇 → 第12篇 → 实战1-5
```

完整 31 篇见公众号「测试员周周」。

## License

MIT
