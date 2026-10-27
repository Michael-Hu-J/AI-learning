# config.py
import os
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_CONFIG = {
    "model": "text-embedding-v3",
    "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "dimensions": 1024,
}

LLM_CONFIG = {
    "model": "qwen-plus",
    "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}

VECTOR_STORE_CONFIG = {
    "provider": "chroma",
    "collection_name": "knowledge_base",
    "persist_directory": "./vector_data/chroma",
}

RAG_CONFIG = {
    "top_k": 5,
    "score_threshold": 0.5,
    "max_context_tokens": 3000,
}

# document_processor.py
import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class Document:
    content: str
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentChunk:
    content: str
    source: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class TextSplitter:
    def split_by_heading(self, document: Document) -> List[DocumentChunk]:
        sections = re.split(r"(?=\n#{1,6}\s)", document.content)
        chunks = []
        for i, section in enumerate(sections):
            section = section.strip()
            if len(section) < 50:  # 过滤太短的切片
                continue
            chunks.append(DocumentChunk(
                content=section,
                source=document.source,
                chunk_index=i,
                metadata={"split_method": "heading", "char_count": len(section)},
            ))
        return chunks

# vector_store.py
from openai import OpenAI
from config import EMBEDDING_CONFIG, VECTOR_STORE_CONFIG

class EmbeddingClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=EMBEDDING_CONFIG["api_key"],
            base_url=EMBEDDING_CONFIG["base_url"],
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=EMBEDDING_CONFIG["model"],
            input=texts,
            dimensions=EMBEDDING_CONFIG["dimensions"],
        )
        return [d.embedding for d in response.data]

class VectorStore:
    def __init__(self):
        import chromadb
        self.client = chromadb.PersistentClient(
            path=VECTOR_STORE_CONFIG["persist_directory"]
        )
        self.collection = self.client.get_or_create_collection(
            name=VECTOR_STORE_CONFIG["collection_name"],
            metadata={"hnsw:space": "cosine"},
        )
        self.embedding_client = EmbeddingClient()

    def add_documents(self, chunks: list) -> int:
        texts = [c.content for c in chunks]
        embeddings = self.embedding_client.embed_texts(texts)
        ids = [f"{c.source}_{c.chunk_index}" for c in chunks]
        self.collection.add(ids=ids, embeddings=embeddings, documents=texts)
        return len(chunks)

    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.0):
        query_embedding = self.embedding_client.embed_text(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        # 距离转相似度分数并过滤
        output = []
        for i, doc in enumerate(results["documents"][0]):
            score = 1.0 - results["distances"][0][i]
            if score >= score_threshold:
                output.append({"content": doc, "score": round(score, 4)})
        return output

# rag_engine.py
from openai import OpenAI
from vector_store import VectorStore
from config import LLM_CONFIG, RAG_CONFIG

class RAGEngine:
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm_client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )

    def answer(self, question: str) -> Dict[str, Any]:
        # 步骤 1：检索相关文档
        contexts = self.vector_store.search(
            question,
            top_k=RAG_CONFIG["top_k"],
            score_threshold=RAG_CONFIG["score_threshold"],
        )
        if not contexts:
            return {"question": question, "answer": "抱歉，未找到相关信息。", "has_context": False}

        # 步骤 2：构建 Prompt
        context_text = "\n\n".join(
            f"[文档{i + 1}]\n{ctx['content']}" for i, ctx in enumerate(contexts)
        )
        prompt = f"""你是一个专业的问答助手。请根据以下参考文档回答用户的问题。

参考文档：
{context_text}

用户问题：{question}

回答要求：
1. 只基于参考文档中的信息回答
2. 如果参考文档中没有相关信息，请明确说明"根据现有文档无法回答该问题"
3. 回答要简洁准确，不要编造信息
4. 如果可能，在回答中标注信息来源
5. 使用中文回答

请回答："""

        # 步骤 3：生成回答
        response = self.llm_client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3,
        )
        return {
            "question": question,
            "answer": response.choices[0].message.content,
            "contexts": contexts,
            "has_context": True,
        }

