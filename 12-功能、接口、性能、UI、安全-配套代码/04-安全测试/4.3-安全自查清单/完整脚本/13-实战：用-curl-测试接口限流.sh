#!/bin/bash
# 测试登录接口是否有限流保护

URL="http://test.example.com/api/login"
DATA='{"username":"admin","password":"wrong"}'

for i in $(seq 1 30); do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "$DATA")
  echo "请求 #$i → HTTP $HTTP_CODE"
  sleep 0.05  # 50ms 间隔，模拟快速请求
done
