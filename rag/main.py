#!/usr/bin/python3
# -*- coding:utf-8 -*-

"""
基于向量数据库的检索式生成式混合查询
"""

import logging
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from typing import List

# 将文档进行切片
def split_into_chunks(doc_file: str) -> List[str]:
    with open(doc_file, "r") as file:
        content = file.read()
    return [chunk for chunk in content.split("\n\n")]

chunks = split_into_chunks("doc.md")
#
# for i, chunk in enumerate(chunks):
#     print(f"[{i}] {chunk}\n")


# 向量化
from pathlib import Path
from sentence_transformers import SentenceTransformer

# 构建指向模型目录的绝对路径
# __file__ 是当前脚本的路径，.parent 获取其所在目录
script_dir = Path(__file__).parent.resolve()
model_path = script_dir.parent / "models" / "Qwen3-Embedding-0.6B"
#
# 使用本地路径加载模型，彻底离线
embedding_model = SentenceTransformer(str(model_path))
#
# 对单个片段进行向量化
def embed_chunk(chunk: str) -> List[float]:
    embedding = embedding_model.encode(chunk)
    return embedding.tolist()

# 将所有片段向量化
embeddings = [embed_chunk(chunk) for chunk in chunks]
# print(len(embeddings))
# print(embeddings[0])



# 将向量存入向量数据库中
import chromadb

# # 创建持久化客户端，数据将保存在 ./chroma_db 目录
chromadb_client = chromadb.PersistentClient(path="./chroma_db")

# 创建或获取一个集合（类似数据表）
chromadb_collection = chromadb_client.get_or_create_collection(name="embeddings_collection")

# 保存向量到数据库
def save_embeddings(chunks: List[str], embeddings:List[List[float]]) -> None:
    ids = [str(i) for i in range(len(chunks))]
    chromadb_collection.upsert(
        documents=chunks,
        embeddings=embeddings,
        ids=ids
    )

save_embeddings(chunks, embeddings)



# 召回
def retrieve(query: str, top_k: int) -> List[str]:
    # 将问题向量化
    query_embedding = embed_chunk(query)
    # 查询与问题相似的片段
    results = chromadb_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    # print(results)
    return results["documents"][0]

query = "哆啦A梦使用的3个秘密道具是什么？"
retrieve_chunks = retrieve(query, 5)

# for i, chunk in enumerate(retrieve_chunks):
#     print(f"[{i}] {chunk}\n")




# 使用cross_encoder进行重排
from sentence_transformers import CrossEncoder

def rerank(query: str, retrieve_chunks: List[str], top_k: int) -> List[str]:
    # 创建一个cross_encoder模型
    rerank_model_path = script_dir.parent / "models" / "Qwen3-Reranker-0.6B"
    cross_encoder = CrossEncoder(str(rerank_model_path))

    # 创建一个问题+召回片段的列表
    pairs = [(query, chunk) for chunk in retrieve_chunks]

    # 给每一个召回片段打分
    scores = cross_encoder.predict(pairs)

    # 将召回的片段和对应分数存入列表
    chunk_with_score_list = [(chunk, score) for chunk, score in zip(retrieve_chunks, scores)]

    # 按分数从高到低排序
    chunk_with_score_list.sort(key=lambda pair: pair[1], reverse=True)
    # print(chunk_with_score_list)

    # 单独取出前几名的片段
    return [chunk for chunk, _ in chunk_with_score_list][:top_k]

rerank_chunks = rerank(query, retrieve_chunks, 3)

# for i, chunk in enumerate(rerank_chunks):
#     print(f"[{i}] {chunk}\n")



# 生成
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    timeout=60,
)

def generate(query: str, rerank_chunks: list[str]) -> str:
    # 1. 拼接上下文（添加分隔符，保持整洁）
    # 最佳实践：为每个 chunk 加上标识或来源信息（此处简化）[reference:2]
    context = "\n\n---\n\n".join(rerank_chunks)

    # 2. 构建系统提示词（System Prompt）—— 核心指令区
    system_prompt = (
        "你是一个严谨的问答助手。请仅根据下面提供的「上下文」来回答问题。\n"
        "【回答要求】：\n"
        "1. 在回答开头，**必须先用一句话作为引导语**，格式类似：“根据提供的片段，[关于问题的总结]分别是：”或“根据参考资料，[结论]如下：”。\n"
        "2. 紧接着，请使用**分点总结（最多不超过 3 点）**的形式列出具体答案。\n"
        "3. 必须**极其简洁**，绝对不要重复上下文中的长篇原话，请用自己的话提炼。\n"
        "4. 如果上下文中没有足够的信息，直接回答“根据已知信息无法回答”，不要输出引导语。\n\n"
        f"=== 上下文开始 ===\n{context}\n=== 上下文结束 ==="
    )

    resp = client.chat.completions.create(
        model="deepseek-chat",          # 你的 models.yaml 里用的是 deepseek-v4-pro，两者写哪个就用哪个                      # 只要一个候选结果
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.2,                # RAG 场景调低，减少发挥
        max_tokens=1024,
    )
    return resp.choices[0].message.content

answer = generate(query, rerank_chunks)
print(answer)




