import requests
import pytest

# 测试数据（数据驱动）
test_cases = [
    # (用户名, 密码, 预期状态码, 预期结果)
    ("validuser", "Valid1234", 200, "success"),       # 正常
    ("a", "Valid1234", 400, "用户名长度不足"),         # 用户名太短
    ("validuser", "123", 400, "密码长度不足"),         # 密码太短
    ("validuser", "12345678", 200, "success"),         # 纯数字密码
    ("valid@user", "Valid1234", 400, "用户名含非法字符"), # 特殊字符
    ("", "Valid1234", 400, "用户名不能为空"),           # 空用户名
    ("validuser", "", 400, "密码不能为空"),             # 空密码
]

def test_register():
    url = "http://test-api.example.com/api/v1/user/register"
    
    for username, password, expected_code, expected_msg in test_cases:
        data = {"username": username, "password": password}
        response = requests.post(url, json=data)
        
        assert response.status_code == expected_code, \
            f"用例失败: username={username}, 预期 {expected_code}, 实际 {response.status_code}"
        
        if expected_code == 200:
            result = response.json()
            assert result["code"] == 0
        else:
            result = response.json()
            assert expected_msg in result.get("message", ""), \
                f"预期错误信息包含'{expected_msg}'，实际'{result.get('message')}'"
        
        print(f"✅ 通过: username={username}, password={password}")

if __name__ == "__main__":
    test_register()
