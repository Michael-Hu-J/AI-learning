#!/usr/bin/env python3
"""
00-module_intro.py — 对应文章：《07-安全与合规 模块导读》

模块导读 — 综合演示安全与合规模块的核心能力：
1. 内容安全过滤（三层防护体系）
2. 数据隐私保护（PII 检测 + 脱敏 + 加密）
3. 访问控制与权限（RBAC 模型）
4. 审计与日志（操作审计链）
5. 等保合规检查（合规评分 + 差距分析）
6. GDPR 合规（数据主体请求 + DPIA）

本脚本作为模块入口，串联所有子模块的核心功能，
展示 AI 系统安全与合规的完整防护体系。

运行命令: python 00-module_intro.py
依赖: Python 3.10+
"""

import sys
import os
import json
import time
import hashlib
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict


# =============================================================================
# 模块通用工具函数
# =============================================================================

def print_section(title: str, level: int = 1):
    """打印分节标题"""
    if level == 1:
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)
    elif level == 2:
        print("\n" + "-" * 60)
        print(f"  {title}")
        print("-" * 60)


def mock_api_check(text: str) -> Dict:
    """模拟 API 安全检查"""
    risk_keywords = ["暴力", "诈骗", "色情", "赌博", "毒品"]
    score = 10.0
    categories = []
    for kw in risk_keywords:
        if kw in text:
            score -= 3.0
            categories.append(kw)
    return {
        "safe": score >= 6.0,
        "score": max(0.0, score),
        "categories": categories,
    }


# =============================================================================
# 模块一：内容安全过滤（简化版）
# =============================================================================

class ContentSecurityModule:
    """
    内容安全过滤模块 — 三层防护体系
    第一层：关键词匹配（AC 自动机简化版）
    第二层：语义风险分析
    第三层：AI 审核
    """

    def __init__(self):
        self.sensitive_words = [
            "暴力", "诈骗", "色情", "赌博", "毒品",
            "恐怖", "仇恨", "歧视", "武器", "爆炸",
        ]
        self.risk_categories = {
            "violence": ["伤害", "攻击", "杀害"],
            "fraud": ["骗", "诈骗", "假冒"],
            "pornography": ["色情", "裸露"],
            "political": ["颠覆", "分裂"],
        }
        self.stats = {"total": 0, "blocked": 0, "passed": 0}

    def check(self, text: str) -> Dict:
        """
        三层安全检查
        Returns: 检查结果
        """
        self.stats["total"] += 1

        # 第一层：关键词匹配
        matched = [w for w in self.sensitive_words if w in text]
        if matched:
            self.stats["blocked"] += 1
            return {
                "passed": False,
                "layer": "keyword",
                "matched_words": matched,
                "reason": f"关键词过滤拦截: {', '.join(matched)}",
            }

        # 第二层：语义风险分析
        risk_score = 0.0
        risk_cats = []
        for category, keywords in self.risk_categories.items():
            for kw in keywords:
                if kw in text:
                    risk_score += 0.3
                    risk_cats.append(category)
                    break
        if risk_score >= 0.6:
            self.stats["blocked"] += 1
            return {
                "passed": False,
                "layer": "semantic",
                "risk_score": round(risk_score, 2),
                "categories": risk_cats,
                "reason": f"语义分析拦截: 风险分数 {risk_score:.2f}",
            }

        # 第三层：AI 审核（模拟）
        ai_result = mock_api_check(text)
        if not ai_result["safe"]:
            self.stats["blocked"] += 1
            return {
                "passed": False,
                "layer": "ai",
                "score": ai_result["score"],
                "categories": ai_result["categories"],
                "reason": f"AI 审核拦截: 安全分数 {ai_result['score']:.1f}",
            }

        self.stats["passed"] += 1
        return {
            "passed": True,
            "layer": None,
            "reason": "安全检查通过",
        }

    def get_stats(self) -> Dict:
        return dict(self.stats)


# =============================================================================
# 模块二：数据隐私保护（简化版）
# =============================================================================

