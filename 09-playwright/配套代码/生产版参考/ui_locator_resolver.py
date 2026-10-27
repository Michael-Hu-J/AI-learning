"""
UI 元素定位解析器
三层降级:
L1 稳定选择器 -> L2 DOM 推断 -> L3 AI 辅助候选
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from collections import OrderedDict
import re
import os
import json
import httpx


class UILocatorResolver:
    """Playwright 元素定位策略解析器。"""

    MAX_CACHE_SIZE = 500

    def __init__(self, enable_l3_ai: bool = False) -> None:
        self._enable_l3_ai = enable_l3_ai
        self._locator_cache: OrderedDict[str, str] = OrderedDict()

    def _resolve_cache(self, page_url: str, action: str, target: str) -> str:
        """查询定位缓存，命中则返回 selector，否则返回空字符串。"""
        key = f"{page_url}:{action}:{target}"
        if key in self._locator_cache:
            self._locator_cache.move_to_end(key)
            return self._locator_cache[key]
        return ""

    def _set_cache(self, page_url: str, action: str, target: str, selector: str) -> None:
        """写入定位缓存，LRU 淘汰。"""
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

        # 先查缓存
        cached = self._resolve_cache(page_url, action, target)
        if cached:
            return {
                "found": True,
                "selector": cached,
                "level": "CACHE",
                "attempts": [],
            }

        if isinstance(hints, dict) and hints.get("prefer_visual_semantic"):
            from .visual_repair import build_semantic_playwright_selectors

            sem = build_semantic_playwright_selectors(step, target, value, latency_anomaly=True)
            selector0, attempts0 = self._first_working_selector(page, sem, "L0_SEM")
            if selector0:
                return {
                    "found": True,
                    "selector": selector0,
                    "level": "L0_SEM",
                    "attempts": attempts0,
                }

        l1_candidates = self._build_l1_candidates(target, value, hints)
        selector, attempts = self._first_working_selector(page, l1_candidates, "L1")
        if selector:
            self._set_cache(page_url, action, target, selector)
            return {
                "found": True,
                "selector": selector,
                "level": "L1",
                "attempts": attempts,
            }

        l2_candidates = self._build_l2_candidates(target, value)
        selector_l2, attempts_l2 = self._first_working_selector(page, l2_candidates, "L2")
        attempts.extend(attempts_l2)
        if selector_l2:
            self._set_cache(page_url, action, target, selector_l2)
            return {
                "found": True,
                "selector": selector_l2,
                "level": "L2",
                "attempts": attempts,
            }

        l3_candidates = self._build_l3_ai_candidates(target, value, attempts)
        selector_l3, attempts_l3 = self._first_working_selector(page, l3_candidates, "L3")
        attempts.extend(attempts_l3)
        if selector_l3:
            self._set_cache(page_url, action, target, selector_l3)
            return {
                "found": True,
                "selector": selector_l3,
                "level": "L3",
                "attempts": attempts,
            }

        return {
            "found": False,
            "selector": "",
            "level": "NONE",
            "attempts": attempts,
        }

    def _build_l1_candidates(self, target: str, value: str, hints: Dict[str, Any]) -> List[str]:
        candidates: List[str] = []

        if target:
            candidates.append(target)
            if target.startswith("text=") or target.startswith("xpath="):
                pass
            elif target.startswith("//"):
                candidates.append(f"xpath={target}")

        test_id = str(hints.get("testid") or hints.get("data-testid") or "").strip()
        role = str(hints.get("role") or "").strip()
        label = str(hints.get("label") or "").strip()
        text = str(hints.get("text") or value or "").strip()

        if test_id:
            candidates.extend([
                f"[data-testid='{test_id}']",
                f"[data-test='{test_id}']",
                f"[data-qa='{test_id}']",
            ])
        if role:
            if text:
                candidates.append(f"role={role}[name='{text}']")
            candidates.append(f"role={role}")
        if label:
            candidates.append(f"label={label}")
        if text:
            candidates.extend([
                f"text={text}",
                f"button:has-text('{text}')",
                f"a:has-text('{text}')",
            ])

        return self._deduplicate(candidates)

    def _build_l2_candidates(self, target: str, value: str) -> List[str]:
        candidates: List[str] = []

        if target:
            token = target.strip().lstrip("#.").split()[0]
            token = re.sub(r"[^a-zA-Z0-9_-]", "", token)
            if token:
                candidates.extend([
                    f"[id*='{token}']",
                    f"[class*='{token}']",
                    f"[name*='{token}']",
                    f"[placeholder*='{token}']",
                    f"//*[@id and contains(@id, '{token}')]",
                    f"//*[@class and contains(@class, '{token}')]",
                ])
                candidates.append(f"xpath=//*[@id and contains(@id, '{token}')]")
                candidates.append(f"xpath=//*[@class and contains(@class, '{token}')]")

        if value:
            safe = value.replace("'", "").strip()
            if safe:
                candidates.extend([
                    f"xpath=//*[contains(text(), '{safe}')]",
                    f"xpath=//*[contains(@placeholder, '{safe}')]",
                ])

        return self._deduplicate(candidates)

    def _build_l3_ai_candidates(self, target: str, value: str, attempts: List[Dict[str, Any]]) -> List[str]:
        """L3 AI 辅助候选生成（可选开关）。"""
        if not self._enable_l3_ai:
            return []

        candidates: List[str] = []

        # 从已有失败选择器提取关键词，模拟 AI 提示生成候选
        tokens: List[str] = []
        for item in attempts:
            raw = str(item.get("selector") or "")
            tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", raw))
        tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", target or ""))
        tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", value or ""))

        seen = set()
        for tk in tokens:
            low = tk.lower()
            if low in seen:
                continue
            seen.add(low)
            candidates.extend([
                f"[id*='{low}']",
                f"[class*='{low}']",
                f"xpath=//*[contains(@id, '{low}') or contains(@class, '{low}') or contains(text(), '{low}')]",
            ])

        llm_candidates = self._query_llm_candidates(target, value, attempts)
        candidates.extend(llm_candidates)
        return self._deduplicate(candidates)[:20]

    def _query_llm_candidates(self, target: str, value: str, attempts: List[Dict[str, Any]]) -> List[str]:
        """
        L3 真实模型候选生成（DashScope）。
        无 key/失败时返回空列表，由启发式候选兜底。
        """
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            return []

        simplified_attempts = [
            {
                "selector": item.get("selector", ""),
                "reason": item.get("reason", ""),
                "level": item.get("level", ""),
            }
            for item in (attempts or [])[-10:]
        ]
        prompt = (
            "你是 UI 自动化元素定位专家。"
            "请根据失败历史和目标语义输出最多 8 个 Playwright 可用选择器，"
            "仅输出 JSON 数组字符串，不要解释。"
            f"\n目标 selector: {target or '-'}"
            f"\n目标文本/值: {value or '-'}"
            f"\n失败尝试: {json.dumps(simplified_attempts, ensure_ascii=False)}"
        )
        try:
            resp = httpx.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-plus",
                    "input": {
                        "messages": [
                            {"role": "system", "content": "只输出 JSON 数组，不输出任何解释"},
                            {"role": "user", "content": prompt},
                        ]
                    },
                    "parameters": {"temperature": 0.1, "max_tokens": 512, "result_format": "message"},
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            content = (
                data.get("output", {})
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            raw = (content or "").strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)
            arr = json.loads(raw)
            if not isinstance(arr, list):
                return []
            return [str(x).strip() for x in arr if str(x).strip()]
        except Exception:
            return []

    def _first_working_selector(
        self,
        page,
        candidates: List[str],
        level: str,
        timeout_ms: int = 1200,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        attempts: List[Dict[str, Any]] = []
        for selector in candidates:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="attached", timeout=timeout_ms)
                attempts.append({"level": level, "selector": selector, "ok": True})
                return selector, attempts
            except Exception as e:
                attempts.append({"level": level, "selector": selector, "ok": False, "reason": str(e)})
        return "", attempts

    @staticmethod
    def _deduplicate(items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            it = (item or "").strip()
            if not it or it in seen:
                continue
            seen.add(it)
            result.append(it)
        return result

