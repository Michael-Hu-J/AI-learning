# ❌ 危险
cursor.execute("DELETE FROM users")

# ✅ 安全
cursor.execute("DELETE FROM users WHERE phone LIKE '139%'")

# ✅ 更安全：先 SELECT 确认
cursor.execute("SELECT COUNT(*) FROM users WHERE phone LIKE '139%'")
count = cursor.fetchone()[0]
print(f"将删除 {count} 条数据")
cursor.execute("DELETE FROM users WHERE phone LIKE '139%'")
