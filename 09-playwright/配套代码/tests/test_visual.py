"""
视觉语义定位测试
对应文章：第5篇
"""
import pytest
from locator.visual_repair import _keywords, build_semantic

class TestVisual:
    def test_kw_text(self): k=_keywords({"locator_hints":{"text":"登录"}},"","登录"); assert "登录" in k
    def test_kw_value(self): k=_keywords({},"","提交订单"); assert "提交订单" in k
    def test_kw_placeholder(self): k=_keywords({"locator_hints":{"placeholder":"请输入"}},"",""); assert "请输入" in k
    def test_sem_text(self): s=build_semantic({"locator_hints":{"text":"确认"}},"",""); assert "text=确认" in s
    def test_sem_button(self): s=build_semantic({"locator_hints":{"text":"提交"}},"",""); assert any("has-text" in x for x in s)
    def test_sem_aria(self): s=build_semantic({"locator_hints":{"aria":"关闭"}},"",""); assert "[aria-label*='关闭']" in s
    def test_sem_role(self): s=build_semantic({"locator_hints":{"text":"提交"}},"",""); assert any("role=button" in x for x in s)
    def test_latency(self):
        n=build_semantic({"locator_hints":{"text":"提交"}},"","")
        a=build_semantic({"locator_hints":{"text":"提交"}},"","",latency_anomaly=True)
        assert "text=提交" in a
    def test_max_24(self): s=build_semantic({"locator_hints":{"text":"a","label":"b","aria":"c","placeholder":"d"}},"",""); assert len(s)<=24
    def test_kw_max_12(self):
        k=_keywords({"locator_hints":{str(i):f"k{i}" for i in range(20)}},"","v"); assert len(k)<=12
