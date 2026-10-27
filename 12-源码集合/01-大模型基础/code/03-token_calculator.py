text = "请帮我生成登录功能的测试用例"

# 不同模型的 Token 数（实际测试数据）
# Qwen（通义千问）: 18 Token
# GLM（智谱）:     15 Token  
# GPT-4o:          22 Token
# Claude:          20 Token

def calculate_cost(input_tokens, output_tokens, model="mid-chat"):
    """
    单次请求成本估算
    注意：以下价格为示例，以服务商控制台定价为准
    """
    pricing = {
        "small-chat":      {"input": 0.002, "output": 0.006},   # 元/千 Token
        "mid-chat":        {"input": 0.004, "output": 0.012},
        "large-reasoning": {"input": 0.02,  "output": 0.06},
    }
    price = pricing.get(model, pricing["mid-chat"])
    input_cost = (input_tokens / 1000) * price["input"]
    output_cost = (output_tokens / 1000) * price["output"]
    return input_cost + output_cost

# 一次典型调用
cost = calculate_cost(1000, 500, "mid-chat")
print(f"单次请求：约 {cost:.4f} 元")  # 约 0.01 元

# 1. 精简系统提示词（500 Token → 100 Token）
# ❌ 冗长
system_prompt = "你是一个专业的测试工程师，你有10年的测试经验...（省略 500 字）"
# ✅ 精简
system_prompt = "你是测试工程师，生成 API 测试用例。"

# 2. 控制历史对话轮数（只保留最近 5 轮）
history = conversation[-10:]  # 5 轮 × 2 条消息

# 3. 限制输出长度
response = llm.chat(messages=messages, max_tokens=500)

import tiktoken

def count_tokens(text, model="gpt-4o"):
    """精确计算文本的 Token 数"""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# 实测对比
text = "请帮我生成登录功能的测试用例"
print(f"GPT-4o: {count_tokens(text, 'gpt-4o')} Token")
print(f"GPT-3.5: {count_tokens(text, 'gpt-3.5-turbo')} Token")

# 中文场景也可以用
chinese_text = "你是一个专业的测试工程师，请根据以下需求生成测试用例"
print(f"中文: {count_tokens(chinese_text, 'gpt-4o')} Token")

# 通义千问的 Token 计算
from dashscope import Generation

def count_qwen_tokens(prompt, api_key):
    """用 DashScope API 计算 Token 数"""
    response = Generation.call(
        model='qwen-max',
        prompt=prompt,
        api_key=api_key,
    )
    return response.usage.input_tokens

def calculate_cost(input_tokens, output_tokens, pricing):
    """
    计算单次请求成本
    
    pricing 格式: {"input_per_k": 0.004, "output_per_k": 0.012}
    价格单位：元/千Token
    """
    input_cost = (input_tokens / 1000) * pricing["input_per_k"]
    output_cost = (output_tokens / 1000) * pricing["output_per_k"]
    return input_cost + output_cost

def calculate_monthly_cost(daily_requests, avg_input, avg_output, pricing):
    """计算月度成本"""
    daily_cost = calculate_cost(avg_input, avg_output, pricing)
    return daily_cost * daily_requests * 30

# 使用示例
pricing = {"input_per_k": 0.004, "output_per_k": 0.012}
print(f"单次成本: ¥{calculate_cost(5500, 800, pricing):.4f}")
print(f"月成本(500次/天): ¥{calculate_monthly_cost(500, 5500, 800, pricing):.0f}")

import time
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class TokenStats:
    count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    peak_timestamp: str = ""
    peak_tokens: int = 0

class TokenMonitor:
    """Token 消耗监控器——支持多维度统计和告警"""
    
    def __init__(self, alert_threshold=100000):
        self.stats = defaultdict(TokenStats)
        self.alert_threshold = alert_threshold  # 单次请求告警阈值
        self.alerts = []
    
    def record(self, label, input_tokens, output_tokens, cost=0):
        """记录一次 API 调用"""
        s = self.stats[label]
        s.count += 1
        s.input_tokens += input_tokens
        s.output_tokens += output_tokens
        s.total_cost += cost
        
        # 峰值检测
        total = input_tokens + output_tokens
        if total > s.peak_tokens:
            s.peak_tokens = total
            s.peak_timestamp = time.strftime("%H:%M:%S")
        
        # 告警检测
        if input_tokens > self.alert_threshold:
            self.alerts.append({
                "time": time.strftime("%H:%M:%S"),
                "label": label,
                "input_tokens": input_tokens,
                "message": f"⚠️ 输入Token异常: {input_tokens} > {self.alert_threshold}"
            })
    
    def report(self):
        """生成消耗报告"""
        print("=" * 60)
        print("📊 Token 消耗报告")
        print("=" * 60)
        for label, s in self.stats.items():
            avg_in = s.input_tokens / s.count if s.count else 0
            avg_out = s.output_tokens / s.count if s.count else 0
            print(f"\n📌 {label}")
            print(f"   请求数: {s.count:,}")
            print(f"   输入Token: {s.input_tokens:,} (平均 {avg_in:.0f})")
            print(f"   输出Token: {s.output_tokens:,} (平均 {avg_out:.0f})")
            print(f"   总成本: ¥{s.total_cost:.2f}")
            print(f"   峰值: {s.peak_tokens:,} Token @ {s.peak_timestamp}")
        
        if self.alerts:
            print(f"\n⚠️ 告警 ({len(self.alerts)} 条):")
            for a in self.alerts[-5:]:  # 只显示最新5条
                print(f"   [{a['time']}] {a['message']}")
        print("=" * 60)

# 使用示例
monitor = TokenMonitor(alert_threshold=50000)
monitor.record("写作助手", 5500, 800, 0.30)
monitor.record("代码生成", 12000, 3000, 0.75)
monitor.record("客服问答", 2000, 500, 0.14)
monitor.report()

