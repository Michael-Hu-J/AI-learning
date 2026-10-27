"""
错误诊断器 — 规则匹配优先，可选 LLM 兜底
分类：element/network/authentication/assertion/unknown
对应文章：第4篇-AI自愈系统
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request


class ErrorDiagnoser:
    def __init__(self):
        # Order matters! element patterns checked first (most common in UI tests)
        self.patterns = [
            (
                "element",
                [
                    r"element\s+not\s+found",
                    r"no\s+such\s+element",
                    r"not\s+interactable",
                    r"stale\s+element",
                    r"waiting for locator",
                    r"selector.*not found",
                    r"Timeout.*locator",
                    r"Timeout.*fill",
                    r"Timeout.*click",
                    r"Timeout.*wait",
                ],
            ),
            (
                "network",
                [
                    r"connection\s+refused",
                    r"network\s+error",
                    r"503",
                    r"econnreset",
                    r"enotfound",
                    r"timeout",
                ],
            ),
            ("assertion", [r"assertion\s+failed", r"expected.*but\s+got", r"assertionerror"]),
            (
                "authentication",
                [r"401", r"403", r"token\s+expired", r"session\s+expired", r"login required"],
            ),
        ]
        self.llm_diagnosis_enabled = bool(os.getenv("DASHSCOPE_API_KEY", "").strip())
        self.llm_model = os.getenv("HEALER_LLM_MODEL", "qwen-plus")
        self.llm_base_url = os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/")

    def classify(self, msg: str) -> Tuple[str, float]:
        low = msg.lower()
        for tp, pts in self.patterns:
            for p in pts:
                if re.search(p, low):
                    return tp, 0.9
        return "unknown", 0.4

    def diagnose(self, msg: str, ctx: Optional[Dict] = None) -> Dict:
        ctx = ctx or {}
        tp, conf = self.classify(msg)
        d: Dict = {
            "error_type": tp,
            "confidence": conf,
            "root_cause": "",
            "suggested_fix": "",
            "auto_repairable": False,
            "repair_strategy": None,
            "diagnosis_source": "regex",
        }
        if tp == "element":
            m = re.search(r"selector[s:]+([^\n]+)", msg, re.I)
            sel = m.group(1).strip() if m else "unknown"
            d.update(
                {
                    "root_cause": "元素不可达: " + sel,
                    "suggested_fix": "尝试更稳定的选择器",
                    "auto_repairable": True,
                }
            )
        elif tp == "authentication":
            d.update(
                {
                    "root_cause": "Token过期或无效",
                    "suggested_fix": "刷新Token后重试",
                    "auto_repairable": True,
                }
            )
        elif tp == "network":
            d.update(
                {
                    "root_cause": "网络连接问题",
                    "suggested_fix": "检查网络后重试",
                    "auto_repairable": True,
                }
            )
        elif tp == "assertion":
            exp = re.search(r"expected[s:]+([^\n]+)", msg, re.I)
            act = re.search(r"but\s+got[:\s]+([^\n]+)", msg, re.I)
            d.update(
                {
                    "root_cause": "实际结果与预期不符",
                    "suggested_fix": "检查测试数据",
                    "expected": exp.group(1).strip() if exp else "unknown",
                    "actual": act.group(1).strip() if act else "unknown",
                }
            )
        else:
            d.update({"root_cause": "未能识别的错误", "suggested_fix": "查看日志手动分析"})

        llm_result: Optional[Dict] = None
        need_llm = (
            d["error_type"] == "unknown"
            or d.get("confidence", 0.0) < 0.8
            or d["error_type"] in ("assertion", "business")
        )
        if need_llm:
            llm_result = self._llm_diagnose(msg, ctx)
            if llm_result and llm_result.get("confidence", 0.0) >= d.get("confidence", 0.0):
                d.update(llm_result)
                d["diagnosis_source"] = "llm"

        from healer.strategies import StrategyFactory

        selected = StrategyFactory().select(d)
        if selected:
            d["repair_strategy"] = selected.name
            if selected.name == "element_locator_repair":
                d["repair_strategy_alias"] = "locator_repair"
            if d["error_type"] in ("element", "authentication", "network"):
                d["auto_repairable"] = True
            elif d.get("diagnosis_source") == "llm" and llm_result and llm_result.get("auto_repairable"):
                d["auto_repairable"] = True

        return d

    def _context_for_llm(self, context: Dict) -> Dict:
        """去掉不可 JSON 序列化的对象（如 Playwright Page）。"""
        safe: Dict = {}
        for k, v in (context or {}).items():
            if k in ("page", "browser", "context"):
                continue
            if isinstance(v, (str, int, float, bool, type(None))):
                safe[k] = v
            elif isinstance(v, (list, dict)):
                try:
                    json.dumps(v, ensure_ascii=False)
                    safe[k] = v
                except (TypeError, ValueError):
                    safe[k] = str(v)
            else:
                safe[k] = str(v)
        return safe

    def _llm_diagnose(self, error_message: str, context: Dict) -> Optional[Dict]:
        """LLM 软判决（需 DASHSCOPE_API_KEY，无 Key 时返回 None）。"""
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not self.llm_diagnosis_enabled or not api_key:
            return None

        prompt = (
            "你是资深测试架构师，请根据错误日志和上下文做诊断。\n"
            "请严格输出 JSON："
            '{"error_type":"network|element|authentication|assertion|business|unknown",'
            '"root_cause":"...",'
            '"suggested_fix":"...",'
            '"confidence":0.0,'
            '"auto_repairable":true}\n\n'
            f"错误日志:\n{error_message}\n\n"
            f"上下文:\n{json.dumps(self._context_for_llm(context), ensure_ascii=False)}"
        )
        payload = json.dumps(
            {
                "model": self.llm_model,
                "messages": [
                    {"role": "system", "content": "你是测试故障诊断专家。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 400,
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            url=f"{self.llm_base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")
            parsed = self._extract_json(content)
            if not isinstance(parsed, dict):
                return None
            et = str(parsed.get("error_type", "unknown")).strip().lower()
            conf = float(parsed.get("confidence", 0.5) or 0.5)
            return {
                "error_type": et if et else "unknown",
                "confidence": max(0.0, min(conf, 1.0)),
                "root_cause": str(parsed.get("root_cause", "")),
                "suggested_fix": str(parsed.get("suggested_fix", "")),
                "auto_repairable": bool(parsed.get("auto_repairable", False)),
            }
        except (
            urllib_error.URLError,
            urllib_error.HTTPError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ):
            return None
        except Exception:
            return None

    def _extract_json(self, content: str) -> Optional[Dict]:
        try:
            return json.loads(content)
        except Exception:
            pass
        match = re.search(r"\{[\s\S]*\}", content or "")
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