class DocumentLoader:
    """文档加载器：支持 md / txt / pdf"""

    def load_file(self, file_path: str) -> Document:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".md":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Document(content=content, source=file_path, metadata={"format": "markdown"})
        elif ext == ".pdf":
            import PyPDF2
            text_parts = []
            with open(file_path, "rb") as f:
                for page in PyPDF2.PdfReader(f).pages:
                    text_parts.append(page.extract_text())
            return Document(content="\n".join(text_parts), source=file_path, metadata={"format": "pdf"})
        # ... txt 等同理

    def load_directory(self, dir_path: str) -> List[Document]:
        documents = []
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path) and os.path.splitext(filename)[1].lower() in (".md", ".txt", ".pdf"):
                documents.append(self.load_file(file_path))
        return documents


class TextSplitter:
    def split_by_paragraph(self, document: Document) -> List[DocumentChunk]:
        paragraphs = re.split(r"\n\s*\n", document.content)
        return [DocumentChunk(content=p.strip(), source=document.source, chunk_index=i,
                metadata={"split_method": "paragraph"})
                for i, p in enumerate(paragraphs) if len(p.strip()) >= 10]

    def split_by_size(self, document: Document, chunk_size=500, chunk_overlap=100) -> List[DocumentChunk]:
        chunks, start, index = [], 0, 0
        while start < len(document.content):
            chunk = document.content[start:start + chunk_size].strip()
            if len(chunk) >= 10:
                chunks.append(DocumentChunk(content=chunk, source=document.source,
                    chunk_index=index, metadata={"split_method": "fixed_size"}))
                index += 1
            start += chunk_size - chunk_overlap
        return chunks
    # split_by_heading 见 §4.3

# main.py — 离线构建 + 在线问答
def build_knowledge_base(knowledge_dir="./knowledge_base"):
    loader, splitter, store = DocumentLoader(), TextSplitter(), VectorStore()
    documents = loader.load_directory(knowledge_dir)
    all_chunks = []
    for doc in documents:
        chunks = splitter.split_by_heading(doc)
        if len(chunks) <= 1:
            chunks = splitter.split_by_paragraph(doc)
        if len(chunks) <= 1:
            chunks = splitter.split_by_size(doc, chunk_size=500, chunk_overlap=100)
        all_chunks.extend(chunks)
    store.clear()
    store.add_documents(all_chunks)
    return len(all_chunks)

# evaluator.py — 检索质量评测
class RAGEvaluator:
    def test_retrieval_quality(self, test_questions, expected_top_k=5):
        results = []
        for item in test_questions:
            contexts = self.engine.retrieve(item["question"], top_k=expected_top_k)
            all_content = " ".join(c["content"] for c in contexts)
            kws = item.get("expected_keywords", [])
            precision = sum(1 for kw in kws if kw in all_content) / len(kws) if kws else 0
            results.append({"question": item["question"], "keyword_precision": precision,
                "retrieved_count": len(contexts)})
        return {"avg_keyword_precision": sum(r["keyword_precision"] for r in results) / len(results),
                "per_question_results": results}

# 测试集示例
test_questions = [
    {"question": "怎么重置密码？", "expected_keywords": ["密码", "重置", "修改"]},
    {"question": "退款流程是什么？", "expected_keywords": ["退款", "流程", "申请"]},
]

def hybrid_search(vector_store, keyword_index, query, top_k=5):
    """混合检索：向量 70% + 关键词 30%"""
    vector_results = vector_store.search(query, top_k=top_k)
    keyword_results = keyword_index.search(query, top_k=top_k)
    combined = {}
    for r in vector_results:
        doc_id = r["metadata"].get("source", "")
        combined[doc_id] = r["score"] * 0.7
    for r in keyword_results:
        doc_id = r["metadata"].get("source", "")
        combined[doc_id] = combined.get(doc_id, 0) + r["score"] * 0.3
    return sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]

def test_rag_pipeline():
    loader = DocumentLoader()
    doc = loader.load_file("./knowledge_base/faq.md")
    assert len(doc.content) > 0, "文档内容为空"

    chunks = TextSplitter().split_by_paragraph(doc)
    assert len(chunks) > 0 and all(len(c.content) >= 10 for c in chunks)

    store = VectorStore()
    assert store.add_documents(chunks) == len(chunks)

    results = store.search("怎么重置密码", top_k=5)
    assert len(results) > 0 and all(r["score"] >= 0.3 for r in results)

    answer = RAGEngine().answer("怎么重置密码")
    assert answer["has_context"] and len(answer["answer"]) > 10
    print("所有测试通过")
