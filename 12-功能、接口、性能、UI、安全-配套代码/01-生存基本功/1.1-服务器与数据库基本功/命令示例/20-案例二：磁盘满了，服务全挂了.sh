# 第一步：看看哪个分区满了
df -h

# 输出：/dev/sda1  100G  98G  2G  98%  /

# 第二步：看哪个目录占空间最大
du -sh /* | sort -rh | head -10

# 输出：
# 45G  /var
# 20G  /home
# 15G  /opt
# ...

# 第三步：继续往下找
du -sh /var/* | sort -rh | head -10

# 输出：
# 40G  /var/log

# 第四步：看看日志里谁最大
du -sh /var/log/* | sort -rh | head -10

# 输出：
# 35G  /var/log/app.log    ← 就是这个！
