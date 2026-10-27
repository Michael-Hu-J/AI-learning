# 定义字符串
name = "张三"
desc = '这是一个测试账号'
email = "zhangsan@test.com"

# 常用操作
print(name + email)              # 拼接：张三zhangsan@test.com
print(f"用户名：{name}")           # f-string 格式化（最常用）
print(len(name))                  # 长度：2
print(name[0])                    # 取第一个字符：张
print(name[0:1])                  # 切片：张
print("张三" in name)             # 包含？True
