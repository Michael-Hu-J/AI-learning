import time
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PerformanceMonitor:
    """
    性能监控器 - 核心思路：
    1. 分层次监控（健康/性能/漂移/公平性）
    2. 告警抑制避免告警风暴
    3. 指标历史用于趋势分析
    """
    def __init__(self, model_endpoint: str, config: Dict[str, Any] = None):
        self.model_endpoint = model_endpoint
        self.config = config or self._default_config()
        self.is_monitoring = False
        self.alert_callbacks = []
        self.performance_history = defaultdict(lambda: deque(maxlen=1000))
        self.alert_history = []
        self.last_alert_times = {}  # 告警抑制用
        
    def _default_config(self) -> Dict[str, Any]:
        return {
            'health_check_interval': 30,
            'performance_check_interval': 60,
            'drift_check_interval': 3600,
            'alert_thresholds': {
                'response_time_p95': 2.0,
                'error_rate': 0.05,
                'accuracy_drop': 0.05,
                'drift_threshold': 0.1,
            },
            'alert_suppression_window': 300,
        }

    def _trigger_alert(self, alert_type, message, severity, details=None):
        """触发告警（带抑制）"""
        current_time = time.time()
        suppression = self.config.get('alert_suppression_window', 300)
        last_time = self.last_alert_times.get(alert_type, 0)
        if current_time - last_time < suppression:
            return  # 抑制重复告警
        
        alert = {'timestamp': current_time, 'type': alert_type,
                 'message': message, 'severity': severity.value, 'details': details or {}}
        self.alert_history.append(alert)
        self.last_alert_times[alert_type] = current_time
        for cb in self.alert_callbacks:
            try: cb(alert)
            except: pass

import numpy as np

def calculate_psi(reference_data, current_data, bins=10):
    """
    计算PSI（Population Stability Index）
    PSI < 0.1: 分布稳定
    0.1 <= PSI < 0.25: 分布有变化
    PSI >= 0.25: 分布显著变化
    """
    # 创建分箱边界（基于参考数据）
    breakpoints = np.percentile(reference_data, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)  # 去重避免空箱
    
    # 计算参考数据和当前数据在各箱中的比例
    ref_counts, _ = np.histogram(reference_data, bins=breakpoints)
    cur_counts, _ = np.histogram(current_data, bins=breakpoints)
    
    # 添加平滑（避免除零）
    ref_pct = (ref_counts + 0.5) / (len(reference_data) + 0.5 * bins)
    cur_pct = (cur_counts + 0.5) / (len(current_data) + 0.5 * bins)
    
    # 计算PSI
    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi)

from scipy import stats

def ks_test_drift(reference_data, current_data):
    """KS检验：p_value < 0.05 认为分布发生变化"""
    ks_stat, p_value = stats.ks_2samp(reference_data, current_data)
    return {
        'ks_statistic': float(ks_stat),
        'p_value': float(p_value),
        'drift_detected': p_value < 0.05,
        'drift_severity': 'high' if ks_stat > 0.2 else 'medium' if ks_stat > 0.1 else 'low'
    }

from collections import defaultdict

class FeedbackProcessor:
    """反馈处理器：收集→分析→提取洞察→驱动改进"""
    def __init__(self):
        self.feedback_data = []
        
    def collect(self, predictions, user_feedback):
        """收集并分析反馈"""
        analysis = {
            'total': len(user_feedback),
            'by_sentiment': defaultdict(int),
            'by_type': defaultdict(int),
            'common_issues': defaultdict(int),
        }
        for pred, fb in zip(predictions, user_feedback):
            analysis['by_sentiment'][fb.get('sentiment', 'neutral')] += 1
            analysis['by_type'][fb.get('type', 'general')] += 1
            if 'issue' in fb:
                analysis['common_issues'][fb['issue']] += 1
        
        pos = analysis['by_sentiment'].get('positive', 0)
        neg = analysis['by_sentiment'].get('negative', 0)
        total = pos + neg + analysis['by_sentiment'].get('neutral', 0)
        analysis['satisfaction'] = {
            'positive_ratio': pos / total if total > 0 else 0,
            'negative_ratio': neg / total if total > 0 else 0,
        }
        analysis['top_issues'] = [
            (issue, count) for issue, count in analysis['common_issues'].items()
            if count / analysis['total'] > 0.1
        ]
        return analysis

def monitoring_pipeline():
    """数据采集→指标计算→异常检测→告警→反馈→报告"""
    requests = collect_model_requests()
    metrics = calculate_metrics(requests)
    drift_score = detect_drift(metrics)
    fairness = evaluate_fairness(requests)
    anomalies = detect_anomalies(metrics, drift_score, fairness)
    for a in anomalies:
        if should_alert(a): send_alert(a)
    feedback = collect_user_feedback()
    analysis = analyze_feedback(feedback)
    report = generate_report(metrics, drift_score, fairness, analysis)
    return report
