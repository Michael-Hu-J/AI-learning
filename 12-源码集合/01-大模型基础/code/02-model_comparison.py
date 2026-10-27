from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    error: Optional[str] = None

class ModelAdapter(ABC):
    """模型适配层基类"""
    @abstractmethod
    def call(self, prompt: str, system_prompt: str = "") -> ModelResponse:
        pass

class TongyiAdapter(ModelAdapter):
    """通义千问适配"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        # 实际项目中用 dashscope SDK

    def call(self, prompt: str, system_prompt: str = "") -> ModelResponse:
        start = time.time()
        try:
            # 调用通义千问 API
            # response = dashscope.Generation.call(...)
            elapsed = (time.time() - start) * 1000
            return ModelResponse(
                content="模拟返回内容",
                input_tokens=100,
                output_tokens=200,
                latency_ms=elapsed
            )
        except Exception as e:
            return ModelResponse(
                content="", input_tokens=0, output_tokens=0,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )

class DeepSeekAdapter(ModelAdapter):
    """DeepSeek 适配"""
    def __init__(self, api_key: str):
        self.api_key = api_key

    def call(self, prompt: str, system_prompt: str = "") -> ModelResponse:
        start = time.time()
        try:
            # 调用 DeepSeek API
            elapsed = (time.time() - start) * 1000
            return ModelResponse(
                content="模拟返回内容",
                input_tokens=100,
                output_tokens=200,
                latency_ms=elapsed
            )
        except Exception as e:
            return ModelResponse(
                content="", input_tokens=0, output_tokens=0,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )

import statistics
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TestResult:
    model_name: str
    total_cases: int = 0
    passed_cases: int = 0
    latencies: List[float] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    errors: int = 0

    @property
    def accuracy(self) -> float:
        return self.passed_cases / self.total_cases if self.total_cases > 0 else 0

    @property
    def p50_latency(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0

    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0

def run_model_comparison(
    adapters: Dict[str, ModelAdapter],
    test_prompts: List[str],
    check_fn=None
) -> Dict[str, TestResult]:
    """
    多模型对比测试
    adapters: {模型名: 适配器实例}
    test_prompts: 测试 Prompt 列表
    check_fn: 可选，验证函数 (response_content) -> bool
    """
    results = {}

    for model_name, adapter in adapters.items():
        result = TestResult(model_name=model_name, total_cases=len(test_prompts))

        for prompt in test_prompts:
            response = adapter.call(prompt)

            if response.error:
                result.errors += 1
                continue

            result.latencies.append(response.latency_ms)
            result.input_tokens += response.input_tokens
            result.output_tokens += response.output_tokens

            if check_fn is None:
                result.passed_cases += 1
            elif check_fn(response.content):
                result.passed_cases += 1

        results[model_name] = result

    return results

def print_comparison_table(results: Dict[str, TestResult]):
    """打印对比表格"""
    print(f"{'模型':20s} | {'准确率':>8s} | {'P50(ms)':>8s} | "
          f"{'P95(ms)':>8s} | {'输入Token':>10s} | {'输出Token':>10s} | {'错误数':>6s}")
    print("-" * 95)
    for name, r in results.items():
        print(f"{name:20s} | {r.accuracy:8.2%} | {r.p50_latency:8.0f} | "
              f"{r.p95_latency:8.0f} | {r.input_tokens:10d} | "
              f"{r.output_tokens:10d} | {r.errors:6d}")

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ModelCandidate:
    name: str
    chinese_score: float        # 中文能力 0-1
    reasoning_score: float      # 推理能力 0-1
    long_text_score: float      # 长文本能力 0-1
    code_score: float           # 代码能力 0-1
    context_window: int         # 上下文窗口 Token 数
    input_price_per_million: float   # 输入价格（元/百万 Token）
    output_price_per_million: float  # 输出价格（元/百万 Token）
    domestic_access: bool       # 国内是否可直接访问
    error_rate: float           # 错误率 0-1（越低越好）

def evaluate_models(
    candidates: List[ModelCandidate],
    requirements: Dict
) -> List[Dict]:
    """
    模型选型评分
    requirements 包含：
      - weights: 各维度权重 {维度名: 权重}
      - max_context: 需要的最小上下文窗口
      - budget_per_month: 月预算
      - need_domestic: 是否必须国内访问
      - need_private: 是否需要私有化部署
      - estimated_tokens_per_month: 预估月 Token 消耗
      - max_error_rate: 最大可接受错误率
    """
    weights = requirements.get("weights", {
        "chinese": 0.25,
        "reasoning": 0.25,
        "long_text": 0.15,
        "code": 0.10,
        "cost": 0.15,
        "stability": 0.10,
    })

    results = []
    for model in candidates:
        # 硬性条件过滤
        if requirements.get("need_domestic") and not model.domestic_access:
            continue        if model.context_window < requirements.get("max_context", 0):
            continue
        if model.error_rate > requirements.get("max_error_rate", 1.0):
            continue

        # 计算得分
        score = 0.0
        score += model.chinese_score * weights.get("chinese", 0)
        score += model.reasoning_score * weights.get("reasoning", 0)
        score += model.long_text_score * weights.get("long_text", 0)
        score += model.code_score * weights.get("code", 0)

        # 成本得分
        monthly_cost = (
            requirements["estimated_tokens_per_month"] / 1_000_000
            * (model.input_price_per_million + model.output_price_per_million)
        )
        cost_score = 1.0 - min(monthly_cost / requirements["budget_per_month"], 1.0)
        score += cost_score * weights.get("cost", 0)

        # 稳定性得分（错误率越低越好）
        stability_score = 1.0 - model.error_rate
        score += stability_score * weights.get("stability", 0)

        results.append({
            "model": model.name,
            "total_score": round(score, 3),
            "monthly_cost": round(monthly_cost, 2),
            "breakdown": {
                "chinese": model.chinese_score,
                "reasoning": model.reasoning_score,
                "long_text": model.long_text_score,
                "code": model.code_score,
                "cost": round(cost_score, 3),
                "stability": round(stability_score, 3),
            }
        })

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results

# 使用示例
if __name__ == "__main__":
    candidates = [
        ModelCandidate("GPT-4o", 0.75, 0.95, 0.90, 0.92, 128000, 25, 50, False, False, 0.01),
        ModelCandidate("Claude 3.5 Sonnet", 0.75, 0.92, 0.96, 0.88, 200000, 15, 75, False, False, 0.02),
        ModelCandidate("通义千问-Max", 0.92, 0.80, 0.75, 0.76, 32000, 120, 120, True, False, 0.003),
        ModelCandidate("智谱 GLM-4", 0.88, 0.85, 0.90, 0.82, 128000, 100, 100, True, False, 0.008),
        ModelCandidate("DeepSeek V3", 0.80, 0.82, 0.85, 0.84, 128000, 2, 8, True, False, 0.012),    ]

    requirements = {
        "need_domestic": True,
        "need_private": False,
        "max_context": 32000,
        "budget_per_month": 5000,
        "estimated_tokens_per_month": 10_000_000,  # 月 1000 万 Token
        "max_error_rate": 0.02,
        "weights": {
            "chinese": 0.30,
            "reasoning": 0.25,
            "long_text": 0.10,
            "code": 0.05,
            "cost": 0.20,
            "stability": 0.10,
        },
    }

    results = evaluate_models(candidates, requirements)
    print("=== 模型选型评分（国内、中文、推理、月预算5000元） ===")
    for r in results:
        print(f"{r['model']:20s} 得分={r['total_score']:.3f} "
              f"月成本={r['monthly_cost']:.0f}元")

def test_chinese_understanding(llm_call, model_name: str) -> dict:
    """中文理解能力测试集"""
    test_cases = [
        {
            "input": "把下面这段话翻译成英文，保持正式语气：'本公司承诺对用户数据严格保密'",
            "check": lambda r: "confidential" in r.lower() or "strictly" in r.lower(),
        },
        {
            "input": "请解释'画蛇添足'这个成语的含义，并举一个现代生活中的例子",
            "check": lambda r: "多余" in r or "不必要" in r,
        },
        {
            "input": "将以下需求文档改写为测试用例格式：'用户登录时，密码错误超过5次应锁定账户30分钟'",
            "check": lambda r: "5" in r and "30" in r and ("锁定" in r or "lock" in r.lower()),
        },
        {
            "input": "分析以下句子的语法结构：'虽然天气不好，但他还是去了'",
            "check": lambda r: "转折" in r or "让步" in r,
        },
    ]

    passed = 0
    for case in test_cases:
        response = llm_call(case["input"])
        if case["check"](response):
            passed += 1

    return {
        "model": model_name,
        "total": len(test_cases),
        "passed": passed,
        "accuracy": round(passed / len(test_cases), 2),
    }

def test_reasoning(llm_call, model_name: str) -> dict:
    """推理能力测试集"""
    test_cases = [
        {
            "input": "一个房间里有3个开关，分别控制隔壁房间的3盏灯。你只能进入隔壁房间一次，如何确定每个开关控制哪盏灯？",
            "check": lambda r: "温度" in r or "热" in r or "开一会儿" in r,
        },
        {
            "input": "写一个 Python 函数，判断一个字符串是否是回文，要求时间复杂度 O(n)",
            "check": lambda r: "def" in r and ("回文" in r or "palindrome" in r.lower()),
        },
        {
            "input": "如果所有 A 都是 B，有些 B 是 C，那么有些 A 是 C 这个结论是否正确？请说明理由",
            "check": lambda r: "不" in r and ("正确" in r or "必然" in r),
        },
    ]

    passed = 0
    for case in test_cases:
        response = llm_call(case["input"])
        if case["check"](response):
            passed += 1

    return {
        "model": model_name,
        "total": len(test_cases),
        "passed": passed,
        "accuracy": round(passed / len(test_cases), 2),
    }

import time

def test_cost_and_performance(llm_call, model_name: str, prompts: list) -> dict:
    """成本与性能综合测试"""
    latencies = []
    total_input_tokens = 0
    total_output_tokens = 0
    errors = 0

    for prompt in prompts:
        start = time.time()
        try:
            response = llm_call(prompt)
            elapsed = time.time() - start
            latencies.append(elapsed)
            # 实际项目中从 response.usage 获取 Token 数
            total_input_tokens += len(prompt) // 2  # 估算
            total_output_tokens += len(response) // 2
        except Exception:
            errors += 1

    latencies.sort()
    n = len(latencies)

    return {
        "model": model_name,
        "total_requests": len(prompts),
        "success": len(prompts) - errors,
        "errors": errors,
        "p50_latency": latencies[n // 2] if n > 0 else 0,
        "p95_latency": latencies[int(n * 0.95)] if n > 0 else 0,
        "avg_latency": sum(latencies) / n if n > 0 else 0,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
    }
