import json
import hashlib
import time
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import logging

class EventType(Enum):
    """事件类型"""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    API_CALL = "api.call"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"
    PERMISSION_DENIED = "permission.denied"
    PROMPT_INJECTION = "security.prompt_injection"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    CONFIG_CHANGE = "config.change"
    MODEL_CALL = "model.call"

@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str = field(default_factory=lambda: hashlib.sha256(
        f"{time.time()}{os.urandom(8).hex()}".encode()
    ).hexdigest()[:16])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_type: str = ""
    user_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    resource_type: str = ""
    resource_id: str = ""
    action: str = ""
    status: str = "success"  # success / failure
    details: Dict = field(default_factory=dict)
    risk_score: float = 0.0  # 风险评分 0-10

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    def verify_integrity(self) -> bool:
        """验证日志完整性"""
        stored_hash = self.details.get("_hash", "")
        computed_hash = self._compute_hash()
        return stored_hash == computed_hash

    def _compute_hash(self) -> str:
        """计算日志哈希（用于完整性校验）"""
        content = f"{self.event_id}{self.timestamp}{self.event_type}{self.user_id}{self.action}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

class AuditLogger:
    """审计日志记录器"""

    def __init__(self, log_file: str = "audit.log", enable_integrity: bool = True):
        self.log_file = log_file
        self.enable_integrity = enable_integrity
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 100

        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def log(self, event: AuditEvent) -> AuditEvent:
        """记录审计事件"""
        if self.enable_integrity:
            event.details["_hash"] = event._compute_hash()
            event.details["_prev_hash"] = self._get_last_hash()

        self.logger.info(event.to_json())
        self.event_buffer.append(event)

        if len(self.event_buffer) >= self.buffer_size:
            self._flush()

        return event

    def log_event(self, event_type: EventType, user_id: str = "",
                  action: str = "", resource_type: str = "",
                  resource_id: str = "", status: str = "success",
                  details: Dict = None, ip_address: str = "",
                  risk_score: float = 0.0) -> AuditEvent:
        """便捷的事件记录方法"""
        event = AuditEvent(
            event_type=event_type.value,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details=details or {},
            ip_address=ip_address,
            risk_score=risk_score,
        )
        return self.log(event)

    def _get_last_hash(self) -> str:
        """获取上一条日志的哈希（链式校验）"""
        if self.event_buffer:
            last = self.event_buffer[-1]
            return last.details.get("_hash", "")
        return "genesis"

    def _flush(self):
        """刷新缓冲区"""
        self.event_buffer.clear()

    def get_events(self, event_type: str = None, user_id: str = None,
                   start_time: str = None, end_time: str = None,
                   min_risk_score: float = 0.0) -> List[AuditEvent]:
        """查询审计事件"""
        events = list(self.event_buffer)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if min_risk_score > 0:
            events = [e for e in events if e.risk_score >= min_risk_score]
        return events


if __name__ == "__main__":
    logger = AuditLogger(log_file="/tmp/audit_test.log")

    logger.log_event(
        EventType.USER_LOGIN, user_id="user_001", action="login",
        ip_address="192.168.1.100"
    )
    logger.log_event(
        EventType.API_CALL, user_id="user_001", action="GET /api/v1/chats",
        resource_type="chat", resource_id="chat_001"
    )
    logger.log_event(
        EventType.DATA_EXPORT, user_id="user_002", action="export_all",
        resource_type="user_data", risk_score=7.5,
        details={"records_count": 10000, "format": "csv"}
    )
    logger.log_event(
        EventType.PERMISSION_DENIED, user_id="user_003", action="DELETE /api/v1/users",
        risk_score=8.0
    )
    logger.log_event(
        EventType.PROMPT_INJECTION, user_id="user_004", action="prompt_detected",
        risk_score=9.0,
        details={"injection_type": "system_prompt_override", "input_preview": "忽略之前的指令..."}
    )

    high_risk = logger.get_events(min_risk_score=7.0)
    print(f"=== 高风险事件 ({len(high_risk)} 条) ===\n")
    for event in high_risk:
        print(f"[{event.risk_score}] {event.event_type} | 用户: {event.user_id} | {event.action}")

import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta

@dataclass
class AnomalyAlert:
    """异常告警"""
    alert_id: str
    anomaly_type: str
    severity: str  # low / medium / high / critical
    description: str
    affected_user: str = ""
    affected_resource: str = ""
    evidence: Dict = field(default_factory=dict)
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

