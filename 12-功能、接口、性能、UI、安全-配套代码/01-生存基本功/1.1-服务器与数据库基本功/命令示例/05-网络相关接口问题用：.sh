# 看能不能连上某个服务器
ping 192.168.1.100

# 看某个接口能不能通
curl http://localhost:8080/api/health

# 看接口返回什么（带详细信息）
curl -v http://localhost:8080/api/health
