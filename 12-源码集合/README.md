# 大模型应用与 AI 测试 · 配套源码集合

**作者**：测试员周周  
**说明**：本目录为知识库全部可运行代码的**独立副本**，与正文 Markdown 分开发放。阅读理论请回到知识库根目录各模块；跑代码在本目录进行。

使用前请阅读 [LICENSE](../LICENSE)。

---

## 包含内容

| 类型 | 路径 | 说明 |
|------|------|------|
| 各模块示例脚本 | `01`–`08`、`10` 下的 `code/` | 66 个 Python 脚本 |
| Agent 示例 | `05-Agent系统/code/` | CrewAI 入门 5 脚本 |
| AgentBench 评测包 | `05-Agent系统/custom_agent_test_package/文档/代码/` | 被测 Agent + 评测器 + 50 条数据集 |
| 五 Agent Demo | `05-Agent系统/seckill-five-agent-demo/` | 秒杀场景 Mock 联调 |
| 项目实战工程 | `09-项目实战/70`–`81` | 12 个完整可运行工程 |
| 附加资源 | `09-项目实战/模型对比脚本`、`agents/` | Benchmark + CustomAgent |
| Skills Demo | `11-Skills技能/demo-skills/` | 3 套 Cursor Skill 示例 + 校验脚本 |
| 公共模块 | `shared/` | 根级共用工具 |

已排除：`.venv`、`__pycache__`、`.pytest_cache`（不含虚拟环境）。

---

## 环境要求

| 项目 | 说明 |
|------|------|
| **Python 版本** | **3.10 / 3.11 / 3.12**（推荐 **3.11 或 3.12**）。3.13 不支持 crewai / pyautogen |
| 操作系统 | Windows / macOS / Linux 均可 |
| 虚拟环境 | 强烈建议使用 `python -m venv .venv` |

---

## 一键演示（非交互）

以下命令无需手动输入，适合学员快速验证环境：

```bash
python 01-大模型基础/code/01-llm_demo.py
python 01-大模型基础/code/03-token_calculator.py --demo
python 01-大模型基础/code/06-model_selector.py --demo
python 09-项目实战/70-智能客服系统/main.py
python 09-项目实战/76-智能问答机器人/main.py --demo
python 09-项目实战/78-langgraph实战/run_tests.py --demo
python 09-项目实战/79-langchain实战/run_rag_tests.py --demo
python 09-项目实战/80-crewAI实战/run_crewai_tests.py --demo
python 09-项目实战/81-autogen实战/run_autogen_tests.py --demo
python 05-Agent系统/custom_agent_test_package/文档/代码/test_e2e.py --demo
```

---

## 项目 78-81 依赖安装

**推荐 Python 3.11 或 3.12**（勿用 3.13：`crewai` / `pyautogen` 尚未完全支持）。

请在虚拟环境中安装（勿与全局 Anaconda 混用）：

```bash
cd "12-源码集合"
py -3.12 -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
pip install -r requirements-frameworks.txt
```

或按项目分别安装（体积更小）：

```bash
pip install -r 09-项目实战/78-langgraph实战/requirements.txt
pip install -r 09-项目实战/79-langchain实战/requirements.txt
pip install -r 09-项目实战/80-crewAI实战/requirements.txt
pip install -r 09-项目实战/81-autogen实战/requirements.txt
```

**一键验证 78-81（演示模式，无需 API Key）：**

```bash
python 09-项目实战/78-langgraph实战/run_tests.py --demo
python 09-项目实战/79-langchain实战/run_rag_tests.py --demo
python 09-项目实战/80-crewAI实战/run_crewai_tests.py --demo
python 09-项目实战/81-autogen实战/run_autogen_tests.py --demo
```

**AgentBench 端到端（无 Key 可用 `--demo`）：**

```bash
cd 05-Agent系统/custom_agent_test_package/文档/代码
pip install -r requirements.txt
python test_e2e.py --demo
```

## 快速开始

```bash
# 1. 进入本目录
cd "12-源码集合"

# 2. 创建虚拟环境（推荐 Python 3.10+）
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 跑第一个示例（无 API Key 自动 Mock）
cd 01-大模型基础/code
python3 01-llm_demo.py

# 5. 跑项目测试
cd ../../09-项目实战/70-智能客服系统
pip install -r requirements.txt
pytest tests/ -v
```

### Agent / CrewAI

```bash
pip install -r requirements-crewai.txt
cd 05-Agent系统/seckill-five-agent-demo
./run.sh demo
```

### AgentBench 完整评测

```bash
cd 05-Agent系统/custom_agent_test_package/文档/代码
pip install -r requirements.txt
export DASHSCOPE_API_KEY='your-key'   # 可选
python test_e2e.py --demo                 # 无 Key 演示
python test_e2e.py                        # 真实 LLM 评测
bash run_all_tests.sh
```

### API Key（可选）

```bash
export DASHSCOPE_API_KEY='your-key'
# 或 export OPENAI_API_KEY='...'
```

未配置 Key 时，大部分脚本与项目自动进入 **Mock 模式**。

---

## 目录结构

```
12-源码集合/
├── LICENSE
├── requirements.txt
├── requirements-crewai.txt
├── shared/
├── 01-大模型基础/code/
├── 02-Prompt工程/code/
├── 03-RAG系统/code/
├── 04-模型评测实战/code/
├── 05-Agent系统/
│   ├── code/
│   ├── custom_agent_test_package/文档/代码/
│   └── seckill-five-agent-demo/
├── 06-AI测试专项/code/
├── 07-安全与合规/code/
├── 08-性能与成本/code/
├── 09-项目实战/
│   ├── 70-智能客服系统/ … 81-autogen实战/
│   ├── 模型对比脚本/
│   ├── agents/
│   └── QUICK_START.md
├── 10-面试专题/code/
└── 11-Skills技能/demo-skills/
```

---

## 与正文对照

| 想学理论 | 看知识库正文 | 跑代码（本目录） |
|----------|--------------|------------------|
| 大模型基础 | `../01-大模型基础/*.md` | `01-大模型基础/code/` |
| Agent 测试 | `../05-Agent系统/custom_agent_test_package/文档/` | `05-Agent系统/custom_agent_test_package/文档/代码/` |
| 项目 78 LangGraph | `../09-项目实战/78-langgraph实战/78-langgraph实战.md` | `09-项目实战/78-langgraph实战/` |
| Skills 编写 | `../11-Skills技能/` | `11-Skills技能/demo-skills/` |

完整篇目见知识库根目录 [00-完整目录.md](../00-完整目录.md)。  
项目索引见 [09-项目实战/README.md](../09-项目实战/README.md)。