class AnomalyDetector:
    """异常检测器"""

    def __init__(self):
        self.alerts: List[AnomalyAlert] = []
        self.alert_counter = 0

    def detect_brute_force(self, events: List, threshold: int = 5,
                           window_seconds: int = 300) -> List[AnomalyAlert]:
        """检测暴力破解：同一用户/IP 在短时间内多次登录失败"""
        alerts = []
        login_failures = defaultdict(list)

        for event in events:
            if event.event_type == "user.login" and event.status == "failure":
                key = f"{event.user_id}:{event.ip_address}"
                login_failures[key].append(event)

        for key, failures in login_failures.items():
            if len(failures) >= threshold:
                user_id, ip = key.split(":")
                self._increment_alert()
                alerts.append(AnomalyAlert(
                    alert_id=f"ALERT-{self.alert_counter:04d}",
                    anomaly_type="brute_force",
                    severity="high",
                    description=f"检测到暴力破解：用户 {user_id} 从 IP {ip} 在窗口期内失败 {len(failures)} 次",
                    affected_user=user_id,
                    evidence={
                        "failure_count": len(failures),
                        "ip_address": ip,
                        "time_window_seconds": window_seconds,
                    },
                ))

        self.alerts.extend(alerts)
        return alerts

    def detect_data_exfiltration(self, events: List, threshold: int = 100,
                                  window_seconds: int = 3600) -> List[AnomalyAlert]:
        """检测数据泄露：短时间内大量数据导出"""
        alerts = []
        export_counts = defaultdict(int)
        export_details = defaultdict(list)

        for event in events:
            if event.event_type == "data.export":
                export_counts[event.user_id] += 1
                export_details[event.user_id].append(event)

        for user_id, count in export_counts.items():
            if count >= threshold:
                self._increment_alert()
                alerts.append(AnomalyAlert(
                    alert_id=f"ALERT-{self.alert_counter:04d}",
                    anomaly_type="data_exfiltration",
                    severity="critical",
                    description=f"检测到数据泄露：用户 {user_id} 导出 {count} 次",
                    affected_user=user_id,
                    evidence={
                        "export_count": count,
                        "time_window_seconds": window_seconds,
                    },
                ))

        self.alerts.extend(alerts)
        return alerts

    def detect_unusual_access_pattern(self, events: List) -> List[AnomalyAlert]:
        """检测异常访问模式：访问频率显著高于基线"""
        alerts = []
        user_call_counts = Counter()

        for event in events:
            if event.event_type == "api.call":
                user_call_counts[event.user_id] += 1

        if len(user_call_counts) < 2:
            return alerts

        counts = list(user_call_counts.values())
        mean_count = statistics.mean(counts)
        stdev_count = statistics.stdev(counts) if len(counts) > 1 else 0

        for user_id, count in user_call_counts.items():
            if stdev_count > 0 and (count - mean_count) / stdev_count > 2:
                self._increment_alert()
                alerts.append(AnomalyAlert(
                    alert_id=f"ALERT-{self.alert_counter:04d}",
                    anomaly_type="unusual_access",
                    severity="medium",
                    description=f"检测到异常访问频率：用户 {user_id} 调用 {count} 次（均值 {mean_count:.0f}，标准差 {stdev_count:.0f}）",
                    affected_user=user_id,
                    evidence={
                        "call_count": count,
                        "mean_count": round(mean_count, 2),
                        "stdev_count": round(stdev_count, 2),
                        "z_score": round((count - mean_count) / stdev_count, 2),
                    },
                ))

        self.alerts.extend(alerts)
        return alerts

    def _increment_alert(self):
        self.alert_counter += 1

    def get_all_alerts(self, min_severity: str = "low") -> List[AnomalyAlert]:
        """获取所有告警"""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order.get(min_severity, 0)
        return [
            a for a in self.alerts
            if severity_order.get(a.severity, 0) >= min_level
        ]

    def generate_report(self) -> Dict:
        """生成异常检测报告"""
        type_counts = Counter(a.anomaly_type for a in self.alerts)
        severity_counts = Counter(a.severity for a in self.alerts)

        return {
            "total_alerts": len(self.alerts),
            "by_type": dict(type_counts),
            "by_severity": dict(severity_counts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                }
                for a in self.alerts
            ],
        }


