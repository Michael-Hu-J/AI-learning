import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class ConsentRecord:
    """用户同意记录——每次用户操作都生成一条记录"""
    consent_id: str
    user_id: str
    consent_given: bool
    timestamp: str
    purpose: str          # 数据使用目的
    ip_address: str = ""
    user_agent: str = ""
    version: str = "1.0"  # 隐私政策版本
    withdrawal_timestamp: str = ""

    def is_valid(self) -> bool:
        """同意是否有效：必须是已同意且未撤回"""
        return self.consent_given and not self.withdrawal_timestamp

class ConsentManager:
    """同意管理器"""
    def __init__(self):
        self.records: Dict[str, ConsentRecord] = {}

    def record_consent(self, user_id: str, purpose: str,
                       ip: str = "", ua: str = "") -> ConsentRecord:
        """记录用户同意——用户主动勾选时调用"""
        cid = hashlib.sha256(f"{user_id}:{purpose}:{time.time()}".encode()).hexdigest()[:16]
        record = ConsentRecord(
            consent_id=cid, user_id=user_id, consent_given=True,
            timestamp=datetime.now().isoformat(), purpose=purpose,
            ip_address=ip, user_agent=ua,
        )
        self.records[cid] = record
        return record

    def withdraw(self, consent_id: str) -> bool:
        """撤回同意——用户点击撤回时调用"""
        rec = self.records.get(consent_id)
        if not rec or rec.withdrawal_timestamp:
            return False
        rec.consent_given = False
        rec.withdrawal_timestamp = datetime.now().isoformat()
        return True

    def has_valid_consent(self, user_id: str, purpose: str) -> bool:
        """检查是否有有效同意"""
        for r in self.records.values():
            if r.user_id == user_id and r.purpose == purpose and r.is_valid():
                return True
        return False

from enum import Enum

class DSR(Enum):
    ACCESS = "访问权"
    RECTIFICATION = "更正权"
    ERASURE = "删除权"
    PORTABILITY = "可携带权"
    RESTRICTION = "限制处理权"
    OBJECT = "反对权"

class DataSubjectRightsEngine:
    """数据主体权利处理引擎"""
    def __init__(self):
        self.user_data: Dict[str, Dict] = {}
        self.restricted_users: set = set()
        self.requests: Dict[str, Dict] = {}

    def handle_request(self, user_id: str, right: DSR) -> Dict:
        """处理数据主体请求"""
        req_id = hashlib.sha256(f"{user_id}:{right.value}:{time.time()}".encode()).hexdigest()[:16]
        result = {"request_id": req_id, "user_id": user_id, "right": right.value,
                  "status": "completed", "timestamp": datetime.now().isoformat()}

        if right == DSR.ACCESS:
            result["data"] = self.user_data.get(user_id, {})

        elif right == DSR.PORTABILITY:
            result["data"] = self.user_data.get(user_id, {})
            result["format"] = "JSON"

        elif right == DSR.ERASURE:
            if user_id in self.user_data:
                del self.user_data[user_id]
            self.restricted_users.discard(user_id)
            result["message"] = "数据已彻底删除"

        elif right == DSR.RESTRICTION:
            self.restricted_users.add(user_id)
            result["message"] = "数据处理已限制"

        elif right == DSR.OBJECT:
            self.restricted_users.add(user_id)
            result["message"] = "已反对数据处理"

        self.requests[req_id] = result
        return result

from datetime import datetime, timedelta

RETENTION_POLICIES = {
    "user_account": {"days": 365, "action": "anonymize"},
    "chat_history": {"days": 180, "action": "delete"},
    "audit_log": {"days": 730, "action": "archive"},
    "training_data": {"days": 365, "action": "remove"},
}

def check_retention(data_type: str, created_at: str) -> Dict:
    """检查数据保留合规性"""
    policy = RETENTION_POLICIES.get(data_type)
    if not policy:
        return {"compliant": False, "reason": "未配置保留策略"}

    created = datetime.fromisoformat(created_at)
    age = (datetime.now() - created).days
    max_age = policy["days"]

    if age > max_age:
        return {
            "compliant": False,
            "age_days": age,
            "max_days": max_age,
            "action": policy["action"],
            "overdue_by": age - max_age,
        }
    return {"compliant": True, "age_days": age, "max_days": max_age}

