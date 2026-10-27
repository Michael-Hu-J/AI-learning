from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List, Dict, Any, Optional
import hashlib
import os
import sys
import time
from pathlib import Path
import numpy as np
from document_loader import DocumentLoader
from embedding_validator import EmbeddingValidator
from retrieval_evaluator import RetrievalEvaluator
from answer_validator import AnswerValidator
from performance_tester import PerformanceTester

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import llm_env


class _DemoEmbeddings:
    """演示模式嵌入模型，无需 API Key"""

    _DIM = 384

    def _vectorize(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode()).digest()
        vec = [(b / 255.0) for b in digest] * (self._DIM // len(digest) + 1)
        return vec[: self._DIM]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vectorize(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vectorize(text)


class _DemoLLM:
    """演示模式 QA 链（callable），无需真实 LLM"""

    def __init__(self, retriever):
        self.retriever = retriever

    def __call__(self, inputs):
        question = inputs.get("query", "")
        docs = self.retriever.get_relevant_documents(question)
        context = docs[0].page_content[:200] if docs else "无相关文档"
        return {
            "result": f"[演示模式] 基于检索内容回答：{context[:120]}",
            "source_documents": docs,
        }


def _use_demo_mode(demo_mode: Optional[bool]) -> bool:
    if demo_mode is not None:
        return demo_mode
    if os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes"):
        return True
    return not (os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY"))


class RAGTestFramework:
    """RAG系统测试验证框架"""
    
    def __init__(self, 
                 embedding_model=None,
                 llm_model=None,
                 chunk_size=1000,
                 chunk_overlap=100,
                 demo_mode: Optional[bool] = None):
        self.demo_mode = _use_demo_mode(demo_mode)
        if self.demo_mode:
            self.embedding_model = _DemoEmbeddings()
            self.llm = None
            print("  ℹ️  演示模式：使用本地模拟嵌入/LLM，无需 API Key")
        else:
            self.embedding_model = llm_env.create_openai_embeddings(model=embedding_model)
            self.llm = llm_env.create_chat_openai(model=llm_model, temperature=0)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vectorstore = None
        self.retriever = None
        self.qa_chain = None
        
        # 初始化验证器
        self.embedding_validator = EmbeddingValidator(self.embedding_model)
        self.retrieval_evaluator = RetrievalEvaluator()
        self.answer_validator = AnswerValidator(embedding_model=self.embedding_model)
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
        split_docs = [d for d in split_docs if d.page_content and d.page_content.strip()]
        
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
        if self.demo_mode:
            self.qa_chain = _DemoLLM(self.retriever)
        else:
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