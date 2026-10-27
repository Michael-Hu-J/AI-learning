# 1. 这是 CI 环境常见问题，等几分钟重试就行
# 2. 如果一直失败，加长 health-retries
options: >-
  --health-cmd="mysqladmin ping"
  --health-interval=10s
  --health-timeout=5s
  --health-retries=10

# 3. 或者换用低版本 MySQL
# image: mysql:5.7 有时候比 8.0 启动快
