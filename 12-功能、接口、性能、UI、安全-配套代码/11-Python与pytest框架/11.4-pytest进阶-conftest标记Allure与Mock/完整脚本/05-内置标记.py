import pytest

@pytest.mark.skip(reason="这个功能还没开发完")
def test_new_feature():
    ...

@pytest.mark.skipif(condition, reason="条件不满足")
def test_only_in_prod():
    ...

@pytest.mark.xfail(reason="已知 bug")
def test_known_bug():
    ...

@pytest.mark.timeout(5)  # 需要 pytest-timeout 插件
def test_no_timeout():
    ...
