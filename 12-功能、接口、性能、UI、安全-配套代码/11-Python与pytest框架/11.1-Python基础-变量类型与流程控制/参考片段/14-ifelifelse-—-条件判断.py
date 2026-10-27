status_code = 200

if status_code == 200:
    print("✅ 接口调用成功")
elif status_code == 400:
    print("❌ 参数错误")
elif status_code == 401:
    print("❌ 未认证")
elif status_code == 500:
    print("❌ 服务器内部错误")
else:
    print(f"⚠️ 未知状态码：{status_code}")
