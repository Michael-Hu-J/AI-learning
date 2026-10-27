def hybrid_search(query, weight_keyword=0.3, weight_vector=0.7):
    keyword_results = keyword_search(query)   # BM25，分数需归一化到 [0,1]
    vector_results = vector_search(query)     # 向量，分数需归一化到 [0,1]
    combined = {}
    for doc, score in keyword_results:
        combined[doc.id] = combined.get(doc.id, 0) + score * weight_keyword
    for doc, score in vector_results:
        combined[doc.id] = combined.get(doc.id, 0) + score * weight_vector
    return sorted(combined.items(), key=lambda x: -x[1])

from rank_bm25 import BM25Okapi
import jieba
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class HybridSearch:
    """混合检索：BM25 + 向量检索 + RRF融合"""
    
    def __init__(self, documents, embedding_model='BAAI/bge-small-zh'):
        self.documents = documents
        # BM25初始化——中文需要分词
        tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        # 向量模型初始化
        self.embedding_model = SentenceTransformer(embedding_model)
        self.doc_embeddings = self.embedding_model.encode(
            documents, normalize_embeddings=True
        )
    
    def search(self, query, top_k=5, rrf_k=10, bm25_weight=0.5, vector_weight=0.5):
        # 1. BM25检索
        query_tokens = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_ranked = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)
        bm25_top = bm25_ranked[:top_k * 3]
        
        # 2. 向量检索
        query_embedding = self.embedding_model.encode([query], normalize_embeddings=True)
        vector_scores = cosine_similarity(query_embedding, self.doc_embeddings)[0]
        vector_ranked = sorted(enumerate(vector_scores), key=lambda x: x[1], reverse=True)
        vector_top = vector_ranked[:top_k * 3]
        
        # 3. RRF融合
        rrf_scores = {}
        for rank, (doc_idx, _) in enumerate(bm25_top):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + bm25_weight / (rank + rrf_k)
        for rank, (doc_idx, _) in enumerate(vector_top):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + vector_weight / (rank + rrf_k)
        
        # 4. 排序返回
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return [(self.documents[idx], score) for idx, score in ranked[:top_k]]

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import EnsembleRetriever

# 构建BM25检索器
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 10

# 构建向量检索器
embeddings = HuggingFaceEmbeddings(model_name='BAAI/bge-large-zh-v1.5')
vectorstore = FAISS.from_documents(documents, embeddings)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

# 混合检索
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5],
)

# 检索
results = ensemble_retriever.invoke("理财产品风险等级")

from elasticsearch import Elasticsearch

es = Elasticsearch(["http://localhost:9200"])

# 创建索引（同时支持BM25和向量）
index_config = {
    "mappings": {
        "properties": {
            "title": {"type": "text", "analyzer": "ik_max_word"},
            "content": {"type": "text", "analyzer": "ik_max_word"},
            "embedding": {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"}
        }
    }
}
es.indices.create(index="knowledge_base", body=index_config)

# 混合检索查询
def hybrid_search(query, top_k=10):
    embedding = embedding_model.encode(query).tolist()
    body = {
        "query": {
            "bool": {
                "should": [
                    {"multi_match": {"query": query, "fields": ["title^3", "content"], "type": "best_fields"}},
                    {"knn": {"field": "embedding", "query_vector": embedding, "k": top_k, "num_candidates": 100}}
                ]
            }
        },
        "size": top_k
    }
    return es.search(index="knowledge_base", body=body)["hits"]["hits"]

from rank_bm25 import BM25Okapi
import numpy as np
from typing import List, Tuple

class HybridSearchWeighted:
    def __init__(self, documents: List[str], embeddings, vector_db):
        self.documents = documents
        self.embeddings = embeddings
        self.vector_db = vector_db
        tokenized_docs = [doc.split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def search(self, query: str, k: int = 10,
               weight_keyword: float = 0.3, weight_vector: float = 0.7) -> List[Tuple]:
        tokenized_query = query.split()
        keyword_scores = self.bm25.get_scores(tokenized_query)
        keyword_ranked = np.argsort(keyword_scores)[::-1][:k]

        query_embedding = self.embeddings.embed_query(query)
        vector_results = self.vector_db.similarity_search_with_score(query, k=k)

        combined_scores = {}
        for idx in keyword_ranked:
            combined_scores[idx] = keyword_scores[idx] * weight_keyword
        for doc, score in vector_results:
            doc_idx = self.documents.index(doc.page_content)
            combined_scores[doc_idx] = combined_scores.get(doc_idx, 0) + score * weight_vector

        ranked = sorted(combined_scores.items(), key=lambda x: -x[1])
        return ranked[:k]

# 使用：hybrid.search("MacBook Pro 2024", k=5, weight_keyword=0.4, weight_vector=0.6)

def test_hybrid_search(search_engine, test_data):
    """
    test_data: [
        {"query": "产品型号A-100", "type": "exact", "expected": "A-100"},
        {"query": "类似功能的商品", "type": "semantic", "expected": ["推荐", "替代"]}
    ]
    """
    results = {"exact": 0, "semantic": 0, "total_exact": 0, "total_semantic": 0}

    for item in test_data:
        hits = search_engine.search(item["query"])
        hit_texts = " ".join(h.text for h in hits)

        if item["type"] == "exact":
            results["total_exact"] += 1
            if item["expected"] in hit_texts:
                results["exact"] += 1
        elif item["type"] == "semantic":
            results["total_semantic"] += 1
            if any(kw in hit_texts for kw in item["expected"]):
                results["semantic"] += 1

    return {
        "exact_recall": results["exact"] / max(results["total_exact"], 1),
        "semantic_recall": results["semantic"] / max(results["total_semantic"], 1),
    }
