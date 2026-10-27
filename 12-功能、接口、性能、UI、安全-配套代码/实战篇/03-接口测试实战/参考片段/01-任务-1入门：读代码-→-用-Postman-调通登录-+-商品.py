@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    return api_login()

def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = authenticate_user(username, password)  # ← 跳转到 auth.py 第 190 行
