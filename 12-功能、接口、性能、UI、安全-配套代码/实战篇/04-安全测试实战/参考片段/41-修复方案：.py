@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(current_user, user_id):
    # 修复：只有 admin 可以查其他用户，普通用户只能查自己
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'error': '无权限查看该用户信息'}), 403
    # ... 继续业务逻辑
