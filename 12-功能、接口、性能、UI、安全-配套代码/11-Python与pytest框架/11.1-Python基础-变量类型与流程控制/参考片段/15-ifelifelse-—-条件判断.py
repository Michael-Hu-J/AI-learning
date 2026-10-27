def verify_response(response):
    """校验接口返回：状态码 + body"""
    if response.status_code != 200:
        print(f"❌ 状态码不对：期望 200，实际 {response.status_code}")
        return False
    
    data = response.json()
    if data.get("code") != 0:
        print(f"❌ 业务码不对：期望 0，实际 {data.get('code')}")
        print(f"   错误信息：{data.get('message')}")
        return False
    
    print("✅ 校验通过")
    return True
