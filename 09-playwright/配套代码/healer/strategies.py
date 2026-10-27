"""
修复策略工厂 — 策略模式
- ElementRepairStrategy: 元素定位修复
- AuthRefreshStrategy: Token刷新
- NetworkRetryStrategy: 网络重试
- AssertionAdjustStrategy: 断言调整
对应文章：第4篇-AI自愈系统
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime

class RepairStrategy(ABC):
    name: str = "base"
    @abstractmethod
    def match(self, diagnosis: Dict) -> bool: pass
    @abstractmethod
    def execute(self, error_message: str, context: Dict) -> Dict: pass

class ElementRepairStrategy(RepairStrategy):
    name = "element_locator_repair"
    def match(self, d): return d.get("error_type") == "element"
    def execute(self, msg, ctx):
        from locator.visual_repair import build_semantic
        sel = ctx.get("selector", "")
        alts = []
        # 只对纯 tag name（如 button/div）加 // 前缀生成 XPath
        # CSS 选择器（#id/.class/[attr]）不能直接加 //
        if sel and not sel.startswith(("//", "#", ".", "[", "xpath=", "text=", "role=")):
            alts.append(f"//{sel}")
        if sel.startswith("#"): alts += [f".{sel[1:]}", f"//*[@id='{sel[1:]}']"]
        if sel.startswith("."): alts += [f"//*[@class*='{sel[1:]}']"]
        raw = ctx.get("raw_step") or {}
        if isinstance(raw, dict): alts.extend(build_semantic(raw, str(sel), ctx.get("value")))
        seen = set()
        dedup = [s for s in alts if s and s not in seen and not seen.add(s)][:40]
        return {
            "action": "retry_with_alternatives",
            "original_selector": sel,
            "alternative_selectors": dedup,
            "success": len(dedup) > 0,
        }
class AuthRefreshStrategy(RepairStrategy):
    name = "auth_refresh"
    def match(self, d): return d.get("error_type") == "authentication"
    def execute(self, msg, ctx):
        return {"action": "refresh_token", "success": True, "new_token": f"mock_token_{datetime.now().strftime('%Y%m%d%H%M%S')}", "expires_in": 3600}

class NetworkRetryStrategy(RepairStrategy):
    name = "network_retry"
    def match(self, d): return d.get("error_type") == "network"
    def execute(self, msg, ctx):
        cur = int(ctx.get("current_retry", 0))
        mx = int(ctx.get("max_retries", 3))
        if cur >= mx: return {"action": "retry", "success": False, "reason": "已达最大重试次数"}
        return {"action": "retry", "success": True, "retry_count": cur + 1, "delay_seconds": 5 * (cur + 1)}

class AssertionAdjustStrategy(RepairStrategy):
    name = "assertion_adjust"
    def match(self, d): return d.get("error_type") == "assertion"
    def execute(self, msg, ctx):
        # 断言失败通常意味着业务逻辑变了，不自动修复
        return {
            "action": "adjust_assertion", "success": False,
            "auto_repairable": False,
            "reason": "断言失败通常意味着业务逻辑变更，需要人工确认",
            "suggestions": ["使用模糊匹配", "添加容差范围", "检查测试数据"],
        }

class StrategyFactory:
    def __init__(self):
        self.strategies: List[RepairStrategy] = [ElementRepairStrategy(), AuthRefreshStrategy(), NetworkRetryStrategy(), AssertionAdjustStrategy()]
    def select(self, d):
        for s in self.strategies:
            if s.match(d): return s
        return None
    def execute(self, d, ctx):
        if not d.get("auto_repairable"): return {"success": False, "reason": "不可自动修复"}
        s = self.select(d)
        if s: return {**s.execute(ctx.get("error_message",""), ctx), "strategy": s.name}
        return {"success": False, "reason": f"未知策略: {d.get('repair_strategy')}"}
