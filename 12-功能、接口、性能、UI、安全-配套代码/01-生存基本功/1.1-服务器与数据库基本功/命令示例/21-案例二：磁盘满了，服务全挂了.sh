# 先备份最近的 10000 行（保留错误信息）
tail -10000 /var/log/app.log > /var/log/app.log.recent

# 然后清空
> /var/log/app.log

# 磁盘空间立刻释放
df -h
# 输出：/dev/sda1  100G  60G  40G  60%  /
