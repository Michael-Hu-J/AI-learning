from dataclasses import dataclass
from typing import Dict

@dataclass
class ModelPricing:
    name: str
    input_price_per_million: float
    output_price_per_million: float
    context_window: int = 8192

MODEL_PRICING: Dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing("GPT-4o", 2.50, 10.00, 128000),
    "gpt-4o-mini": ModelPricing("GPT-4o-mini", 0.15, 0.60, 128000),
    "gpt-3.5-turbo": ModelPricing("GPT-3.5-Turbo", 0.50, 1.50, 16385),
    "qwen-max": ModelPricing("通义千问-Max", 40.0, 120.0, 32000),
    "qwen-plus": ModelPricing("通义千问-Plus", 8.0, 20.0, 131072),
    "glm-4": ModelPricing("智谱GLM-4", 10.0, 10.0, 128000),
}

class CostEstimator:
    def __init__(self, currency: str = "USD"):
        self.currency = currency

    def estimate_single_call(self, model: str, input_tokens: int, output_tokens: int) -> dict:
        pricing = MODEL_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing.input_price_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_price_per_million
        return {
            "model": pricing.name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": round(input_cost + output_cost, 6),
        }

    def estimate_monthly(self, model: str, daily_requests: int,
                         avg_input_tokens: int, avg_output_tokens: int) -> dict:
        single = self.estimate_single_call(model, avg_input_tokens, avg_output_tokens)
        monthly = single["total_cost"] * daily_requests * 30
        return {**single, "monthly_cost": round(monthly, 2)}

    def compare_models(self, input_tokens: int, output_tokens: int, daily_requests: int):
        results = []
        for key in MODEL_PRICING:
            r = self.estimate_monthly(key, daily_requests, input_tokens, output_tokens)
            results.append(r)
        results.sort(key=lambda x: x["monthly_cost"])
        return results

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date
from collections import defaultdict

@dataclass
class CostRecord:
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    user_id: str = ""
    endpoint: str = ""

class CostTracker:
    def __init__(self):
        self.records: List[CostRecord] = []
        self.lock = threading.Lock()
        self.daily_budget: Optional[float] = None
        self.monthly_budget: Optional[float] = None
        self.alerts: List[dict] = []
        self._circuit_breaker = False

    def record_call(self, model, input_tokens, output_tokens, cost, user_id="", endpoint=""):
        record = CostRecord(time.time(), model, input_tokens, output_tokens, cost, user_id, endpoint)
        with self.lock:
            self.records.append(record)
        self._check_budget()
        return record

    def _check_budget(self):
        today = date.today()
        today_cost = sum(r.cost for r in self.records if date.fromtimestamp(r.timestamp) == today)
        if self.daily_budget:
            if today_cost > self.daily_budget * 0.8 and not self._alerted_80:
                self.alerts.append({"type": "budget_80%", "cost": today_cost})
                self._alerted_80 = True
            if today_cost > self.daily_budget:
                self._circuit_breaker = True
                self.alerts.append({"type": "budget_exceeded", "cost": today_cost})

    def is_allowed(self) -> bool:
        return not self._circuit_breaker

    def get_summary(self) -> dict:
        total_cost = sum(r.cost for r in self.records)
        return {
            "total_calls": len(self.records),
            "total_cost": round(total_cost, 4),
            "cost_by_model": self._group_by("model"),
            "cost_by_user": self._group_by("user_id"),
            "alerts": self.alerts,
        }

    def _group_by(self, key: str) -> Dict[str, float]:
        grouped = defaultdict(float)
        for r in self.records:
            grouped[getattr(r, key)] += r.cost
        return dict(grouped)

import tiktoken

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# 实际使用示例
system_prompt = "你是一个专业的客服助手..."
user_message = "我想退款"
history = "用户：上次买的商品有问题\n助手：请问是什么问题？"

total_input = count_tokens(system_prompt) + count_tokens(history) + count_tokens(user_message)
print(f"总输入Token: {total_input}")

from enum import Enum

class Complexity(Enum):
    SIMPLE = "simple"       # FAQ、简单查询
    MEDIUM = "medium"       # 订单查询、账户问题
    COMPLEX = "complex"     # 投诉、个性化推荐

class ModelRouter:
    def __init__(self):
        self.model_map = {
            Complexity.SIMPLE: "gpt-3.5-turbo",
            Complexity.MEDIUM: "gpt-4o-mini",
            Complexity.COMPLEX: "gpt-4o",
        }
        self.stats = {"simple": 0, "medium": 0, "complex": 0}

    def classify(self, user_message: str) -> Complexity:
        # 简单规则分类：包含关键词的走小模型
        faq_keywords = ["退款", "发货", "物流", "支付", "发票", "退换"]
        if any(kw in user_message for kw in faq_keywords):
            self.stats["simple"] += 1
            return Complexity.SIMPLE
        
        order_keywords = ["订单", "账户", "密码", "地址"]
        if any(kw in user_message for kw in order_keywords):
            self.stats["medium"] += 1
            return Complexity.MEDIUM
        
        self.stats["complex"] += 1
        return Complexity.COMPLEX

    def get_model(self, user_message: str) -> str:
        complexity = self.classify(user_message)
        return self.model_map[complexity]

import hashlib
import time
from typing import Optional, Dict

class CostAwareCache:
    def __init__(self, default_ttl: int = 86400):
        self.cache: Dict[str, dict] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def _make_key(self, model: str, messages: list) -> str:
        content = f"{model}:{str(messages)}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, model: str, messages: list) -> Optional[str]:
        key = self._make_key(model, messages)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["time"] < entry["ttl"]:
                self.hits += 1
                return entry["response"]
            else:
                del self.cache[key]
        self.misses += 1
        return None

    def set(self, model: str, messages: list, response: str, ttl: Optional[int] = None):
        key = self._make_key(model, messages)
        self.cache[key] = {
            "response": response,
            "time": time.time(),
            "ttl": ttl or self.default_ttl,
        }

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

from datetime import datetime, timedelta

class CostReporter:
    def __init__(self, tracker: CostTracker):
        self.tracker = tracker

    def generate_daily_report(self, target_date=None) -> str:
        date = target_date or datetime.now().date()
        records = [r for r in self.tracker.records 
                   if datetime.fromtimestamp(r.timestamp).date() == date]
        
        total_cost = sum(r.cost for r in records)
        total_calls = len(records)
        avg_cost = total_cost / max(1, total_calls)
        
        report = f"=== {date} 成本日报 ===\n"
        report += f"总调用次数: {total_calls}\n"
        report += f"总成本: ¥{total_cost:.2f}\n"
        report += f"平均单次成本: ¥{avg_cost:.4f}\n"
        
        # 按模型统计
        model_costs = {}
        for r in records:
            model_costs[r.model] = model_costs.get(r.model, 0) + r.cost
        report += "\n按模型统计:\n"
        for model, cost in sorted(model_costs.items(), key=lambda x: -x[1]):
            report += f"  {model}: ¥{cost:.2f} ({cost/total_cost*100:.1f}%)\n"
        
        return report
