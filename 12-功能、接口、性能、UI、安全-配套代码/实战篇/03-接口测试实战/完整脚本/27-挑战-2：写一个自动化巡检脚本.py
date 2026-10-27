"""抢购系统巡检脚本 — 每天定时跑"""
import requests
import time
from datetime import datetime

BASE = "http://localhost:5000"

def check_seckill_health():
    """检查抢购系统是否健康"""
    log = []
    
    # 1. 检查登录
    resp = requests.post(f"{BASE}/api/auth/login", json={
        "username": "admin", "password": "***"
    })
    if resp.status_code != 200:
        log.append(f"❌ 登录失败: {resp.status_code}")
        return log
    token = resp.json()["token"]
    log.append("✅ 登录成功")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 检查抢购列表
    resp = requests.get(f"{BASE}/api/seckill/list", headers=headers)
    if resp.status_code != 200:
        log.append(f"❌ 抢购列表获取失败: {resp.status_code}")
        return log
    
    products = resp.json()
    if not products:
        log.append("⚠️ 没有抢购活动")
        return log
    
    log.append(f"✅ 抢购活动数: {len(products)}")
    
    # 3. 检查库存
    for p in products:
        if p["current_stock"] <= 0:
            log.append(f"⚠️ 商品 {p['product_name']} 库存为 0")
        elif p["current_stock"] <= 5:
            log.append(f"⚠️ 商品 {p['product_name']} 库存低: {p['current_stock']}")
        else:
            log.append(f"✅ 商品 {p['product_name']} 库存正常: {p['current_stock']}")
    
    # 4. 写入日志
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("seckill_health.log", "a") as f:
        f.write(f"[{timestamp}] {' | '.join(log)}\n")
    
    return log

# 运行
result = check_seckill_health()
for line in result:
    print(line)
