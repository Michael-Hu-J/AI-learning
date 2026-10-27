"""RAG 服务包（FastAPI 版）。

目录约定：
- main.py     应用入口，只做组装
- config.py   全部配置项
- schemas.py  接口出入参
- errors.py   业务异常
- deps.py     依赖注入
- api/        HTTP 路由，只做协议转换
- services/   业务实现，不依赖 FastAPI

旧的 rag/main.py 是单文件脚本，保持原样，未被本包引用。
"""
