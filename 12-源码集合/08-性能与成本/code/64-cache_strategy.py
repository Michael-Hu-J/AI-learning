import time
import hashlib
import threading
from collections import OrderedDict

class LRUCache:
    """带 TTL 的 LRU 缓存"""

    def __init__(self, max_size=1000, default_ttl=3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _make_key(self, prompt, model="default"):
        raw = f"{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt, model="default"):
        key = self._make_key(prompt, model)
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry["time"] > entry["ttl"]:
                    del self.cache[key]
                    self.stats["misses"] += 1
                    return None
                self.cache.move_to_end(key)
                self.stats["hits"] += 1
                return entry["value"]
            self.stats["misses"] += 1
            return None

    def put(self, prompt, value, model="default", ttl=None):
        key = self._make_key(prompt, model)
        ttl = ttl or self.default_ttl
        entry = {"value": value, "time": time.time(), "ttl": ttl}
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = entry
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
                self.stats["evictions"] += 1

from sentence_transformers import SentenceTransformer, util
import threading

class SemanticCache:
    """语义缓存（使用 sentence-transformers）"""

    def __init__(self, threshold=0.85, max_size=5000):
        self.threshold = threshold
        self.max_size = max_size
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.queries = []
        self.responses = []
        self.embeddings = None  # 预计算的 embedding 矩阵
        self.lock = threading.Lock()
        self.stats = {"hits": 0, "misses": 0}

    def get(self, query):
        embedding = self.model.encode(query, convert_to_tensor=True)
        with self.lock:
            if len(self.queries) == 0:
                self.stats["misses"] += 1
                return None
            scores = util.cos_sim(embedding, self.embeddings)[0]
            best_idx = scores.argmax().item()
            if scores[best_idx] >= self.threshold:
                self.stats["hits"] += 1
                return self.responses[best_idx]
            self.stats["misses"] += 1
            return None

    def put(self, query, response):
        embedding = self.model.encode(query)
        with self.lock:
            self.queries.append(query)
            self.responses.append(response)
            if self.embeddings is None:
                self.embeddings = embedding.unsqueeze(0)
            else:
                self.embeddings = torch.cat([self.embeddings, embedding.unsqueeze(0)])
            # 超出容量时删除最旧的
            if len(self.queries) > self.max_size:
                self.queries.pop(0)
                self.responses.pop(0)
                self.embeddings = self.embeddings[1:]

import redis
import json
import time

class MultiLevelCache:
    """分层缓存：L1 内存 → L2 Redis → L3 数据库"""

    def __init__(self, redis_host='localhost', redis_port=6379):
        self.l1_cache = {}           # 内存缓存
        self.l1_ttl = 60             # L1 TTL: 60秒
        self.r = redis.Redis(redis_host, redis_port, decode_responses=True)
        self.l2_ttl = 3600           # L2 TTL: 1小时
        self.l3_db = None            # 数据库连接（按需初始化）
        self.l3_ttl = 86400          # L3 TTL: 24小时
        self.metrics = {"l1_hits": 0, "l2_hits": 0, "l3_hits": 0, "misses": 0}

    def get(self, prompt, model="default"):
        key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()

        # L1: 内存缓存
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if time.time() - entry["time"] < self.l1_ttl:
                self.metrics["l1_hits"] += 1
                return entry["value"]
            del self.l1_cache[key]

        # L2: Redis 缓存
        try:
            data = self.r.get(f"cache:{key}")
            if data:
                entry = json.loads(data)
                if time.time() - entry["time"] < self.l2_ttl:
                    self.metrics["l2_hits"] += 1
                    self.l1_cache[key] = entry  # 回填 L1
                    return entry["value"]
                self.r.delete(f"cache:{key}")
        except redis.ConnectionError:
            pass  # Redis 不可用时降级

        # L3: 数据库
        # ... 数据库查询逻辑 ...

        self.metrics["misses"] += 1
        return None

    def put(self, prompt, value, model="default"):
        key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
        entry = {"value": value, "time": time.time()}

        # 写入所有层级
        self.l1_cache[key] = entry
        try:
            self.r.setex(f"cache:{key}", self.l2_ttl, json.dumps(entry, ensure_ascii=False))
        except redis.ConnectionError:
            pass  # Redis 不可用时只写 L1
        # ... 写入数据库 ...

import time
from dataclasses import dataclass, field

@dataclass
class CacheMonitor:
    """缓存监控器"""
    total_requests: int = 0
    cache_hits: int = 0
    api_calls: int = 0
    total_saved_tokens: int = 0
    total_saved_cost: float = 0.0
    start_time: float = field(default_factory=time.time)

    def record_hit(self, tokens_saved=0):
        self.total_requests += 1
        self.cache_hits += 1
        self.total_saved_tokens += tokens_saved
        # GPT-4: $30/1M tokens
        self.total_saved_cost += tokens_saved * 30 / 1_000_000

    def record_miss(self):
        self.total_requests += 1
        self.api_calls += 1

    @property
    def hit_rate(self):
        return self.cache_hits / max(1, self.total_requests)

    @property
    def uptime_hours(self):
        return (time.time() - self.start_time) / 3600

    def report(self):
        return {
            "hit_rate": f"{self.hit_rate:.1%}",
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "api_calls": self.api_calls,
            "saved_tokens": f"{self.total_saved_tokens:,}",
            "saved_cost": f"${self.total_saved_cost:.2f}",
            "uptime_hours": f"{self.uptime_hours:.1f}",
        }
