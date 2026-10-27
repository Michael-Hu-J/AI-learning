# 1秒调100次
for i in $(seq 1 100); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"***"}' &
done
wait
# 如果全是 200，说明没有限流
# 如果中间有 429（Too Many Requests），说明有限流
