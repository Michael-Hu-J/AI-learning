# 正确做法：清空文件内容，文件还在，进程不会断
> /var/log/app.log

# 或者
cat /dev/null > /var/log/app.log
