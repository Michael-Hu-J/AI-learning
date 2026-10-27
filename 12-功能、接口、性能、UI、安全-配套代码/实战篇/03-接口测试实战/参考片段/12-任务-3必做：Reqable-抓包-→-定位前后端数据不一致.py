@app.route('/seckill')
def seckill_page():
    """抢购页面"""
    # 不强制登录，让前端处理
    return render_template('seckill.html')
