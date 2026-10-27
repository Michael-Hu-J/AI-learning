# tests/api/test_seckill.py
import requests
import pytest

BASE = "http://localhost:5001"

@pytest.fixture
def auth_token():
    """获取认证 token"""
    resp = requests.post(f"{BASE}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return resp.json()["data"]["token"]

def test_create_seckill_activity(auth_token):
    """创建抢购活动"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = requests.post(f"{BASE}/api/seckill/activities", json={
        "product_id": 1,
        "seckill_price": 1.0,
        "stock": 10,
        "start_time": "2025-06-07 10:00:00",
        "end_time": "2025-06-08 10:00:00"
    }, headers=headers)
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["stock"] == 10

def test_purchase_seckill(auth_token):
    """抢购"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = requests.post(f"{BASE}/api/seckill/purchase", json={
        "product_id": 1,
        "quantity": 1
    }, headers=headers)
    assert resp.json()["code"] == 0

def test_stock_out(auth_token):
    """库存不足"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # 先买光库存
    for _ in range(10):
        requests.post(f"{BASE}/api/seckill/purchase", json={
            "product_id": 1,
            "quantity": 1
        }, headers=headers)
    
    # 再买应该失败
    resp = requests.post(f"{BASE}/api/seckill/purchase", json={
        "product_id": 1,
        "quantity": 1
    }, headers=headers)
    assert resp.json()["message"] == "库存不足"
