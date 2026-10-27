"""
第 14 节 — 接口 + 数据库校验示例

- test_create_product_then_list：仅 HTTP，无数据库依赖（默认可跑）
- test_create_product_row_in_mysql：需配置 TEST_DB_* 且安装 pymysql

环境变量（MySQL 校验可选）:
  TEST_BASE_URL          默认 http://127.0.0.1:5000
  TEST_ADMIN_PASSWORD    默认 admin123
  TEST_DB_HOST / TEST_DB_PORT / TEST_DB_USER / TEST_DB_PASSWORD / TEST_DB_NAME
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

DB_CONFIGURED = all(
    os.getenv(k)
    for k in (
        "TEST_DB_HOST",
        "TEST_DB_USER",
        "TEST_DB_PASSWORD",
        "TEST_DB_NAME",
    )
)


@pytest.fixture(scope="module")
def admin_token():
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        pytest.skip(f"无法登录演示系统: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        pytest.skip("登录响应中无 token 字段")
    return token


def test_create_product_then_list(admin_token):
    """创建商品后，通过列表 API 能查到（不依赖数据库）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    unique_name = f"db_check_{uuid.uuid4().hex[:8]}"
    create = requests.post(
        f"{BASE_URL}/api/products",
        headers=headers,
        json={
            "name": unique_name,
            "description": "第14节接口+落库验证示例",
            "price": 12.34,
            "stock": 3,
        },
        timeout=10,
    )
    assert create.status_code in (200, 201), create.text

    listed = requests.get(f"{BASE_URL}/api/products", headers=headers, timeout=10)
    assert listed.status_code == 200
    products = listed.json()
    if isinstance(products, dict):
        products = products.get("data") or products.get("items") or products.get("products") or []
    names = {p.get("name") for p in products if isinstance(p, dict)}
    assert unique_name in names, f"列表中未找到新建商品: {unique_name}"


@pytest.mark.skipif(not DB_CONFIGURED, reason="未配置 TEST_DB_*，跳过 MySQL 直连校验")
def test_create_product_row_in_mysql(admin_token):
    """创建商品后，在 products 表中能查到对应行（需 MySQL 环境）。"""
    pymysql = pytest.importorskip("pymysql")

    headers = {"Authorization": f"Bearer {admin_token}"}
    unique_name = f"mysql_check_{uuid.uuid4().hex[:8]}"
    create = requests.post(
        f"{BASE_URL}/api/products",
        headers=headers,
        json={"name": unique_name, "price": 9.9, "stock": 1},
        timeout=10,
    )
    assert create.status_code in (200, 201)
    body = create.json()
    product_id = body.get("id") or (body.get("data") or {}).get("id")
    assert product_id, "创建响应需包含商品 id"

    time.sleep(0.3)  # 给异步写库留一点时间（若存在）

    conn = pymysql.connect(
        host=os.environ["TEST_DB_HOST"],
        port=int(os.getenv("TEST_DB_PORT", "3306")),
        user=os.environ["TEST_DB_USER"],
        password=os.environ["TEST_DB_PASSWORD"],
        database=os.environ["TEST_DB_NAME"],
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name FROM products WHERE id = %s",
                (product_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None, f"MySQL 中未找到 id={product_id}"
    assert row[1] == unique_name
