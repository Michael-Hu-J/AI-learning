from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", " ", ""],
)
chunks = splitter.split_documents(documents)

results = vector_db.similarity_search(
    query,
    k=10,
    filter={"category": "基金费率", "document_type": "产品说明书"},  # 电商可换 category / brand
)

def rewrite_query(user_query: str) -> str:
    if "费率" in user_query:
        return f"{user_query} 基金申购费 赎回费 管理费 托管费"
    return user_query

from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")  # 或 bge-reranker-large

def rerank(query: str, candidates, top_k=3):
    pairs = [[query, doc.page_content] for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: -x[1])
    return [doc for doc, _ in ranked[:top_k]]

def test_retrieval_quality(vectorstore, test_cases):
    """
    test_cases: [{"query": "问题", "expected": ["期望关键词1", ...]}]
    """
    passed = 0
    for case in test_cases:
        results = vectorstore.similarity_search(case["query"], k=5)
        result_text = " ".join(doc.page_content for doc in results)
        if all(kw in result_text for kw in case["expected"]):
            passed += 1
            print(f"✅ {case['query']}")
        else:
            print(f"❌ {case['query']}: 缺少 {case['expected']}")
    n = len(test_cases)
    print(f"\n通过率: {passed}/{n} = {passed/n:.0%}")

from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# 1. 向量检索器
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-zh-v1.5")
vectorstore = FAISS.from_documents(documents, embeddings)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

# 2. BM25检索器
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 10

# 3. 混合检索器（RRF融合）
ensemble_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.5, 0.5],  # 权重可调
)

# 4. 检索
results = ensemble_retriever.get_relevant_documents("这款手机支持无线充电吗")

from llama_index.core import VectorStoreIndex
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine

# 1. 构建索引
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-zh-v1.5")
index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

# 2. Rerank处理器
rerank = SentenceTransformerRerank(
    model="BAAI/bge-reranker-large",
    top_n=5,  # 重排序后返回5个
)

# 3. 检索+重排序
query_engine = index.as_query_engine(
    similarity_top_k=20,  # 先召回20个
    node_postprocessors=[rerank],  # 再重排序取5个
)

response = query_engine.query("这款手机支持无线充电吗")

from langsmith import Client, evaluate

client = Client()

# 1. 定义检索函数
def retrieve_answer(question: str) -> dict:
    results = ensemble_retriever.get_relevant_documents(question)
    reranked = reranker.rerank(question, results)
    return {"result": reranked[:5]}

# 2. 定义评测数据集
dataset = client.read_dataset(dataset_name="rag-evaluation")

# 3. 定义评测指标
def recall_at_k(inputs, outputs, reference):
    relevant_docs = reference.get("expected_docs", [])
    retrieved_docs = [doc.page_content for doc in outputs["result"]]
    hits = sum(1 for doc in relevant_docs if any(doc in r for r in retrieved_docs))
    return {"score": hits / len(relevant_docs) if relevant_docs else 0}

# 4. 执行评测
evaluate(
    retrieve_answer,
    data=dataset,
    evaluators=[recall_at_k],
    experiment_name="hybrid-search-rerank-v1",
)

from elasticsearch import Elasticsearch

es = Elasticsearch(["http://localhost:9200"])

# 1. 创建索引（同时支持向量字段和文本字段）
es.indices.create(index="products", body={
    "mappings": {
        "properties": {
            "text": {"type": "text", "analyzer": "ik_max_word"},
            "embedding": {"type": "dense_vector", "dims": 1024},
            "category": {"type": "keyword"},
            "brand": {"type": "keyword"},
        }
    }
})

# 2. 混合检索（hybrid search）
def hybrid_search(query: str, category: str = None, top_k: int = 5):
    vector_query = {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": query_embedding},
            },
        }
    }
    
    bm25_query = {
        "multi_match": {
            "query": query,
            "fields": ["text"],
            "fuzziness": "AUTO",
        }
    }
    
    hybrid_query = {
        "rank": {
            "rrf": {
                "rank_window_size": 10,
                "alpha": 0.8,
                "queries": [vector_query, bm25_query],
            }
        }
    }
    
    if category:
        hybrid_query = {
            "bool": {
                "filter": {"term": {"category": category}},
                "must": [{"rank": hybrid_query["rank"]}],
            }
        }
    
    response = es.search(index="products", body=hybrid_query, size=top_k)
    return [hit["_source"] for hit in response["hits"]["hits"]]
