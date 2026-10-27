def test_login():
    status_code = 200
    
    # 基本断言
    assert status_code == 200                       # 等于
    assert status_code != 500                       # 不等于
    assert status_code > 200                        # 大于
    assert status_code >= 200 and status_code < 300 # 范围
    
    # 包含
    assert "token" in response_data                  # 字典包含某键
    assert "成功" in response_text                   # 文本包含
    
    # 布尔
    assert result is True
    assert result is False
    assert result is None
