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