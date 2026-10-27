"""
从业务系统前端模板自动提取页面/控件信息，供 LLM 理解系统（非写死业务流程）。
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from seckill_config import LOGIN_URL, PRODUCTS_URL, SECKILL_BASE_URL

# 默认扫描秒杀系统模板目录（可用 SECKILL_APP_ROOT 覆盖）
DEFAULT_APP_ROOT = os.environ.get(
    "SECKILL_APP_ROOT",
    "seckill_finance_system",
)


def _scan_html(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    inputs = re.findall(
        r'<input[^>]*id=["\']([^"\']+)["\'][^>]*(?:placeholder=["\']([^"\']*)["\'])?',
        text,
        re.I,
    )
    buttons = re.findall(
        r'<button[^>]*id=["\']([^"\']+)["\'][^>]*>([^<]{0,40})</button>',
        text,
        re.I,
    )
    btn_text = re.findall(r'<button[^>]*>([^<]{1,30})</button>', text, re.I)
    return {
        "file": path.name,
        "inputs": [{"id": i, "placeholder": p or ""} for i, p in inputs],
        "buttons": [{"id": b[0], "text": b[1].strip()} for b in buttons if b[0]],
        "button_labels": list(dict.fromkeys(t.strip() for t in btn_text if t.strip()))[:20],
    }


def build_ui_catalog(app_root: str | None = None) -> Dict[str, Any]:
    root = Path(app_root or DEFAULT_APP_ROOT)
    templates = root / "templates"
    pages: List[Dict[str, Any]] = []
    if templates.is_dir():
        for html in sorted(templates.glob("*.html")):
            if html.name.startswith("_"):
                continue
            pages.append(_scan_html(html))

    return {
        "app": root.name,
        "base_url": SECKILL_BASE_URL,
        "routes": {
            "login": LOGIN_URL,
            "products": PRODUCTS_URL,
            "home": f"{SECKILL_BASE_URL}/",
        },
        "default_credentials": {"username": "admin", "password": "admin123"},
        "pages": pages,
        "skills": ["navigate", "input", "fill", "click", "select", "verify", "wait_url", "wait"],
    }


def catalog_to_prompt_text(catalog: Dict[str, Any]) -> str:
    lines = [
        f"系统: {catalog.get('app')} @ {catalog.get('base_url')}",
        "常用路由: " + ", ".join(f"{k}={v}" for k, v in (catalog.get("routes") or {}).items()),
        "默认测试账号（用户未指定时）: admin / admin123",
        "可用步骤技能: " + ", ".join(catalog.get("skills") or []),
        "页面控件（从模板自动扫描）:",
    ]
    for p in catalog.get("pages") or []:
        lines.append(f"  - {p.get('file')}:")
        for inp in p.get("inputs") or []:
            lines.append(f"      input #{inp['id']} placeholder={inp.get('placeholder') or '-'}")
        for btn in p.get("buttons") or []:
            lines.append(f"      button #{btn['id']} text={btn.get('text')}")
        for lbl in p.get("button_labels") or []:
            if lbl and lbl not in [b.get("text") for b in p.get("buttons") or []]:
                lines.append(f"      button text={lbl}")
    return "\n".join(lines)
