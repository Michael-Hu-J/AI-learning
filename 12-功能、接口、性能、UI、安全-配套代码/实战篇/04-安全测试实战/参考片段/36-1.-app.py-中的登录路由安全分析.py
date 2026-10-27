# 第 307-340 行：登录接口
@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    return api_login()

def api_login():
    data = request.get_json()          # ← 从请求体拿JSON
    username = data.get('username')     # ← 取用户名
    password = data.get('password')     # ← 取密码
    user = authenticate_user(username, password)
    #   ↑ 调用 auth.py 的验证函数