import functools
import time

class CostOptimizedClient:
    """带成本优化的 API 客户端包装器"""
    
    def __init__(self, client, monitor=None):
        self.client = client
        self.monitor = monitor or TokenMonitor()
        self.cache = {}  # 简单缓存
    
    def call(self, label, messages, max_tokens=1000, use_cache=True):
        """带缓存和监控的 API 调用"""
        # 缓存检查
        cache_key = str(messages)
        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            print(f"💾 缓存命中: {label} (省 {cached['input_tokens']} Token)")
            return cached["response"]
        
        # 实际调用
        start = time.time()
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=max_tokens,
        )
        elapsed = time.time() - start
        
        # 记录 Token 消耗
        usage = response.usage
        self.monitor.record(
            label=label,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
        )
        
        # 缓存结果
        if use_cache:
            self.cache[cache_key] = {
                "response": response,
                "input_tokens": usage.prompt_tokens,
            }
        
        return response
    
    def get_report(self):
        """获取成本报告"""
        self.monitor.report()

def compare_token_efficiency(texts, models=None):
    """
    对比不同模型的 Token 效率
    
    参数:
        texts: 测试文本列表
        models: 模型列表，默认对比主流模型
    """
    if models is None:
        models = ["gpt-4o", "gpt-3.5-turbo", "claude-3-5-sonnet"]
    
    results = {}
    for model in models:
        results[model] = {"total_tokens": 0, "total_chars": 0, "count": 0}
        for text in texts:
            tokens = count_tokens(text, model)
            results[model]["total_tokens"] += tokens
            results[model]["total_chars"] += len(text)
            results[model]["count"] += 1
    
    # 输出对比报告
    print("模型 Token 效率对比:")
    print("-" * 50)
    for model, data in results.items():
        avg_tokens = data["total_tokens"] / data["count"]
        avg_chars = data["total_chars"] / data["count"]
        ratio = avg_tokens / avg_chars if avg_chars else 0
        print(f"{model}:")
        print(f"  平均Token: {avg_tokens:.1f}")
        print(f"  平均字符: {avg_chars:.1f}")
        print(f"  Token/字符比: {ratio:.2f}")
        print()

# 使用示例
test_texts = [
    "请帮我生成登录功能的测试用例",
    "你是一个测试工程师，请分析以下API接口的测试要点",
    "def test_user_login(): assert response.status_code == 200",
]
compare_token_efficiency(test_texts)

def test_token_estimation():
    """验证 Token 成本估算是否准确"""
    # 无输入输出，成本为 0
    cost = calculate_cost(0, 0, "mid-chat")
    assert cost == 0

    # 小模型比大模型便宜
    cost_small = calculate_cost(1000, 500, "small-chat")
    cost_large = calculate_cost(1000, 500, "large-reasoning")
    assert cost_small < cost_large

    # 输出比输入贵（同 Token 数下）
    input_only = calculate_cost(1000, 0, "mid-chat")
    output_only = calculate_cost(0, 1000, "mid-chat")
    assert input_only * 2 < output_only  # 输出至少贵 2 倍

import tiktoken

def count_tokens(text, model="gpt-3.5-turbo"):
    """计算文本的 Token 数"""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

texts = {
    "英文": "Please help me generate test cases for the login function",
    "中文": "请帮我生成登录功能的测试用例",
    "代码": "def test_login(): assert response.status_code == 200",
}

for lang, text in texts.items():
    tokens = count_tokens(text)
    print(f"{lang}: {len(text)}字符 → {tokens} Token")

def calculate_monthly_cost(qps, avg_input_tokens, avg_output_tokens,
                           input_price_per_k, output_price_per_k):
    """
    计算月度成本
    qps: 每秒请求数
    价格单位：元/千 Token
    """
    seconds_per_month = 30 * 24 * 3600
    requests_per_month = qps * seconds_per_month

    input_cost = (requests_per_month * avg_input_tokens / 1000) * input_price_per_k
    output_cost = (requests_per_month * avg_output_tokens / 1000) * output_price_per_k

    return input_cost + output_cost

# 示例：QPS=10，输入1000 Token，输出500 Token
cost = calculate_monthly_cost(
    qps=10,
    avg_input_tokens=1000,
    avg_output_tokens=500,
    input_price_per_k=0.004,
    output_price_per_k=0.012,
)
print(f"月度成本：约 {cost:,.0f} 元")
# 输出：月度成本：约 25,920 元

from collections import defaultdict

class SimpleTokenMonitor:
    """轻量 Token 消耗监控器——适合集成到测试流程"""

    def __init__(self):
        self.stats = defaultdict(lambda: {
            "count": 0, "input_tokens": 0, "output_tokens": 0
        })

    def record(self, model, input_tokens, output_tokens):
        self.stats[model]["count"] += 1
        self.stats[model]["input_tokens"] += input_tokens
        self.stats[model]["output_tokens"] += output_tokens

    def report(self):
        print("=" * 50)
        print("📊 Token 消耗报告")
        print("=" * 50)
        for model, data in self.stats.items():
            avg_in = data["input_tokens"] / data["count"]
            avg_out = data["output_tokens"] / data["count"]
            print(f"模型: {model}")
            print(f"  请求数: {data['count']}")
            print(f"  输入Token: {data['input_tokens']:,} (平均 {avg_in:.0f})")
            print(f"  输出Token: {data['output_tokens']:,} (平均 {avg_out:.0f})")
        print("=" * 50)

monitor = SimpleTokenMonitor()
monitor.record("qwen-plus", 1200, 450)
monitor.record("qwen-plus", 980, 520)
monitor.record("glm-4", 1100, 480)
monitor.report()
