import json

with open("test_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

base_url = data["base_url"]
users = data["test_users"]

for user in users:
    print(f"{user['role']} 账号：{user['username']}")
    # 调用登录接口...
