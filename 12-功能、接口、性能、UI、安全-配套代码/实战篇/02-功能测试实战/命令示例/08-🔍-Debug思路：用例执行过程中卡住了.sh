# 1. 先确认环境状态
curl http://localhost:5000
# 如果返回 Connection refused，说明服务没启动

# 2. 检查 Docker 容器
docker ps | grep seckill
# 如果容器没在运行，重新启动

# 3. 如果环境没问题，那就是 Bug，提 Bug
# 标题：[环境] 登录页面返回500
