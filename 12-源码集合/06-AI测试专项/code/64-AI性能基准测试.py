import time
import statistics
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

class AIPerformanceBenchmark:
    """AI性能基准测试框架——实战版"""
    
    def __init__(self, model, hardware_config=None):
        self.model = model
        self.hardware_config = hardware_config or self._detect_hardware()
        self.results = {}
    
    def _detect_hardware(self):
        """自动检测硬件配置"""
        return {
            'cpu_count': psutil.cpu_count(logical=False),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'platform': __import__('platform').platform()
        }
    
    def warm_up(self, test_inputs, rounds=10):
        """预热模型——这一步千万别省！"""
        for inp in test_inputs[:rounds]:
            try:
                self.model.predict(inp)
            except:
                pass
    
    def run_single_benchmark(self, test_inputs, iterations=100):
        """单请求基准测试"""
        self.warm_up(test_inputs)
        
        latencies = []
        for i in range(iterations):
            start = time.perf_counter()  # 用perf_counter而不是time.time
            self.model.predict(test_inputs[i % len(test_inputs)])
            latencies.append(time.perf_counter() - start)
        
        return {
            'mean': statistics.mean(latencies),
            'median': statistics.median(latencies),
            'p95': np.percentile(latencies, 95),
            'p99': np.percentile(latencies, 99),
            'min': min(latencies),
            'max': max(latencies),
            'std': statistics.stdev(latencies) if len(latencies) > 1 else 0
        }

def run_concurrency_test(self, test_inputs, concurrency_levels=[1, 5, 10, 20, 50], duration=30):
    """并发测试——模拟多用户同时访问"""
    results = {}
    
    for level in concurrency_levels:
        print(f"并发级别: {level}")
        responses = []
        start_time = time.time()
        
        def worker():
            while time.time() - start_time < duration:
                req_start = time.time()
                try:
                    inp = test_inputs[hash(time.time()) % len(test_inputs)]
                    self.model.predict(inp)
                    responses.append(time.time() - req_start)
                except:
                    responses.append(-1)  # 用-1标记失败
        
        with ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(worker) for _ in range(level)]
            for f in as_completed(futures, timeout=duration + 10):
                try:
                    f.result()
                except:
                    pass
        
        successful = [r for r in responses if r > 0]
        results[level] = {
            'total': len(responses),
            'success': len(successful),
            'success_rate': len(successful) / len(responses) if responses else 0,
            'avg_latency': statistics.mean(successful) if successful else 0,
            'p95': np.percentile(successful, 95) if successful else 0,
            'throughput': len(successful) / duration
        }
    
    return results

def run_stability_test(self, test_inputs, duration=3600, interval=10):
    """稳定性测试——长时间运行，检测内存泄漏和性能退化"""
    measurements = []
    start = time.time()
    
    while time.time() - start < duration:
        req_start = time.time()
        try:
            inp = test_inputs[int(time.time()) % len(test_inputs)]
            self.model.predict(inp)
            latency = time.time() - req_start
        except Exception as e:
            latency = -1
            error = str(e)
        
        mem = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent()
        
        measurements.append({
            'time': time.time() - start,
            'latency': latency,
            'memory': mem,
            'cpu': cpu
        })
        
        time.sleep(interval)
    
    return self._analyze_stability(measurements)

def _analyze_stability(self, measurements):
    """分析稳定性数据"""
    latencies = [m['latency'] for m in measurements if m['latency'] > 0]
    memories = [m['memory'] for m in measurements]
    
    # 检测内存增长趋势
    mem_trend = np.polyfit(range(len(memories)), memories, 1)[0]
    
    return {
        'avg_latency': statistics.mean(latencies),
        'p99_latency': np.percentile(latencies, 99),
        'avg_memory': statistics.mean(memories),
        'memory_trend_per_hour': mem_trend * 3600,  # 每小时增长百分点
        'has_memory_leak': mem_trend > 0.01,  # 如果每小时增长超过0.01%，认为有泄漏
        'total_requests': len(measurements),
        'error_count': sum(1 for m in measurements if m['latency'] < 0)
    }

import matplotlib.pyplot as plt
import pandas as pd

def plot_latency_distribution(latencies, title="延迟分布"):
    """绘制延迟分布图"""
    plt.figure(figsize=(10, 6))
    plt.hist(latencies, bins=50, edgecolor='black', alpha=0.7)
    plt.axvline(x=pd.Series(latencies).mean(), color='red', 
                linestyle='--', label=f'平均: {pd.Series(latencies).mean():.3f}s')
    plt.axvline(x=pd.Series(latencies).quantile(0.95), color='orange', 
                linestyle='--', label=f'P95: {pd.Series(latencies).quantile(0.95):.3f}s')
    plt.axvline(x=pd.Series(latencies).quantile(0.99), color='purple', 
                linestyle='--', label=f'P99: {pd.Series(latencies).quantile(0.99):.3f}s')
    plt.xlabel('延迟 (秒)')
    plt.ylabel('请求数')
    plt.title(title)
    plt.legend()
    plt.savefig('latency_distribution.png', dpi=150)
    plt.show()

def plot_concurrency_comparison(results):
    """绘制并发对比图"""
    levels = sorted(results.keys())
    avg_latencies = [results[l]['avg_latency'] for l in levels]
    throughputs = [results[l]['throughput'] for l in levels]
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(levels, avg_latencies, 'b-', label='平均延迟')
    ax1.set_xlabel('并发数')
    ax1.set_ylabel('延迟 (秒)', color='b')
    
    ax2 = ax1.twinx()
    ax2.plot(levels, throughputs, 'r-', label='吞吐量')
    ax2.set_ylabel('吞吐量 (请求/秒)', color='r')
    
    plt.title('并发性能对比')
    plt.savefig('concurrency_comparison.png', dpi=150)
    plt.show()
