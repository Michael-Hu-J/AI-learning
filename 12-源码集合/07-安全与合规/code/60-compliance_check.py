class EqualProtectionTester:
    """等保合规测试器 — 加载检查项模板并生成报告"""

    CHECK_TEMPLATES = {
        "IDENT-002": {
            "category": CheckCategory.COMPUTE, "level": 3,
            "description": "身份鉴别 - 口令复杂度",
            "check_method": "检查口令复杂度策略（长度、字符类型、更换周期）",
            "expected_result": "长度≥8位，包含大小写字母、数字、特殊字符，90天更换",
            "weight": 3,
        },
        "IDENT-003": {
            "category": CheckCategory.COMPUTE, "level": 3,
            "description": "身份鉴别 - 双因素认证",
            "expected_result": "支持双因素认证", "weight": 3,
        },
        "AUDIT-003": {
            "category": CheckCategory.COMPUTE, "level": 3,
            "description": "安全审计 - 日志保留期",
            "expected_result": "日志保留期 ≥ 6 个月", "weight": 2,
        },
        "DATA-002": {
            "category": CheckCategory.COMPUTE, "level": 3,
            "description": "数据保密性 - 敏感数据加密存储",
            "expected_result": "敏感数据加密存储", "weight": 3,
        },
        "BOUND-002": {
            "category": CheckCategory.BOUNDARY, "level": 3,
            "description": "入侵防范 - 入侵检测",
            "expected_result": "部署 IDS/IPS", "weight": 3,
        },
        # 完整模板见 CHECK_TEMPLATES 定义（IDENT/ACCESS/AUDIT/DATA/COMM/BOUND 共 15 项）
    }

    def load_checks(self):
        """加载适用于当前等保等级的检查项"""
        for check_id, tpl in self.CHECK_TEMPLATES.items():
            if tpl["level"] <= self.target_level.value:
                self.report.checks.append(ComplianceCheck(check_id=check_id, **tpl))
                self.report.max_score += tpl["weight"]

    def generate_report(self) -> Dict:
        gaps = [c.description for c in self.report.checks if c.passed is False]
        return {
            "target_level": f"等保{self.target_level.value}级",
            "score": f"{self.report.score_percentage:.1f}%",
            "is_compliant": self.report.is_compliant,
            "gaps": gaps,
        }

import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime

class ComplianceLevel(Enum):
    """等保等级"""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4

class CheckCategory(Enum):
    """检查类别"""
    PHYSICAL = "安全物理环境"
    NETWORK = "安全通信网络"
    BOUNDARY = "安全区域边界"
    COMPUTE = "安全计算环境"
    MANAGEMENT = "安全管理中心"

@dataclass
class ComplianceCheck:
    """合规检查项"""
    check_id: str
    category: CheckCategory
    level: int
    description: str
    check_method: str
    expected_result: str
    weight: int = 1
    passed: Optional[bool] = None
    evidence: str = ""
    comment: str = ""

@dataclass
class ComplianceReport:
    """合规报告"""
    system_name: str
    compliance_level: ComplianceLevel
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    not_applicable: int = 0
    total_score: float = 0.0
    max_score: float = 0.0
    checks: List[ComplianceCheck] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)

    @property
    def score_percentage(self) -> float:
        if self.max_score == 0:
            return 0.0
        return (self.total_score / self.max_score) * 100

    @property
    def is_compliant(self) -> bool:
        """是否合规（80 分以上且无关键项不合格）"""
        return self.score_percentage >= 80 and self.failed_checks == 0

import re
import subprocess

def check_password_policy(config: Dict) -> Tuple[bool, str]:
    """
    检查密码策略是否符合等保要求
    等保三级要求：
    - 最小长度 ≥ 8
    - 包含大小写字母、数字、特殊字符
    - 更换周期 ≤ 90 天
    - 禁止弱密码
    """
    issues = []
    
    min_length = config.get("min_length", 0)
    if min_length < 8:
        issues.append(f"密码最小长度 {min_length} < 8")
    
    if not config.get("require_upper", False):
        issues.append("未要求大写字母")
    if not config.get("require_lower", False):
        issues.append("未要求小写字母")
    if not config.get("require_digit", False):
        issues.append("未要求数字")
    if not config.get("require_special", False):
        issues.append("未要求特殊字符")
    
    max_age = config.get("max_age_days", 999)
    if max_age > 90:
        issues.append(f"密码更换周期 {max_age} 天 > 90 天")
    
    # 检查弱密码字典
    weak_passwords = config.get("weak_passwords", [])
    common_weak = ["123456", "password", "admin123", "qwerty", "111111"]
    for wp in common_weak:
        if wp not in weak_passwords:
            issues.append(f"弱密码字典未包含 '{wp}'")
            break  # 有一个没包含就说明字典不完整
    
    if issues:
        return False, "; ".join(issues)
    return True, "密码策略符合要求"

