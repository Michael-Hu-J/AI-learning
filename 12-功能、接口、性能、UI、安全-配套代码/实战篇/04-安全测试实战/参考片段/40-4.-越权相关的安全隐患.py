# 假设的代码（基于常见进销存系统架构）
@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(current_user, user_id):
    # current_user 来自 login_required 装饰器
    # user_id 来自 URL 参数
    
    # ⚠️ 安全隐患：没有校验 current_user.id == user_id
    # 用户 A 传 user_id=2 就能看到用户 B 的信息
    # 这就是水平越权
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'id': user.id, 'username': user.username, 'role': user.role})
