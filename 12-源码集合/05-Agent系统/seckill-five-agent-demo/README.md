# 秒杀五 Agent 测试演示

> 对应 [20-多 Agent 测试场景](CrewAI系列文章/20-多-Agent-测试场景实现方案-秒杀系统实战.md) 与 [21-五 Agent 框架实战](CrewAI系列文章/21-CrewAI-多-Agent-测试框架实战-5-个-Agent-自动化测试秒杀系统.md)

五 Agent 顺序协作：**测试经理 → 设计师 → 工程师 → 分析师 → 报告专员**

## 快速开始（约 1 分钟）

```bash
cd seckill-five-agent-demo
chmod +x run.sh
./run.sh demo          # 默认：Mock 模式，无需 API Key
```

完成后查看 `reports/` 下 5 份 Markdown（计划 / 用例 / 结果 / 分析 / 总结）。

## 运行模式

| 模式 | 命令 | 说明 |
|------|------|------|
| demo | `./run.sh demo` | Mock 流水线，**无需 Key**，适合买家 5 分钟体验 |
| crew | `./run.sh crew` | 真实 CrewAI + LLM，需 `DASHSCOPE_API_KEY` |
| test | `./run.sh test` | pytest 自动化测试 |

## 真实 CrewAI 模式

```bash
export DASHSCOPE_API_KEY='your-key'
./run.sh crew
```

## 项目结构

```
seckill-five-agent-demo/
├── run.sh
├── main.py
├── samples/seckill_requirements.md
├── src/
│   ├── mock_pipeline.py    # Demo 模式
│   ├── crew_runner.py      # CrewAI 五 Agent
│   └── tools/api_test_tool.py
├── reports/                # 运行产出
└── tests/
```

## 许可证

MIT