def check_password_hash(password: str) -> Tuple[bool, str]:
    """检查密码哈希算法是否符合要求"""
    # 检查是否使用了安全的哈希算法
    if password.startswith("$2b$") or password.startswith("$2a$"):
        return True, "使用bcrypt哈希算法，符合要求"
    elif password.startswith("$pbkdf2$"):
        return True, "使用PBKDF2哈希算法，符合要求"
    elif re.match(r'^[a-f0-9]{32}$', password):
        return False, "疑似MD5哈希，不符合安全要求"
    elif re.match(r'^[a-f0-9]{64}$', password):
        return False, "疑似SHA-256哈希（无salt），不符合安全要求"
    else:
        return False, "无法识别的哈希算法"

import os
from datetime import datetime, timedelta

def check_log_retention(log_dir: str) -> Tuple[bool, str]:
    """
    检查日志保留期是否不少于6个月（180天）
    """
    if not os.path.exists(log_dir):
        return False, f"日志目录 {log_dir} 不存在"
    
    # 获取日志目录中最早的文件
    files = []
    for root, dirs, filenames in os.walk(log_dir):
        for f in filenames:
            filepath = os.path.join(root, f)
            mtime = os.path.getmtime(filepath)
            files.append((filepath, mtime))
    
    if not files:
        return False, "日志目录为空，没有日志文件"
    
    earliest = min(files, key=lambda x: x[1])
    earliest_date = datetime.fromtimestamp(earliest[1])
    days_retained = (datetime.now() - earliest_date).days
    
    if days_retained < 180:
        return False, f"日志保留期 {days_retained} 天 < 180 天（6个月）"
    
    return True, f"日志保留期 {days_retained} 天，符合要求"

