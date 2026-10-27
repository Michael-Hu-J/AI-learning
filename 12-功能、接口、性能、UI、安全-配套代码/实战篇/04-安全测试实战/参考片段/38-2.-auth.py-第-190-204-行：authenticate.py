def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    #   ↑ SQLAlchemy 的 filter_by 是参数化查询
    #   → 不管 username 传什么，都会被当作参数绑定，不会拼到 SQL 里
    #   → 所以 ' OR 1=1 -- 在这里只是"用户名等于这个字符串"的查询
    
    if user and user.check_password(password):
        #   ↑ check_password 用 werkzeug.security.check_password_hash
        #   → 这是 werkzeug 提供的密码哈希校验
        #   → 它把用户输入的明文密码和存储的哈希做比对
        #   → 即使数据库泄露，黑客也拿不到明文密码
        return user
    return None
