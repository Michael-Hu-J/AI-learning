import time
import threading
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, date
from enum import Enum
from collections import defaultdict

class AlertLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

@dataclass
class AlertThreshold:
    """告警阈值配置"""
    level: AlertLevel
    budget_ratio: float      # 预算比例（0.3 = 30%）
    notify_channels: List[str] = field(default_factory=list)
    auto_action: Optional[str] = None  # 自动执行的动作

@dataclass
class AlertRecord:
    """告警记录"""
    level: AlertLevel
    timestamp: float
    current_cost: float
    budget: float
    ratio: float
    message: str
    channels_sent: List[str] = field(default_factory=list)
    action_taken: Optional[str] = None

class BudgetAlertManager:
    """分级预算告警管理器"""

    # 默认阈值配置
    DEFAULT_THRESHOLDS = [
        AlertThreshold(
            level=AlertLevel.INFO,
            budget_ratio=0.3,
            notify_channels=["log"],
        ),
        AlertThreshold(
            level=AlertLevel.WARNING,
            budget_ratio=0.5,
            notify_channels=["log", "email", "wechat"],
        ),
        AlertThreshold(
            level=AlertLevel.ALERT,
            budget_ratio=0.8,
            notify_channels=["log", "email", "wechat", "sms"],
            auto_action="limit_non_core",
        ),
        AlertThreshold(
            level=AlertLevel.CRITICAL,
            budget_ratio=1.0,
            notify_channels=["log", "email", "wechat", "sms", "phone"],
            auto_action="stop_api",
        ),
        AlertThreshold(
            level=AlertLevel.EMERGENCY,
            budget_ratio=1.5,
            notify_channels=["log", "email", "wechat", "sms", "phone", "all_staff"],
            auto_action="circuit_breaker",
        ),
    ]

    def __init__(self, budget: float, thresholds: Optional[List[AlertThreshold]] = None):
        self.budget = budget
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self.current_cost = 0.0
        self.alert_history: List[AlertRecord] = []
        self.triggered_levels: set = set()
        self.lock = threading.Lock()

        # 通知回调（实际项目中替换为真实的通知接口）
        self.notify_callbacks: Dict[str, Callable] = {
            "log": self._notify_log,
            "email": self._notify_email,
            "wechat": self._notify_wechat,
            "sms": self._notify_sms,
            "phone": self._notify_phone,
            "all_staff": self._notify_all_staff,
        }

        # 自动动作回调
        self.action_callbacks: Dict[str, Callable] = {
            "limit_non_core": self._action_limit_non_core,
            "stop_api": self._action_stop_api,
            "circuit_breaker": self._action_circuit_breaker,
        }

    def add_cost(self, cost: float) -> List[AlertRecord]:
        """增加成本并检查告警"""
        with self.lock:
            self.current_cost += cost
            alerts = []

            for threshold in self.thresholds:
                ratio = self.current_cost / self.budget

                if ratio >= threshold.budget_ratio and threshold.level not in self.triggered_levels:
                    self.triggered_levels.add(threshold.level)

                    message = (
                        f"[{threshold.level.value}] 预算告警: "
                        f"当前花费 ${self.current_cost:.2f} / 预算 ${self.budget:.2f} "
                        f"({ratio:.0%})"
                    )

                    # 发送通知
                    channels_sent = []
                    for channel in threshold.notify_channels:
                        if channel in self.notify_callbacks:
                            self.notify_callbacks[channel](message)
                            channels_sent.append(channel)

                    # 执行自动动作
                    action_taken = None
                    if threshold.auto_action and threshold.auto_action in self.action_callbacks:
                        self.action_callbacks[threshold.auto_action](self.current_cost, self.budget)
                        action_taken = threshold.auto_action

                    record = AlertRecord(
                        level=threshold.level,
                        timestamp=time.time(),
                        current_cost=self.current_cost,
                        budget=self.budget,
                        ratio=ratio,
                        message=message,
                        channels_sent=channels_sent,
                        action_taken=action_taken,
                    )
                    self.alert_history.append(record)
                    alerts.append(record)

            return alerts

    # ========== 通知方法（模拟实现） ==========

    def _notify_log(self, message: str):
        print(f"  [LOG] {message}")

    def _notify_email(self, message: str):
        print(f"  [EMAIL] 发送邮件: {message}")

    def _notify_wechat(self, message: str):
        print(f"  [WECHAT] 发送企业微信: {message}")

    def _notify_sms(self, message: str):
        print(f"  [SMS] 发送短信: {message}")

    def _notify_phone(self, message: str):
        print(f"  [PHONE] 拨打电话: {message}")

    def _notify_all_staff(self, message: str):
        print(f"  [ALL_STAFF] 全员通知: {message}")

    # ========== 自动动作（模拟实现） ==========

    def _action_limit_non_core(self, cost: float, budget: float):
        print(f"  [ACTION] 限制非核心功能: 当前 ${cost:.2f} / 预算 ${budget:.2f}")

    def _action_stop_api(self, cost: float, budget: float):
        print(f"  [ACTION] 停止 API 调用: 当前 ${cost:.2f} / 预算 ${budget:.2f}")

    def _action_circuit_breaker(self, cost: float, budget: float):
        print(f"  [ACTION] 紧急熔断: 当前 ${cost:.2f} / 预算 ${budget:.2f}")

    def get_status(self) -> dict:
        """获取当前状态"""
        ratio = self.current_cost / self.budget if self.budget > 0 else 0
        return {
            "current_cost": round(self.current_cost, 2),
            "budget": self.budget,
            "usage_ratio": round(ratio, 4),
            "triggered_levels": [l.value for l in self.triggered_levels],
            "total_alerts": len(self.alert_history),
            "remaining_budget": round(max(0, self.budget - self.current_cost), 2),
        }

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict

