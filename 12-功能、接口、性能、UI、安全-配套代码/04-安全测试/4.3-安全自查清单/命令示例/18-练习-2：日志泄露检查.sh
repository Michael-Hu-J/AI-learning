# 查日志里有没有敏感信息
grep -E "(身份证|手机号|密码|银行卡|IDCard|phone|password)" /var/log/app.log --ignore-case
