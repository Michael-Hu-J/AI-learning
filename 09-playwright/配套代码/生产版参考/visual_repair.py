"""
视觉 / 语义降级定位：XPath/CSS 失败时补充 Playwright 文本、角色锚点与可选 OpenCV 颜色区域→坐标→XPath。
opencv-python-headless 为可选依赖；未安装时自动跳过 OpenCV 分支。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _keywords_from_step(raw_step: Dict[str, Any], target: str, value: Any) -> List[str]:
    hints = raw_step.get("locator_hints") or {}
    if not isinstance(hints, dict):
        hints = {}
    parts: List[str] = []
    for key in ("text", "label", "aria", "placeholder"):
        v = hints.get(key)
        if v and isinstance(v, str):
            parts.append(v.strip())
    if value and isinstance(value, str) and value.strip():
        parts.append(value.strip())
    t = (target or "").strip()
    if t and not t.startswith(("#", ".", "/", "[", "xpath", "text=", "role=")):
        parts.append(t)
    seen = set()
    out: List[str] = []
    for p in parts:
        if not p or len(p) > 120:
            continue
        low = p.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(p)
    return out[:12]


def build_semantic_playwright_selectors(
    raw_step: Dict[str, Any],
    target: str,
    value: Any,
    *,
    latency_anomaly: bool = False,
) -> List[str]:
    """
    生成 Playwright 引擎可识别的选择器串（与现有 page.click 兼容）。
    latency_anomaly 为 True 时优先插入文案/角色锚点（预测性维护路径）。
    """
    kws = _keywords_from_step(raw_step, target, value)
    candidates: List[str] = []
    for kw in kws:
        safe = kw.replace("'", "\\'")
        candidates.extend(
            [
                f"text={kw}",
                f"button:has-text('{safe}')",
                f"div:has-text('{safe}')",
                f"a:has-text('{safe}')",
                f"[aria-label*='{safe}']",
                f"[placeholder*='{safe}']",
                f"role=button[name='{safe}']",
            ]
        )
    if latency_anomaly and kws:
        # 页面变慢时：把文案锚点前置（重复项后面会去重）
        for kw in reversed(kws[:5]):
            candidates.insert(0, f"text={kw}")
    seen = set()
    dedup: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    return dedup[:24]


def _selector_from_viewport_point(page: Any, cx: int, cy: int) -> Optional[str]:
    """在浏览器内由视口坐标得到 Playwright 可用选择器（id / text= / 标签）。"""
    try:
        sel = page.evaluate(
            """([x, y]) => {
            const el = document.elementFromPoint(x, y);
            if (!el || el.nodeType !== 1) return null;
            if (el.id) return '#' + el.id;
            const txt = (el.innerText || '').trim().slice(0, 80);
            if (txt) return 'text=' + txt;
            return el.tagName.toLowerCase();
          }""",
            [cx, cy],
        )
        if sel and isinstance(sel, str) and sel.strip():
            return sel.strip()
    except Exception:
        return None
    return None


def opencv_red_regions_to_selectors(page: Any, max_regions: int = 4) -> List[str]:
    """
    在视口截图上检测偏红色高亮区域，取形心映射回 DOM，生成 xpath= 备选。
    未安装 OpenCV 或失败时返回空列表。
    """
    try:
        import numpy as np  # noqa: F401
        import cv2  # type: ignore
    except Exception:
        return []

    try:
        png = page.screenshot(type="png")
        arr = np.frombuffer(png, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return []
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, (0, 60, 50), (10, 255, 255))
        m2 = cv2.inRange(hsv, (170, 60, 50), (180, 255, 255))
        mask = cv2.bitwise_or(m1, m2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []
        h, w = img.shape[:2]
        scored = sorted(contours, key=cv2.contourArea, reverse=True)[:15]
        out: List[str] = []
        for cnt in scored:
            area = cv2.contourArea(cnt)
            if area < (w * h) * 0.0001:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            cx = int(x + bw / 2)
            cy = int(y + bh / 2)
            alt = _selector_from_viewport_point(page, cx, cy)
            if alt:
                out.append(alt)
            if len(out) >= max_regions:
                break
        return out
    except Exception:
        return []
