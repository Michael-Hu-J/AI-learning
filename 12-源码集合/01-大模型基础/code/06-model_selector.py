model_selection = {
    "简单问答": "small-chat",        # 便宜高效
    "日常对话": "small-chat",
    "内容创作": "mid-chat",          # 平衡
    "代码生成": "mid-chat",
    "复杂推理": "large-reasoning",  # 最贵但最准
    "数学计算": "large-reasoning",
    "长文档分析": "long-context",
    "图片理解": "vision-model",
}

# 用 small 模型快速验证 Prompt
response = llm.chat(prompt, model="qwen-turbo")
if validate(response):
    print("✅ 流程验证通过，可以进入下一步")

# small 效果不够，换 mid
small_result = llm.chat(prompt, model="qwen-turbo")
mid_result = llm.chat(prompt, model="qwen-plus")

if evaluate(mid_result) - evaluate(small_result) > 0.1:
    print("✅ mid模型提升明显，值得升级")

# mid 还不够，换 large
mid_score = evaluate(llm.chat(prompt, model="qwen-plus"))
large_score = evaluate(llm.chat(prompt, model="qwen-max"))

print(f"mid: {mid_score:.2f}, large: {large_score:.2f}")
if large_score - mid_score > 0.05:
    print("✅ 提升超过5%，考虑用大模型")

# 每个模型跑同一批测试数据
models = ["qwen-turbo", "qwen-plus", "qwen-max"]
results = {}

