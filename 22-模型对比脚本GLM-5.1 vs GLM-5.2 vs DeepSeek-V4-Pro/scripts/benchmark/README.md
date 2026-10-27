# 🧪 模型评测框架 - Benchmark

新模型上线对比测试工具，包含 10 条真实评测任务，可独立运行。默认对比 **GLM-5.1（百炼）**、**GLM-5.2（百炼）**、**DeepSeek-V4-Pro（官方）** 三个模型。

**作者**: 测试员周周（14 年测试经验，全网同名），微信公众号：测试员周周    微信：testzhouzhou  微信群：添加周周微信可拉群，已超200人不能扫码  

## 📁 目录结构

```
scripts/benchmark/
├── config/
│   └── models.yaml           # 模型配置（三模型已预置）
├── tasks/
│   └── benchmark_tasks.json  # 10 条评测任务
├── results/                  # 评测结果（JSON，运行后生成）
├── reports/                  # 对比报告（Markdown / HTML）
├── benchmark_runner.py       # 评测执行引擎
├── compare_results.py        # 对比报告生成器（Markdown + HTML）
├── html_report.py            # HTML 报告渲染
└── README.md
```

## 🚀 快速开始

### 1. 配置模型

编辑 `config/models.yaml`（当前已配置三个模型）：

```yaml
model1:
  name: "GLM-5.1（百炼）"
  model: "glm-5.1"
  api_key: ""  # 留空则从环境变量读取
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  temperature: 0.3

model2:
  name: "GLM-5.2（百炼）"
  model: "glm-5.2"
  api_key: ""
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  temperature: 0.3

model3:
  name: "DeepSeek-V4-Pro（官方）"
  model: "deepseek-v4-pro"
  api_key: ""
  base_url: "https://api.deepseek.com/v1"
  temperature: 0.3
```

也可通过 `--config` 指定其他配置文件。

### 2. 设置 API Key

```bash
# 百炼 API Key（GLM-5.1 / GLM-5.2）
export DASHSCOPE_API_KEY="<你的百炼 API Key>"

# DeepSeek API Key（DeepSeek-V4-Pro）
export DEEPSEEK_API_KEY="<你的 DeepSeek API Key>"
```

### 3. 安装依赖

```bash
pip install pyyaml
```

> 评测执行依赖系统已安装 `curl`。

### 4. 执行评测

```bash
# 依次评测三个模型
python benchmark_runner.py --model model1 --repeat 1
python benchmark_runner.py --model model2 --repeat 1
python benchmark_runner.py --model model3 --repeat 1

# 快速验证（只跑 3 条）
python benchmark_runner.py --model model3 --max-tasks 3

# 只测某个类别
python benchmark_runner.py --model model2 --filter "用例生成"

# 只跑指定任务（支持逗号分隔）
python benchmark_runner.py --model model2 --task-id BENCH_007

# 重复 3 次（稳定性测试）
python benchmark_runner.py --model model2 --repeat 3
```

结果默认保存到 `results/benchmark_<model>_<时间戳>.json`。

### 5. 生成对比报告

```bash
python compare_results.py \
  --model1 results/benchmark_glm-5.1_20260618_000958.json \
  --model2 results/benchmark_glm-5.2_20260618_004003.json \
  --model3 results/benchmark_deepseek-v4-pro_20260618_002542.json
```

默认同时在 `reports/` 下生成 Markdown 和 HTML 报告。也可指定输出路径：

```bash
python compare_results.py \
  --model1 results/benchmark_glm-5.1_20260618_000958.json \
  --model2 results/benchmark_glm-5.2_20260618_004003.json \
  --model3 results/benchmark_deepseek-v4-pro_20260618_002542.json \
  --output reports/comparison_20260618.md \
  --html reports/comparison_3models_20260618.html
```

## 📊 评测维度

| 维度 | 任务数 | 测试内容 |
|------|--------|---------|
| 任务规划 | 4 | 用例生成、需求解析、性能方案、用例评审 |
| 代码能力 | 3 | Pytest 脚本、Locust 脚本、代码 Review |
| 工具使用 | 1 | 模糊测试数据生成 |
| 知识问答 | 1 | Bug 分析诊断 |
| 多轮对话 | 1 | 测试报告生成 |

## 📋 评测任务列表

