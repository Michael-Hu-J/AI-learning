"""全局配置。

设计要点：
1. 所有可变参数（路径、模型名、切片大小、top_k 等）集中在这里，其他模块不出现硬编码；
2. 使用 pydantic-settings，字段既可以被环境变量覆盖，也可以写在 .env 里；
   环境变量名 = 字段名大写，例如 `deepseek_api_key` -> `DEEPSEEK_API_KEY`；
3. 路径全部基于本文件位置推导，因此从任何目录启动服务都能找到模型和向量库
   （旧版 main.py 用的是相对路径，必须 cd 到 rag/ 才能跑）。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# __file__ 是 rag/app/config.py
# parents[0] = rag/app，parents[1] = rag，parents[2] = 项目根目录
RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RAG_DIR.parent


class Settings(BaseSettings):
    # env_file 给出候选文件，靠前的优先；extra="ignore" 表示 .env 里有多余键也不报错
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", RAG_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 文件与向量库 ----------
    # 原始文件落盘目录：上传后按 doc_id 命名保存，方便排查解析问题
    upload_dir: Path = RAG_DIR / "data" / "uploads"
    # Chroma 持久化目录
    chroma_dir: Path = RAG_DIR / "chroma_db"
    # 与旧脚本的 collection 隔离，避免继承它原有的 L2 索引设置
    # （Chroma 的 distance 空间在建库时就固定了，改 cosine 必须换 collection）
    collection_name: str = "rag_chunks_v1"
    # 上传大小上限（MB），超出返回 413
    max_upload_mb: int = 20

    # ---------- 切片 ----------
    # 单个切片的最大字符数。太小会切断语义，太大会稀释向量、降低召回精度
    chunk_max_chars: int = 500
    # 相邻切片的重叠字符数，用于避免答案正好被切在两个块的交界处
    chunk_overlap: int = 50

    # ---------- 本地模型 ----------
    # 向量模型：Qwen3-Embedding-0.6B，本地目录（不是 HuggingFace 仓库名）
    embedding_model_path: Path = PROJECT_ROOT / "models" / "Qwen3-Embedding-0.6B"
    # 重排模型：Qwen3-Reranker-0.6B
    reranker_model_path: Path = PROJECT_ROOT / "models" / "Qwen3-Reranker-0.6B"
    # 向量化时的批大小，显存/内存紧张可调小
    embed_batch_size: int = 16

    # ---------- 检索与重排 ----------
    # 第一阶段向量召回条数（粗排），交给重排去挑
    top_k: int = 10
    # 最终送给大模型的片段数（精排后）
    top_n: int = 3
    # 重排默认关闭：先前排查时 Qwen3-Reranker 的分数被怀疑不可靠，
    # 先用纯向量检索跑通主链路，确认稳定后再通过 ENABLE_RERANK=true 打开
    enable_rerank: bool = False

    # ---------- 生成（DeepSeek，OpenAI 兼容接口） ----------
    # 未配置时服务仍可启动，但 /query 会返回 502
    deepseek_api_key: str | None = None
    # DeepSeek 兼容 OpenAI 协议，改 base_url 即可复用 openai SDK
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    # 通用对话模型；推理模型可用 deepseek-reasoner（但不支持 temperature）
    deepseek_model: str = "deepseek-chat"
    # RAG 场景调低温度，减少模型自由发挥
    deepseek_temperature: float = 0.2
    # 答案长度上限（token）
    deepseek_max_tokens: int = 1024
    # 单次请求超时（秒），超时会抛 GenerationError -> 502
    deepseek_timeout: float = 60.0

    def ensure_dirs(self) -> None:
        """创建运行期需要写入的目录；exist_ok=True 保证重复调用安全。"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


# 模块级单例：整个进程共用一份配置（读取 .env 只发生一次）
settings = Settings()
