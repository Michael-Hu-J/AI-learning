mkdir ~/mall-test && cd ~/mall-test && git init
cat > check_mall.sh << 'EOF'
#!/bin/bash
echo "=== 健康检查 ==="
mysql -u root -e "SELECT COUNT(*) AS 用户数 FROM mall_test.users;"
mysql -u root -e "SELECT u.name, o.amount FROM mall_test.users u LEFT JOIN mall_test.orders o ON u.id = o.user_id;"
echo "=== 检查完成 ==="
EOF
chmod +x check_mall.sh && ./check_mall.sh
git add . && git commit -m "初始化商城检查脚本"
