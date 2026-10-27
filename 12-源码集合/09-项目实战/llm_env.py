"""共享 LLM 环境配置 — 与 ai-test-kit 使用相同的 DashScope 兼容模式"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_ENV_LOADED = False
PROJECT_ROOT = Path(__file__).resolve().parent


def load_env():
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if not load_dotenv:
        _ENV_LOADED = True
        return
    for path in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
        if path.exists():
            load_dotenv(path)
            break
    _ENV_LOADED = True


def get_api_key() -> str:
    load_env()
    return os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")


def get_base_url() -> str:
    load_env()
    return os.getenv(
        "OPENAI_BASE_URL",
        os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )


def get_llm_model(default: str = "qwen-plus") -> str:
    load_env()
    return os.getenv("LLM_MODEL", default)


def get_embedding_model(default: str = "text-embedding-v2") -> str:
    load_env()
    return os.getenv("EMBEDDING_MODEL", default)


def has_api_key() -> bool:
    return bool(get_api_key())


def create_chat_openai(model: str = None, temperature: float = None):
    from langchain_openai import ChatOpenAI

    load_env()
    model = model or get_llm_model()
    api_key = get_api_key()
    base_url = get_base_url()
    extra = {"temperature": temperature} if temperature is not None else {}
    try:
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            **extra,
        )
    except TypeError:
        return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, **extra)


def create_openai_embeddings(model: str = None):
    load_env()
    base_url = get_base_url()
    if "dashscope" in base_url:
        return create_dashscope_embeddings(model=model)
    from langchain_openai import OpenAIEmbeddings

    model = model or get_embedding_model()
    api_key = get_api_key()
    try:
        return OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
        )
    except TypeError:
        return OpenAIEmbeddings(model=model, api_key=api_key, base_url=base_url)


class DashScopeEmbeddings:
    """DashScope 原生 Embedding API（兼容 langchain 向量库接口）"""

    def __init__(self, model: str = None, dimension: int = 1536):
        self.model = model or get_embedding_model()
        self.dimension = dimension

    def _normalize(self, text: str) -> str:
        if not text or not str(text).strip():
            return " "
        return str(text).strip()

    def _call_batch(self, texts: list) -> list:
        import dashscope

        load_env()
        dashscope.api_key = get_api_key()
        texts = [self._normalize(t) for t in texts]
        results = []
        batch_size = 25
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = dashscope.TextEmbedding.call(
                model=self.model,
                input=batch,
                dimension=self.dimension,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"DashScope embedding 失败: {getattr(response, 'code', '')} - {getattr(response, 'message', response)}"
                )
            output = response.output
            if isinstance(output, dict):
                items = output.get("embeddings", [])
                for item in items:
                    results.append(item["embedding"] if isinstance(item, dict) else item.embedding)
            else:
                for item in output.embeddings:
                    results.append(item.embedding)
        return results

    def embed_documents(self, texts: list) -> list:
        if not texts:
            return []
        return self._call_batch(texts)

    def embed_query(self, text: str) -> list:
        return self.embed_documents([text])[0]


def create_dashscope_embeddings(model: str = None):
    return DashScopeEmbeddings(model=model)


def get_autogen_llm_config(temperature: float = 0.1) -> dict:
    load_env()
    return {
        "config_list": [{
            "model": get_llm_model(),
            "api_key": get_api_key(),
            "base_url": get_base_url(),
        }],
        "temperature": temperature,
    }
