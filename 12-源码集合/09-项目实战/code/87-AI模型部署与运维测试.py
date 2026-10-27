import time
import requests
from typing import Dict, Any

class DeploymentValidator:
    """部署验证器——上线前的最后一道防线"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip('/')
    
    def validate_all(self) -> Dict[str, Any]:
        """执行完整的部署验证"""
        results = {}
        
        # 1. 连接性验证
        results['connectivity'] = self._check_connectivity()
        if results['connectivity']['status'] != 'passed':
            return self._fail_fast("连接性验证失败，终止后续验证", results)
        
        # 2. 健康检查
        results['health'] = self._check_health()
        
        # 3. 功能验证
        results['functionality'] = self._check_functionality()
        
        # 4. 性能验证
        results['performance'] = self._check_performance()
        
        # 5. 安全验证
        results['security'] = self._check_security()
        
        # 6. 资源验证
        results['resources'] = self._check_resources()
        
        # 计算综合评分
        results['overall_score'] = self._calculate_score(results)
        results['deploy_ready'] = results['overall_score'] >= 0.8
        
        return results
    
    def _check_connectivity(self) -> Dict[str, Any]:
        """检查连接性——三层验证"""
        try:
            # 第一层：HTTP 连接
            resp = requests.get(f"{self.endpoint}/health", timeout=10)
            if resp.status_code != 200:
                return {'status': 'failed', 'detail': f'HTTP {resp.status_code}'}
            
            # 第二层：API 可用性
            resp = requests.post(
                f"{self.endpoint}/predict",
                json={"input": "connectivity test"},
                timeout=30
            )
            if resp.status_code not in [200, 400]:
                return {'status': 'failed', 'detail': f'API returned {resp.status_code}'}
            
            return {'status': 'passed', 'latency_ms': resp.elapsed.total_seconds() * 1000}
        except Exception as e:
            return {'status': 'failed', 'detail': str(e)}

import threading
import time
from collections import defaultdict

class ProductionMonitor:
    """生产监控器——让模型运行透明化"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.metrics_history = defaultdict(list)
        self.alert_rules = []
        self.running = False
    
    def start(self, interval_seconds: int = 60):
        """启动持续监控"""
        self.running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval_seconds,), daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_loop(self, interval: int):
        """监控主循环"""
        while self.running:
            metrics = self._collect_metrics()
            for key, value in metrics.items():
                self.metrics_history[key].append({
                    'timestamp': time.time(),
                    'value': value
                })
            self._check_alerts(metrics)
            time.sleep(interval)
    
    def _collect_metrics(self) -> Dict[str, float]:
        """采集当前时刻的各项指标"""
        metrics = {}
        # 健康检查
        try:
            resp = requests.get(f"{self.endpoint}/health", timeout=10)
            metrics['health_status'] = 1.0 if resp.status_code == 200 else 0.0
            metrics['health_latency'] = resp.elapsed.total_seconds()
        except Exception:
            metrics['health_status'] = 0.0
            metrics['health_latency'] = -1.0
        # 模型推理测试
        try:
            start = time.time()
            resp = requests.post(
                f"{self.endpoint}/predict",
                json={"input": "monitoring probe"},
                timeout=30
            )
            metrics['inference_latency'] = time.time() - start
            metrics['inference_status'] = 1.0 if resp.status_code == 200 else 0.0
        except Exception:
            metrics['inference_latency'] = -1.0
            metrics['inference_status'] = 0.0
        return metrics

import numpy as np
from scipy import stats

class DriftDetector:
    """数据漂移检测器——用统计方法发现数据变化"""
    
    def __init__(self, baseline_data: np.ndarray, feature_names: list):
        self.baseline_data = baseline_data
        self.feature_names = feature_names
        self.drift_threshold = 0.05  # p-value 阈值
    
    def detect(self, current_data: np.ndarray) -> Dict[str, Any]:
        """检测当前数据相对于基准数据是否发生漂移"""
        results = {}
        for i, name in enumerate(self.feature_names):
            baseline_col = self.baseline_data[:, i]
            current_col = current_data[:, i]
            # 使用 KS 检验检测分布变化
            ks_stat, p_value = stats.ks_2samp(baseline_col, current_col)
            results[name] = {
                'ks_statistic': float(ks_stat),
                'p_value': float(p_value),
                'drift_detected': p_value < self.drift_threshold,
                'drift_magnitude': float(ks_stat)
            }
        drifted_features = [name for name, result in results.items() if result['drift_detected']]
        return {
            'overall_drift_detected': len(drifted_features) > 0,
            'drifted_features': drifted_features,
            'drift_ratio': len(drifted_features) / len(self.feature_names),
            'feature_results': results
        }

def validate_rollback_capability(
    current_version: str,
    previous_versions: list,
    rollback_script: str,
    test_endpoint: str
) -> Dict[str, Any]:
    """
    验证回滚能力——在测试环境实际执行一次回滚演练
    """
    results = {
        'backup_exists': False,
        'rollback_script_valid': False,
        'rollback_test_passed': False,
        'estimated_rollback_time': None,
        'issues': []
    }
    
    if not previous_versions:
        results['issues'].append("没有可用的历史版本")
        return results
    
    # 验证回滚脚本语法
    try:
        import subprocess
        result = subprocess.run(
            ['bash', '-n', rollback_script],
            capture_output=True, timeout=10
        )
        results['rollback_script_valid'] = (result.returncode == 0)
    except Exception as e:
        results['issues'].append(f"回滚脚本验证失败: {e}")
    
    # 在测试环境执行回滚演练
    try:
        start_time = time.time()
        subprocess.run(
            ['bash', rollback_script, previous_versions[0]],
            timeout=600
        )
        rollback_time = time.time() - start_time
        results['estimated_rollback_time'] = f"{rollback_time:.0f} 秒"
        
        # 验证回滚后的服务
        resp = requests.get(f"{test_endpoint}/health", timeout=30)
        results['rollback_test_passed'] = (resp.status_code == 200)
    except Exception as e:
        results['issues'].append(f"回滚演练失败: {e}")
    
    return results
