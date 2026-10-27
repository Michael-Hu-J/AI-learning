"""
三层定位降级策略测试
对应文章：第3篇
"""
import pytest
from locator.resolver import UILocatorResolver

class TestLocator:
    @pytest.fixture
    def r(self): return UILocatorResolver(enable_l3_ai=True)

    def test_l1_id(self, r): c = r._build_l1_candidates("#username","",{}); assert "#username" in c
    def test_l1_text(self, r): c = r._build_l1_candidates("","登录",{"text":"登录"}); assert "text=登录" in c; assert "button:has-text('登录')" in c
    def test_l1_testid(self, r): c = r._build_l1_candidates("","",{"testid":"btn"}); assert "[data-testid='btn']" in c
    def test_l2_dom(self, r): c = r._build_l2_candidates("username",""); assert any("username" in x for x in c)
    def test_l2_val(self, r): c = r._build_l2_candidates("","登录"); assert any("登录" in x for x in c)
    def test_l3_heuristic(self, r): c = r._build_l3_candidates("btn-submit","",[{"selector":"#my-btn","level":"L1","ok":False}]); assert len(c) > 0; assert any("btn" in x for x in c)
    def test_dedup(self, r): assert r._dedup(["a","b","a","c"]) == ["a","b","c"]
    def test_cache(self, r):
        r._set_cache("http://t.com","click","#btn","#btn")
        assert r._resolve_cache("http://t.com","click","#btn") == "#btn"
        assert r._resolve_cache("http://t.com","click","#other") == ""
