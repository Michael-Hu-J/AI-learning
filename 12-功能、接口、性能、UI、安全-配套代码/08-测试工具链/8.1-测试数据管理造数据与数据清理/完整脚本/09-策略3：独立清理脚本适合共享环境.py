# cleanup_test_data.py
import mysql.connector
import argparse

def cleanup(env, prefix, days=7):
    """清理测试数据"""
    if env == "prod":
        print("❌ 禁止在生产环境执行清理脚本！")
        return
    
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="***",
        database=f"{env}_db"
    )
    cursor = conn.cursor()
    
    # 清理 7 天前的测试数据
    tables = ["users", "orders", "order_items", "products", "seckill_activities"]
    
    for table in tables:
        cursor.execute(f"""
            DELETE FROM {table} 
            WHERE phone LIKE '{prefix}%' 
            AND created_at < DATE_SUB(NOW(), INTERVAL {days} DAY)
        """)
        print(f"✅ {table}: 清理了 {cursor.rowcount} 条")
    
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["dev", "test", "pre"])
    parser.add_argument("--prefix", default="139")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    
    cleanup(args.env, args.prefix, args.days)
