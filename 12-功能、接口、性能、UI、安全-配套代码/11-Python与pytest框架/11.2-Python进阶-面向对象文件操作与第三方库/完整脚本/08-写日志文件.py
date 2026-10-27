from datetime import datetime

def write_log(message, level="INFO"):
    """写入日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("test_run.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")

# 使用
write_log("开始测试登录功能")
write_log("admin 登录成功", "INFO")
write_log("admin 登录失败：密码错误", "WARN")
write_log("连接数据库失败", "ERROR")
