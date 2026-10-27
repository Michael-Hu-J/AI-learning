# 生产项目源码对照

>  **这些文件来自真实生产项目，配套代码环境无法直接运行。**
> 
> 用途：**对照阅读**，理解"文章写的概念"和"生产项目完整实现"之间的关系。

## 文件说明

| 文件 | 来源 | 行数 | 对应文章 | 配套代码教学版 |
|------|------|------|----------|---------------|
| `healing_graph.py` | `app/graphs/healing_graph.py` | 209行 | 第4篇：AI自愈系统 | `healer/healing_graph.py`（教学精简版，无 MCP） |
| `ui_worker.py` | `app/workers/ui_worker.py` | 234行 | 第2篇：执行引擎 | `worker/ui_worker.py`（78行） |
| `ui_locator_resolver.py` | `app/services/ui_locator_resolver.py` | 304行 | 第3篇：三层定位 | `locator/resolver.py`（147行） |
| `visual_repair.py` | `app/services/visual_repair.py` | 138行 | 第5篇：视觉语义 | `locator/visual_repair.py`（64行） |

## 为什么不能直接运行？

这些文件依赖完整的生产项目环境：
- `from app.services.xxx import ...` — 需要项目的 services 层
- `from app.graphs.healing_graph import ...` — 需要 LangGraph 子图
- `from app.skills.healer import healer_skill` — 需要 healer_skill 模块
- DashScope API Key、MCP 工具、Phoenix 追踪等

配套代码为了**零依赖可运行**，用策略模式替代了 LangGraph，用正则规则替代了 LLM，用 JSON 文件替代了数据库。

## 怎么对照看？

1. 先读配套代码的教学版（能跑，概念清晰）
2. 再看生产版源码（不能跑，但看完整实现）
3. 对照 `COMPARISON.md` 理解架构差异

**教学版 ≈ 生产版的核心逻辑抽取 + 去掉外部依赖**

## 详细对照表

见 `COMPARISON.md`
