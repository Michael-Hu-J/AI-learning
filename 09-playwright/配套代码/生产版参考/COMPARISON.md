# 生产版 vs 教学版对照表

> 配套代码为了零依赖可运行，对真实项目做了简化。
> 下面列出的差异帮你看到："文章讲的" 和 "生产真正用的" 之间的关系。

## 1. 自愈引擎

| 维度 | 教学版（配套代码） | 生产版（真实项目） |
|------|------------------|------------------|
| 文件 | `healer/healing_graph.py` + `strategies.py` | `生产版参考/healing_graph.py`（209行） |
| 架构 | LangGraph 子图（教学版，无 MCP） | LangGraph StateGraph + MCP 编排 |
| 节点 | StrategyFactory.execute() | diagnose → plan → execute → 条件重试 |
| 异步 | 纯同步 | 异步子图 + 同步桥接入口 |
| MCP工具 | `healing_tools.py` 教学 stub（8 工具，本地模拟） | 真实 MCP + DB + 会话 |
| 追踪 | 无 | Phoenix/LangSmith 可观测性 |
| 重试逻辑 | factory.execute() 中处理 | 图内条件边 `_heal_should_retry` |
| 复杂度 | ⭐⭐ | ⭐⭐⭐⭐ |

**文章对照**：第4篇（AI自愈系统）的架构图画的其实是生产版，配套代码是实现思路的简化版。

## 2. 执行引擎

| 维度 | 教学版（配套代码） | 生产版（真实项目） |
|------|------------------|------------------|
| 文件 | `worker/ui_worker.py`（78行） | `生产版参考/ui_worker.py`（234行） |
| 定位解析 | 基础 resolve | 完整 resolve + locator_resolution 记录 |
| 自愈触发 | `invoke_healing_subgraph_sync()`（`worker/ui_worker.py`） | 同上 + MCP 工具层 |
| 日志 | 普通列表 | SSE 兼容的 `_push_log` + 限流500条 |
| 停止信号 | 无 | 支持 `stop_flag_path` 优雅停止 |
| 统计 | 基础 passed/failed | passed/failed/repaired + success_rate + self_healing 摘要 |
| 结果 | 简单 dict | 完整结构：locator_resolution + self_healing 计划 + 错误详情 |
| 错误处理 | 单个 try/except | 外层执行器异常 + 内层自愈异常分别捕获 |

**文章对照**：第2篇（执行引擎）和第7篇（并发控制）。

## 3. 定位解析器

| 维度 | 教学版（配套代码） | 生产版（真实项目） |
|------|------------------|------------------|
| 文件 | `locator/resolver.py`（147行） | `生产版参考/ui_locator_resolver.py`（304行） |
| L0_SEM | 简单语义选择器 | 完整语义 + latency_anomaly 优先级调整 |
| L3 | 纯规则启发式（token提取） | 规则启发式 + **真实 DashScope LLM 调用** |
| API调用 | 无 | httpx 调用 qwen-plus，15s超时，JSON 响应解析 |
| 缓存 | LRU 500条 | 同上 |
| L3 配置 | 无 | `enable_l3_ai` 开关 + `_query_llm_candidates()` |

**文章对照**：第3篇（三层定位降级）和第5篇（视觉语义定位）。

## 4. 视觉语义定位

| 维度 | 教学版（配套代码） | 生产版（真实项目） |
|------|------------------|------------------|
| 文件 | `locator/visual_repair.py`（64行） | `生产版参考/visual_repair.py` |*
| 函数名 | `build_semantic()` | `build_semantic_playwright_selectors()` |
| OpenCV | `opencv_to_selectors()` | `opencv_red_regions_to_selectors()` |
| 函数签名 | 简洁参数 | 完整参数 + latency_anomaly 控制 |
| 关键词提取 | 基础 | 更完善的关键词过滤（长度、起始字符） |

> *注：生产版 visual_repair.py 内容与配套代码的 `locator/visual_repair.py` 高度接近，生产版主要差异在函数命名和参数完整性。直接看配套代码版本即可。

## 5. 测试覆盖

| 维度 | 教学版（配套代码） | 生产版（真实项目） |
|------|------------------|------------------|
| 单元测试 | 19 个（test_healer.py） | 集成在 `test_ui_agents.py` 中 |
| E2E测试 | 7 个测试场景 | `test_seckill_playwright.py` + 集成测试 |
| 可运行性 |  零依赖，直接 `pytest` |  需完整项目环境 |

## 为什么要做简化？

```
教学版目标：零依赖、3步跑通、看代码理解概念
   |
   v
门槛降到最低 — 不需要DashScope API key、不需要LangGraph环境
   |
   v
生产版目标：高可用、可观测、真实AI能力
   |
   v
需要依赖环境 — LLM API、MCP工具、可观测性平台
```

两者架构上保持一致，核心差异在：
- 教学版用 **策略模式** 替代 LangGraph（概念等价）
- 教学版用 **正则规则** 替代 LLM（接口预留）
- 教学版用 **JSON文件** 替代数据库（零配置）

**教学版可直接运行的代码 ≈ 生产版的核心逻辑抽取 + 去掉外部依赖。**
