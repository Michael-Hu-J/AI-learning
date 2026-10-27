"""
三层定位降级策略 — 让测试不再脆弱

L1 稳定选择器 → L2 DOM 推断 → L3 启发式候选
（原版依赖 DashScope LLM API，已改为纯规则启发式）

对应文章：第3篇-三层定位降级策略
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from collections import OrderedDict
import re

class UILocatorResolver:
    """Playwright 元素定位策略解析器。"""
    MAX_CACHE_SIZE = 500

    def __init__(self, enable_l3_ai: bool = False) -> None:
        self._enable_l3_ai = enable_l3_ai
        self._locator_cache: OrderedDict[str, str] = OrderedDict()

    def _resolve_cache(self, page_url: str, action: str, target: str) -> str:
        key = f"{page_url}:{action}:{target}"
        if key in self._locator_cache:
            self._locator_cache.move_to_end(key)
            return self._locator_cache[key]
        return ""

    def _set_cache(self, page_url: str, action: str, target: str, selector: str) -> None:
        key = f"{page_url}:{action}:{target}"
        if key in self._locator_cache:
            self._locator_cache.move_to_end(key)
        else:
            if len(self._locator_cache) >= self.MAX_CACHE_SIZE:
                self._locator_cache.popitem(last=False)
        self._locator_cache[key] = selector

    def resolve(self, page, step: Dict[str, Any]) -> Dict[str, Any]:
        target = str(step.get("target") or "").strip()
        value = str(step.get("value") or "").strip()
        hints = step.get("locator_hints") or {}
        action = str(step.get("action") or "").strip()
        page_url = str(getattr(page, "url", "") or "").strip()

        cached = self._resolve_cache(page_url, action, target)
        if cached:
            return {"found": True, "selector": cached, "level": "CACHE", "attempts": []}

        # L0 视觉语义
        if isinstance(hints, dict) and hints.get("prefer_visual_semantic"):
            from .visual_repair import build_semantic
            sem = build_semantic(step, target, value, latency_anomaly=True)
            selector0, attempts0 = self._first_working_selector(page, sem, "L0_SEM")
            if selector0:
                return {"found": True, "selector": selector0, "level": "L0_SEM", "attempts": attempts0}

        # L1 稳定选择器
        l1 = self._build_l1_candidates(target, value, hints)
        sel1, att1 = self._first_working_selector(page, l1, "L1")
        if sel1:
            self._set_cache(page_url, action, target, sel1)
            return {"found": True, "selector": sel1, "level": "L1", "attempts": att1}

        # L2 DOM 推断
        l2 = self._build_l2_candidates(target, value)
        sel2, att2 = self._first_working_selector(page, l2, "L2")
        att1.extend(att2)
        if sel2:
            self._set_cache(page_url, action, target, sel2)
            return {"found": True, "selector": sel2, "level": "L2", "attempts": att1}

        # L3 启发式
        l3 = self._build_l3_candidates(target, value, att1)
        sel3, att3 = self._first_working_selector(page, l3, "L3")
        att1.extend(att3)
        if sel3:
            self._set_cache(page_url, action, target, sel3)
            return {"found": True, "selector": sel3, "level": "L3", "attempts": att1}

        return {"found": False, "selector": "", "level": "NONE", "attempts": att1}

    def _build_l1_candidates(self, target, value, hints):
        candidates = []
        if target:
            candidates.append(target)
            if target.startswith("//"):
                candidates.append(f"xpath={target}")
        tid = str(hints.get("testid") or hints.get("data-testid") or "").strip()
        role = str(hints.get("role") or "").strip()
        label = str(hints.get("label") or "").strip()
        text = str(hints.get("text") or value or "").strip()
        if tid:
            candidates.extend([f"[data-testid='{tid}']", f"[data-test='{tid}']", f"[data-qa='{tid}']"])
        if role:
            candidates.append(f"role={role}[name='{text}']" if text else f"role={role}")
        if label:
            candidates.append(f"label={label}")
        if text:
            candidates.extend([f"text={text}", f"button:has-text('{text}')", f"a:has-text('{text}')"])
        return self._dedup(candidates)

    def _build_l2_candidates(self, target, value):
        candidates = []
        if target:
            token = re.sub(r"[^a-zA-Z0-9_-]", "", target.strip().lstrip("#.").split()[0])
            if token:
                candidates.extend([f"[id*='{token}']", f"[class*='{token}']", f"[name*='{token}']", f"[placeholder*='{token}']"])
                candidates.extend([f"//*[@id and contains(@id, '{token}')]", f"//*[@class and contains(@class, '{token}')]"])
        if value:
            safe = value.replace("'", "").strip()
            if safe:
                candidates.extend([f"xpath=//*[contains(text(), '{safe}')]", f"xpath=//*[contains(@placeholder, '{safe}')]"])
        return self._dedup(candidates)

    def _build_l3_candidates(self, target, value, attempts):
        if not self._enable_l3_ai:
            return []
        tokens = []
        for item in attempts:
            tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", str(item.get("selector") or "")))
        tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", target or ""))
        tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", value or ""))
        candidates = []
        seen = set()
        for tk in tokens:
            low = tk.lower()
            if low in seen: continue
            seen.add(low)
            candidates.extend([f"[id*='{low}']", f"[class*='{low}']", f"xpath=//*[contains(@id, '{low}') or contains(@class, '{low}') or contains(text(), '{low}')]"])
        return self._dedup(candidates)[:20]

    def _first_working_selector(self, page, candidates, level, timeout_ms=1200):
        attempts = []
        for sel in candidates:
            try:
                page.locator(sel).first.wait_for(state="attached", timeout=timeout_ms)
                attempts.append({"level": level, "selector": sel, "ok": True})
                return sel, attempts
            except Exception as e:
                attempts.append({"level": level, "selector": sel, "ok": False, "reason": str(e)})
        return "", attempts

    @staticmethod
    def _dedup(items):
        seen = set()
        return [i for i in (i.strip() for i in items) if i and i not in seen and not seen.add(i)]
