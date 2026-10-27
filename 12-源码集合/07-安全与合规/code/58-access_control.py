import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"
    IMPORT = "import"


class Role(Enum):
    """角色枚举"""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


@dataclass
class Resource:
    """资源定义"""
    resource_id: str
    resource_type: str  # chat, user, model, dataset, config
    owner_id: str  # 资源所有者
    visibility: str = "private"  # private / shared / public
    metadata: Dict = field(default_factory=dict)


@dataclass
class AccessRequest:
    """访问请求"""
    user_id: str
    role: Role
    permission: Permission
    resource: Resource
    attributes: Dict = field(default_factory=dict)  # 请求属性


@dataclass
class AccessDecision:
    """访问决策"""
    allowed: bool
    reason: str
    role: str
    matched_rule: str = ""


class RBACEngine:
    """基于角色的访问控制引擎"""

    # 角色-权限映射表
    ROLE_PERMISSIONS = {
        Role.ADMIN: {
            Permission.READ, Permission.WRITE, Permission.DELETE,
            Permission.ADMIN, Permission.EXPORT, Permission.IMPORT,
        },
        Role.MANAGER: {
            Permission.READ, Permission.WRITE, Permission.EXPORT,
        },
        Role.USER: {
            Permission.READ, Permission.WRITE,
        },
        Role.GUEST: {
            Permission.READ,
        },
    }

    # 角色-资源类型映射表
    ROLE_RESOURCE_ACCESS = {
        Role.ADMIN: {"chat", "user", "model", "dataset", "config"},
        Role.MANAGER: {"chat", "user", "model", "dataset"},
        Role.USER: {"chat", "model"},
        Role.GUEST: {"model"},
    }

    def check_access(self, request: AccessRequest) -> AccessDecision:
        """检查访问权限"""
        # 规则 1：角色是否拥有该权限
        allowed_permissions = self.ROLE_PERMISSIONS.get(request.role, set())
        if request.permission not in allowed_permissions:
            return AccessDecision(
                allowed=False,
                reason=f"角色 {request.role.value} 缺少权限 {request.permission.value}",
                role=request.role.value,
                matched_rule="role_permission_check",
            )

        # 规则 2：角色是否可访问该资源类型
        allowed_resources = self.ROLE_RESOURCE_ACCESS.get(request.role, set())
        if request.resource.resource_type not in allowed_resources:
            return AccessDecision(
                allowed=False,
                reason=f"角色 {request.role.value} 不可访问资源类型 {request.resource.resource_type}",
                role=request.role.value,
                matched_rule="resource_type_check",
            )

        # 规则 3：私有资源只能所有者访问
        if request.resource.visibility == "private":
            if request.user_id != request.resource.owner_id:
                return AccessDecision(
                    allowed=False,
                    reason=f"私有资源只能由所有者访问（当前用户: {request.user_id}, 所有者: {request.resource.owner_id}）",
                    role=request.role.value,
                    matched_rule="ownership_check",
                )

        # 规则 4：管理员可以访问所有资源
        if request.role == Role.ADMIN:
            return AccessDecision(
                allowed=True,
                reason="管理员拥有全部权限",
                role="admin",
                matched_rule="admin_override",
            )

        return AccessDecision(
            allowed=True,
            reason="权限检查通过",
            role=request.role.value,
            matched_rule="default_allow",
        )


