#!/bin/bash
# 测试登录接口限流
for i in $(seq 1 30); do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://test-api.example.com/api/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Test1234"}')
  echo "请求 #$i → HTTP $HTTP_CODE"
  sleep 0.1
done
