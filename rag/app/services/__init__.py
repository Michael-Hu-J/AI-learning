"""RAG 各功能模块。

数据流：
    loader -> chunker -> embedder -> vector_store        （导入）
    embedder -> vector_store -> reranker -> generator    （问答）

pipeline.py 负责把上面两条链路串起来，其余模块彼此尽量不感知对方。
"""
