# ChromaDB 导出
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("knowledge_base")
all_data = collection.get(include=["embeddings", "documents", "metadatas"])

# Milvus 导入
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
]
schema = CollectionSchema(fields)
milvus_col = Collection("knowledge_base", schema)

milvus_col.insert([
    all_data["ids"],
    all_data["embeddings"],
    all_data["documents"],
    [m.get("category", "") for m in all_data["metadatas"]]
])
milvus_col.flush()

import chromadb

# 创建客户端（持久化模式）
client = chromadb.PersistentClient(path="./my_chroma_db")

# 创建集合
collection = client.get_or_create_collection(
    name="knowledge_base",
    metadata={"hnsw:space": "cosine"}  # 重要：指定距离度量
)

# 插入数据
collection.add(
    documents=["Python是一种编程语言", "机器学习是AI的子领域", "向量数据库用于相似性搜索"],
    metadatas=[{"source": "wiki"}, {"source": "wiki"}, {"source": "blog"}],
    ids=["doc1", "doc2", "doc3"]
)

# 检索
results = collection.query(
    query_texts=["什么是人工智能"],
    n_results=2
)
print(results)

import faiss
import numpy as np

# 生成测试数据（实际项目中是你的Embedding向量）
dim = 768
vectors = np.random.rand(10000, dim).astype(np.float32)

# 归一化（余弦相似度需要）
faiss.normalize_L2(vectors)

# 创建索引（IVFPQ：适合大数据量）
nlist = 100  # 聚类中心数
m = 32       # PQ的子空间数
quantizer = faiss.IndexFlatIP(dim)  # 内积作为量化的距离度量
index = faiss.IndexIVFPQ(quantizer, dim, nlist, m, 8)

# 训练索引（必须！）
index.train(vectors)
index.add(vectors)

# 检索
query = np.random.rand(1, dim).astype(np.float32)
faiss.normalize_L2(query)
index.nprobe = 10  # 搜索时探查的聚类中心数
distances, indices = index.search(query, k=10)
print(f"最相似的索引: {indices[0]}")
print(f"距离: {distances[0]}")

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 连接
connections.connect(alias="default", host="localhost", port="19530")

# 定义schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
    FieldSchema(name="timestamp", dtype=DataType.INT64),
]
schema = CollectionSchema(fields, description="知识库")
collection = Collection("knowledge_base", schema)

# 插入数据
import numpy as np
vectors = np.random.rand(1000, 768).astype(np.float32)
data = [
    vectors.tolist(),
    [f"文档内容{i}" for i in range(1000)],
    [f"category_{i % 5}" for i in range(1000)],
    [1000000 + i for i in range(1000)],
]
collection.insert(data)
collection.flush()  # 重要：持久化到磁盘

# 创建索引
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 200}
}
collection.create_index("embedding", index_params)
collection.load()  # 加载到内存才能检索

# 检索
search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
results = collection.search(
    data=[np.random.rand(768).astype(np.float32)],
    anns_field="embedding",
    param=search_params,
    limit=10,
    expr="category == 'category_1'"  # 元数据过滤
)

for hits in results:
    for hit in hits:
        print(f"ID: {hit.id}, 距离: {hit.distance}, 实体: {hit.entity}")

# 清理
collection.drop()
connections.disconnect("default")

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 连接（本地Docker或内存模式）
client = QdrantClient(path="./qdrant_db")  # 本地持久化
# client = QdrantClient(host="localhost", port=6333)  # Docker模式

# 创建集合
client.create_collection(
    collection_name="knowledge_base",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)

# 插入数据
points = [
    PointStruct(
        id=1,
        vector=np.random.rand(768).tolist(),
        payload={"content": "Python编程", "category": "tech"}
    ),
    PointStruct(
        id=2,
        vector=np.random.rand(768).tolist(),
        payload={"content": "机器学习入门", "category": "tech"}
    ),
]
client.upsert(collection_name="knowledge_base", points=points)

# 检索
results = client.search(
    collection_name="knowledge_base",
    query_vector=np.random.rand(768).tolist(),
    query_filter=None,  # 可以加过滤条件
    limit=10,
)
for r in results:
    print(f"ID: {r.id}, 分数: {r.score}, payload: {r.payload}")

import time
import numpy as np

def benchmark_insert(collection, vectors, ids, batch_size=1000):
    """批量插入基准测试"""
    start = time.time()
    for i in range(0, len(vectors), batch_size):
        batch_vectors = vectors[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        collection.add(embeddings=batch_vectors, ids=batch_ids)
    elapsed = time.time() - start
    return elapsed, len(vectors) / elapsed

def benchmark_search(collection, vectors, k=10, num_queries=100):
    """检索基准测试"""
    latencies = []
    for _ in range(num_queries):
        query = np.random.rand(vectors.shape[1]).astype(np.float32)
        start = time.time()
        collection.query(query_embeddings=[query], n_results=k)
        latencies.append(time.time() - start)
    
    latencies_ms = [t * 1000 for t in latencies]
    return {
        "avg_ms": np.mean(latencies_ms),
        "p99_ms": np.percentile(latencies_ms, 99),
        "max_ms": np.max(latencies_ms),
        "min_ms": np.min(latencies_ms),
    }

def benchmark_recall(collection, test_queries, ground_truth, k=10):
    """召回率测试"""
    hits = 0
    total = len(test_queries)
    for query, true_neighbors in zip(test_queries, ground_truth):
        results = collection.query(query_embeddings=[query], n_results=k)
        result_ids = set(results["ids"][0])
        hits += len(result_ids & set(true_neighbors))
    return hits / (total * k)

import time
import numpy as np

def benchmark_vector_db(db_init_fn, num_vectors=10000, dim=1536):
    db = db_init_fn()
    vectors = np.random.rand(num_vectors, dim).astype(np.float32)
    metadata = [{"id": i, "text": f"doc_{i}"} for i in range(num_vectors)]

    start = time.time()
    db.add_vectors(vectors, metadata)
    insert_time = time.time() - start

    query = np.random.rand(1, dim).astype(np.float32)
    times = []
    for _ in range(100):
        start = time.time()
        db.search(query, k=10)
        times.append(time.time() - start)

    return {
        "insert_time": insert_time,
        "vectors_per_sec": num_vectors / insert_time,
        "avg_search_ms": np.mean(times) * 1000,
        "p99_search_ms": np.percentile(times, 99) * 1000,
    }
