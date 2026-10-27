#!/bin/bash
# security_audit.sh — 10项安全自查自动化
BASE="http://localhost:5000"
TOKEN=""  # 先手动登录拿 Token

echo "===== 安全自查报告 ====="
echo "时间: $(date)"
echo ""

# 1. SQL注入
RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'"'"' OR 1=1 --", "password": "***"}')
echo "1. SQL注入: $([ "$RESULT" = "401" ] && echo "✅ 安全" || echo "❌ 有漏洞")"

# 2. XSS
RESULT=$(curl -s "$BASE/products?q=<script>alert(1)</script>" | grep -c "alert")
echo "2. XSS: $([ "$RESULT" -eq 0 ] && echo "✅ 安全" || echo "❌ 有漏洞")"

# 3. 敏感数据泄露
RESULT=$(curl -s -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}' | grep -c "password")
echo "3. 敏感数据泄露: $([ "$RESULT" -eq 0 ] && echo "✅ 安全" || echo "❌ 泄露")"

# ... 继续其他检查项
echo "===== 检查完成 ====="
