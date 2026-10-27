# 1. 创建一个本地 JSON 文件（模拟接口返回）
cat > mock_order.json << 'EOF'
{
  "code": 0,
  "data": {
    "orderId": 99999,
    "status": "created",
    "amount": 199.00
  },
  "message": "success"
}
EOF

# 2. 查看文件内容
cat mock_order.json
