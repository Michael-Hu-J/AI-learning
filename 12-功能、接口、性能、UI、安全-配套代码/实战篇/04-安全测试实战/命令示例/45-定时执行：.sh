crontab -e
# 每天 9:00 跑安全巡检
0 9 * * * cd /path/to/project && python3 security_patrol.py