@dataclass
class DPIAReport:
    """数据保护影响评估报告"""
    project_name: str
    data_categories: List[str]
    purpose: str
    risk_level: str       # low / medium / high
    risks: List[Dict]
    safeguards: List[str]
    conclusion: str

def run_dpia(project_name: str, data_cats: List[str], purpose: str) -> DPIAReport:
    """执行DPIA评估"""
    risks = []
    if "personal_data" in data_cats:
        risks.append({"risk": "个人数据泄露", "level": "high"})
    if "special_category" in data_cats:
        risks.append({"risk": "敏感数据处理", "level": "high"})
    if "automated_decision" in purpose:
        risks.append({"risk": "自动化决策影响权益", "level": "medium"})

    levels = [r["level"] for r in risks]
    overall = "high" if "high" in levels else ("medium" if "medium" in levels else "low")

    safeguards = (
        ["加密存储", "访问控制", "审计日志", "数据最小化", "用户同意", "定期评估"]
        if overall == "high" else
        ["加密存储", "访问控制", "审计日志"]
    )

    return DPIAReport(
        project_name=project_name, data_categories=data_cats,
        purpose=purpose, risk_level=overall, risks=risks,
        safeguards=safeguards,
        conclusion="需实施所有保障措施后方可处理" if overall == "high" else "风险可控",
    )

class GDPRTestSuite:
    """GDPR合规测试套件"""
    def __init__(self, consent_mgr, dsr_engine):
        self.cm = consent_mgr
        self.dsre = dsr_engine
        self.results = []

    def test_consent_flow(self):
        """测试完整的同意流程"""
        uid = "test_user_001"
        # 1. 记录同意
        rec = self.cm.record_consent(uid, "model_training", ip="10.0.0.1")
        self.results.append(("记录同意", rec.is_valid()))
        # 2. 检查同意
        self.results.append(("有有效同意", self.cm.has_valid_consent(uid, "model_training")))
        # 3. 撤回同意
        self.cm.withdraw(rec.consent_id)
        self.results.append(("撤回后无效", not self.cm.has_valid_consent(uid, "model_training")))

    def test_dsr_flow(self):
        """测试数据主体权利流程"""
        uid = "test_user_002"
        self.dsre.user_data[uid] = {"name": "测试", "email": "test@x.com"}
        # 访问权
        r = self.dsre.handle_request(uid, DSR.ACCESS)
        self.results.append(("访问权", r["status"] == "completed" and bool(r.get("data"))))
        # 删除权
        self.dsre.handle_request(uid, DSR.ERASURE)
        self.results.append(("删除权", uid not in self.dsre.user_data))

    def run_all(self):
        self.test_consent_flow()
        self.test_dsr_flow()
        passed = sum(1 for _, p in self.results if p)
        return {"total": len(self.results), "passed": passed, "failed": len(self.results) - passed}

class GDPRComplianceEngine:
    """GDPR 合规引擎 — 同意、DSR、保留策略一体化"""

    RETENTION_POLICIES = {
        "user_account": {"duration_days": 365, "after_action": "anonymize"},
        "chat_history": {"duration_days": 180, "after_action": "delete"},
        "audit_log": {"duration_days": 730, "after_action": "archive"},
        "model_training_data": {"duration_days": 365, "after_action": "remove"},
    }

    def record_consent(self, user_id: str, purpose: str, ip_address: str = "") -> ConsentRecord:
        consent_id = hashlib.sha256(f"{user_id}:{purpose}:{time.time()}".encode()).hexdigest()[:16]
        record = ConsentRecord(consent_id=consent_id, user_id=user_id, consent_given=True,
                               timestamp=datetime.now().isoformat(), purpose=purpose,
                               ip_address=ip_address)
        self.consent_records[consent_id] = record
        return record

    def process_data_request(self, user_id: str, right: DataSubjectRight) -> DataSubjectRequest:
        """处理访问/导出/删除等数据主体请求"""
        # 删除权：物理删除 + 撤回所有同意
        ...

class GDPRTester:
    """GDPR 合规测试器 — 纳入 CI 的自动化套件"""

    def test_consent_management(self) -> Dict:
        consent = self.engine.record_consent("test_user_001", "model_training")
        self.engine.withdraw_consent(consent.consent_id)
        assert not self.engine.check_consent("test_user_001", "model_training")
        ...

    def run_all_tests(self) -> Dict:
        self.test_consent_management()
        self.test_data_subject_rights()
        self.test_data_retention()
        # 返回 total / passed / pass_rate
