from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List, Dict, Any, Optional
import time
import numpy as np
from document_loader import DocumentLoader
from embedding_validator import EmbeddingValidator
from retrieval_evaluator import RetrievalEvaluator
from answer_validator import AnswerValidator
from performance_tester import PerformanceTester

class RAGTestFramework:
    """RAG系统测试验证框架"""
    
    def __init__(self, 
                 embedding_model="text-embedding-ada-002",
                 llm_model="gpt-3.5-turbo",
                 chunk_size=1000,
                 chunk_overlap=100):
        self.embedding_model = OpenAIEmbeddings(model=embedding_model)
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vectorstore = None
        self.retriever = None
        self.qa_chain = None
        
        # 初始化验证器
        self.embedding_validator = EmbeddingValidator(self.embedding_model)
        self.retrieval_evaluator = RetrievalEvaluator()
        self.answer_validator = AnswerValidator()
        self.performance_tester = PerformanceTester()
        
        # 测试结果存储
        self.test_results = {
            'setup_time': 0,
            'retrieval_metrics': {},
            'answer_metrics': {},
            'performance_metrics': {},
            'overall_score': 0.0
        }
    
    def setup_vectorstore(self, documents: List[Document]):
        """设置向量存储"""
        start_time = time.time()
        
        # 文本分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        split_docs = text_splitter.split_documents(documents)
        
        # 创建向量存储
        self.vectorstore = Chroma.from_documents(
            split_docs, 
            self.embedding_model,
            collection_name="rag_test_collection"
        )
        
        # 创建检索器
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 5}  # 默认返回5个最相似的文档
        )
        
        # 创建QA链
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True
        )
        
        setup_duration = time.time() - start_time
        self.test_results['setup_time'] = setup_duration
        
        print(f"Vectorstore setup completed in {setup_duration:.2f}s")
        print(f"Indexed {len(split_docs)} document chunks")
    
    def test_retrieval_accuracy(self, queries_with_ground_truth: List[Dict]) -> Dict[str, Any]:
        """测试检索准确性"""
        retrieval_results = []
        
        for query_item in queries_with_ground_truth:
            query = query_item['query']
            expected_docs = query_item.get('expected_docs', [])
            
            # 执行检索
            retrieved_docs = self.retriever.get_relevant_documents(query)
            
            # 评估检索结果
            eval_result = self.retrieval_evaluator.evaluate(
                query, retrieved_docs, expected_docs
            )
            
            retrieval_results.append(eval_result)
        
        # 计算整体指标
        avg_precision = np.mean([r['precision'] for r in retrieval_results])
        avg_recall = np.mean([r['recall'] for r in retrieval_results])
        avg_f1 = np.mean([r['f1_score'] for r in retrieval_results])
        
        retrieval_metrics = {
            'avg_precision': avg_precision,
            'avg_recall': avg_recall,
            'avg_f1_score': avg_f1,
            'total_queries': len(queries_with_ground_truth),
            'detailed_results': retrieval_results
        }
        
        self.test_results['retrieval_metrics'] = retrieval_metrics
        return retrieval_metrics
    
    def test_answer_quality(self, test_questions: List[Dict]) -> Dict[str, Any]:
        """测试答案质量"""
        answer_results = []
        
        for question_item in test_questions:
            question = question_item['question']
            expected_answer = question_item.get('expected_answer', '')
            expected_sources = question_item.get('expected_sources', [])
            
            # 执行问答
            start_time = time.time()
            result = self.qa_chain({"query": question})
            response_time = time.time() - start_time
            
            generated_answer = result['result']
            source_documents = result.get('source_documents', [])
            
            # 验证答案质量
            validation_result = self.answer_validator.validate(
                question=question,
                generated_answer=generated_answer,
                expected_answer=expected_answer,
                expected_sources=expected_sources,
                source_documents=source_documents
            )
            
            answer_results.append({
                **validation_result,
                'response_time': response_time,
                'generated_answer': generated_answer,
                'source_count': len(source_documents)
            })
        
        # 计算整体指标
        avg_relevance = np.mean([r['relevance_score'] for r in answer_results])
        avg_accuracy = np.mean([r['accuracy_score'] for r in answer_results])
        avg_faithfulness = np.mean([r['faithfulness_score'] for r in answer_results])
        avg_response_time = np.mean([r['response_time'] for r in answer_results])
        
        answer_metrics = {
            'avg_relevance': avg_relevance,
            'avg_accuracy': avg_accuracy,
            'avg_faithfulness': avg_faithfulness,
            'avg_response_time': avg_response_time,
            'total_questions': len(test_questions),
            'detailed_results': answer_results
        }
        
        self.test_results['answer_metrics'] = answer_metrics
        return answer_metrics
    
    def test_performance(self, stress_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """性能测试"""
        if stress_config is None:
            stress_config = {
                'concurrent_users': 5,
                'requests_per_user': 10,
                'questions': [
                    "什么是人工智能?",
                    "公司的发展历程是什么?",
                    "产品的核心功能有哪些?"
                ]
            }
        
        performance_results = self.performance_tester.run_stress_test(
            qa_chain=self.qa_chain,
            config=stress_config
        )
        
        self.test_results['performance_metrics'] = performance_results
        return performance_results
    
    def run_complete_test_suite(self, 
                              documents: List[Document],
                              queries_with_ground_truth: List[Dict],
                              test_questions: List[Dict],
                              stress_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行完整测试套件"""
        print("开始执行RAG系统完整测试套件...")
        
        # 1. 设置向量存储
        print("1. 设置向量存储...")
        self.setup_vectorstore(documents)
        
        # 2. 测试检索准确性
        print("2. 测试检索准确性...")
        retrieval_metrics = self.test_retrieval_accuracy(queries_with_ground_truth)
        
        # 3. 测试答案质量
        print("3. 测试答案质量...")
        answer_metrics = self.test_answer_quality(test_questions)
        
        # 4. 性能测试
        print("4. 执行性能测试...")
        performance_metrics = self.test_performance(stress_config)
        
        # 5. 计算总体评分
        overall_score = self._calculate_overall_score(
            retrieval_metrics, 
            answer_metrics, 
            performance_metrics
        )
        
        self.test_results['overall_score'] = overall_score
        
        print(f"测试完成！总体评分: {overall_score:.2f}")
        return self.test_results
    
    def _calculate_overall_score(self, retrieval_metrics, answer_metrics, performance_metrics):
        """计算总体评分"""
        # 权重分配（可根据业务需求调整）
        retrieval_weight = 0.3
        answer_weight = 0.5
        performance_weight = 0.2
        
        # 检索质量评分（精确率、召回率、F1分数的平均值）
        retrieval_score = (
            retrieval_metrics.get('avg_precision', 0) +
            retrieval_metrics.get('avg_recall', 0) +
            retrieval_metrics.get('avg_f1_score', 0)
        ) / 3
        
        # 答案质量评分（相关性、准确性、忠实度的平均值）
        answer_score = (
            answer_metrics.get('avg_relevance', 0) +
            answer_metrics.get('avg_accuracy', 0) +
            answer_metrics.get('avg_faithfulness', 0)
        ) / 3
        
        # 性能评分（基于响应时间和吞吐量）
        performance_score = performance_metrics.get('efficiency_score', 0)
        
        overall_score = (
            retrieval_weight * retrieval_score +
            answer_weight * answer_score +
            performance_weight * performance_score
        )
        
        return overall_score
    
    def export_test_report(self, filename: str = "rag_test_report.html"):
        """导出测试报告"""
        import pandas as pd
        
        # 准备报告数据
        report_data = {
            'Metric': [
                'Setup Time (s)',
                'Avg Precision',
                'Avg Recall', 
                'Avg F1 Score',
                'Avg Relevance',
                'Avg Accuracy',
                'Avg Faithfulness',
                'Avg Response Time (s)',
                'Overall Score'
            ],
            'Value': [
                round(self.test_results['setup_time'], 2),
                round(self.test_results['retrieval_metrics'].get('avg_precision', 0), 3),
                round(self.test_results['retrieval_metrics'].get('avg_recall', 0), 3),
                round(self.test_results['retrieval_metrics'].get('avg_f1_score', 0), 3),
                round(self.test_results['answer_metrics'].get('avg_relevance', 0), 3),
                round(self.test_results['answer_metrics'].get('avg_accuracy', 0), 3),
                round(self.test_results['answer_metrics'].get('avg_faithfulness', 0), 3),
                round(self.test_results['answer_metrics'].get('avg_response_time', 0), 3),
                round(self.test_results['overall_score'], 3)
            ]
        }
        
        df = pd.DataFrame(report_data)
        
        # 生成HTML报告
        html_content = f"""
        <html>
        <head>
            <title>RAG系统测试报告</title>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .score-high {{ color: green; font-weight: bold; }}
                .score-medium {{ color: orange; font-weight: bold; }}
                .score-low {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>RAG系统测试报告</h1>
            <p>生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
        """
        
        for _, row in df.iterrows():
            metric = row['Metric']
            value = row['Value']
            
            # 根据数值确定样式
            css_class = ""
            if 'Score' in metric or 'Precision' in metric or 'Recall' in metric or 'F1' in metric:
                if value >= 0.8:
                    css_class = "score-high"
                elif value >= 0.6:
                    css_class = "score-medium"
                else:
                    css_class = "score-low"
            
            html_content += f'<tr><td>{metric}</td><td class="{css_class}">{value}</td></tr>\n'
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"测试报告已导出至: {filename}")

from langchain.schema import Document
from langchain.document_loaders import (
    TextLoader, PDFPlumberLoader, UnstructuredWordDocumentLoader,
    CSVLoader, JSONLoader
)
from typing import List, Dict, Any
import os
from pathlib import Path

class DocumentLoader:
    """文档加载器"""
    
    SUPPORTED_FORMATS = {
        '.txt': TextLoader,
        '.pdf': PDFPlumberLoader,
        '.docx': UnstructuredWordDocumentLoader,
        '.csv': CSVLoader,
        '.json': JSONLoader,
    }
    
    def __init__(self):
        self.documents = []
    
    def load_from_directory(self, directory_path: str, recursive: bool = True) -> List[Document]:
        """从目录加载所有支持格式的文档"""
        directory = Path(directory_path)
        all_documents = []
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory {directory_path} does not exist")
        
        # 遍历目录
        if recursive:
            file_paths = [f for f in directory.rglob('*') if f.is_file()]
        else:
            file_paths = [f for f in directory.iterdir() if f.is_file()]
        
        for file_path in file_paths:
            ext = file_path.srsion().lower()
            if ext in self.SUPPORTED_FORMATS:
                try:
                    documents = self.load_document(str(file_path))
                    all_documents.extend(documents)
                    print(f"Loaded {len(documents)} documents from {file_path}")
                except Exception as e:
                    print(f"Failed to load {file_path}: {str(e)}")
        
        self.documents.extend(all_documents)
        return all_documents
    
    def load_document(self, file_path: str) -> List[Document]:
        """加载单个文档"""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")
        
        loader_class = self.SUPPORTED_FORMATS[ext]
        
        # 特殊处理JSON文件
        if ext == '.json':
            loader = loader_class(
                file_path=file_path,
                jq_schema=".[]",  # 假设JSON是数组格式
                content_key="content"  # 假设内容字段名为content
            )
        else:
            loader = loader_class(str(file_path))
        
        documents = loader.load()
        
        # 添加元数据
        for doc in documents:
            doc.metadata['source_file'] = str(file_path)
            doc.metadata['file_type'] = ext
            doc.metadata['loaded_at'] = time.time()
        
        return documents
    
    def load_from_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """从纯文本加载文档"""
        if metadata is None:
            metadata = {}
        
        doc = Document(page_content=text, metadata=metadata)
        self.documents.append(doc)
        return [doc]
    
    def validate_documents(self) -> Dict[str, Any]:
        """验证加载的文档"""
        stats = {
            'total_documents': len(self.documents),
            'total_chars': sum(len(doc.page_content) for doc in self.documents),
            'avg_doc_length': 0,
            'file_types': {},
            'empty_docs': 0
        }
        
        if stats['total_documents'] > 0:
            stats['avg_doc_length'] = stats['total_chars'] / stats['total_documents']
        
        # 统计文件类型
        for doc in self.documents:
            file_type = doc.metadata.get('file_type', 'unknown')
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
            if len(doc.page_content.strip()) == 0:
                stats['empty_docs'] += 1
        
        return stats

def create_sample_documents():
    """创建示例文档用于测试"""
    sample_docs = [
        Document(
            page_content="""
            人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
            它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
            该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
            """,
            metadata={'title': '人工智能概述', 'category': 'tech', 'source': 'sample'}
        ),
        Document(
            page_content="""
            机器学习（Machine Learning，ML）是人工智能的一个子领域，
            它使计算机能够在没有明确编程的情况下学习和改进。
            机器学习算法通过数据构建模型，从而做出预测或决策。
            """,
            metadata={'title': '机器学习基础', 'category': 'tech', 'source': 'sample'}
        ),
        Document(
            page_content="""
            深度学习（Deep Learning）是机器学习的一个分支，
            它基于人工神经网络的结构和功能。
            深度学习模型通常具有多个隐藏层，可以学习数据的层次化特征表示。
            """,
            metadata={'title': '深度学习原理', 'category': 'tech', 'source': 'sample'}
        )
    ]
    return sample_docs

from typing import List, Dict, Any
import numpy as np
from scipy.spatial.distance import cosine
from sentence_transformers import util

class EmbeddingValidator:
    """嵌入向量验证器"""
    
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的语义相似度"""
        embeddings = self.embedding_model.embed_documents([text1, text2])
        emb1, emb2 = embeddings[0], embeddings[1]
        
        # 使用余弦相似度
        similarity = 1 - cosine(emb1, emb2)
        return similarity
    
    def validate_embedding_quality(self, texts: List[str], threshold: float = 0.7) -> Dict[str, Any]:
        """验证嵌入质量"""
        if len(texts) < 2:
            return {'error': 'Need at least 2 texts for similarity comparison'}
        
        embeddings = self.embedding_model.embed_documents(texts)
        
        # 计算所有文本对之间的相似度
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = 1 - cosine(embeddings[i], embeddings[j])
                similarities.append(sim)
        
        avg_similarity = np.mean(similarities)
        max_similarity = np.max(similarities)
        min_similarity = np.min(similarities)
        
        # 检查是否有过于相似的文本（可能重复）
        highly_similar_pairs = [s for s in similarities if s > threshold]
        
        validation_result = {
            'avg_similarity': avg_similarity,
            'max_similarity': max_similarity,
            'min_similarity': min_similarity,
            'highly_similar_pairs': len(highly_similar_pairs),
            'total_pairs': len(similarities),
            'recommended_action': 'ok' if len(highly_similar_pairs) / len(similarities) < 0.1 else 'review_duplicates'
        }
        
        return validation_result
    
    def find_similar_texts(self, query_text: str, candidate_texts: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """查找最相似的文本"""
        query_embedding = self.embedding_model.embed_query(query_text)
        candidate_embeddings = self.embedding_model.embed_documents(candidate_texts)
        
        # 计算相似度
        similarities = []
        for i, cand_emb in enumerate(candidate_embeddings):
            sim = 1 - cosine(query_embedding, cand_emb)
            similarities.append({
                'index': i,
                'text': candidate_texts[i][:100] + '...' if len(candidate_texts[i]) > 100 else candidate_texts[i],
                'similarity': sim
            })
        
        # 按相似度排序
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

def test_embedding_validator():
    """测试嵌入验证器"""
    from langchain_openai import OpenAIEmbeddings
    
    # 初始化嵌入模型
    embedding_model = OpenAIEmbeddings()
    validator = EmbeddingValidator(embedding_model)
    
    # 测试文本
    texts = [
        "人工智能是计算机科学的分支",
        "机器学习属于人工智能领域", 
        "今天的天气很好",
        "人工智能和机器学习密切相关"
    ]
    
    # 验证嵌入质量
    quality_result = validator.validate_embedding_quality(texts)
    print("嵌入质量验证结果:", quality_result)
    
    # 查找相似文本
    similar_texts = validator.find_similar_texts(
        "AI技术的发展", 
        texts, 
        top_k=3
    )
    print("相似文本查找结果:", similar_texts)

from typing import List, Dict, Any
from langchain.schema import Document
import numpy as np

class RetrievalEvaluator:
    """检索评估器"""
    
    def evaluate(self, query: str, retrieved_docs: List[Document], expected_docs: List[Document] = None) -> Dict[str, Any]:
        """评估检索结果"""
        if expected_docs is None:
            # 如果没有预期文档，只计算基本指标
            return {
                'precision': 1.0,  # 假设所有检索到的都是相关的
                'recall': 1.0,     # 假设所有相关文档都已检索到
                'f1_score': 1.0,
                'hit_rate': 1.0,
                'mrr': 1.0,  # Mean Reciprocal Rank
                'ndcg': 1.0, # Normalized Discounted Cumulative Gain
                'query': query,
                'retrieved_count': len(retrieved_docs)
            }
        
        # 将预期文档转换为文本集合以便比较
        expected_texts = {doc.page_content.strip() for doc in expected_docs}
        
        # 将检索到的文档转换为文本集合
        retrieved_texts = {doc.page_content.strip() for doc in retrieved_docs}
        
        # 计算基本指标
        true_positives = len(expected_texts.intersection(retrieved_texts))
        false_positives = len(retrieved_texts) - true_positives
        false_negatives = len(expected_texts) - true_positives
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Hit Rate (至少检索到一个相关文档的比例)
        hit_rate = 1.0 if true_positives > 0 else 0.0
        
        # Mean Reciprocal Rank (MRR)
        mrr = self._calculate_mrr(retrieved_docs, expected_docs)
        
        # Normalized Discounted Cumulative Gain (NDCG)
        ndcg = self._calculate_ndcg(retrieved_docs, expected_docs)
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'hit_rate': hit_rate,
            'mrr': mrr,
            'ndcg': ndcg,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'query': query,
            'retrieved_count': len(retrieved_docs),
            'expected_count': len(expected_docs)
        }
    
    def _calculate_mrr(self, retrieved_docs: List[Document], expected_docs: List[Document]) -> float:
        """计算平均倒数排名"""
        expected_texts = {doc.page_content.strip() for doc in expected_docs}
        
        for rank, doc in enumerate(retrieved_docs, 1):
            if doc.page_content.strip() in expected_texts:
                return 1.0 / rank
        
        return 0.0  # 没有找到相关文档
    
    def _calculate_ndcg(self, retrieved_docs: List[Document], expected_docs: List[Document]) -> float:
        """计算归一化折损累积增益"""
        # 简化版NDCG计算
        # 假设相关性为二元（相关或不相关）
        
        expected_texts = {doc.page_content.strip() for doc in expected_docs}
        relevance_scores = [1 if doc.page_content.strip() in expected_texts else 0 
                           for doc in retrieved_docs]
        
        if not relevance_scores or sum(relevance_scores) == 0:
            return 0.0
        
        # 计算DCG
        dcg = relevance_scores[0]  # 第一个元素不打折
        for i in range(1, len(relevance_scores)):
            dcg += relevance_scores[i] / np.log2(i + 1)
        
        # 计算理想DCG (IDCG)
        ideal_relevance = sorted(relevance_scores, reverse=True)
        idcg = ideal_relevance[0]  # 第一个元素不打折
        for i in range(1, len(ideal_relevance)):
            idcg += ideal_relevance[i] / np.log2(i + 1)
        
        # 避免除零错误
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def batch_evaluate(self, queries_with_ground_truth: List[Dict]) -> Dict[str, Any]:
        """批量评估多个查询"""
        all_results = []
        
        for query_item in queries_with_ground_truth:
            result = self.evaluate(
                query=query_item['query'],
                retrieved_docs=query_item.get('retrieved_docs', []),
                expected_docs=query_item.get('expected_docs', [])
            )
            all_results.append(result)
        
        # 计算平均指标
        avg_precision = np.mean([r['precision'] for r in all_results])
        avg_recall = np.mean([r['recall'] for r in all_results])
        avg_f1_score = np.mean([r['f1_score'] for r in all_results])
        avg_hit_rate = np.mean([r['hit_rate'] for r in all_results])
        avg_mrr = np.mean([r['mrr'] for r in all_results])
        avg_ndcg = np.mean([r['ndcg'] for r in all_results])
        
        return {
            'average_metrics': {
                'avg_precision': avg_precision,
                'avg_recall': avg_recall,
                'avg_f1_score': avg_f1_score,
                'avg_hit_rate': avg_hit_rate,
                'avg_mrr': avg_mrr,
                'avg_ndcg': avg_ndcg
            },
            'individual_results': all_results,
            'total_queries': len(queries_with_ground_truth)
        }

def test_retrieval_evaluator():
    """测试检索评估器"""
    from langchain.schema import Document
    
    evaluator = RetrievalEvaluator()
    
    # 创建测试数据
    query = "人工智能的发展历史"
    retrieved_docs = [
        Document(page_content="人工智能起源于20世纪50年代"),
        Document(page_content="机器学习是AI的重要分支"),
        Document(page_content="深度学习推动了AI的快速发展")
    ]
    expected_docs = [
        Document(page_content="人工智能起源于20世纪50年代"),
        Document(page_content="AI发展经历了多个阶段")
    ]
    
    result = evaluator.evaluate(query, retrieved_docs, expected_docs)
    print("检索评估结果:", result)

from typing import List, Dict, Any
from langchain.schema import Document
import numpy as np
from embedding_validator import EmbeddingValidator

class AnswerValidator:
    """答案验证器"""
    
    def __init__(self):
        self.embedding_validator = None  # 延迟初始化
    
    def validate(self, 
                 question: str, 
                 generated_answer: str, 
                 expected_answer: str = "",
                 expected_sources: List[str] = None,
                 source_documents: List[Document] = None) -> Dict[str, Any]:
        """验证生成的答案"""
        if self.embedding_validator is None:
            from langchain_openai import OpenAIEmbeddings
            embedding_model = OpenAIEmbeddings()
            self.embedding_validator = EmbeddingValidator(embedding_model)
        
        # 1. 相关性评分 (与问题的相关性)
        relevance_score = self._calculate_relevance_score(question, generated_answer)
        
        # 2. 准确性评分 (与期望答案的相似度，如果有提供)
        accuracy_score = self._calculate_accuracy_score(generated_answer, expected_answer)
        
        # 3. 忠实度评分 (答案是否基于提供的文档)
        faithfulness_score = self._calculate_faithfulness_score(
            generated_answer, source_documents or []
        )
        
        # 4. 来源验证 (答案是否引用了正确的文档)
        source_coverage_score = self._calculate_source_coverage_score(
            generated_answer, expected_sources or [], source_documents or []
        )
        
        # 5. 语法和流畅性评分
        fluency_score = self._calculate_fluency_score(generated_answer)
        
        return {
            'relevance_score': relevance_score,
            'accuracy_score': accuracy_score,
            'faithfulness_score': faithfulness_score,
            'source_coverage_score': source_coverage_score,
            'fluency_score': fluency_score,
            'overall_score': self._calculate_overall_answer_score(
                relevance_score, accuracy_score, faithfulness_score, 
                source_coverage_score, fluency_score
            )
        }
    
    def _calculate_relevance_score(self, question: str, answer: str) -> float:
        """计算答案与问题的相关性"""
        return self.embedding_validator.calculate_similarity(question, answer)
    
    def _calculate_accuracy_score(self, generated: str, expected: str) -> float:
        """计算答案准确性"""
        if not expected:
            return 0.5  # 没有期望答案时返回中等分数
        
        return self.embedding_validator.calculate_similarity(generated, expected)
    
    def _calculate_faithfulness_score(self, answer: str, source_docs: List[Document]) -> float:
        """计算答案忠实度（基于源文档）"""
        if not source_docs:
            return 0.3  # 没有源文档时返回较低分数
        
        # 检查答案中的关键信息是否在源文档中
        answer_sentences = self._split_into_sentences(answer)
        source_text = " ".join([doc.page_content for doc in source_docs])
        
        faithful_sentences = 0
        total_sentences = len(answer_sentences)
        
        for sent in answer_sentences:
            if len(sent.strip()) > 10:  # 只考虑有意义的句子
                # 检查句子是否在源文档中能找到相关信息
                similarity = self.embedding_validator.calculate_similarity(sent, source_text)
                if similarity > 0.3:  # 阈值可调整
                    faithful_sentences += 1
        
        return faithful_sentences / total_sentences if total_sentences > 0 else 0.0
    
    def _calculate_source_coverage_score(self, answer: str, expected_sources: List[str], source_docs: List[Document]) -> float:
        """计算来源覆盖评分"""
        if not expected_sources or not source_docs:
            return 0.5  # 没有预期来源时返回中等分数
        
        # 检查答案是否提到了预期的来源信息
        answer_lower = answer.lower()
        expected_found = 0
        
        for expected in expected_sources:
            if expected.lower() in answer_lower:
                expected_found += 1
        
        return expected_found / len(expected_sources) if len(expected_sources) > 0 else 0.0
    
    def _calculate_fluency_score(self, answer: str) -> float:
        """计算语法和流畅性评分"""
        # 简单的启发式评分
        score = 0.5  # 基础分数
        
        # 长度合理性
        words = answer.split()
        if 10 <= len(words) <= 200:  # 合理的回答长度
            score += 0.2
        
        # 是否包含完整的句子
        sentences = self._split_into_sentences(answer)
        if len(sentences) >= 1:
            score += 0.2
        
        # 是否包含适当的标点符号
        if '.' in answer or '?' in answer or '!' in answer:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_overall_answer_score(self, *scores) -> float:
        """计算总体答案评分"""
        return np.mean(scores)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """简单的句子分割"""
        import re
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[.!?]+', text)
        # 过滤空字符串并去除首尾空格
        return [s.strip() for s in sentences if s.strip()]

def test_answer_validator():
    """测试答案验证器"""
    validator = AnswerValidator()
    
    # 测试数据
    question = "人工智能的发展历史是什么？"
    generated_answer = "人工智能起源于20世纪50年代，经过了多个发展阶段，现在已经成为重要的技术领域。"
    expected_answer = "人工智能始于1956年的达特茅斯会议，至今经历了多次起伏。"
    source_docs = [
        Document(page_content="人工智能起源于20世纪50年代"),
        Document(page_content="AI发展经历了多个阶段")
    ]
    
    result = validator.validate(
        question=question,
        generated_answer=generated_answer,
        expected_answer=expected_answer,
        source_documents=source_docs
    )
    
    print("答案验证结果:", result)

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from langchain.chains import RetrievalQA
import statistics

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = []
    
    def run_stress_test(self, qa_chain: RetrievalQA, config: Dict[str, Any]) -> Dict[str, Any]:
        """运行压力测试"""
        concurrent_users = config.get('concurrent_users', 5)
        requests_per_user = config.get('requests_per_user', 10)
        questions = config.get('questions', [])
        
        if not questions:
            questions = [
                "什么是人工智能?",
                "机器学习和深度学习有什么区别?",
                "RAG系统的工作原理是什么?"
            ]
        
        print(f"开始压力测试: {concurrent_users}并发用户, 每用户{requests_per_user}请求")
        
        start_time = time.time()
        
        # 使用线程池模拟并发用户
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for user_id in range(concurrent_users):
                # 为每个用户安排请求
                for req_id in range(requests_per_user):
                    question = questions[req_id % len(questions)]  # 循环使用问题
                    future = executor.submit(
                        self._single_request, 
                        qa_chain, 
                        question, 
                        user_id, 
                        req_id
                    )
                    futures.append(future)
            
            # 收集结果
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 分析结果
        analysis = self._analyze_performance_results(results, total_time)
        
        return analysis
    
    def _single_request(self, qa_chain: RetrievalQA, question: str, user_id: int, req_id: int) -> Dict[str, Any]:
        """执行单个请求"""
        start_time = time.time()
        
        try:
            result = qa_chain({"query": question})
            success = True
            error_msg = None
        except Exception as e:
            success = False
            error_msg = str(e)
            result = {'result': '', 'source_documents': []}
        
        duration = time.time() - start_time
        
        return {
            'user_id': user_id,
            'request_id': req_id,
            'question': question,
            'success': success,
            'duration': duration,
            'error': error_msg,
            'timestamp': time.time()
        }
    
    def _analyze_performance_results(self, results: List[Dict], total_duration: float) -> Dict[str, Any]:
        """分析性能测试结果"""
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        if successful_requests:
            durations = [r['duration'] for r in successful_requests]
            
            analysis = {
                'total_requests': len(results),
                'successful_requests': len(successful_requests),
                'failed_requests': len(failed_requests),
                'success_rate': len(successful_requests) / len(results) if results else 0,
                'total_duration': total_duration,
                'requests_per_second': len(successful_requests) / total_duration if total_duration > 0 else 0,
                'avg_response_time': statistics.mean(durations) if durations else 0,
                'median_response_time': statistics.median(durations) if durations else 0,
                'min_response_time': min(durations) if durations else 0,
                'max_response_time': max(durations) if durations else 0,
                'p95_response_time': self._percentile(durations, 95) if durations else 0,
                'p99_response_time': self._percentile(durations, 99) if durations else 0,
                'throughput': len(successful_requests) / total_duration if total_duration > 0 else 0,
                'efficiency_score': self._calculate_efficiency_score(
                    len(successful_requests), 
                    total_duration, 
                    statistics.mean(durations) if durations else 1.0
                )
            }
        else:
            analysis = {
                'total_requests': len(results),
                'successful_requests': 0,
                'failed_requests': len(failed_requests),
                'success_rate': 0,
                'total_duration': total_duration,
                'requests_per_second': 0,
                'avg_response_time': 0,
                'median_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'p95_response_time': 0,
                'p99_response_time': 0,
                'throughput': 0,
                'efficiency_score': 0
            }
        
        # 添加失败详情
        if failed_requests:
            analysis['failure_details'] = {
                'error_types': {},
                'most_common_errors': []
            }
            
            for fail in failed_requests:
                error = fail.get('error', 'Unknown error')
                if error in analysis['failure_details']['error_types']:
                    analysis['failure_details']['error_types'][error] += 1
                else:
                    analysis['failure_details']['error_types'][error] = 1
        
        return analysis
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index >= len(sorted_data):
                return sorted_data[-1]
            
            return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
    
    def _calculate_efficiency_score(self, successful_requests: int, total_time: float, avg_response_time: float) -> float:
        """计算效率评分"""
        # 基于吞吐量和响应时间的综合评分
        # 吞吐量得分 (越高越好)
        throughput = successful_requests / total_time if total_time > 0 else 0
        throughput_score = min(throughput / 10, 1.0)  # 假设10 req/s为满分
        
        # 响应时间得分 (越低越好)
        response_time_score = max(0, 1 - (avg_response_time / 5))  # 假设5秒为最低分
        
        # 成功率得分
        # 此处假设在调用函数之前已经知道总请求数
        # 实际使用中可能需要传递更多信息
        
        efficiency_score = (throughput_score * 0.6 + response_time_score * 0.4)
        return max(0, min(1, efficiency_score))

def test_performance_tester():
    """测试性能测试器"""
    # 注意：这需要一个真实的qa_chain实例才能运行
    print("性能测试器已准备就绪")
    print("使用方法: performance_tester.run_stress_test(qa_chain, config)")

#!/usr/bin/env python3
"""
LangChain RAG系统测试执行脚本
作为14年测试工程师，确保企业级RAG系统的质量验证
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_test_framework import RAGTestFramework
from document_loader import DocumentLoader, create_sample_documents
from embedding_validator import test_embedding_validator
from retrieval_evaluator import test_retrieval_evaluator
from answer_validator import test_answer_validator
from performance_tester import test_performance_tester


def setup_environment():
    """设置环境变量"""
    env_file = project_root / ".env"
    if env_file.exists():
        import dotenv
        dotenv.load_dotenv(env_file)


def run_rag_demo():
    """运行RAG测试演示"""
    print("="*70)
    print("LangChain RAG系统测试框架 - 演示测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 1. 创建测试数据
    print("\n1. 创建测试文档...")
    documents = create_sample_documents()
    print(f"   ✅ 创建了 {len(documents)} 个测试文档")
    
    # 2. 创建查询-真实文档对
    queries_with_ground_truth = [
        {
            'query': '人工智能的定义是什么？',
            'expected_docs': [documents[0]]  # 期望返回第一个人工智能概述文档
        },
        {
            'query': '机器学习和人工智能的关系',
            'expected_docs': [documents[1], documents[0]]  # 期望返回机器学习和AI概述文档
        },
        {
            'query': '深度学习的基本原理',
            'expected_docs': [documents[2]]  # 期望返回深度学习原理文档
        }
    ]
    
    # 3. 创建测试问题
    test_questions = [
        {
            'question': '什么是人工智能?',
            'expected_answer': '人工智能是计算机科学的一个分支',
            'expected_sources': ['人工智能概述']
        },
        {
            'question': '机器学习与人工智能有什么关系?',
            'expected_answer': '机器学习是人工智能的一个子领域',
            'expected_sources': ['机器学习基础']
        },
        {
            'question': '深度学习是如何工作的?',
            'expected_answer': '深度学习基于人工神经网络',
            'expected_sources': ['深度学习原理']
        }
    ]
    
    # 4. 配置压力测试
    stress_config = {
        'concurrent_users': 3,
        'requests_per_user': 5,
        'questions': [q['question'] for q in test_questions]
    }
    
    # 5. 初始化并运行测试
    print("\n2. 初始化RAG测试框架...")
    rag_tester = RAGTestFramework()
    
    print("\n3. 运行完整测试套件...")
    results = rag_tester.run_complete_test_suite(
        documents=documents,
        queries_with_ground_truth=queries_with_ground_truth,
        test_questions=test_questions,
        stress_config=stress_config
    )
    
    # 6. 输出结果摘要
    print(f"\n{'='*70}")
    print("测试结果摘要")
    print(f"{'='*70}")
    
    print(f"设置时间: {results['setup_time']:.2f}s")
    
    retrieval_metrics = results['retrieval_metrics']
    print(f"检索性能 - 精确率: {retrieval_metrics.get('avg_precision', 0):.3f}, "
          f"召回率: {retrieval_metrics.get('avg_recall', 0):.3f}, "
          f"F1分数: {retrieval_metrics.get('avg_f1_score', 0):.3f}")
    
    answer_metrics = results['answer_metrics']
    print(f"答案质量 - 相关性: {answer_metrics.get('avg_relevance', 0):.3f}, "
          f"准确性: {answer_metrics.get('avg_accuracy', 0):.3f}, "
          f"忠实度: {answer_metrics.get('avg_faithfulness', 0):.3f}")
    
    perf_metrics = results['performance_metrics']
    print(f"性能表现 - 成功率: {perf_metrics.get('success_rate', 0):.1%}, "
          f"吞吐量: {perf_metrics.get('throughput', 0):.2f} req/s, "
          f"平均响应: {perf_metrics.get('avg_response_time', 0):.3f}s")
    
    print(f"总体评分: {results['overall_score']:.3f}")
    
    # 7. 导出测试报告
    print(f"\n4. 生成测试报告...")
    rag_tester.export_test_report("rag_test_report.html")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


def run_unit_tests():
    """运行单元测试"""
    print("运行各个组件的单元测试...")
    
    print("\n测试嵌入验证器...")
    test_embedding_validator()
    
    print("\n测试检索评估器...")
    test_retrieval_evaluator()
    
    print("\n测试答案验证器...")
    test_answer_validator()
    
    print("\n测试性能测试器...")
    test_performance_tester()
    
    print("\n所有单元测试完成！")


def run_custom_test(doc_dir: str, num_samples: int = 10):
    """运行自定义测试"""
    print(f"运行自定义RAG测试，文档目录: {doc_dir}")
    
    # 加载文档
    loader = DocumentLoader()
    documents = loader.load_from_directory(doc_dir)
    
    if not documents:
        print(f"警告: 在目录 {doc_dir} 中未找到任何文档")
        return
    
    print(f"加载了 {len(documents)} 个文档")
    
    # 限制文档数量以加快测试
    if len(documents) > num_samples:
        documents = documents[:num_samples]
        print(f"限制为前 {num_samples} 个文档进行测试")
    
    # 创建简单的测试数据
    sample_queries = [
        {'query': '文档的主要内容是什么？', 'expected_docs': documents[:2]},
        {'query': '这里讨论了哪些主题？', 'expected_docs': documents[:3]},
    ]
    
    sample_questions = [
        {'question': '这个文档集的主要话题是什么?', 'expected_answer': ''},
        {'question': '能否总结一下这些文档的内容?', 'expected_answer': ''}
    ]
    
    # 运行测试
    rag_tester = RAGTestFramework()
    results = rag_tester.run_complete_test_suite(
        documents=documents,
        queries_with_ground_truth=sample_queries,
        test_questions=sample_questions
    )
    
    print(f"自定义测试完成，总体评分: {results['overall_score']:.3f}")


def main():
    parser = argparse.ArgumentParser(description='LangChain RAG系统测试框架')
    parser.add_argument('--demo', action='store_true',
                       help='运行演示测试')
    parser.add_argument('--unit-tests', action='store_true',
                       help='运行单元测试')
    parser.add_argument('--custom', type=str,
                       help='运行自定义测试，指定文档目录')
    parser.add_argument('--samples', type=int, default=10,
                       help='自定义测试时使用的样本数量 (默认: 10)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    if args.demo:
        run_rag_demo()
    elif args.unit_tests:
        run_unit_tests()
    elif args.custom:
        run_custom_test(args.custom, args.samples)
    else:
        # 默认运行演示
        run_rag_demo()


if __name__ == "__main__":
    main()
