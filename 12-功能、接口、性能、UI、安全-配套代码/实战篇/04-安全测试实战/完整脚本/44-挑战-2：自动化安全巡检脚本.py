"""
security_patrol.py — 每天9点跑一次的安全巡检
"""
import requests
import json
from datetime import datetime

BASE = "http://localhost:5000"

def patrol():
    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 检查项 1：登录接口是否可用
    resp = requests.post(f"{BASE}/api/auth/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    if resp.status_code == 401:
        results.append("✅ 登录接口正常（密码错误返回401）")
    else:
        results.append(f"❌ 登录接口异常（状态码: {resp.status_code}）")
    
    # 检查项 2：Token 过期是否正常返回 401
    fake_token = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3MDAwMDAwMDB9.xxx"
    resp = requests.get(f"{BASE}/api/users/1", 
        headers={"Authorization": f"Bearer {fake_token}"})
    if resp.status_code == 401:
        results.append("✅ Token鉴权正常（假Token返回401）")
    else:
        results.append(f"❌ Token鉴权异常（状态码: {resp.status_code}）")
    
    # 检查项 3：SQL注入防护依然有效
    resp = requests.post(f"{BASE}/api/auth/login", json={
        "username": "' OR 1=1 --",
        "password": "***"
    })
    if resp.status_code == 401:
        results.append("✅ SQL注入防护正常")
    else:
        results.append("❌ SQL注入防护失效！")
    
    # 写入日志
    with open("security_patrol.log", "a") as f:
        f.write(f"[{timestamp}] {' | '.join(results)}\n")
    
    return results

result = patrol()
for line in result:
    print(line)
