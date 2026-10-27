def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):  # ← 用 werkzeug 的 check_password_hash 验证
        return user
    return None
