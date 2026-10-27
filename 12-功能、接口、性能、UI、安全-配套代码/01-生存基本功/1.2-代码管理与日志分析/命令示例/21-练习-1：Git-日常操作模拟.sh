# 1️⃣ 克隆项目
git clone https://github.com/xxx/mall-test.git

# 2️⃣ 创建功能分支
git checkout -b feature/order-test

# 3️⃣ 修改脚本（假设你改了一个文件）
echo "# 新增订单测试" >> test_order.py

# 4️⃣ 提交
git add test_order.py
git commit -m "新增订单接口自动化测试"

# 5️⃣ 推送
git push origin feature/order-test

# 6️⃣ 切回主分支拉最新代码
git checkout main
git pull
