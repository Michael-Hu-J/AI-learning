import pytest
import requests
import pymysql

BASE_URL = "http://test-api.example.com"
TOKEN = "your_token_here"

def get_db_connection():
    return pymysql.connect(
        host='localhost', user='root', password='', database='mall_test'
    )

class TestOrderCreate:
    
    @pytest.mark.parametrize("user_id,items,address_id,expected_code,expected_status", [
        # 正常场景
        (100, [{"productId": 12345, "quantity": 1}], 56, 0, "created"),
        # 边界值
        (1, [{"productId": 1, "quantity": 1}], 1, 0, "created"),  # 最小值
        (99999, [{"productId": 99999, "quantity": 99}], 999, 0, "created"),  # 较大值
        # 异常场景
        (0, [{"productId": 12345, "quantity": 1}], 56, 1002, "用户不存在"),  # userId=0
        (100, [], 56, 1001, "参数错误"),  # items 为空
        (100, [{"productId": 12345, "quantity": 0}], 56, 1001, "参数错误"),  # quantity=0
        (100, [{"productId": 12345, "quantity": -1}], 56, 1001, "参数错误"),  # quantity=-1
    ])
    def test_create_order(self, user_id, items, address_id, expected_code, expected_status):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}"
        }
        data = {
            "userId": user_id,
            "items": items,
            "addressId": address_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/order/create",
            json=data,
            headers=headers
        )
        
        # 断言状态码
        assert response.status_code == 200
        
        # 断言业务码
        result = response.json()
        assert result["code"] == expected_code, f"预期 code={expected_code}，实际 code={result['code']}"
        
        if expected_code == 0:
            # 断言返回数据
            assert result["data"]["orderId"] > 0
            assert result["data"]["status"] == expected_status
            
            # 断言数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM orders WHERE id = %s",
                result["data"]["orderId"]
            )
            db_status = cursor.fetchone()[0]
            assert db_status == expected_status
            cursor.close()
            conn.close()
        else:
            # 断言错误信息
            assert expected_status in result.get("message", "")
