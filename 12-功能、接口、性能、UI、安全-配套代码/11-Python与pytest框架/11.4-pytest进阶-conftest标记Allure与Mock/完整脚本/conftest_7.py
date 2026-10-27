# test_auth.py
import pytest

@pytest.mark.smoke
@pytest.mark.p0
def test_login(base_url):
    """登录 — 核心流程，冒烟必测"""
    ...

@pytest.mark.slow
def test_load_test(base_url, admin_token):
    """压测 — 慢速测试"""
    ...
