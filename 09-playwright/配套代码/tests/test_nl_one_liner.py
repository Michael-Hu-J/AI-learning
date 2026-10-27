"""
一句话自然语言 UI — 集成测试（需秒杀系统在 5000 端口；LLM 测试需 API Key）。
"""
import os

import pytest
import requests

from nl_executor import run_nl_command
from seckill_config import PRODUCTS_URL, SECKILL_BASE_URL


def _server_up() -> bool:
    try:
        return requests.get(f"{SECKILL_BASE_URL}/login", timeout=3).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _server_up(), reason=f"秒杀系统未启动: {SECKILL_BASE_URL}")
def test_one_liner_add_product_llm():
    """任意口语由 LLM 拆分后执行（强制 llm 模式）。"""
    os.environ["NL_PARSER"] = "llm"
    results = run_nl_command(
        "给我新增一个商品，名字叫「智能拆分测试」",
        base_url=PRODUCTS_URL,
        headless=True,
        verbose=False,
    )
    assert results
    assert all(r["status"] == "passed" for r in results), results


@pytest.mark.skipif(not _server_up(), reason=f"秒杀系统未启动: {SECKILL_BASE_URL}")
def test_llm_parser_returns_steps():
    from llm_step_parser import llm_available, parse_with_llm

    if not llm_available():
        pytest.skip("未配置 LLM API Key")
    steps = parse_with_llm("登录后打开商品页，新增一个叫测试A的商品", PRODUCTS_URL)
    skills = {s["skill"] for s in steps}
    assert "navigate" in skills or "click" in skills
    assert len(steps) >= 3
