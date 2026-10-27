# 看目录内容
ls -la

# 看文件内容（只适合小文件）
cat app.log

# 打开大文件，可以翻页看
less app.log

# 复制文件
cp app.log app.log.bak

# 移动文件
mv app.log /backup/

# ⚠️ 高危操作，严禁在生产环境执行
rm app.log

# 创建目录
mkdir test-data