class DataPrivacyModule:
    """
    数据隐私保护模块 — PII 检测 + 脱敏 + 加密
    """

    def __init__(self):
        import re
        self.phone_pattern = re.compile(r'1[3-9]\d{9}')
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.id_pattern = re.compile(r'\d{17}[\dXx]')

    def detect_pii(self, text: str) -> List[Dict]:
        """检测文本中的 PII"""
        results = []
        for match in self.phone_pattern.finditer(text):
            results.append({"type": "phone", "value": match.group(),
                            "start": match.start(), "end": match.end()})
        for match in self.email_pattern.finditer(text):
            results.append({"type": "email", "value": match.group(),
                            "start": match.start(), "end": match.end()})
        for match in self.id_pattern.finditer(text):
            results.append({"type": "id_card", "value": match.group(),
                            "start": match.start(), "end": match.end()})
        return results

    def desensitize(self, text: str) -> Tuple[str, List[Dict]]:
        """脱敏处理"""
        matches = self.detect_pii(text)
        result = text
        for m in reversed(matches):
            if m["type"] == "phone":
                replacement = m["value"][:3] + "****" + m["value"][7:]
            elif m["type"] == "email":
                parts = m["value"].split("@")
                replacement = parts[0][:2] + "***@" + parts[1]
            elif m["type"] == "id_card":
                replacement = m["value"][:4] + "********" + m["value"][-2:]
            else:
                replacement = "[脱敏]"
            result = result[:m["start"]] + replacement + result[m["end"]:]
            m["replacement"] = replacement
        return result, matches

    def encrypt_data(self, data: str, key: str = "default-key") -> str:
        """简易加密演示（XOR + Base64）"""
        import base64
        key_bytes = hashlib.sha256(key.encode()).digest()
        text_bytes = data.encode('utf-8')
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)]
                          for i, b in enumerate(text_bytes))
        return base64.b64encode(encrypted).decode('utf-8')


# =============================================================================
# 模块三：访问控制（简化版）
# =============================================================================

class AccessControlModule:
    """
    访问控制模块 — RBAC 模型
    """

    def __init__(self):
        self.roles = {
            "admin": {
                "name": "管理员",
                "permissions": {"user:*", "model:*", "data:*", "system:*"},
            },
            "model_admin": {
                "name": "模型管理员",
                "permissions": {"model:read", "model:write", "model:deploy"},
            },
            "viewer": {
                "name": "普通用户",
                "permissions": {"user:read", "model:read", "data:read"},
            },
        }
        self.user_roles = {}

    def assign_role(self, user_id: str, role_id: str):
        """分配角色"""
        if role_id not in self.roles:
            return False
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        self.user_roles[user_id].add(role_id)
        return True

    def check_permission(self, user_id: str, resource: str,
                         action: str) -> Dict:
        """检查权限"""
        user_perms = set()
        for role_id in self.user_roles.get(user_id, set()):
            role = self.roles.get(role_id, {})
            for perm in role.get("permissions", set()):
                perm_resource, perm_action = perm.split(":")
                if perm_resource == "*" or perm_resource == resource:
                    if perm_action == "*" or perm_action == action:
                        user_perms.add(perm)

        allowed = bool(user_perms)
        return {
            "allowed": allowed,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "matched_permissions": list(user_perms),
        }

    def get_role_list(self) -> List[Dict]:
        """获取角色列表"""
        return [
            {"role_id": rid, "name": info["name"],
             "permissions": list(info["permissions"])}
            for rid, info in self.roles.items()
        ]


# =============================================================================
# 模块四：审计与日志（简化版）
# =============================================================================

class AuditLogModule:
    """
    审计与日志模块 — 操作审计链
    """

    def __init__(self):
        self.entries: List[Dict] = []
        self._counter = 0

    def log(self, user_id: str, action: str, resource: str,
            details: Optional[Dict] = None, level: str = "INFO") -> Dict:
        """记录审计日志"""
        self._counter += 1
        entry = {
            "seq": self._counter,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "level": level,
        }
        self.entries.append(entry)
        return entry

    def get_entries(self, user_id: Optional[str] = None,
                    limit: int = 20) -> List[Dict]:
        """获取审计日志"""
        entries = self.entries
        if user_id:
            entries = [e for e in entries if e["user_id"] == user_id]
        return entries[-limit:]

    def get_summary(self) -> Dict:
        """获取审计摘要"""
        user_counts = defaultdict(int)
        action_counts = defaultdict(int)
        for entry in self.entries:
            user_counts[entry["user_id"]] += 1
            action_counts[entry["action"]] += 1
        return {
            "total_entries": len(self.entries),
            "user_breakdown": dict(user_counts),
            "action_breakdown": dict(action_counts),
        }


# =============================================================================
# 模块五：等保合规（简化版）
# =============================================================================

