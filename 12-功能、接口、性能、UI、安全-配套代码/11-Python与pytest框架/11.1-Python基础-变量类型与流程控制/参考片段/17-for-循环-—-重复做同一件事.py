# 重复发送 5 次请求，验证幂等性
for i in range(5):
    print(f"第 {i+1} 次请求")
    # 发请求...
