temperature_configs = {
    "数学计算":   0.0,   # 确定性最强
    "代码生成":   0.1,   # 需要准确，每次输出一致
    "测试用例":   0.1,   # 需要稳定，便于回归
    "数据提取":   0.1,
    "文本摘要":   0.3,
    "日常对话":   0.7,   # 平衡
    "创意写作":   0.8,   # 需要创意，但别直接上 1.0
    "头脑风暴":   1.0,   # 需要多样性，生产环境慎用
}

def test_temperature_impact():
    """测试温度对输出稳定性的影响"""
    prompt = "生成一条登录功能的测试用例"

    for temp in [0.0, 0.3, 0.7, 1.0]:
        results = []
        for _ in range(5):
            result = call_llm(prompt, temperature=temp)
            results.append(result)

        # 计算两两相似度
        similarities = []
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                sim = compute_similarity(results[i], results[j])
                similarities.append(sim)

        avg_sim = sum(similarities) / len(similarities)
        print(f"temperature={temp}: 平均相似度={avg_sim:.2f}")

    # 典型结果（GPT-4 类模型，仅供参考，以你的实测为准）
    # temperature=0.0: 平均相似度=1.00（几乎完全相同）
    # temperature=0.3: 平均相似度=0.92
    # temperature=0.7: 平均相似度=0.65
    # temperature=1.0: 平均相似度=0.45

# 常用组合参考（固定 top_p=0.9，只调 temperature 是入门最稳的做法）
configs = [
    {"temperature": 0.1, "top_p": 0.9},    # 稳定输出
    {"temperature": 0.3, "top_p": 0.95},   # 轻度创意
    {"temperature": 0.7, "top_p": 0.9},    # 平衡
    {"temperature": 1.0, "top_p": 1.0},    # 最大创意（测试环境慎用）
]

penalty_configs = {
    "写文章":     0.5,   # 避免重复表达
    "写测试用例": 0.3,   # 适度避免重复
    "写代码":     0.0,   # 代码里重复关键字合法，必须为 0
}

def test_penalty_on_code():
    """测试重复惩罚对代码生成的影响"""
    prompt = "写一个高效排序函数"

    for penalty in [0.0, 0.3, 0.7, 1.0]:
        code = call_llm(prompt, presence_penalty=penalty)

        # 检查代码是否可编译
        try:
            compile(code, "<test>", "exec")
            valid = True
        except SyntaxError:
            valid = False

        # 检查重复关键词
        repeat_count = code.count("def ") + code.count("return ")

        print(f"penalty={penalty}: 可编译={valid}, 重复关键词={repeat_count}")

    # 典型结果
    # penalty=0.0: 可编译=True, 重复关键词=5
    # penalty=0.3: 可编译=True, 重复关键词=3
    # penalty=0.7: 可编译=True, 重复关键词=2
    # penalty=1.0: 可编译=False, 重复关键词=1  ← 过度惩罚导致代码不合法！

# 稳定优先场景（代码、数据、计算）
stable_configs = {
    "数学计算":      {"temperature": 0.0, "top_p": 1.0, "presence_penalty": 0.0},
    "代码生成":      {"temperature": 0.1, "top_p": 0.9, "presence_penalty": 0.0},
    "数据提取":      {"temperature": 0.1, "top_p": 0.9, "presence_penalty": 0.0},
    "测试用例生成":  {"temperature": 0.1, "top_p": 0.9, "presence_penalty": 0.3},
    "回归测试":      {"temperature": 0.0, "top_p": 1.0, "presence_penalty": 0.0, "seed": 42},
}

# 平衡场景（对话、摘要、翻译）
balanced_configs = {
    "日常对话":      {"temperature": 0.7, "top_p": 0.9, "presence_penalty": 0.0},
    "文本摘要":      {"temperature": 0.3, "top_p": 0.9, "presence_penalty": 0.3},
    "翻译":          {"temperature": 0.3, "top_p": 0.9, "presence_penalty": 0.0},
    "问答":          {"temperature": 0.3, "top_p": 0.9, "presence_penalty": 0.0},
}

# 创意优先场景（写作、头脑风暴）
creative_configs = {
    "创意写作":      {"temperature": 0.8, "top_p": 0.95, "presence_penalty": 0.5},
    "头脑风暴":      {"temperature": 1.0, "top_p": 1.0, "presence_penalty": 0.5},
    "文案生成":      {"temperature": 0.7, "top_p": 0.95, "presence_penalty": 0.5},
    "角色扮演":      {"temperature": 0.8, "top_p": 0.95, "presence_penalty": 0.3},
}

import openai
from difflib import SequenceMatcher

client = openai.OpenAI()

