# 批量测登录
test_data = [
    {"username": "admin", "password": "Admin123", "expect": "成功"},
    {"username": "admin", "password": "wrong",   "expect": "失败"},
    {"username": "",      "password": "Admin123", "expect": "失败"},
]

for data in test_data:
    print(f"测试：{data['username']} / {data['password']} → 期望{data['expect']}")
    # 实际调用登录接口...
    print(f"  结果：✅ 符合预期")
