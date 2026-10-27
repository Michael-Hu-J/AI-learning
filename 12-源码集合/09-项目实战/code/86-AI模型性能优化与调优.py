import time
import psutil
import threading
from functools import wraps
from typing import Dict, Any, List
import numpy as np

class PerformanceAnalyzer:
    """性能分析器——帮你找到真正的瓶颈"""
    
    def __init__(self):
        self.metrics = {}
    
    def profile_inference(self, model, data, rounds=100):
        """分析模型推理性能"""
        # 预热——第一次推理通常慢，要排除
        for _ in range(5):
            _ = model.predict(data[:1])
        
        times = []
        for i in range(rounds):
            start = time.perf_counter()
            _ = model.predict(data[i:i+1])
            times.append(time.perf_counter() - start)
        
        return {
            'avg_ms': np.mean(times) * 1000,
            'p50_ms': np.percentile(times, 50) * 1000,
            'p95_ms': np.percentile(times, 95) * 1000,
            'p99_ms': np.percentile(times, 99) * 1000,
            'max_ms': max(times) * 1000,
            'throughput': rounds / sum(times)
        }

import torch

def quantize_model(model, quantization_type='dynamic'):
    """模型量化——FP32/FP16 → INT8"""
    model.eval()
    
    if quantization_type == 'dynamic':
        # 动态量化：简单快速，适合CPU推理
        model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
        torch.quantization.prepare(model, inplace=True)
        torch.quantization.convert(model, inplace=True)
    
    elif quantization_type == 'static':
        # 静态量化：需要校准数据，精度更好
        model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
        torch.quantization.prepare(model, inplace=True)
        # 用校准数据跑一遍
        with torch.no_grad():
            for batch in calibration_data:
                model(batch)
        torch.quantization.convert(model, inplace=True)
    
    return model

import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

def optimize_with_optuna(X_train, y_train, n_trials=50):
    """用Optuna做超参数优化"""
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 20),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
            'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        }
        model = RandomForestClassifier(**params, random_state=42)
        scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
        return scores.mean()
    
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)
    
    print(f"最佳参数: {study.best_params}")
    print(f"最佳精度: {study.best_value:.4f}")
    return study.best_params

from concurrent.futures import ThreadPoolExecutor
import queue
import threading

class BatchInferenceEngine:
    """批处理推理引擎——提升吞吐量的利器"""
    
    def __init__(self, model, batch_size=64, max_wait_ms=100):
        self.model = model
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
        self.request_queue = queue.Queue()
        self._running = True
    
    def start(self):
        """启动批处理线程"""
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.batch_thread = threading.Thread(target=self._process_batches)
        self.batch_thread.daemon = True
        self.batch_thread.start()
    
    def predict(self, data):
        """提交推理请求"""
        future = self.executor.submit(self._batched_predict, data)
        return future.result()
    
    def _batched_predict(self, data):
        """单个请求的批处理推理"""
        event = threading.Event()
        result = [None]
        self.request_queue.put((data, event, result))
        event.wait(timeout=5.0)
        return result[0]
    
    def _process_batches(self):
        """批量处理线程"""
        while self._running:
            batch = []
            events = []
            results = []
            
            # 攒够一批或者超时
            try:
                item = self.request_queue.get(timeout=self.max_wait_ms / 1000)
                batch.append(item[0])
                events.append(item[1])
                results.append(item[2])
                
                while len(batch) < self.batch_size:
                    try:
                        item = self.request_queue.get_nowait()
                        batch.append(item[0])
                        events.append(item[1])
                        results.append(item[2])
                    except queue.Empty:
                        break
                
                # 批量推理
                batch_result = self.model.predict(np.array(batch))
                
                # 分发结果
                for i, res in enumerate(batch_result):
                    results[i][0] = res
                    events[i].set()
            except Exception as e:
                print(f"批处理出错: {e}")

import time
import psutil
import threading
from collections import deque
import statistics

class PerformanceMonitor:
    """端到端性能监控器——上线后持续监控"""
    
    def __init__(self, window_size=1000):
        self.latencies = deque(maxlen=window_size)
        self.errors = deque(maxlen=window_size)
        self.throughput_window = deque(maxlen=window_size)
        self._running = False
    
    def start(self):
        """启动监控"""
        self._running = True
        self.report_thread = threading.Thread(target=self._report_loop)
        self.report_thread.daemon = True
        self.report_thread.start()
    
    def record(self, latency, success=True):
        """记录一次推理"""
        self.latencies.append(latency)
        self.errors.append(0 if success else 1)
        self.throughput_window.append(time.time())
    
    def get_metrics(self):
        """获取当前指标"""
        if not self.latencies:
            return None
        return {
            'p50_ms': statistics.median(self.latencies) * 1000,
            'p95_ms': sorted(self.latencies)[int(len(self.latencies)*0.95)] * 1000,
            'p99_ms': sorted(self.latencies)[int(len(self.latencies)*0.99)] * 1000,
            'error_rate': sum(self.errors) / len(self.errors) * 100,
            'qps': len(self.throughput_window) / max(1, time.time() - self.throughput_window[0]) if self.throughput_window else 0,
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
        }
    
    def _report_loop(self):
        """定期输出报告"""
        while self._running:
            metrics = self.get_metrics()
            if metrics:
                print(f"[监控] P50={metrics['p50_ms']:.1f}ms | "
                      f"P95={metrics['p95_ms']:.1f}ms | "
                      f"P99={metrics['p99_ms']:.1f}ms | "
                      f"错误率={metrics['error_rate']:.2f}% | "
                      f"QPS={metrics['qps']:.1f}")
            time.sleep(10)
