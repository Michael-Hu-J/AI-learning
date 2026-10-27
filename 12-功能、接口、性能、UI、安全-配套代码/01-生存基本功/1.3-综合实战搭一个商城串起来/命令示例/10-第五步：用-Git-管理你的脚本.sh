# 创建一个项目目录
mkdir ~/mall-test
cd ~/mall-test

# 初始化 Git
git init

# 创建一个测试脚本
cat > test_mall.sh << 'EOF'
#!/bin/bash
# 商城测试脚本

echo "=== 测试开始 ==="

# 1. 检查数据库连接
echo "1. 检查数据库..."
mysql -u root -e "SELECT COUNT(*) FROM mall_test.users;" 

# 2. 检查订单数据
echo "2. 检查订单..."
mysql -u root -e "SELECT * FROM mall_test.orders;"

# 3. 检查日志
echo "3. 检查日志..."
if [ -f /var/log/mall/order-service.log ]; then
    echo "日志文件存在"
    grep "ERROR" /var/log/mall/order-service.log || echo "没有错误日志"
else
    echo "日志文件不存在"
fi

echo "=== 测试完成 ==="
EOF

# 加执行权限
chmod +x test_mall.sh

# 运行
./test_mall.sh

# 提交到 Git
git add .
git commit -m "初始化商城测试脚本"