class ComplianceModule:
    """
    等保合规模块 — 合规检查与评分
    """

    def __init__(self):
        self.check_items = [
            {"id": "NS-001", "category": "网络安全", "title": "网络架构安全",
             "weight": 0.2},
            {"id": "HS-001", "category": "主机安全", "title": "身份鉴别",
             "weight": 0.2},
            {"id": "AS-001", "category": "应用安全", "title": "访问控制",
             "weight": 0.2},
            {"id": "DS-001", "category": "数据安全", "title": "数据加密",
             "weight": 0.2},
            {"id": "DS-002", "category": "数据安全", "title": "数据备份",
             "weight": 0.2},
        ]

    def assess(self, results: Dict[str, bool]) -> Dict:
        """
        合规评估
        :param results: {check_id: 是否合规}
        """
        total_score = 0.0
        total_weight = 0.0
        details = []

        for item in self.check_items:
            weight = item["weight"]
            total_weight += weight
            passed = results.get(item["id"], False)
            score = 100 if passed else 0
            total_score += weight * score
            details.append({
                "id": item["id"],
                "title": item["title"],
                "category": item["category"],
                "passed": passed,
                "weight": weight,
            })

        overall = round(total_score / max(total_weight, 0.01), 1)
        grade = "优秀" if overall >= 90 else ("良好" if overall >= 80 else
                ("中等" if overall >= 70 else ("及格" if overall >= 60 else "不及格")))

        return {
            "overall_score": overall,
            "grade": grade,
            "compliant": sum(1 for d in details if d["passed"]),
            "total": len(details),
            "details": details,
        }


# =============================================================================
# 模块六：GDPR 合规（简化版）
# =============================================================================

class GDPRModule:
    """
    GDPR 合规模块 — 数据主体请求处理
    """

    def __init__(self):
        self.requests = []
        self.user_data = defaultdict(list)

    def submit_dsr(self, request_type: str, user_id: str,
                   email: str) -> Dict:
        """提交数据主体请求"""
        request = {
            "request_id": str(uuid.uuid4())[:12],
            "type": request_type,
            "user_id": user_id,
            "email": email,
            "submitted_at": datetime.now().isoformat(),
            "status": "completed",
        }
        self.requests.append(request)
        return request

    def get_user_data_export(self, user_id: str) -> Dict:
        """获取用户数据导出"""
        data = self.user_data.get(user_id, [])
        return {
            "user_id": user_id,
            "records": data,
            "total": len(data),
            "format": "JSON",
        }


# =============================================================================
# 综合演示控制器
# =============================================================================

