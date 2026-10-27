import time
import threading
from collections import deque
import numpy as np
import statistics

class ModelMonitor:
    """AI模型监控器 - 核心骨架"""
    
    def __init__(self, model_endpoint, config=None):
        self.model_endpoint = model_endpoint
        self.config = config or self._default_config()
        self.is_monitoring = False
        self.performance_history = deque(maxlen=1000)
        self.alert_history = deque(maxlen=500)
        self.current_metrics = {}
        self.last_alert_time = {}
    
    def _default_config(self):
        return {
            'collection_interval': 60,
            'metric_calc_interval': 300,
            'drift_check_interval': 3600,
            'performance_thresholds': {
                'accuracy_drop': 0.05,
                'error_rate_increase': 0.1,
            },
            'drift_thresholds': {'psi_threshold': 0.2},
            'alert_suppression': 300,
        }
    
    def start_monitoring(self):
        """启动监控循环"""
        self.is_monitoring = True
        thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        thread.start()
    
    def _monitoring_loop(self):
        """监控主循环 - 核心逻辑"""
        last_metric_calc = time.time()
        last_drift_check = time.time()
        
        while self.is_monitoring:
            try:
                self._collect_data()
                now = time.time()
                
                # 定期计算指标
                if now - last_metric_calc > self.config['metric_calc_interval']:
                    self._calculate_metrics()
                    last_metric_calc = now
                
                # 定期检测漂移
                if now - last_drift_check > self.config['drift_check_interval']:
                    self._detect_drift()
                    last_drift_check = now
                
                time.sleep(1)
            except Exception as e:
                print(f"监控循环异常: {e}")
                time.sleep(10)
    
    def _collect_data(self):
        """从模型端点收集预测数据"""
        import random
        data_point = {
            'timestamp': time.time(),
            'prediction': random.choice([0, 1]),
            'confidence': random.uniform(0.5, 1.0),
            'response_time': random.uniform(0.05, 2.0),
            'features': [random.random() for _ in range(10)],
        }
        self.performance_history.append(data_point)
    
    def _calculate_metrics(self):
        """计算性能指标"""
        if len(self.performance_history) < 10:
            return
        recent = list(self.performance_history)
        response_times = [d['response_time'] for d in recent]
        confidences = [d['confidence'] for d in recent]
        
        self.current_metrics = {
            'avg_response_time': statistics.mean(response_times),
            'p95_response_time': np.percentile(response_times, 95),
            'avg_confidence': statistics.mean(confidences),
            'prediction_count': len(recent),
        }
        self._check_thresholds()
    
    def _check_thresholds(self):
        """检查是否触发告警"""
        metrics = self.current_metrics
        if metrics.get('p95_response_time', 0) > 1.5:
            self._send_alert('high_latency', 'P95延迟超过阈值', 'warning')
        if metrics.get('avg_confidence', 1.0) < 0.6:
            self._send_alert('low_confidence', '平均置信度过低', 'critical')
    
    def _send_alert(self, alert_type, message, severity):
        """发送告警（带抑制逻辑）"""
        now = time.time()
        suppression = self.config.get('alert_suppression', 300)
        if alert_type in self.last_alert_time:
            if now - self.last_alert_time[alert_type] < suppression:
                return
        self.last_alert_time[alert_type] = now
        self.alert_history.append({'timestamp': now, 'type': alert_type, 'severity': severity})
        print(f"[{severity.upper()}] {alert_type}: {message}")
    
    def _detect_drift(self):
        """检测数据漂移 - 核心是PSI计算"""
        if len(self.performance_history) < 100:
            return
        history = list(self.performance_history)
        mid = len(history) // 2
        baseline = history[:mid]
        current = history[mid:]
        
        for feat_idx in range(len(baseline[0]['features'])):
            baseline_vals = [d['features'][feat_idx] for d in baseline]
            current_vals = [d['features'][feat_idx] for d in current]
            psi = self._calculate_psi(baseline_vals, current_vals)
            if psi > self.config['drift_thresholds']['psi_threshold']:
                self._send_alert(f'feature_drift_{feat_idx}',
                    f'特征{feat_idx} PSI={psi:.3f} 超过阈值', 'warning')
    
    def _calculate_psi(self, baseline, current, bins=10):
        """计算PSI（Population Stability Index）"""
        all_vals = np.concatenate([baseline, current])
        bin_edges = np.histogram_bin_edges(all_vals, bins=bins)
        base_hist, _ = np.histogram(baseline, bins=bin_edges)
        curr_hist, _ = np.histogram(current, bins=bin_edges)
        base_prop = (base_hist + 0.5) / (len(baseline) + bins * 0.5)
        curr_prop = (curr_hist + 0.5) / (len(current) + bins * 0.5)
        psi = np.sum((curr_prop - base_prop) * np.log(curr_prop / base_prop))
        return float(psi) if not np.isnan(psi) else 0.0
    
    def get_status(self):
        """获取当前监控状态"""
        return {
            'is_monitoring': self.is_monitoring,
            'metrics': self.current_metrics,
            'recent_alerts': list(self.alert_history)[-5:],
            'data_points': len(self.performance_history),
        }

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
import pandas as pd

def detect_drift(baseline_df, current_df):
    """使用Evidently AI检测数据漂移"""
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=baseline_df, current_data=current_df)
    result = report.as_dict()
    return {
        'num_drifted_features': result['metrics'][0]['result']['number_of_drifted_features'],
        'total_features': result['metrics'][0]['result']['number_of_features'],
        'dataset_drift': result['metrics'][0]['result']['dataset_drift'],
    }

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 定义监控指标
prediction_counter = Counter('model_predictions_total', 'Total predictions', ['model_version'])
prediction_latency = Histogram('model_prediction_latency_seconds', 'Prediction latency')
model_accuracy = Gauge('model_accuracy', 'Current model accuracy')

# 启动Prometheus指标服务
start_http_server(8000)

def record_prediction(model_version, latency):
    """记录一次预测的监控数据"""
    prediction_counter.labels(model_version=model_version).inc()
    prediction_latency.observe(latency)

import sqlite3
import time

class FeedbackSystem:
    """模型反馈收集与闭环系统"""
    
    def __init__(self, db_path='feedback.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT, user_id TEXT,
                feedback_type TEXT, rating INTEGER,
                signal TEXT, timestamp REAL, model_version TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def record_explicit_feedback(self, prediction_id, user_id, rating, model_version):
        """记录显式反馈（用户打分）"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'INSERT INTO feedback (prediction_id, user_id, feedback_type, rating, timestamp, model_version) VALUES (?, ?, ?, ?, ?, ?)',
            (prediction_id, user_id, 'explicit', rating, time.time(), model_version))
        conn.commit()
        conn.close()
    
    def get_satisfaction_rate(self, hours=24):
        """计算满意度（最近N小时）"""
        conn = sqlite3.connect(self.db_path)
        cutoff = time.time() - hours * 3600
        cursor = conn.execute(
            'SELECT COUNT(*), SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) FROM feedback WHERE feedback_type = ? AND timestamp > ?',
            ('explicit', cutoff))
        total, good = cursor.fetchone()
        conn.close()
        return (good / total * 100) if total > 0 else 0
    
    def check_retraining_needed(self, hours=72, threshold=70):
        """检查是否需要重新训练模型"""
        satisfaction = self.get_satisfaction_rate(hours)
        if satisfaction < threshold:
            print(f"⚠️ 满意度 {satisfaction:.1f}% 低于阈值 {threshold}%，建议重新训练")
            return True
        print(f"✅ 满意度 {satisfaction:.1f}%，模型状态正常")
        return False