| ID | 类别 | 维度 | 难度 | 说明 |
|----|------|------|------|------|
| BENCH_001 | 用例生成 | 任务规划 | Medium | 电商秒杀系统测试用例 |
| BENCH_002 | 用例评审 | 任务规划 | Medium | 评审用例质量 |
| BENCH_003 | API 测试脚本 | 代码能力 | Medium | 生成 Pytest 脚本 |
| BENCH_004 | 性能测试方案 | 任务规划 | Hard | 秒杀接口压测方案 |
| BENCH_005 | Bug 分析 | 知识问答 | Hard | 性能瓶颈诊断 |
| BENCH_006 | 安全测试数据 | 工具使用 | Medium | 模糊测试数据 |
| BENCH_007 | Locust 脚本 | 代码能力 | Hard | 秒杀场景压测 |
| BENCH_008 | 测试报告 | 多轮对话 | Medium | 生成测试报告 |
| BENCH_009 | 需求解析 | 任务规划 | Easy | 提取测试要点 |
| BENCH_010 | 代码 Review | 代码能力 | Hard | Review 测试代码 |

## 🔧 扩展指南

### 添加新任务

编辑 `tasks/benchmark_tasks.json`，添加：

```json
{
  "task_id": "BENCH_011",
  "category": "新类别",
  "dimension": "对应维度",
  "difficulty": "Easy/Medium/Hard",
  "description": "任务描述",
  "input": "测试输入",
  "expected_output": "期望输出",
  "evaluation_criteria": ["标准1", "标准2"]
}
```

### 添加新模型

1. 在 `config/models.yaml` 中新增 `model4` 配置
2. 在 `benchmark_runner.py` 的 `MODEL_CHOICES` 和 `MODEL_ENV_VARS` 中注册新模型
3. 运行：`python benchmark_runner.py --model model4`

## 📈 输出示例

### 单模型评测报告

```
============================================================
📊 评测报告: GLM-5.2（百炼）
============================================================
测试日期: 2026-06-18 00:40:03
总任务: 10
通过: 10  ✅
失败: 0  ❌
通过率: 100.0%
平均耗时: 62.0s
平均 Token: 3,160
============================================================
```

### 三模型对比报告（2026-06-18 实测）

```
============================================================
📊 模型对比报告
============================================================
  GLM-5.1（百炼）:         通过率 100.0% | 平均耗时 61.5s | 平均 Token 3,414
  GLM-5.2（百炼）:         通过率 100.0% | 平均耗时 62.0s | 平均 Token 3,160
  DeepSeek-V4-Pro（官方）: 通过率 100.0% | 平均耗时 25.2s | 平均 Token 2,092

🎯 结论: DeepSeek-V4-Pro 速度最快，比 GLM-5.1 快 59.0%；Token 效率最高，比 GLM-5.1 省 38.7%
============================================================
```

## ⚠️ 注意事项

1. **API 费用**：全量评测每个模型约消耗 20,000+ tokens，三模型合计注意控制成本
2. **网络稳定**：默认超时 120 秒，可通过 `--timeout` 或配置文件调整
3. **结果复现**：建议 `--repeat 3` 取平均值，减少随机性
4. **公平对比**：所有模型使用相同的 temperature 和 max_tokens

## 📝 已有评测报告

```
reports/
├── comparison_3models_20260618_rerun.html      # 三模型对比（百炼通道，HTML）
├── comparison_official_3models_20260618.html   # 三模型对比（智谱官方通道，HTML）
├── comparison_20260618_004916.md               # 百炼通道 Markdown
└── comparison_20260618_065440.md               # 智谱官方通道 Markdown

results/
├── benchmark_glm-5.1_20260618_000958.json      # 百炼 GLM-5.1
├── benchmark_glm-5.2_20260618_004003.json      # 百炼 GLM-5.2
├── benchmark_deepseek-v4-pro_20260618_002542.json
├── benchmark_glm-5.1_20260618_064219.json      # 智谱官方 GLM-5.1
├── benchmark_glm-5.2_20260618_065043.json      # 智谱官方 GLM-5.2
└── benchmark_deepseek-v4-pro_20260618_065438.json
```

---

**作者**: 测试员周周（14 年测试经验，全网同名），微信公众号：测试员周周    微信：testzhouzhou  微信群：添加周周微信可拉群，已超200人不能扫码  
**创建时间**: 2026-04-27  
**最近更新**: 2026-06-18（GLM-5.1 vs GLM-5.2 vs DeepSeek-V4-Pro 三模型版）
