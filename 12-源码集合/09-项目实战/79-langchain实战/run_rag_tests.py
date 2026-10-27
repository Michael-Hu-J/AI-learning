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