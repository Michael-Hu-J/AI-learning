"""
MCP Playwright Server — 浏览器自动化服务
导航/点击/输入/截图/内容提取
对应文章：第6篇-MCP协议集成
"""
from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright, Page, Browser
from typing import Optional, Dict
import base64

mcp = FastMCP("Playwright Server")
_b: Optional[Browser] = None
_p: Optional[Page] = None

def _browser():
    global _b
    if _b is None: _b = sync_playwright().start().chromium.launch(headless=True)
    return _b

def _page():
    global _p
    if _p is None: _p = _browser().new_page()
    return _p

@mcp.tool()
def navigate(url: str) -> Dict:
    try:
        r = _page().goto(url, wait_until="networkidle")
        return {"success": True, "url": _page().url, "status": r.status, "title": _page().title()}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
def click(selector: str) -> Dict:
    try: _page().click(selector); _page().wait_for_load_state("networkidle"); return {"success": True, "selector": selector}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
def fill(selector: str, value: str) -> Dict:
    try: _page().fill(selector, value); return {"success": True, "selector": selector, "value": value}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
def screenshot(name: str = "screenshot") -> Dict:
    try:
        d = _page().screenshot(full_page=True)
        b64 = base64.b64encode(d).decode()
        open(f"/tmp/{name}.png","wb").write(d)
        return {"success": True, "filepath": f"/tmp/{name}.png", "base64": b64[:100]+"..."}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
def get_text(selector: str) -> Dict:
    try: return {"success": True, "text": _page().text_content(selector)}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
def find_elements(selector: str) -> Dict:
    try:
        els = _page().query_selector_all(selector)
        return {"success": True, "count": len(els), "elements": [{"text": e.text_content(), "visible": e.is_visible()} for e in els[:10]]}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
def get_page_content() -> Dict:
    try:
        html = _page().content()
        text = _page().text_content()
        return {"success": True, "url": _page().url, "title": _page().title(), "html_length": len(html), "text_length": len(text)}
    except Exception as e: return {"success": False, "error": str(e)}

if __name__ == "__main__": mcp.run()
