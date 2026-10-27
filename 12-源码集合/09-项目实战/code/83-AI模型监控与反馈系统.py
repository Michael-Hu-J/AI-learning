# 在模型服务中加一个中间件
@app.middleware("http")
async def monitor_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    monitor.record(
        input_features=request.json(),
        output=response.json(),
        response_time=duration,
        timestamp=time.time()
    )
    return response

class ModelMonitoringSystem:
    """模型监控系统 - 核心入口"""
    def __init__(self, config=None):
        self.config = config or self.default_config()
        self.data_collector = DataCollector()
        self.performance_monitor = PerformanceMonitor()
        self.drift_detector = DriftDetector()
        self.fairness_monitor = FairnessMonitor()
        self.alert_manager = AlertManager()
        self.feedback_processor = FeedbackProcessor()

    def default_config(self):
        return {
            'performance_thresholds': {
                'accuracy': 0.85,
                'response_time': 2.0,
                'throughput': 100
            },
            'drift_detection': {
                'drift_threshold': 0.1,
                'retrain_threshold': 0.2,
                'detection_frequency': 'hourly'
            },
            'alerting': {
                'critical_threshold': 0.9,
                'warning_threshold': 0.95,
                'notification_channels': ['email', 'slack', 'pagerduty']
            }
        }

class DriftDetector:
    """漂移检测器"""
    def _population_stability_index(self, baseline, current):
        """计算 PSI - 最常用的漂移检测方法"""
        import numpy as np
        bins = np.linspace(
            min(baseline.min(), current.min()),
            max(baseline.max(), current.max()),
            11  # 10个分箱
        )
        baseline_hist, _ = np.histogram(baseline, bins=bins)
        current_hist, _ = np.histogram(current, bins=bins)
        baseline_prop = (baseline_hist + 0.5) / (len(baseline) + 5)
        current_prop = (current_hist + 0.5) / (len(current) + 5)
        psi = np.sum((current_prop - baseline_prop) *
                     np.log(current_prop / baseline_prop))
        return {'psi': psi, 'significant': psi > 0.1}

class AlertManager:
    """告警管理器"""
    def __init__(self):
        self.suppress_window = 300  # 5分钟内不重复告警
        self.last_alert_times = {}

    def send_alert(self, alert_type, details, severity='medium'):
        alert_key = f"{alert_type}_{str(details)[:50]}"
        last_time = self.last_alert_times.get(alert_key, 0)
        if time.time() - last_time < self.suppress_window:
            return  # 抑制重复告警
        self._dispatch(alert_type, severity)

    def _dispatch(self, alert_type, severity):
        if severity == 'critical':
            self._send_sms(alert_type)
            self._send_email(alert_type)
        elif severity == 'warning':
            self._send_email(alert_type)
