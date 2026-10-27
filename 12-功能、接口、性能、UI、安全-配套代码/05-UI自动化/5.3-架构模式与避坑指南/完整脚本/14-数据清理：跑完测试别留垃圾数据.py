# 方案 1：每次测试前清理
def setup():
    # 删除上次测试的数据
    db.execute("DELETE FROM users WHERE phone LIKE '139%'")

# 方案 2：每次测试后用唯一数据
import random
phone = f"139{random.randint(10000000, 99999999)}"
page.fill('input[name="phone"]', phone)

# 方案 3：用事务，测完回滚
# （适合数据库测试）