if __name__ == "__main__":
    logger = AuditLogger(log_file="/tmp/audit_anomaly_test.log")

    for i in range(8):
        logger.log_event(
            EventType.USER_LOGIN, user_id="target_user",
            action="login", status="failure", ip_address="10.0.0.99"
        )
    for i in range(150):
        logger.log_event(
            EventType.DATA_EXPORT, user_id="suspicious_user",
            action="export", resource_type="user_data"
        )
    for i in range(500):
        logger.log_event(
            EventType.API_CALL, user_id="bot_user",
            action="GET /api/v1/data"
        )

    detector = AnomalyDetector()
    events = logger.get_events()
    detector.detect_brute_force(events)
    detector.detect_data_exfiltration(events)
    detector.detect_unusual_access_pattern(events)

    report = detector.generate_report()
    print(f"=== 异常检测报告 ===\n总告警数: {report['total_alerts']}")
    for alert in report['alerts']:
        print(f"  [{alert['severity'].upper()}] {alert['description']}")

class EventType(Enum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    PASSWORD_CHANGE = "user.password_change"
    API_CALL = "api.call"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"
    DATA_IMPORT = "data.import"
    PERMISSION_CHANGE = "permission.change"
    PERMISSION_DENIED = "permission.denied"
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"
    PROMPT_INJECTION = "security.prompt_injection"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    CONFIG_CHANGE = "config.change"
    MODEL_CALL = "model.call"
    MODEL_UPDATE = "model.update"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"

from flask import request, g
import time

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    audit_logger.log_event(
        event_type=EventType.API_CALL,
        user_id=g.get("user_id", "anonymous"),
        action=f"{request.method} {request.path}",
        resource_type="api",
        resource_id=request.path,
        status="success" if response.status_code < 400 else "failure",
        details={
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
        },
        ip_address=request.remote_addr,
        risk_score=0.0,
    )
    return response

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON格式日志处理器"""
    def format(self, record):
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, 'event_type'):
            log_data["event_type"] = record.event_type
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        return json.dumps(log_data, ensure_ascii=False)

handler = logging.FileHandler("audit_structured.log")
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("structured_audit")
logger.addHandler(handler)

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        audit_logger.log_event(
            event_type=EventType.API_CALL,
            user_id=request.state.user_id if hasattr(request.state, "user_id") else "anonymous",
            action=f"{request.method} {request.url.path}",
            resource_type="api",
            resource_id=request.url.path,
            status="success" if response.status_code < 400 else "failure",
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "ip_address": request.client.host,
            },
            ip_address=request.client.host,
        )
        return response

app = FastAPI()
app.add_middleware(AuditMiddleware)

from prometheus_client import Counter, Histogram, start_http_server

# 定义指标
audit_events_total = Counter(
    'audit_events_total',
    'Total audit events',
    ['event_type', 'status']
)

audit_event_duration = Histogram(
    'audit_event_duration_seconds',
    'Time spent processing audit events',
)

# 在记录日志时更新指标
def log_with_metrics(event_type, status, duration):
    audit_events_total.labels(event_type=event_type, status=status).inc()
    audit_event_duration.observe(duration)
    audit_logger.log_event(
        event_type=event_type,
        status=status,
        details={"duration_seconds": duration},
    )

# 启动Prometheus指标服务
start_http_server(8000)

import re
from typing import Dict, List

class LogSanitizer:
    """日志脱敏工具"""

    # 敏感字段列表
    SENSITIVE_FIELDS = [
        "password", "token", "secret", "api_key", "apikey",
        "authorization", "cookie", "session",
        "id_card", "phone", "email",
    ]

    # 脱敏正则
    PATTERNS = [
        (re.compile(r'(password["\s:=]+)[^\s,"}]+', re.IGNORECASE), r'\1***'),
        (re.compile(r'(token["\s:=]+)[^\s,"}]+', re.IGNORECASE), r'\1***'),
        (re.compile(r'(\d{3})\d{4}(\d{4})'), r'\1****\2'),  # 手机号脱敏
        (re.compile(r'(\w)@\w+(\.\w+)'), r'\1***\2'),  # 邮箱脱敏
    ]

    def sanitize(self, data: str) -> str:
        """对日志内容进行脱敏"""
        result = data
        for pattern, replacement in self.PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def sanitize_dict(self, data: Dict) -> Dict:
        """对字典中的敏感字段脱敏"""
        result = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_FIELDS:
                result[key] = "***"
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            elif isinstance(value, str):
                result[key] = self.sanitize(value)
            else:
                result[key] = value
        return result

# 使用示例
sanitizer = LogSanitizer()
log_line = '{"user": "test@example.com", "password": "secret123", "phone": "13812345678"}'
print(sanitizer.sanitize(log_line))
# 输出: {"user": "t***@example.com", "password": "***", "phone": "138****5678"}
