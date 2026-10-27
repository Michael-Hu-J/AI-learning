# 看某个进程在不在
ps aux | grep java

# 看某个端口被谁占了（比如 8080）
netstat -tlnp | grep 8080

# 或者用这个（新版 Linux）
ss -tlnp | grep 8080

# 看某个进程打开了哪些文件
lsof -p 12345
