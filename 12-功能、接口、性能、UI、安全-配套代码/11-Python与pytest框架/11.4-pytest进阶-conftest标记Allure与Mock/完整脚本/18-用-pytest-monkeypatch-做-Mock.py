def test_process_payment_success(monkeypatch):
    """模拟支付成功"""
    def mock_pay(url, json):
        return MockResponse(200, {"code": 0})
    
    monkeypatch.setattr(requests, "post", mock_pay)
    
    result = process_payment(12345, 99.99)
    assert result is True

def test_process_payment_fail(monkeypatch):
    """模拟支付失败"""
    def mock_pay(url, json):
        return MockResponse(500, {})
    
    monkeypatch.setattr(requests, "post", mock_pay)
    
    result = process_payment(12345, 99.99)
    assert result is False
