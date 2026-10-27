"""HTTP 路由层。

- documents.py  文档上传 / 列表 / 删除
- query.py      问答 / 健康检查

这一层不写业务逻辑，只负责：读参数 -> 调 pipeline -> 拼响应。
"""
