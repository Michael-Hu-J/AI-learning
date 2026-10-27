# 一个简单的登录校验函数
def check_login(username, password):
    if username == "admin" and password == "123456":
        return True
    else:
        return False