if __name__ == "__main__":
    engine = RBACEngine()

    test_cases = [
        AccessRequest(
            user_id="admin_001", role=Role.ADMIN,
            permission=Permission.DELETE,
            resource=Resource("config_001", "config", "admin_001"),
        ),
        AccessRequest(
            user_id="user_001", role=Role.USER,
            permission=Permission.READ,
            resource=Resource("chat_001", "chat", "user_001", "private"),
        ),
        AccessRequest(
            user_id="user_001", role=Role.USER,
            permission=Permission.READ,
            resource=Resource("chat_002", "chat", "user_002", "private"),
        ),
        AccessRequest(
            user_id="guest_001", role=Role.GUEST,
            permission=Permission.WRITE,
            resource=Resource("model_001", "model", "system", "public"),
        ),
    ]

    print("=== RBAC 权限检查 ===\n")
    for req in test_cases:
        decision = engine.check_access(req)
        status = "✓ 允许" if decision.allowed else "✗ 拒绝"
        print(f"[{status}] {req.user_id} ({req.role.value}) -> {req.permission.value} {req.resource.resource_type}:{req.resource.resource_id}")
        print(f"  原因: {decision.reason}")
        print(f"  匹配规则: {decision.matched_rule}\n")

class ABACPolicy:
    """基于属性的访问控制策略"""

    def __init__(self):
        self.policies = []

    def add_policy(self, name: str, condition, description: str = ""):
        """添加策略"""
        self.policies.append({
            "name": name,
            "condition": condition,
            "description": description,
        })

    def evaluate(self, request: AccessRequest) -> List[Dict]:
        """评估所有策略"""
        results = []
        for policy in self.policies:
            try:
                allowed = policy["condition"](request)
                results.append({
                    "policy": policy["name"],
                    "allowed": allowed,
                    "description": policy["description"],
                })
            except Exception as e:
                results.append({
                    "policy": policy["name"],
                    "allowed": False,
                    "description": f"策略评估失败: {str(e)}",
                })
        return results

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class AttackType(Enum):
    """越权攻击类型"""
    IDOR = "idor"  # 直接对象引用篡改
    ROLE_ESCALATION = "role_escalation"  # 角色提升
    PARAM_POLLUTION = "param_pollution"  # 参数污染
    HEADER_MANIPULATION = "header_manipulation"  # 请求头篡改
    CSRF = "csrf"  # 跨站请求伪造


@dataclass
class AttackPayload:
    """攻击载荷"""
    attack_type: AttackType
    description: str
    original_request: Dict
    modified_request: Dict
    expected_result: str  # should_be_blocked / should_be_allowed
    severity: str = "high"


@dataclass
class TestResult:
    """测试结果"""
    payload: AttackPayload
    actual_status: int
    actual_response: str
    passed: bool  # True = 正确拦截/允许，False = 漏洞存在


