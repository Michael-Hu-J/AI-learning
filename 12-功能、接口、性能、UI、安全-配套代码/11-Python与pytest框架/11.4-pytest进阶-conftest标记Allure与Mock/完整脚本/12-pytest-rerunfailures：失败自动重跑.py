@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_unstable_api():
    """不稳定接口，失败自动重试 3 次，每次间隔 2 秒"""
    ...
