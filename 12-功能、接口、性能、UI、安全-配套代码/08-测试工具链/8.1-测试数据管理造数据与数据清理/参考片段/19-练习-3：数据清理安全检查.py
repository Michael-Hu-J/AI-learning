# ❌ 危险代码——不加 WHERE
cursor.execute("DELETE FROM users")

# ✅ 安全代码——加 WHERE
phone_prefix = "139"
cursor.execute("SELECT COUNT(*) FROM users WHERE phone LIKE %s", (phone_prefix + '%',))
count = cursor.fetchone()[0]
print(f"将删除 {count} 条数据")
confirm = input("确认删除？(y/n): ")
if confirm.lower() == 'y':
    cursor.execute("DELETE FROM users WHERE phone LIKE %s", (phone_prefix + '%',))
    print("✅ 清理完成")
else:
    print("取消操作")
