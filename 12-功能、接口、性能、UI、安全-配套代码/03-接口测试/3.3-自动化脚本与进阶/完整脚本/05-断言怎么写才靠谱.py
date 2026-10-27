response = requests.post(url, json=data, headers=headers)

# 1. 断言状态码
assert response.status_code == 200

# 2. 断言业务码
result = response.json()
assert result["code"] == 0, f"业务失败: {result.get('message')}"

# 3. 断言返回数据
assert result["data"]["orderId"] > 0, "orderId 应该大于 0"
assert result["data"]["status"] == "created", f"状态应该是 created，实际是 {result['data']['status']}"

# 4. 断言数据库（可选，但很有价值）
# 查数据库确认订单真的创建了
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='', database='mall_test')
cursor = conn.cursor()
cursor.execute("SELECT status FROM orders WHERE id = %s", result["data"]["orderId"])
db_status = cursor.fetchone()[0]
assert db_status == "created", f"数据库状态应该是 created，实际是 {db_status}"
cursor.close()
conn.close()
