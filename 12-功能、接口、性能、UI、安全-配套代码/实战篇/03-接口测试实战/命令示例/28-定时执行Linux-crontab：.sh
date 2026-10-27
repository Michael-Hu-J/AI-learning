# 每天 9:00 跑一次
crontab -e
# 添加：
0 9 * * * cd /path/to/project && python3 seckill_health_check.py
