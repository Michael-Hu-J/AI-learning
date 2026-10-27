def test_context_window_edge():
    """测试上下文窗口边界行为"""
    long_history = []
    for i in range(100):
        long_history.append({"role": "user", "content": f"第{i}轮对话的内容" * 50})
        long_history.append({"role": "assistant", "content": f"第{i}轮回复" * 50})

    # 加一条关键约束
    long_history.append({"role": "user", "content": "请记住：我的名字是张三。"})

    # 再加更多对话，故意撑满窗口
    for i in range(50):
        long_history.append({"role": "user", "content": f"额外对话{i}"})
        long_history.append({"role": "assistant", "content": f"回复{i}"})

    long_history.append({"role": "user", "content": "我叫什么名字？"})
    response = call_llm(messages=long_history)

    if "张三" in response:
        print("✅ 模型记住了关键信息")
    else:
        print("❌ 模型丢失了关键信息（被截断或遗忘）")

response = llm.chat(messages=messages)

# 检查输出是否被截断
if response.usage.completion_tokens >= max_tokens:
    print("⚠️ 输出被截断，可能不完整")

# 检查输入是否被截断
if hasattr(response, 'input_truncated') and response.input_truncated:
    print("⚠️ 输入被截断，可能丢失信息")

# finish_reason 为 "length" 也说明输出到了上限
if getattr(response.choices[0], 'finish_reason', None) == "length":
    print("⚠️ finish_reason=length，输出被强制截断")

def compare_window_costs_simple():
    """对比不同窗口大小的单次/月度成本"""
    for window in [8000, 32000, 128000]:
        input_tokens = window * 0.5   # 假设用满窗口的 50%
        output_tokens = 500
        cost = calculate_cost(input_tokens, output_tokens)
        print(f"窗口 {window}: 单次 {cost:.4f} 元, 月1万次 {cost * 10000:.2f} 元")

# 输出示例:
# 窗口 8000: 单次 0.016 元, 月1万次 160.00 元
# 窗口 32000: 单次 0.064 元, 月1万次 640.00 元
# 窗口 128000: 单次 0.256 元, 月1万次 2560.00 元

import tiktoken

def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-Plus")

def count_qwen_tokens(text):
    return len(tokenizer.encode(text))

def approximate_tokens(text, language="zh"):
    if language == "zh":
        return int(len(text) * 1.5)  # GPT 系列
    return int(len(text.split()) * 1.3)  # 英文

def test_boundary(llm_client, max_tokens):
    messages = generate_conversation(rounds=200)
    messages.insert(100, {"role": "user", "content": "记住：密码是 123456"})
    messages.append({"role": "user", "content": "密码是什么？"})
    response = llm_client.chat(messages, max_tokens=500)
    return "123456" in response

def detect_truncation(llm_client):
    messages = [
        {"role": "user", "content": "开头记住：ALPHA"},
        {"role": "assistant", "content": "收到"},
    ]
    for i in range(100):
        messages.extend([
            {"role": "user", "content": f"填充{i}" * 10},
            {"role": "assistant", "content": f"回复{i}"},
        ])
    messages.extend([
        {"role": "user", "content": "结尾记住：BRAVO"},
        {"role": "user", "content": "开头和结尾分别记住了什么？"},
    ])
    response = llm_client.chat(messages)
    return {"has_beginning": "ALPHA" in response, "has_ending": "BRAVO" in response}

def build_rag_prompt(query, history, retriever, max_tokens):
    available = max_tokens - count_tokens(history) - count_tokens(query) - 2000
    docs = retriever.search(query, top_k=10)
    # 动态调整：只放入能装下的文档
    selected = []
    total = 0
    for doc in docs:
        if total + count_tokens(doc) <= available:
            selected.append(doc)
            total += count_tokens(doc)
    return assemble_prompt(query, history, selected)

class CostMonitor:
    def __init__(self, pricing):
        self.pricing = pricing
        self.records = []
    
    def record(self, input_t, output_t):
        cost = (input_t/1000)*self.pricing["in"] + (output_t/1000)*self.pricing["out"]
        self.records.append({"input": input_t, "output": output_t, "cost": cost})
    
    def total_cost(self):
        return sum(r["cost"] for r in self.records)

def test_context_window_boundary():
    """测试上下文窗口边界行为"""
    messages = []
    for i in range(200):
        messages.append({"role": "user", "content": f"第{i}轮：{'A' * 30}"})
        messages.append({"role": "assistant", "content": f"回复{i}：{'B' * 30}"})

    # 在中间插入关键信息
    messages.insert(100, {"role": "user", "content": "请记住：测试密码是 123456"})

    messages.append({"role": "user", "content": "测试密码是什么？"})
    response = call_llm(messages=messages, max_tokens=500)

    if "123456" in response:
        print("✅ 模型记住了关键信息")
    else:
        print("❌ 模型丢失了关键信息（窗口溢出或截断）")

def compare_window_costs(qps=10, hours_per_day=8, days_per_month=22):
    """对比不同窗口大小的月度成本"""
    windows = [8000, 32000, 128000]

    print("=" * 60)
    print("📊 不同窗口大小的成本对比")
    print("=" * 60)

    for window in windows:
        input_tokens = window * 0.5
        output_tokens = 500
        input_cost = (input_tokens / 1000) * 0.004
        output_cost = (output_tokens / 1000) * 0.012
        single_cost = input_cost + output_cost

        requests_per_month = qps * 3600 * hours_per_day * days_per_month
        monthly_cost = single_cost * requests_per_month

        print(f"窗口 {window}: 单次 {single_cost:.4f} 元, "
              f"月 {requests_per_month:,} 次, 总 {monthly_cost:,.0f} 元")

    print("=" * 60)

def detect_truncation_strategy():
    """检测平台的截断策略"""
    messages = [
        {"role": "user", "content": "开头记住：密码A"},
        {"role": "assistant", "content": "收到"},
    ]

    for i in range(100):
        messages.append({"role": "user", "content": f"无关内容{i}" * 10})
        messages.append({"role": "assistant", "content": f"回复{i}"})

    messages.append({"role": "user", "content": "结尾记住：密码B"})
    messages.append({"role": "assistant", "content": "收到"})
    messages.append({"role": "user", "content": "密码A和密码B分别是什么？"})

    response = call_llm(messages=messages)

    has_a = "密码A" in response or "A" in response
    has_b = "密码B" in response or "B" in response

    if has_a and has_b:
        print("✅ 平台保留了开头和结尾（可能是摘要压缩或中间截断）")
    elif has_a and not has_b:
        print("⚠️ 平台保留了开头，丢弃了结尾（丢弃最新策略）")
    elif not has_a and has_b:
        print("⚠️ 平台保留了结尾，丢弃了开头（丢弃最早/FIFO 策略）")
    else:
        print("❌ 平台两个都丢了（可能中间截断或窗口严重溢出）")
