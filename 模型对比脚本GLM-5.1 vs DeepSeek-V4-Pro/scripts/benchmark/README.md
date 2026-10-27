# 🧪 模型评测框架 - Benchmark

新模型上线对比测试工具，包含 10 条真实评测任务，可独立运行。

**作者**: 测试员周周（14 年测试经验，全网同名），微信公众号：测试员周周    微信：testzhouzhou  微信群：添加周周微信可拉群，已超200人不能扫码  

## 📁 目录结构

```
scripts/benchmark/
├── config/
│   └── models.yaml          # 模型配置（添加新模型只需改这里）
├── tasks/
│   └── benchmark_tasks.json  # 10 条真实评测任务
├── results/                   # 评测结果（JSON）
├── reports/                   # 对比报告（Markdown）
├── benchmark_runner.py        # 评测执行引擎
├── compare_results.py         # 对比报告生成器
└── README.md                  # 本文件
```

## 🚀 快速开始

### 1. 配置模型

编辑 `config/models.yaml`（当前已配置 GLM-5.1 和 DeepSeek-V4-Pro）：

```yaml
model1:
  name: "GLM-5.1（百炼）"
  model: "glm-5.1"
  api_key: ""  # 留空则从环境变量读取
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  temperature: 0.3

model2:
  name: "DeepSeek-V4-Pro（官方）"
  model: "deepseek-v4-pro"
  api_key: ""
  base_url: "https://api.deepseek.com/v1"
  temperature: 0.3
```

### 2. 设置 API Key

```bash
# 百炼 API Key（GLM-5.1）
export DASHSCOPE_API_KEY="<你的百炼 API Key>"

# DeepSeek API Key（DeepSeek-V4-Pro）
export DEEPSEEK_API_KEY="<你的 DeepSeek API Key>"
```

### 3. 安装依赖

```bash
pip install pyyaml
```

### 4. 执行评测

```bash
# 评测 GLM-5.1
python benchmark_runner.py --model model1 --repeat 1

# 评测 DeepSeek-V4-Pro
python benchmark_runner.py --model model2 --repeat 1

# 快速验证（只跑 3 条）
python benchmark_runner.py --model model2 --max-tasks 3

# 只测某个类别
python benchmark_runner.py --model model2 --filter "用例生成"

# 重复 3 次（稳定性测试）
python benchmark_runner.py --model model2 --repeat 3
```

### 5. 对比结果

```bash
python compare_results.py \
  --model1 results/benchmark_glm-5.1_final.json \
  --model2 results/benchmark_deepseek-v4-pro_final.json
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

编辑 `config/models.yaml`，添加 `model3`：

```yaml
model3:
  name: "新模型名称"
  model: "模型 ID"
  api_key: ""
  base_url: "API 地址"
  temperature: 0.3
```

然后运行：

```bash
python benchmark_runner.py --model model3
```

## 📈 输出示例

### 评测报告

```
============================================================
📊 评测报告: GLM-5.1（百炼）
============================================================
测试日期: 2026-04-27 13:10:00
总任务: 10
通过: 10  ✅
失败: 0  ❌
通过率: 100.0%
平均耗时: 70.4s
平均 Token: 3,369

--- 按维度 ---
  任务规划: 100% (4/4)
  代码能力: 100% (3/3)
  工具使用: 100% (1/1)
  知识问答: 100% (1/1)
  多轮对话: 100% (1/1)
============================================================
```

### 对比报告

```
============================================================
📊 模型对比报告
============================================================
  GLM-5.1（百炼）: 通过率 100.0% | 平均耗时 70.4s | 平均 Token 3,369
  DeepSeek-V4-Pro（官方）: 通过率 100.0% | 平均耗时 60.1s | 平均 Token 2,275

🎯 结论: DeepSeek-V4-Pro 在速度和 Token 效率上明显领先（快 14.6%，省 32.5% Token）

--- 逐任务对比 ---
  BENCH_001  用例生成    ✅ 80.2s/79.2s  4017/2712
  BENCH_002  用例评审    ✅ 67.9s/49.7s  2804/1791
  BENCH_003  API脚本     ✅ 54.0s/73.9s  3272/2850
  ...
============================================================
```

## ⚠️ 注意事项

1. **API 费用**：每次评测约消耗 10,000+ tokens，注意控制成本
2. **网络稳定**：确保网络稳定，超时设置 120 秒
3. **结果复现**：建议 `--repeat 3` 取平均值，减少随机性
4. **公平对比**：两个模型使用相同的 temperature 和 max_tokens

## 📝 已有评测报告

```
reports/
├── glm-5.1-vs-deepseek-v4-pro.md   # GLM-5.1 vs DeepSeek-V4-Pro 完整对比
├── glm-5.1-report.md               # GLM-5.1 单独评测报告
├── comparison_20260427.md          # qwen-plus vs qwen3.5-plus（历史，API 失败）
└── status_update.md                # 评测进度记录
```

---

**作者**: 测试员周周（14 年测试经验，全网同名），微信公众号：测试员周周    微信：testzhouzhou  微信群：添加周周微信可拉群，已超200人不能扫码  
**创建时间**: 2026-04-27  
**最近更新**: 2026-04-28（GLM-5.1 vs DeepSeek-V4-Pro 最终版）
