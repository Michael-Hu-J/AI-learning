import mysql.connector

conn = mysql.connector.connect(host="localhost", user="root", password="***", database="test_db")
conn.autocommit = False  # 关闭自动提交

try:
    cursor = conn.cursor()
    
    # 造数据
    cursor.execute("INSERT INTO users (name, phone) VALUES ('事务测试', '13900000001')")
    user_id = cursor.lastrowid
    
    # 测试...
    # assert ...
    
    # 回滚（数据不会真正写入）
    conn.rollback()
    print("✅ 测试完成，数据已回滚")
    
except Exception as e:
    conn.rollback()
    print(f"❌ 测试失败，数据已回滚: {e}")
