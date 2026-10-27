# ❌ 错误写法
count = "100"     # 字符串
result = count + 50   # TypeError: can only concatenate str not int to str

# ✅ 正确写法
count = "100"
result = int(count) + 50   # 先转类型，再运算
print(result)   # 150
