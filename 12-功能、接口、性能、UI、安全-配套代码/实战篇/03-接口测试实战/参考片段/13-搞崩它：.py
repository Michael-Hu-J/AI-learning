# 7. 在 Reqable 里找到 /api/seckill/order 的请求
# 看 Request headers：没有 Authorization
# 看 Response：401, {"error": "未授权，请先登录"}
# 结论：前端没处理未登录状态的交互逻辑

# 8. 改 Reqable 的断点，强行加一个假 Token
# Request header 加：
# Authorization: Bearer fake_token_123
# 响应：401, {"error": "未授权，请先登录", "detail": "Token无效或已过期"}
# 源码：auth.py 第 43-49 行，verify_token() 捕获 InvalidTokenError 返回 None