def call_llm(prompt, **kwargs):
    """调用大模型，支持传入任意采样参数"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        **kwargs
    )
    return response.choices[0].message.content

def compute_similarity(text1, text2):
    """计算两个文本的相似度"""
    return SequenceMatcher(None, text1, text2).ratio()

def test_param_stability(prompt, params, n_runs=5):
    """测试一组参数配置的输出稳定性"""
    results = []
    for _ in range(n_runs):
        result = call_llm(prompt, **params)
        results.append(result)

    # 计算两两相似度
    similarities = []
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            similarities.append(compute_similarity(results[i], results[j]))

    avg_sim = sum(similarities) / len(similarities)
    return avg_sim

def compare_configs(prompts, configs):
    """对比多组参数配置"""
    for name, params in configs.items():
        scores = [test_param_stability(p, params) for p in prompts]
        print(f"{name}: 平均相似度={sum(scores)/len(scores):.3f}")

# 使用示例
configs = {
    "稳定型": {"temperature": 0.1, "top_p": 0.9},
    "平衡型": {"temperature": 0.7, "top_p": 0.9},
    "创意型": {"temperature": 1.0, "top_p": 1.0},
}
compare_configs(["生成测试用例", "写排序函数", "解释API"], configs)

def test_parameter_regression():
    """参数变更后，用基线集对比"""
    baseline_results = load_baseline("before_change.json")

    # 修改参数后的新结果
    new_results = []
    for item in test_dataset:
        result = call_llm(item["prompt"], temperature=0.2, top_p=0.9)
        new_results.append(result)

    # 逐条对比
    for i, (baseline, new) in enumerate(zip(baseline_results, new_results)):
        similarity = compute_similarity(baseline, new)
        if similarity < 0.8:
            print(f"[{i}] 输出变化过大: 相似度={similarity:.2f}")
            print(f"  基线: {baseline[:80]}...")
            print(f"  新版: {new[:80]}...")

import pytest

class TestSamplingParams:
    """采样参数回归测试"""

    BASELINE = {
        "temperature_0.1_stability": 0.90,  # 基线：温度0.1时稳定性>=0.90
        "temperature_0.7_stability": 0.50,  # 基线：温度0.7时稳定性>=0.50
    }

    def test_temperature_zero_stability(self):
        """temperature=0 时输出应高度一致"""
        prompt = "计算 2+2 等于几"
        sim = test_param_stability(prompt, {"temperature": 0.0})
        assert sim >= 0.99, f"temperature=0 时相似度应为0.99以上，实际为{sim:.3f}"

    def test_temperature_impact(self):
        """温度升高应导致稳定性下降"""
        prompt = "写一个冒泡排序"
        sim_low = test_param_stability(prompt, {"temperature": 0.1})
        sim_high = test_param_stability(prompt, {"temperature": 0.7})
        assert sim_low > sim_high, "温度越高，稳定性应该越低"

    def test_penalty_on_code(self):
        """重复惩罚不应破坏代码合法性"""
        prompt = "写一个Python的类，包含__init__和__str__方法"
        for penalty in [0.0, 0.3, 0.7]:
            code = call_llm(prompt, presence_penalty=penalty)
            assert "def" in code, f"penalty={penalty} 时代码缺少 def 关键字"
            assert "__init__" in code or "def " in code, f"penalty={penalty} 时代码结构不完整"
            # 高惩罚不应导致语法错误
            if penalty <= 0.3:
                compile(code, "<test>", "exec")  # 不应抛 SyntaxError

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# 定义不同场景的模型配置
def get_model(task_type="balanced"):
    configs = {
        "stable": {"temperature": 0.1, "top_p": 0.9},
        "balanced": {"temperature": 0.7, "top_p": 0.9},
        "creative": {"temperature": 1.0, "top_p": 1.0},
    }
    config = configs[task_type]
    return ChatOpenAI(model="gpt-4", **config)

# 使用示例
stable_model = get_model("stable")
creative_model = get_model("creative")

template = PromptTemplate.from_template("生成一条{feature}功能的测试用例")
chain = template | stable_model
result = chain.invoke({"feature": "登录"})

import requests
import json

def test_temperature(prompt, temps=[0.0, 0.3, 0.7, 1.0]):
    """测试不同温度下的输出差异"""
    print("=" * 60)
    print(f"📝 测试 Prompt: {prompt[:30]}...")
    print("=" * 60)

    for temp in temps:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer YOUR_API_KEY"},
            json={
                "model": "qwen-plus",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temp,
                "max_tokens": 100,
            }
        )
        data = response.json()
        output = data["choices"][0]["message"]["content"]
        print(f"\n温度 {temp}: {output[:60]}...")

    print("=" * 60)

# 测试：创意任务 vs 稳定任务，对比差异
test_temperature("写一句关于春天的诗")
test_temperature("解释什么是测试用例")

def test_top_p(prompt, top_ps=[0.1, 0.5, 0.9, 1.0]):
    """测试不同 Top_P 下的输出差异"""
    print("=" * 60)
    print(f"📝 测试 Prompt: {prompt[:30]}...")
    print("=" * 60)

    for top_p in top_ps:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer YOUR_API_KEY"},
            json={
                "model": "qwen-plus",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,  # 固定温度，只观察 top_p 的影响
                "top_p": top_p,
                "max_tokens": 100,
            }
        )
        data = response.json()
        output = data["choices"][0]["message"]["content"]
        print(f"\nTop_P {top_p}: {output[:60]}...")

    print("=" * 60)

test_top_p("写一个关于科技的故事开头")

def test_repetition_penalty(prompt, penalties=[1.0, 1.2, 1.5, 2.0]):
    """测试不同重复惩罚下的输出（Qwen 用 repetition_penalty，1.0=不惩罚）"""
    print("=" * 60)
    print(f"📝 测试 Prompt: {prompt[:30]}...")
    print("=" * 60)

    for penalty in penalties:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer YOUR_API_KEY"},
            json={
                "model": "qwen-plus",
                "messages": [{"role": "user", "content": prompt}],
                "repetition_penalty": penalty,
                "max_tokens": 200,
            }
        )
        data = response.json()
        output = data["choices"][0]["message"]["content"]

        # 统计重复词
        words = output.split()
        unique_words = set(words)
        repetition_rate = 1 - len(unique_words) / len(words) if words else 0

        print(f"\n惩罚 {penalty}: 重复率 {repetition_rate:.1%}")
        print(f"  输出: {output[:80]}...")

    print("=" * 60)

test_repetition_penalty("写一段关于测试的文字")