def check_log_integrity(log_file: str, expected_hash: str) -> Tuple[bool, str]:
    """
    检查日志文件完整性
    """
    if not os.path.exists(log_file):
        return False, f"日志文件 {log_file} 不存在"
    
    # 计算文件的SHA-256
    sha256 = hashlib.sha256()
    with open(log_file, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    actual_hash = sha256.hexdigest()
    
    if actual_hash != expected_hash:
        return False, f"日志文件完整性校验失败，文件可能被篡改"
    
    return True, "日志文件完整性校验通过"

def check_log_content(log_file: str) -> Tuple[bool, str]:
    """
    检查日志内容是否包含等保要求的信息
    等保要求审计记录包含：事件日期、时间、发起者、事件类型、结果
    """
    required_fields = ["日期", "时间", "用户", "事件类型", "结果"]
    missing_fields = []
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            first_lines = [f.readline() for _ in range(10)]
            
        content = " ".join(first_lines)
        for field in required_fields:
            if field not in content:
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"日志缺少以下字段: {', '.join(missing_fields)}"
        
        return True, "日志内容包含所有必要字段"
    except Exception as e:
        return False, f"读取日志文件失败: {str(e)}"

import ssl
import socket

def check_tls_version(host: str, port: int = 443) -> Tuple[bool, str]:
    """
    检查TLS版本是否符合要求（≥1.2）
    """
    issues = []
    
    # 检查是否支持不安全的TLS版本
    insecure_versions = ["SSLv3", "TLSv1", "TLSv1.1"]
    
    for version in insecure_versions:
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if version == "SSLv3":
                ctx.minimum_version = ssl.TLSVersion.TLSv1
                ctx.maximum_version = ssl.TLSVersion.TLSv1
            elif version == "TLSv1":
                ctx.minimum_version = ssl.TLSVersion.TLSv1
                ctx.maximum_version = ssl.TLSVersion.TLSv1
            elif version == "TLSv1.1":
                ctx.minimum_version = ssl.TLSVersion.TLSv1_1
                ctx.maximum_version = ssl.TLSVersion.TLSv1_1
            
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    actual_version = ssock.version()
                    issues.append(f"服务器支持不安全的 {version}（实际协商: {actual_version}）")
        except (ssl.SSLError, socket.error):
            pass  # 不支持该版本，是好事
    
    # 检查是否支持TLS 1.2+
    try:
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                version = ssock.version()
    except (ssl.SSLError, socket.error) as e:
        issues.append(f"不支持TLS 1.2+: {str(e)}")
    
    if issues:
        return False, "; ".join(issues)
    return True, "TLS版本符合要求（≥1.2）"

def check_database_encryption(db_config: Dict) -> Tuple[bool, str]:
    """
    检查数据库加密配置
    """
    issues = []
    
    # 检查透明数据加密（TDE）
    if not db_config.get("tde_enabled", False):
        issues.append("未启用透明数据加密（TDE）")
    
    # 检查连接加密
    if not db_config.get("ssl_mode", "").upper() in ["REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"]:
        issues.append("数据库连接未强制加密")
    
    # 检查字段级加密
    sensitive_fields = db_config.get("sensitive_fields", [])
    encrypted_fields = db_config.get("encrypted_fields", [])
    for field in sensitive_fields:
        if field not in encrypted_fields:
            issues.append(f"敏感字段 '{field}' 未加密")
    
    if issues:
        return False, "; ".join(issues)
    return True, "数据库加密配置符合要求"

def check_rbac_implementation(users: List[Dict], roles: List[Dict]) -> Tuple[bool, str]:
    """
    检查RBAC实现是否符合等保要求
    """
    issues = []
    
    # 检查是否有角色定义
    if not roles:
        issues.append("未定义任何角色")
    
    # 检查是否有用户未分配角色
    unassigned = [u["username"] for u in users if not u.get("roles")]
    if unassigned:
        issues.append(f"以下用户未分配角色: {', '.join(unassigned[:5])}")
    
    # 检查是否有用户拥有多个角色（可能违反最小权限）
    multi_role = [u["username"] for u in users if len(u.get("roles", [])) > 3]
    if multi_role:
        issues.append(f"以下用户拥有过多角色（>3）: {', '.join(multi_role[:5])}")
    
    # 检查是否有管理员账户过多
    admin_users = [u["username"] for u in users if "admin" in u.get("roles", [])]
    if len(admin_users) > 3:
        issues.append(f"管理员账户过多（{len(admin_users)}个），违反最小权限原则")
    
    # 检查是否有默认账户
    default_accounts = ["admin", "root", "test", "guest"]
    for account in default_accounts:
        if any(u["username"] == account for u in users):
            issues.append(f"存在默认账户 '{account}'")
    
    if issues:
        return False, "; ".join(issues)
    return True, "RBAC实现符合要求"

def check_sensitive_operation_approval(operations: List[Dict]) -> Tuple[bool, str]:
    """
    检查敏感操作是否需要审批
    """
    sensitive_ops = ["delete", "export", "config_change", "user_create", "role_assign"]
    missing_approval = []
    
    for op in operations:
        op_name = op.get("operation", "")
        requires_approval = op.get("requires_approval", False)
        if op_name in sensitive_ops and not requires_approval:
            missing_approval.append(op_name)
    
    if missing_approval:
        return False, f"以下敏感操作未配置审批: {', '.join(missing_approval)}"
    return True, "敏感操作审批配置符合要求"

def run_full_compliance_check(system_name: str, target_level: int = 3) -> Dict:
    """
    运行完整的等保合规检查
    """
    results = {
        "system_name": system_name,
        "target_level": f"等保{target_level}级",
        "check_time": datetime.now().isoformat(),
        "categories": {}
    }
    
    # 1. 密码策略检查
    password_config = load_password_config()  # 从配置文件中加载
    passed, msg = check_password_policy(password_config)
    results["categories"]["password_policy"] = {"passed": passed, "message": msg}
    
    # 2. 日志保留期检查
    passed, msg = check_log_retention("/var/log/app")
    results["categories"]["log_retention"] = {"passed": passed, "message": msg}
    
    # 3. TLS版本检查
    passed, msg = check_tls_version("api.example.com")
    results["categories"]["tls_version"] = {"passed": passed, "message": msg}
    
    # 4. 数据库加密检查
    db_config = load_db_config()
    passed, msg = check_database_encryption(db_config)
    results["categories"]["db_encryption"] = {"passed": passed, "message": msg}
    
    # 5. RBAC检查
    users = load_users()
    roles = load_roles()
    passed, msg = check_rbac_implementation(users, roles)
    results["categories"]["rbac"] = {"passed": passed, "message": msg}
    
    # 统计结果
    total = len(results["categories"])
    passed_count = sum(1 for v in results["categories"].values() if v["passed"])
    results["summary"] = {
        "total_checks": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": f"{passed_count/total*100:.1f}%"
    }
    
    return results

if __name__ == "__main__":
    result = run_full_compliance_check("AI平台")
    print(json.dumps(result, indent=2, ensure_ascii=False))
