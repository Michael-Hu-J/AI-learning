# ❌ 错误写法
try:
    response = requests.get("http://localhost:5001/api/users")
    data = response.json()
except:
    pass  # 吞掉了所有错误！你不知道哪里出问题了
print("继续执行...")  # data 没定义，会崩在别的地方

# ✅ 正确写法
try:
    response = requests.get("http://localhost:5001/api/users")
    response.raise_for_status()  # 非 200 会主动抛异常
    data = response.json()
except Exception as e:
    print(f"❌ 请求失败：{e}")
    data = []  # 给一个默认值，不至于后续代码崩