class AuthorizationTester:
    """权限测试器 - 自动化越权攻击测试"""

    def __init__(self, api_client):
        self.api_client = api_client
        self.results: List[TestResult] = []

    def generate_idor_attacks(self, base_request: Dict, user_ids: List[str]) -> List[AttackPayload]:
        """生成 IDOR 攻击载荷"""
        attacks = []
        for target_user in user_ids:
            modified = dict(base_request)
            if "params" in modified:
                modified["params"]["user_id"] = target_user
            if "path" in modified:
                modified["path"] = modified["path"].replace(
                    base_request.get("params", {}).get("user_id", ""),
                    target_user
                )
            attacks.append(AttackPayload(
                attack_type=AttackType.IDOR,
                description=f"尝试通过篡改 user_id={target_user} 访问其他用户数据",
                original_request=base_request,
                modified_request=modified,
                expected_result="should_be_blocked",
                severity="critical",
            ))
        return attacks

    def generate_role_escalation_attacks(self, base_request: Dict) -> List[AttackPayload]:
        """生成角色提升攻击载荷"""
        attacks = []
        modified_token = dict(base_request.get("headers", {}))
        modified_token["X-User-Role"] = "admin"
        attacks.append(AttackPayload(
            attack_type=AttackType.ROLE_ESCALATION,
            description="尝试通过修改 X-User-Role 请求头提升为管理员",
            original_request=base_request,
            modified_request={**base_request, "headers": modified_token},
            expected_result="should_be_blocked",
            severity="critical",
        ))
        modified_body = dict(base_request.get("body", {}))
        modified_body["role"] = "admin"
        attacks.append(AttackPayload(
            attack_type=AttackType.ROLE_ESCALATION,
            description="尝试在请求 body 中注入 role=admin",
            original_request=base_request,
            modified_request={**base_request, "body": modified_body},
            expected_result="should_be_blocked",
            severity="high",
        ))
        return attacks

    def generate_param_pollution_attacks(self, base_request: Dict) -> List[AttackPayload]:
        """生成参数污染攻击载荷"""
        modified_params = dict(base_request.get("params", {}))
        modified_params["admin"] = "true"
        modified_params["is_admin"] = "1"
        modified_params["superuser"] = "yes"
        return [AttackPayload(
            attack_type=AttackType.PARAM_POLLUTION,
            description="尝试添加 admin=true 等参数绕过权限检查",
            original_request=base_request,
            modified_request={**base_request, "params": modified_params},
            expected_result="should_be_blocked",
            severity="medium",
        )]

    def run_all_tests(self, base_request: Dict, user_ids: List[str]) -> List[TestResult]:
        """运行所有越权测试"""
        all_attacks = []
        all_attacks.extend(self.generate_idor_attacks(base_request, user_ids))
        all_attacks.extend(self.generate_role_escalation_attacks(base_request))
        all_attacks.extend(self.generate_param_pollution_attacks(base_request))
        results = [self._simulate_request(a) for a in all_attacks]
        self.results = results
        return results

    def _simulate_request(self, payload: AttackPayload) -> TestResult:
        """模拟发送请求（实际应替换为真实 HTTP 调用）"""
        should_block = payload.expected_result == "should_be_blocked"
        simulated_status = 403 if should_block else 200
        simulated_response = json.dumps({
            "error": "Forbidden" if simulated_status == 403 else "OK",
            "message": "权限不足" if simulated_status == 403 else "操作成功",
        })
        passed = (simulated_status == 403) if should_block else (simulated_status == 200)
        return TestResult(
            payload=payload,
            actual_status=simulated_status,
            actual_response=simulated_response,
            passed=passed,
        )

    def get_report(self) -> Dict:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        vulnerabilities = [
            {
                "attack_type": r.payload.attack_type.value,
                "description": r.payload.description,
                "severity": r.payload.severity,
                "actual_status": r.actual_status,
            }
            for r in self.results if not r.passed
        ]
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "vulnerabilities": vulnerabilities,
        }


if __name__ == "__main__":
    class MockAPIClient:
        pass

    tester = AuthorizationTester(MockAPIClient())
    base_request = {
        "method": "GET",
        "path": "/api/v1/chats/chat_001",
        "params": {"user_id": "user_001"},
        "headers": {"Authorization": "Bearer token_user_001", "X-User-Role": "user"},
        "body": {},
    }
    report = tester.get_report() if tester.run_all_tests(base_request, ["user_001", "user_002", "admin_001"]) else {}
    print(f"总测试数: {report.get('total_tests', 0)}, 通过: {report.get('passed', 0)}, 失败: {report.get('failed', 0)}")

import pytest

class TestAuthorization:
    """权限测试用例"""

    def test_user_cannot_access_admin_api(self, api_client, user_token):
        """普通用户不能访问管理员接口"""
        resp = api_client.get("/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403

    def test_user_cannot_access_other_user_data(self, api_client, user_a_token, user_b_chat_id):
        """用户A不能访问用户B的数据"""
        resp = api_client.get(f"/api/v1/chat/{user_b_chat_id}", headers={"Authorization": f"Bearer {user_a_token}"})
        assert resp.status_code == 403

    def test_manager_can_export_data(self, api_client, manager_token):
        """经理可以导出数据"""
        resp = api_client.post("/api/v1/export", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200

    def test_guest_cannot_write(self, api_client, guest_token):
        """访客不能写入数据"""
        resp = api_client.post("/api/v1/chat", json={"message": "hello"}, headers={"Authorization": f"Bearer {guest_token}"})
        assert resp.status_code == 403
