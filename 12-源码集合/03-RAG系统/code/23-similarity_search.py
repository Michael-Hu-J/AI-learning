# 用相同 test_data 横向对比召回率（完整版见 §5.1 compare_models）
candidate_models = [
    "text-embedding-ada-002",   # OpenAI，中文慎用
    "text-embedding-v3",        # 通义等国产 API
    "paraphrase-multilingual",  # 多语言
    "BAAI/bge-base-zh",         # 中文首选之一
]
for model_name in candidate_models:
    metrics = test_retrieval(model_name, test_data)  # 返回 recall / mrr 等
    print(f"{model_name}: 召回率 {metrics.recall:.2f}, MRR {metrics.mrr:.2f}")

# 最容易被忽略、见效最快的优化之一
results = vectorstore.similarity_search_with_score(query, k=10)
filtered = [doc for doc, score in results if score > 0.5]  # 阈值随模型分布调整，bge 常用 0.6~0.7

def optimized_search(query, vectorstore, threshold=0.65, final_k=3):
    """
    1. 多取候选（k=10）供 rerank
    2. 阈值过滤低分噪声
    3. LLM/Cross-Encoder rerank 后取 top
    """
    results = vectorstore.similarity_search_with_score(query, k=10)
    filtered = [(doc, score) for doc, score in results if score > threshold]
    if not filtered:
        return []
    reranked = rerank_by_llm(query, [doc for doc, _ in filtered])  # 或 Cross-Encoder
    return reranked[:final_k]

results = vectorstore.max_marginal_relevance_search(
    query,
    k=5,
    fetch_k=20,       # 先检索 20 条
    lambda_mult=0.7,  # 相关性为主；探索型场景可降到 0.5~0.6
)

def evaluate_search(vectorstore, test_data, k=10):
    """
    test_data: [{"query": "...", "relevant_docs": [id, ...]}]
    """
    total_recall, total_mrr = 0.0, 0.0
    for item in test_data:
        results = vectorstore.similarity_search(item["query"], k=k)
        result_ids = [doc.metadata.get("id") for doc in results]
        relevant = set(item["relevant_docs"])
        found = relevant & set(result_ids)
        total_recall += len(found) / max(len(relevant), 1)
        for rank, doc_id in enumerate(result_ids, 1):
            if doc_id in relevant:
                total_mrr += 1.0 / rank
                break
    n = len(test_data)
    return {"recall": total_recall / n, "mrr": total_mrr / n}

from sentence_transformers import SentenceTransformer
import numpy as np

def compare_models(documents, queries, relevant_docs, top_k=5):
    models = {
        'bge-small-zh': SentenceTransformer('BAAI/bge-small-zh'),
        'bge-base-zh': SentenceTransformer('BAAI/bge-base-zh'),
        'bge-m3': SentenceTransformer('BAAI/bge-m3'),
        'm3e-base': SentenceTransformer('moka-ai/m3e-base'),
    }
    results = {}
    for name, model in models.items():
        doc_embs = model.encode(documents, normalize_embeddings=True)
        query_embs = model.encode(queries, normalize_embeddings=True)
        recalls, precisions, mrrs = [], [], []
        for qi in range(len(queries)):
            sims = np.dot(doc_embs, query_embs[qi])
            top_idx = np.argsort(sims)[-top_k:][::-1]
            hit = len(set(top_idx) & set(relevant_docs[qi]))
            recalls.append(hit / max(len(relevant_docs[qi]), 1))
            precisions.append(hit / top_k)
            for r, idx in enumerate(top_idx, 1):
                if idx in relevant_docs[qi]:
                    mrrs.append(1.0 / r); break
            else:
                mrrs.append(0.0)
        results[name] = {
            'recall@5': round(np.mean(recalls), 4),
            'precision@5': round(np.mean(precisions), 4),
            'MRR': round(np.mean(mrrs), 4),
        }
    return results

def tune_top_k_and_threshold(doc_embs, query_embs, relevant_docs,
                              k_values=[3, 5, 10, 15, 20],
                              thresholds=[0.5, 0.6, 0.7, 0.8, 0.9]):
    """联合调优top_k和相似度阈值"""
    results = {}
    
    for k in k_values:
        for th in thresholds:
            recalls, precisions = [], []
            
            for qi in range(len(query_embs)):
                similarities = np.dot(doc_embs, query_embs[qi])
                # 先过滤阈值，再取top_k
                above_threshold = np.where(similarities >= th)[0]
                top_k_indices = above_threshold[np.argsort(similarities[above_threshold])[-k:][::-1]]
                
                hit = len(set(top_k_indices) & set(relevant_docs[qi]))
                recalls.append(hit / max(len(relevant_docs[qi]), 1))
                precisions.append(hit / max(len(top_k_indices), 1))
            
            results[f"k={k}_th={th}"] = {
                'recall': round(np.mean(recalls), 4),
                'precision': round(np.mean(precisions), 4),
            }
    
    return results

from sklearn.metrics.pairwise import cosine_similarity

def mmr_search(query_emb, doc_embs, documents, top_k=5, lambda_param=0.7):
    query_sim = cosine_similarity(query_emb, doc_embs)[0]
    selected, candidates = [], list(range(len(documents)))
    
    for _ in range(top_k):
        if not candidates: break
        best_score, best_idx = -float('inf'), -1
        for idx in candidates:
            rel = query_sim[idx]
            penalty = max(cosine_similarity(doc_embs[idx:idx+1], doc_embs[selected])[0]) if selected else 0
            score = lambda_param * rel - (1 - lambda_param) * penalty
            if score > best_score:
                best_score, best_idx = score, idx
        selected.append(best_idx)
        candidates.remove(best_idx)
    return [documents[i] for i in selected]

from rank_bm25 import BM25Okapi
import jieba, numpy as np
from sentence_transformers import SentenceTransformer

def hybrid_search(documents, queries, top_k=5, alpha=0.7):
    model = SentenceTransformer('BAAI/bge-base-zh')
    tokenized_docs = [list(jieba.cut(d)) for d in documents]
    bm25 = BM25Okapi(tokenized_docs)
    doc_embs = model.encode(documents, normalize_embeddings=True)
    
    results = {}
    for query in queries:
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        vec_scores = np.dot(doc_embs, q_emb)
        bm25_scores = bm25.get_scores(list(jieba.cut(query)))
        # 归一化后加权融合
        v = (vec_scores - vec_scores.min()) / (vec_scores.max() - vec_scores.min() + 1e-10)
        b = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-10)
        final = alpha * v + (1 - alpha) * b
        top_idx = np.argsort(final)[-top_k:][::-1]
        results[query] = [documents[i] for i in top_idx]
    return results

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-zh")
vectorstore = FAISS.from_texts(documents, embeddings)
vector_retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})
bm25_retriever = BM25Retriever.from_texts(documents)
bm25_retriever.k = 10

ensemble = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.7, 0.3]
)
results = ensemble.invoke("违约责任条款")

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ef = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-base-zh")
client = chromadb.Client()
collection = client.create_collection(name="contracts", embedding_function=ef)
collection.add(documents=documents, ids=[str(i) for i in range(len(documents))])
results = collection.query(query_texts=["违约责任条款"], n_results=5)