@dataclass
class BudgetConfig:
    """预算配置（多维度）"""
    daily_budget: float = 200.0
    weekly_budget: float = 1000.0
    monthly_budget: float = 3000.0

@dataclass
class BudgetSnapshot:
    """预算快照"""
    period: str          # "daily", "weekly", "monthly"
    spent: float
    budget: float
    ratio: float
    remaining: float
    projected_total: float  # 按当前速率预测的期末总花费
    status: str            # "normal", "warning", "critical"

class MultiPeriodBudgetMonitor:
    """多维度预算监控器"""

    def __init__(self, config: BudgetConfig):
        self.config = config
        self.records: List[dict] = []
        self.lock = threading.Lock()

    def record_cost(self, amount: float, metadata: Optional[dict] = None):
        """记录一笔花费"""
        with self.lock:
            self.records.append({
                "amount": amount,
                "timestamp": time.time(),
                "metadata": metadata or {},
            })

    def _get_period_records(self, days: int) -> List[dict]:
        """获取最近 N 天的记录"""
        cutoff = time.time() - days * 86400
        return [r for r in self.records if r["timestamp"] >= cutoff]

    def get_snapshot(self) -> Dict[str, BudgetSnapshot]:
        """获取所有维度的预算快照"""
        snapshots = {}

        # 日预算
        daily_records = self._get_period_records(1)
        daily_spent = sum(r["amount"] for r in daily_records)
        days_elapsed = max(1, (time.time() - daily_records[0]["timestamp"]) / 86400) if daily_records else 1
        daily_rate = daily_spent / days_elapsed if days_elapsed > 0 else daily_spent

        snapshots["daily"] = BudgetSnapshot(
            period="daily",
            spent=daily_spent,
            budget=self.config.daily_budget,
            ratio=daily_spent / self.config.daily_budget,
            remaining=max(0, self.config.daily_budget - daily_spent),
            projected_total=daily_rate * 30,
            status=self._get_status(daily_spent / self.config.daily_budget),
        )

        # 周预算
        weekly_records = self._get_period_records(7)
        weekly_spent = sum(r["amount"] for r in weekly_records)
        weeks_elapsed = max(1, (time.time() - weekly_records[0]["timestamp"]) / (7 * 86400)) if weekly_records else 1
        weekly_rate = weekly_spent / weeks_elapsed

        snapshots["weekly"] = BudgetSnapshot(
            period="weekly",
            spent=weekly_spent,
            budget=self.config.weekly_budget,
            ratio=weekly_spent / self.config.weekly_budget,
            remaining=max(0, self.config.weekly_budget - weekly_spent),
            projected_total=weekly_rate * 4,
            status=self._get_status(weekly_spent / self.config.weekly_budget),
        )

        # 月预算
        monthly_records = self._get_period_records(30)
        monthly_spent = sum(r["amount"] for r in monthly_records)
        months_elapsed = max(1, (time.time() - monthly_records[0]["timestamp"]) / (30 * 86400)) if monthly_records else 1
        monthly_rate = monthly_spent / months_elapsed

        snapshots["monthly"] = BudgetSnapshot(
            period="monthly",
            spent=monthly_spent,
            budget=self.config.monthly_budget,
            ratio=monthly_spent / self.config.monthly_budget,
            remaining=max(0, self.config.monthly_budget - monthly_spent),
            projected_total=monthly_rate,
            status=self._get_status(monthly_spent / self.config.monthly_budget),
        )

        return snapshots

    def _get_status(self, ratio: float) -> str:
        if ratio >= 1.0:
            return "critical"
        elif ratio >= 0.8:
            return "warning"
        return "normal"

    def print_dashboard(self):
        """打印预算仪表盘"""
        snapshots = self.get_snapshot()

        print("\n" + "=" * 65)
        print("预算监控仪表盘")
        print("=" * 65)

        for period, snap in snapshots.items():
            bar_length = 30
            filled = int(bar_length * min(1.0, snap.ratio))
            bar = "█" * filled + "░" * (bar_length - filled)

            status_icon = {"normal": "通过", "warning": "黄色", "critical": "严重"}[snap.status]

            print(f"\n  {status_icon} {period.upper()} 预算")
            print(f"     [{bar}] {snap.ratio:.0%}")
            print(f"     已花费: ${snap.spent:.2f} / 预算: ${snap.budget:.2f}")
            print(f"     剩余: ${snap.remaining:.2f}")
            print(f"     预测期末: ${snap.projected_total:.2f}")

        print("\n" + "=" * 65)