for model in models:
    scores = []
    latencies = []
    for item in test_dataset:
        start = time.time()
        response = llm.chat(item["prompt"], model=model)
        latency = time.time() - start
        score = evaluate(response, item["expected"])
        scores.append(score)
        latencies.append(latency)
    
    results[model] = {
        "avg_score": sum(scores) / len(scores),
        "pass_rate": sum(1 for s in scores if s >= 0.8) / len(scores),
        "p50_latency": sorted(latencies)[len(latencies)//2],
        "p95_latency": sorted(latencies)[int(len(latencies)*0.95)],
    }

# 输出对比表格
for model, metrics in results.items():
    print(f"{model}: 平均分={metrics['avg_score']:.2f}, "
          f"通过率={metrics['pass_rate']:.1%}, "
          f"P50={metrics['p50_latency']:.2f}s, "
          f"P95={metrics['p95_latency']:.2f}s")

def cost_benefit_analysis():
    """成本效益分析"""
    models = {
        "qwen-turbo": {"input_per_1k": 0.002, "output_per_1k": 0.006, "quality": 70},
        "qwen-plus": {"input_per_1k": 0.004, "output_per_1k": 0.012, "quality": 85},
        "glm-4": {"input_per_1k": 0.01, "output_per_1k": 0.03, "quality": 92},
    }
    
    # 假设月请求 10 万次，平均输入 1000Token，输出 500Token
    monthly_requests = 100000
    avg_input = 1000
    avg_output = 500
    
    print("=" * 60)
    print("📊 成本效益分析")
    print("=" * 60)
    
    for name, pricing in models.items():
        monthly_cost = (
            (monthly_requests * avg_input / 1000 * pricing["input_per_1k"]) +
            (monthly_requests * avg_output / 1000 * pricing["output_per_1k"])
        )
        cost_efficiency = pricing["quality"] / monthly_cost * 1000
        
        print(f"{name}: 月成本 {monthly_cost:,.0f}元, "
              f"质量{pricing['quality']}分, 性价比 {cost_efficiency:.1f}")
    
    print("=" * 60)

def route_request(user_input):
    """根据请求类型路由到不同模型"""
    if is_simple_question(user_input):
        return "qwen-turbo"      # 简单问题用便宜模型
    elif is_complex_reasoning(user_input):
        return "qwen-max"        # 复杂推理用大模型
    elif has_images(user_input):
        return "qwen-vl"         # 含图片用多模态模型
    elif is_long_document(user_input):
        return "qwen-long"       # 长文档用长上下文模型
    else:
        return "qwen-plus"       # 默认用中模型

def test_fallback_strategy():
    """测试模型降级策略"""
    models = ["qwen-max", "qwen-plus", "qwen-turbo"]
    
    for model in models:
        try:
            output = call_model(model, "测试", "YOUR_API_KEY")
            print(f"✅ {model}: 正常")
            return output
        except Exception as e:
            print(f"❌ {model}: {e}")
    
    print("❌ 所有模型都不可用！")
    return get_cached_response()  # 返回缓存的兜底答案

import time
import json
from typing import List, Dict

class ModelBenchmark:
    """模型基线测试框架"""
    
    def __init__(self, models: List[str], test_data: List[Dict]):
        self.models = models
        self.test_data = test_data
        self.results = {}
    
    def run(self):
        """运行基线测试"""
        for model in self.models:
            print(f"\n🧪 测试模型: {model}")
            scores = []
            latencies = []
            token_counts = []
            
            for i, item in enumerate(self.test_data):
                start = time.time()
                response = call_llm(model, item["prompt"])
                latency = time.time() - start
                
                score = evaluate_response(response, item["expected"])
                tokens = count_tokens(response)
                
                scores.append(score)
                latencies.append(latency)
                token_counts.append(tokens)
                
                if (i + 1) % 10 == 0:
                    print(f"  进度: {i+1}/{len(self.test_data)}")
            
            self.results[model] = {
                "avg_score": sum(scores) / len(scores),
                "pass_rate": sum(1 for s in scores if s >= 0.8) / len(scores),
                "p50_latency": sorted(latencies)[len(latencies)//2],
                "p95_latency": sorted(latencies)[int(len(latencies)*0.95)],
                "avg_tokens": sum(token_counts) / len(token_counts),
            }
        
        return self.results
    
    def report(self):
        """生成对比报告"""
        print("\n" + "=" * 70)
        print("📊 模型基线测试报告")
        print("=" * 70)
        print(f"{'模型':<15} {'平均分':>8} {'通过率':>8} "
              f"{'P50延迟':>10} {'P95延迟':>10} {'平均Token':>10}")
        print("-" * 70)
        
        for model, metrics in self.results.items():
            print(f"{model:<15} {metrics['avg_score']:>8.2f} "
                  f"{metrics['pass_rate']:>7.1%} "
                  f"{metrics['p50_latency']:>9.2f}s "
                  f"{metrics['p95_latency']:>9.2f}s "
                  f"{metrics['avg_tokens']:>10.0f}")
        
        print("=" * 70)

class CostCalculator:
    """成本计算器"""
    
    PRICING = {
        "qwen-turbo": {"input_per_1k": 0.002, "output_per_1k": 0.006},
        "qwen-plus": {"input_per_1k": 0.004, "output_per_1k": 0.012},
        "qwen-max": {"input_per_1k": 0.04, "output_per_1k": 0.12},
        "glm-4": {"input_per_1k": 0.01, "output_per_1k": 0.03},
    }
    
    def calculate_monthly_cost(self, model: str, 
                                daily_requests: int,
                                avg_input_tokens: int,
                                avg_output_tokens: int) -> dict:
        """计算月度成本"""
        pricing = self.PRICING[model]
        daily_requests = int(daily_requests)
        
        daily_cost = (
            daily_requests * avg_input_tokens / 1000 * pricing["input_per_1k"] +
            daily_requests * avg_output_tokens / 1000 * pricing["output_per_1k"]
        )
        monthly_cost = daily_cost * 30
        yearly_cost = monthly_cost * 12
        
        return {
            "model": model,
            "daily_cost": daily_cost,
            "monthly_cost": monthly_cost,
            "yearly_cost": yearly_cost,
        }
    
    def compare_models(self, daily_requests, avg_input, avg_output):
        """对比所有模型的成本"""
        print("\n💰 成本对比（日请求{}次，输入{}Token，输出{}Token）".format(
            daily_requests, avg_input, avg_output))
        print("-" * 50)
        
        for model in self.PRICING:
            result = self.calculate_monthly_cost(model, daily_requests, avg_input, avg_output)
            print(f"{model:<15} 月成本: ¥{result['monthly_cost']:>10,.2f}  "
                  f"年成本: ¥{result['yearly_cost']:>12,.2f}")

class ModelRouter:
    """模型路由器 - 根据请求特征选择最优模型"""
    
    def __init__(self):
        self.routes = {
            "faq": "qwen-turbo",
            "conversation": "qwen-turbo",
            "content_creation": "qwen-plus",
            "code_generation": "qwen-plus",
            "complex_reasoning": "qwen-max",
            "math": "qwen-max",
            "long_document": "qwen-long",
            "image_understanding": "qwen-vl",
        }
    
    def classify_request(self, text: str) -> str:
        """分类请求类型"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ["快递", "物流", "退款", "发货", "订单"]):
            return "faq"
        elif any(kw in text_lower for kw in ["写", "创作", "文案", "文章"]):
            return "content_creation"
        elif any(kw in text_lower for kw in ["代码", "编程", "function", "class"]):
            return "code_generation"
        elif any(kw in text_lower for kw in ["计算", "数学", "公式", "方程"]):
            return "math"
        elif len(text) > 5000:
            return "long_document"
        else:
            return "conversation"
    
    def route(self, text: str) -> str:
        """路由请求"""
        category = self.classify_request(text)
        model = self.routes[category]
        print(f"📍 请求分类: {category} → 选择模型: {model}")
        return model

import random

class FallbackTester:
    """降级策略测试工具"""
    
    def __init__(self, primary_model: str, fallback_models: list):
        self.primary = primary_model
        self.fallbacks = fallback_models
    
    def simulate_failure(self, model: str, failure_rate: float = 0.5) -> bool:
        """模拟模型故障"""
        return random.random() < failure_rate
    
    def test_fallback(self, num_trials: int = 100):
        """测试降级策略"""
        success_count = 0
        fallback_count = 0
        
        for _ in range(num_trials):
            # 尝试主模型
            if not self.simulate_failure(self.primary):
                success_count += 1
                continue
            
            # 主模型失败，尝试降级
            for fallback in self.fallbacks:
                if not self.simulate_failure(fallback, 0.1):  # 备用模型故障率低
                    success_count += 1
                    fallback_count += 1
                    break
            else:
                print(f"⚠️ 所有模型都不可用！")
        
        print(f"\n📊 降级测试结果（{num_trials}次试验）:")
        print(f"  成功: {success_count}/{num_trials} ({success_count/num_trials:.1%})")
        print(f"  降级触发: {fallback_count}/{num_trials} ({fallback_count/num_trials:.1%})")

def test_model_id_validation():
    """验证模型 ID 配置正确"""
    valid_models = {
        "small-chat", "mid-chat", "large-reasoning", "long-context",
        "qwen-turbo", "qwen-plus", "qwen-max", "glm-4",
    }

    config = load_config()
    model_id = config.get("model_id")

    assert model_id in valid_models, f"无效的模型 ID: {model_id}"
    print(f"✅ 模型 ID 校验通过: {model_id}")

import requests
import time

def call_model(model, prompt, api_key):
    """调用大模型 API（以 DashScope 兼容模式为例）"""
    response = requests.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 500,
        },
        timeout=30,
    )
    data = response.json()
    return data["choices"][0]["message"]["content"]

def benchmark_models(models, prompts, api_key):
    """对比多个模型的表现"""
    results = []

    for model in models:
        print(f"\n{'='*60}")
        print(f"🔍 测试模型: {model}")
        print("=" * 60)

        total_time = 0
        total_tokens = 0

        for i, prompt in enumerate(prompts):
            start = time.time()
            output = call_model(model, prompt, api_key)
            elapsed = time.time() - start

            # 粗略估算 Token（生产环境用 response.usage）
            tokens = len(prompt) * 1.5 + len(output) * 1.5
            total_time += elapsed
            total_tokens += tokens

            print(f"  用例{i+1}: {elapsed:.2f}s, ~{tokens:.0f} Token")
            print(f"  输出: {output[:60]}...")

        results.append({
            "model": model,
            "avg_time": total_time / len(prompts),
            "avg_tokens": total_tokens / len(prompts),
        })

    print(f"\n{'='*60}")
    print("📊 模型对比结果")
    print("=" * 60)
    for r in results:
        print(f"{r['model']}: 平均{r['avg_time']:.2f}s, ~{r['avg_tokens']:.0f} Token")
    return results

# 使用
models = ["qwen-turbo", "qwen-plus", "glm-4"]
prompts = [
    "解释什么是测试用例",
    "写一段 Python 代码实现二分查找",
    "分析这段日志的错误原因...",
]
# benchmark_models(models, prompts, "YOUR_API_KEY")

def cost_benefit_analysis():
    """成本效益分析"""
    models = {
        "qwen-turbo": {"input": 0.002, "output": 0.006, "quality": 70},
        "qwen-plus": {"input": 0.004, "output": 0.012, "quality": 85},
        "glm-4": {"input": 0.01, "output": 0.03, "quality": 92},
    }

    monthly_requests = 100000
    avg_input, avg_output = 1000, 500

    print("=" * 60)
    print("📊 成本效益分析")
    print("=" * 60)

    for name, pricing in models.items():
        monthly_cost = (
            monthly_requests * avg_input / 1000 * pricing["input"] +
            monthly_requests * avg_output / 1000 * pricing["output"]
        )
        cost_efficiency = pricing["quality"] / monthly_cost * 1000
        print(f"{name}: 月成本 {monthly_cost:,.0f}元, "
              f"质量{pricing['quality']}分, 性价比 {cost_efficiency:.1f}")
    print("=" * 60)

cost_benefit_analysis()

def test_fallback_strategy_live():
    """测试模型降级策略（联调版）"""
    models = ["qwen-plus", "qwen-turbo", "glm-4"]

    for model in models:
        try:
            output = call_model(model, "测试", "YOUR_API_KEY")
            print(f"✅ {model}: 正常")
            break
        except Exception as e:
            print(f"❌ {model}: {e}")
    else:
        print("❌ 所有模型都不可用！")