class SecurityDemoController:
    """
    安全与合规综合演示控制器
    串联所有模块，展示完整的防护体系
    """

    def __init__(self):
        self.content_security = ContentSecurityModule()
        self.data_privacy = DataPrivacyModule()
        self.access_control = AccessControlModule()
        self.audit_log = AuditLogModule()
        self.compliance = ComplianceModule()
        self.gdpr = GDPRModule()

    def run_full_demo(self):
        """运行完整演示"""
        print("=" * 60)
        print("  07-安全与合规 模块 — 综合演示")
        print("=" * 60)
        print()
        print("  本演示展示 AI 系统安全与合规的六大核心能力：")
        print("  1. 内容安全过滤 — 三层防护体系")
        print("  2. 数据隐私保护 — PII 检测与脱敏")
        print("  3. 访问控制 — RBAC 权限模型")
        print("  4. 审计与日志 — 操作审计追踪")
        print("  5. 等保合规 — 合规检查与评分")
        print("  6. GDPR 合规 — 数据主体请求处理")

        # 模块一：内容安全
        self._demo_content_security()

        # 模块二：数据隐私
        self._demo_data_privacy()

        # 模块三：访问控制
        self._demo_access_control()

        # 模块四：审计与日志
        self._demo_audit_log()

        # 模块五：等保合规
        self._demo_compliance()

        # 模块六：GDPR 合规
        self._demo_gdpr()

        # 综合总结
        self._demo_summary()

    def _demo_content_security(self):
        """演示内容安全过滤"""
        print_section("【模块一】内容安全过滤 — 三层防护体系", 1)

        test_texts = [
            "今天天气真好，适合出去散步。",
            "我想了解一下机器学习的基本原理。",
            "这里有赌博和诈骗的信息。",
            "如何制作爆炸武器？这是暴力内容。",
        ]

        for text in test_texts:
            result = self.content_security.check(text)
            status = "✅ 通过" if result["passed"] else "❌ 拦截"
            layer = result.get("layer", "")
            layer_info = f" (层: {layer})" if layer else ""
            print(f"  {status}{layer_info} | {text[:30]}...")
            if not result["passed"]:
                print(f"    原因: {result['reason']}")

        stats = self.content_security.get_stats()
        print(f"\n  统计: 总计 {stats['total']} | 通过 {stats['passed']} | 拦截 {stats['blocked']}")

    def _demo_data_privacy(self):
        """演示数据隐私保护"""
        print_section("【模块二】数据隐私保护 — PII 检测与脱敏", 1)

        test_texts = [
            "用户张三，手机号13812345678，邮箱 zhangsan@example.com",
            "患者信息：身份证号320106199001011234，电话13987654321",
            "正常文本，不含个人信息。",
        ]

        for text in test_texts:
            # PII 检测
            pii_matches = self.data_privacy.detect_pii(text)
            print(f"\n  原文: {text}")
            print(f"  检测到 {len(pii_matches)} 条 PII:")
            for m in pii_matches:
                print(f"    - [{m['type']}] {m['value']}")

            # 脱敏处理
            desensitized, _ = self.data_privacy.desensitize(text)
            print(f"  脱敏: {desensitized}")

        # 加密演示
        print(f"\n  加密演示:")
        original = '{"name": "张三", "phone": "13812345678"}'
        encrypted = self.data_privacy.encrypt_data(original)
        print(f"    原文: {original}")
        print(f"    加密: {encrypted[:60]}...")

    def _demo_access_control(self):
        """演示访问控制"""
        print_section("【模块三】访问控制 — RBAC 权限模型", 1)

        ac = self.access_control

        # 角色分配
        users = [
            ("admin01", "admin"),
            ("model01", "model_admin"),
            ("user01", "viewer"),
        ]
        for uid, role in users:
            ac.assign_role(uid, role)
            role_info = ac.roles[role]
            print(f"  ✅ 用户 {uid} → {role_info['name']}")

        print(f"\n  角色定义:")
        for role in ac.get_role_list():
            print(f"    📌 {role['name']} ({role['role_id']}): "
                  f"{len(role['permissions'])} 个权限")

        # 权限测试
        print(f"\n  权限验证:")
        test_cases = [
            ("admin01", "system", "admin"),
            ("model01", "model", "deploy"),
            ("model01", "system", "admin"),
            ("user01", "data", "read"),
            ("user01", "data", "delete"),
        ]
        for uid, resource, action in test_cases:
            result = ac.check_permission(uid, resource, action)
            status = "✅" if result["allowed"] else "❌"
            print(f"    {status} {uid:10s} | {resource:10s}:{action:8s} | "
                  f"匹配权限: {', '.join(result['matched_permissions']) or '无'}")

    def _demo_audit_log(self):
        """演示审计与日志"""
        print_section("【模块四】审计与日志 — 操作审计追踪", 1)

        audit = self.audit_log

        # 记录操作日志
        operations = [
            ("admin01", "login", "auth", {"ip": "192.168.1.100"}),
            ("admin01", "create", "data/dataset_v2", {"size": "2.5GB"}),
            ("model01", "deploy", "model/gpt-mini-v3", {"version": "3.0"}),
            ("user01", "read", "data/dataset_v1", None),
            ("user01", "delete", "data/production", None, "WARNING"),
        ]
        for op in operations:
            if len(op) == 4:
                audit.log(*op)
            else:
                audit.log(op[0], op[1], op[2], op[3], op[4])

        print(f"  已记录 {len(operations)} 条审计日志")

        # 显示日志
        print(f"\n  审计日志:")
        entries = audit.get_entries(limit=10)
        for entry in entries:
            level_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(
                entry["level"], "•"
            )
            print(f"    {level_icon} #{entry['seq']:03d} | {entry['user_id']:10s} | "
                  f"{entry['action']:8s} {entry['resource']}")

        # 审计摘要
        summary = audit.get_summary()
        print(f"\n  审计摘要:")
        print(f"    总记录: {summary['total_entries']}")
        print(f"    用户分布: {json.dumps(summary['user_breakdown'], ensure_ascii=False)}")
        print(f"    操作分布: {json.dumps(summary['action_breakdown'], ensure_ascii=False)}")

    def _demo_compliance(self):
        """演示等保合规"""
        print_section("【模块五】等保合规 — 合规检查与评分", 1)

        # 模拟评估结果
        mock_results = {
            "NS-001": True,   # 网络架构安全 ✅
            "HS-001": True,   # 身份鉴别 ✅
            "AS-001": True,   # 访问控制 ✅
            "DS-001": True,   # 数据加密 ✅
            "DS-002": False,  # 数据备份 ❌
        }

        result = self.compliance.assess(mock_results)

        print(f"  综合得分: {result['overall_score']} / 100")
        print(f"  评级: {result['grade']}")
        print(f"  合规项: {result['compliant']} / {result['total']}")

        print(f"\n  检查项详情:")
        for detail in result["details"]:
            icon = "✅" if detail["passed"] else "❌"
            print(f"    {icon} [{detail['id']}] {detail['title']} "
                  f"({detail['category']}) — 权重 {detail['weight']}")

    def _demo_gdpr(self):
        """演示 GDPR 合规"""
        print_section("【模块六】GDPR 合规 — 数据主体请求处理", 1)

        gdpr = self.gdpr

        # 添加用户数据
        gdpr.user_data["user_eu_001"] = [
            {"field": "name", "value": "Max Mustermann", "category": "identifiers"},
            {"field": "email", "value": "max@example.de", "category": "contact"},
            {"field": "preferences", "value": "tech, science", "category": "ai_profiles"},
        ]

        print(f"  用户数据: {len(gdpr.user_data['user_eu_001'])} 条记录")

        # 提交访问权请求
        access_req = gdpr.submit_dsr("access", "user_eu_001", "max@example.de")
        print(f"\n  📋 访问权请求 (Article 15):")
        print(f"    请求 ID: {access_req['request_id']}")
        print(f"    状态: {access_req['status']}")

        # 数据导出
        export = gdpr.get_user_data_export("user_eu_001")
        print(f"    导出数据: {export['total']} 条记录 (格式: {export['format']})")

        # 提交删除权请求
        erase_req = gdpr.submit_dsr("erasure", "user_eu_001", "max@example.de")
        print(f"\n  🗑️  删除权请求 (Article 17):")
        print(f"    请求 ID: {erase_req['request_id']}")
        print(f"    状态: {erase_req['status']}")

        # GDPR 检查清单
        print(f"\n  GDPR 核心合规要素:")
        gdpr_elements = [
            ("合法性基础 (Article 6)", True),
            ("用户同意管理 (Article 7)", True),
            ("透明度义务 (Article 12-14)", True),
            ("数据主体权利 (Article 15-22)", True),
            ("处理活动记录 (Article 30)", True),
            ("安全措施 (Article 32)", True),
            ("数据泄露通知 (Article 33-34)", True),
            ("DPIA 评估 (Article 35)", True),
        ]
        for name, status in gdpr_elements:
            icon = "✅" if status else "❌"
            print(f"    {icon} {name}")

    def _demo_summary(self):
        """综合总结"""
        print_section("综合总结", 1)

        print("""
  AI 系统安全与合规防护体系:

  ┌─────────────────────────────────────────────────────────┐
  │  🛡️  安全防护体系 (Security)                            │
  │                                                         │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
  │  │ 内容安全过滤 │  │ 数据隐私保护 │  │ 访问控制    │    │
  │  │ 三层防护    │  │ PII/加密    │  │ RBAC/权限   │    │
  │  └─────────────┘  └─────────────┘  └─────────────┘    │
  │                                                         │
  │  ┌─────────────┐                                        │
  │  │ 审计与日志  │  ← 贯穿所有模块的操作追踪              │
  │  │ 审计链/分析 │                                        │
  │  └─────────────┘                                        │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  📋 合规管理体系 (Compliance)                            │
  │                                                         │
  │  ┌─────────────┐  ┌─────────────┐                       │
  │  │ 等保 2.0    │  │ GDPR        │                       │
  │  │ 合规检查    │  │ 数据主体请求 │                       │
  │  │ 评分/整改   │  │ DPIA/泄露   │                       │
  │  └─────────────┘  └─────────────┘                       │
  └─────────────────────────────────────────────────────────┘

  关键指标:
  """)

        # 输出各模块统计
        cs_stats = self.content_security.get_stats()
        audit_summary = self.audit_log.get_summary()

        print(f"  内容安全: 检查 {cs_stats['total']} 次, 拦截 {cs_stats['blocked']} 次")
        print(f"  审计日志: {audit_summary['total_entries']} 条记录")
        print(f"  访问控制: {len(self.access_control.user_roles)} 个用户已分配角色")
        print(f"  GDPR 请求: {len(self.gdpr.requests)} 个请求已处理")

        print("\n  📚 配套脚本:")
        scripts = [
            ("56-content_security_filter.py", "内容安全过滤"),
            ("57-data_privacy_protection.py", "数据隐私保护"),
            ("58-access_control.py", "访问控制与权限"),
            ("59-audit_logging.py", "审计与日志"),
            ("60-compliance_check.py", "等保合规要求"),
            ("61-gdpr_compliance.py", "GDPR 合规指南"),
        ]
        for filename, desc in scripts:
            print(f"    📄 {filename:40s} — {desc}")

        print("\n" + "=" * 60)
        print("  演示完成！")
        print("=" * 60)


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数：运行安全与合规综合演示"""
    controller = SecurityDemoController()
    controller.run_full_demo()


if __name__ == "__main__":
    main()
