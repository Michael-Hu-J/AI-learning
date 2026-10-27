"""视觉/语义降级定位 — 文本/角色锚点 + 可选 OpenCV 颜色检测
对应文章：第5篇-视觉语义定位"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

def _keywords(raw_step: Dict[str, Any], target: str, value: Any) -> List[str]:
    hints = raw_step.get("locator_hints") or {}
    if not isinstance(hints, dict): hints = {}
    parts = []
    for k in ("text", "label", "aria", "placeholder"):
        v = hints.get(k)
        if v and isinstance(v, str): parts.append(v.strip())
    if value and isinstance(value, str) and value.strip():
        parts.append(value.strip())
    t = (target or "").strip()
    if t and not t.startswith(("#", ".", "/", "[", "xpath", "text=", "role=")):
        parts.append(t)
    seen = set()
    return [p for p in parts if p and len(p) <= 120 and p.lower() not in seen and not seen.add(p.lower())][:12]

def build_semantic(dct, target, value, *, latency_anomaly=False):
    kws = _keywords(dct, target, value)
    cand = []
    for kw in kws:
        safe = kw.replace("'", "\\'")
        cand += [f"text={kw}", f"button:has-text('{safe}')", f"div:has-text('{safe}')", f"a:has-text('{safe}')",
                 f"[aria-label*='{safe}']", f"[placeholder*='{safe}']", f"role=button[name='{safe}']"]
    if latency_anomaly and kws:
        for kw in reversed(kws[:5]):
            cand.insert(0, f"text={kw}")
    seen = set()
    return [c for c in cand if c not in seen and not seen.add(c)][:24]

def selector_from_point(page, cx, cy):
    try:
        sel = page.evaluate("([x,y]) => {const el=document.elementFromPoint(x,y); if(!el||el.nodeType!==1)return null; "
                           "if(el.id)return '#'+el.id; const txt=(el.innerText||'').trim().slice(0,80); "
                           "return txt?'text='+txt:el.tagName.toLowerCase();}", [cx, cy])
        return sel.strip() if sel and isinstance(sel, str) and sel.strip() else None
    except: return None

def opencv_to_selectors(page, max_regions=4):
    try:
        import numpy as np, cv2
    except: return []
    try:
        png = page.screenshot(type="png")
        arr = np.frombuffer(png, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None: return []
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.bitwise_or(cv2.inRange(hsv, (0,60,50), (10,255,255)), cv2.inRange(hsv, (170,60,50), (180,255,255)))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return []
        h, w = img.shape[:2]
        out = []
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:15]:
            x, y, bw, bh = cv2.boundingRect(cnt)
            cx, cy = int(x+bw/2), int(y+bh/2)
            alt = selector_from_point(page, cx, cy)
            if alt: out.append(alt)
            if len(out) >= max_regions: break
        return out
    except: return []
