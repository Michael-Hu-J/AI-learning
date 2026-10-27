# 测试用例列表
test_cases = ["登录成功", "登录失败-密码错误", "登录失败-账号不存在"]

# 常用操作
print(test_cases[0])            # 取第一个：登录成功
print(test_cases[-1])           # 取最后一个：登录失败-账号不存在
print(len(test_cases))          # 长度：3
test_cases.append("登录失败-账号锁定")  # 追加一个
test_cases.remove("登录成功")   # 删除一个

# 遍历列表（最常用）
for case in test_cases:
    print(f"执行用例：{case}")