from prometheus_client import Counter, Gauge, start_http_server

# 定义指标
cost_total = Counter('api_cost_total', '总API花费', ['model', 'status'])
budget_usage = Gauge('budget_usage_ratio', '预算使用率', ['period'])
alert_triggered = Counter('budget_alerts_total', '预算告警次数', ['level'])
rate_anomaly = Gauge('call_rate_anomaly', '调用速率异常倍数')

# 启动 Prometheus 指标服务
start_http_server(8000)

# 在告警管理器中集成
class PrometheusBudgetAlertManager(BudgetAlertManager):
    def _notify_email(self, message: str):
        super()._notify_email(message)
        alert_triggered.labels(level="WARNING").inc()
    
    def _action_stop_api(self, cost: float, budget: float):
        super()._action_stop_api(cost, budget)
        alert_triggered.labels(level="CRITICAL").inc()

import time
from collections import deque
from typing import Optional

class RateAlertMonitor:
    """速率告警监控器"""
    
    def __init__(self, window_seconds: int = 600, threshold_multiplier: float = 5.0):
        """
        window_seconds: 滑动窗口大小（秒）
        threshold_multiplier: 异常倍数阈值（超过基线多少倍告警）
        """
        self.window_seconds = window_seconds
        self.threshold_multiplier = threshold_multiplier
        self.call_records = deque()  # (timestamp, count)
        self.baseline_records = deque(maxlen=7 * 24 * 60)  # 7天的基线数据
        self.last_alert_time = 0
        self.alert_cooldown = 300  # 告警冷却时间（秒）
    
    def record_calls(self, count: int):
        """记录一次调用批次"""
        now = time.time()
        self.call_records.append((now, count))
        self.baseline_records.append((now, count))
        self._cleanup_old_records()
    
    def _cleanup_old_records(self):
        """清理过期记录"""
        cutoff = time.time() - self.window_seconds
        while self.call_records and self.call_records[0][0] < cutoff:
            self.call_records.popleft()
    
    def check_rate_anomaly(self) -> Optional[dict]:
        """检查是否存在速率异常"""
        now = time.time()
        
        # 冷却期不检查
        if now - self.last_alert_time < self.alert_cooldown:
            return None
        
        # 计算当前窗口内的调用量
        current_count = sum(c for _, c in self.call_records)
        
        # 计算基线（过去 7 天同一时段的平均值）
        baseline_count = self._calculate_baseline()
        
        if baseline_count == 0:
            return None
        
        anomaly_ratio = current_count / baseline_count
        
        if anomaly_ratio >= self.threshold_multiplier:
            self.last_alert_time = now
            return {
                "current_count": current_count,
                "baseline_count": baseline_count,
                "anomaly_ratio": anomaly_ratio,
                "message": f"速率异常: 当前 {current_count} 次, 基线 {baseline_count} 次, 异常倍数 {anomaly_ratio:.1f}x"
            }
        
        return None
    
    def _calculate_baseline(self) -> float:
        """计算基线值"""
        if not self.baseline_records:
            return 0
        
        # 简化版：取过去 7 天的平均值
        total = sum(c for _, c in self.baseline_records)
        days = 7
        return total / days
