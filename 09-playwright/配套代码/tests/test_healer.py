"""
AI自愈系统测试
对应文章：第4篇
"""
import os
from unittest.mock import patch

import pytest
from healer.diagnostic import ErrorDiagnoser
from healer.strategies import StrategyFactory, ElementRepairStrategy, AuthRefreshStrategy, NetworkRetryStrategy, AssertionAdjustStrategy

class TestDiagnose:
    @pytest.fixture
    def d(self): return ErrorDiagnoser()
    def test_element(self, d): r=d.diagnose("element not found: #username"); assert r["error_type"]=="element"; assert r["auto_repairable"]
    def test_network(self, d): r=d.diagnose("timeout: page.navigate timeout"); assert r["error_type"]=="network"
    def test_auth(self, d): r=d.diagnose("401 unauthorized"); assert r["error_type"]=="authentication"
    def test_assert(self, d): r=d.diagnose("AssertionError: expected 'ok' but got 'fail'"); assert r["error_type"]=="assertion"
    def test_unknown(self, d): r=d.diagnose("random js error"); assert r["error_type"]=="unknown"; assert not r["auto_repairable"]
    def test_suggest(self, d): r=d.diagnose("element not found: #btn"); assert r["suggested_fix"]
    def test_root_cause(self, d): r=d.diagnose("connection refused"); assert r["root_cause"]

    def test_repair_strategy(self, d):
        r = d.diagnose("element not found: #btn")
        assert r.get("repair_strategy") == "element_locator_repair"

    def test_diagnosis_source_regex(self, d):
        r = d.diagnose("401 unauthorized")
        assert r.get("diagnosis_source") == "regex"

    def test_llm_skipped_without_api_key(self, d):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DASHSCOPE_API_KEY", None)
            d.llm_diagnosis_enabled = False
            r = d.diagnose("totally weird js engine fault xyz", {})
            assert r.get("diagnosis_source") == "regex"
            assert r["error_type"] == "unknown"

    def test_llm_fallback_when_mocked(self, d):
        fake = {
            "error_type": "element",
            "confidence": 0.85,
            "root_cause": "mock",
            "suggested_fix": "mock fix",
            "auto_repairable": True,
        }
        with patch.object(d, "_llm_diagnose", return_value=fake):
            d.llm_diagnosis_enabled = True
            r = d.diagnose("totally weird js engine fault xyz", {"url": "http://x"})
            assert r.get("diagnosis_source") == "llm"
            assert r["error_type"] == "element"
            assert r["auto_repairable"]

class TestStrategies:
    @pytest.fixture
    def f(self): return StrategyFactory()
    def test_element_match(self): assert ElementRepairStrategy().match({"error_type":"element"}); assert not ElementRepairStrategy().match({"error_type":"network"})
    def test_auth_match(self): assert AuthRefreshStrategy().match({"error_type":"authentication"})
    def test_net_match(self): assert NetworkRetryStrategy().match({"error_type":"network"})
    def test_assert_match(self): assert AssertionAdjustStrategy().match({"error_type":"assertion"})
    def test_element_alt(self):
        r=ElementRepairStrategy().execute("not found",{"selector":"#btn","value":"提交","raw_step":{}})
        assert r["success"]; assert len(r["alternative_selectors"]) > 0
    def test_auth_token(self):
        r=AuthRefreshStrategy().execute("expired",{}); assert r["success"]; assert "mock_token_" in r["new_token"]
    def test_net_retry(self):
        r=NetworkRetryStrategy().execute("timeout",{"max_retries":3,"current_retry":0}); assert r["success"]; assert r["retry_count"]==1
    def test_net_exceed(self):
        r=NetworkRetryStrategy().execute("timeout",{"max_retries":3,"current_retry":3}); assert not r["success"]
    def test_factory_select(self, f): assert f.select({"error_type":"element"}).name=="element_locator_repair"
    def test_factory_unknown(self, f): assert f.select({"error_type":"unknown"}) is None
    def test_factory_execute(self, f):
        r=f.execute({"error_type":"network","auto_repairable":True},{"max_retries":3,"current_retry":0,"error_message":"timeout"})
        assert r["success"]; assert r["action"]=="retry"
    def test_factory_not_repairable(self, f):
        r=f.execute({"error_type":"unknown","auto_repairable":False},{"error_message":"err"})
        assert not r["success"]

class TestHealingGraph:
    @pytest.fixture
    def subgraph(self):
        pytest.importorskip("langgraph")
        from healer.healing_graph import invoke_healing_subgraph_sync
        return invoke_healing_subgraph_sync

    def test_element_heal(self, subgraph):
        sg = subgraph(
            "Timeout: waiting for locator('#login-btn')",
            {"selector": "#login-btn", "raw_step": {"action": "点击元素", "target": "#login-btn"}},
        )
        assert sg.get("healed")
        assert (sg.get("repair_result") or {}).get("action") == "retry_with_alternatives"
        assert "diagnose:element" in " ".join(sg.get("heal_log") or [])

    def test_unknown_no_heal(self, subgraph):
        sg = subgraph("totally unrecognized xyz", {})
        assert not sg.get("healed")
