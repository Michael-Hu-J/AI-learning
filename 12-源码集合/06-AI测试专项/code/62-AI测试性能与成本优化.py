import time
import statistics

class AITestBenchmark:
    def __init__(self, warmup_runs=3):
        self.warmup_runs = warmup_runs
        self.results = {}
    
    def benchmark(self, name, func, num_runs=10):
        for _ in range(self.warmup_runs):
            func()
        durations = []
        for _ in range(num_runs):
            start = time.perf_counter()
            func()
            durations.append((time.perf_counter() - start) * 1000)
        self.results[name] = durations
        return {
            "avg_ms": statistics.mean(durations),
            "p95_ms": sorted(durations)[int(len(durations)*0.95)],
            "runs": len(durations)
        }

# 使用示例
bench = AITestBenchmark()
print(bench.benchmark("original", lambda: original_model.generate(prompt)))
print(bench.benchmark("quantized", lambda: quantized_model.generate(prompt)))

class CostTracker:
    def __init__(self, budget=1000):
        self.budget = budget
        self.spent = 0.0
    
    def record(self, test_name, cost):
        self.spent += cost
        pct = self.spent / self.budget
        if pct > 0.8:
            print(f"⚠️ 预算告警: 已使用{pct:.0%} (${self.spent:.2f}/${self.budget:.2f})")
        if pct > 1.0:
            print(f"🚨 预算超支! 已花费${self.spent:.2f}")
        return self.spent

tracker = CostTracker(budget=500)
tracker.record("test_case_1", 2.5)

from collections import OrderedDict
import hashlib, json, time

class SmartCache:
    def __init__(self, max_size=10000, ttl=3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.stats = {"hits": 0, "misses": 0}
    
    def get(self, *args):
        key = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()
        if key in self.cache:
            if time.time() - self.cache[key][0] < self.ttl:
                self.stats["hits"] += 1
                return self.cache[key][1]
            del self.cache[key]
        self.stats["misses"] += 1
        return None
    
    def put(self, value, *args):
        key = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = (time.time(), value)
