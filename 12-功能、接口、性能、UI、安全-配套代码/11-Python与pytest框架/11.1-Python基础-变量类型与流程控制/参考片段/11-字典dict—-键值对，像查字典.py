# 一个测试用户的信息
user = {
    "name": "张三",
    "age": 28,
    "role": "admin",
    "phone": "13800138000"
}

# 取值
print(user["name"])             # 张三
print(user.get("email"))        # 安全取值：不存在返回 None 而不是报错

# 改值
user["age"] = 29

# 新增
user["email"] = "zhang@test.com"

# 遍历（实际测试中最常用）
for key, value in user.items():
    print(f"{key} → {value}")
