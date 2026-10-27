def verify_token(token):
    try:
        payload = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        #   ↑ PyJWT 库解码 Token
        #   → 如果 Token 被篡改（改一个字符），decode 会抛出 InvalidTokenError
        #   → 第 49 行捕获异常返回 None
        #   → 所以前端改了 Token 调接口会返回 401
        
        return User.query.get(payload['user_id'])
        #   ↑ 从 Token 的 payload 里拿 user_id 查用户
        #   → 这里有个问题：如果 Token 是之前签发但用户已被删除的
        #   → User.query.get() 返回 None，verify_token 最终返回 None
        #   → 接口会返回 401
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        #   ↑ 从请求头拿 Token，去掉 Bearer 前缀
        #   ⚠️ 如果没传 Authorization 头，token = ''
        #   → jwt.decode('', SECRET_KEY, ...) 会抛异常
        
        current_user = verify_token(token)
        if not current_user:
            return jsonify({'error': '未授权，请先登录'}), 401
        return f(current_user, *args, **kwargs)
    return decorated_function
