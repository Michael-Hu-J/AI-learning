from typing import List, Dict, Any
import time
from crew_manager import CrewManager
from tasks.test_generation_task import (
    TestGenerationTask, TestExecutionTask, 
    ResultAnalysisTask, ReportGenerationTask
)

class TestOrchestrator:
    """测试编排器"""
    
    def __init__(self, 
                 crew_manager: CrewManager,
                 test_generation_task,
                 test_execution_task, 
                 result_analysis_task,
                 report_generation_task):
        self.crew_manager = crew_manager
        self.test_generation_task = test_generation_task
        self.test_execution_task = test_execution_task
        self.result_analysis_task = result_analysis_task
        self.report_generation_task = report_generation_task
        self.execution_history = []
    
    def execute_campaign(self, 
                        target_system_description: str, 
                        test_requirements: List[str],
                        test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行测试活动"""
        start_time = time.time()
        
        print("开始执行多智能体测试活动...")
        
        # 阶段1: 测试设计
        print("阶段1: 测试设计中...")
        test_design_result = self._execute_test_design(
            target_system_description, test_requirements
        )
        
        # 从设计结果中提取测试用例
        test_cases = self._extract_test_cases_from_design(test_design_result)
        
        # 阶段2: 测试执行
        print("阶段2: 测试执行中...")
        test_execution_result = self._execute_test_execution(
            test_cases, target_system_description
        )
        
        # 阶段3: 结果分析
        print("阶段3: 结果分析中...")
        analysis_result = self._execute_result_analysis(
            test_execution_result
        )
        
        # 阶段4: 报告生成
        print("阶段4: 报告生成中...")
        report_result = self._execute_report_generation(
            analysis_result
        )
        
        total_duration = time.time() - start_time
        
        # 汇总结果
        campaign_results = {
            'timestamp': time.time(),
            'total_duration': total_duration,
            'stages': {
                'design': test_design_result,
                'execution': test_execution_result,
                'analysis': analysis_result,
                'report': report_result
            },
            'summary': {
                'total_tasks': 4,
                'completed_tasks': 4,
                'success_rate': 1.0,
                'overall_pass_rate': self._calculate_overall_pass_rate(test_execution_result)
            },
            'metrics': self._extract_metrics(test_execution_result, analysis_result)
        }
        
        self.execution_history.append(campaign_results)
        
        print(f"测试活动完成，耗时 {total_duration:.2f} 秒")
        return campaign_results
    
    def _execute_test_design(self, target_system_description: str, test_requirements: List[str]) -> Dict[str, Any]:
        """执行测试设计"""
        task = self.test_generation_task.create_task(
            test_designer_agent=self.crew_manager.test_designer_agent,
            target_system_description=target_system_description,
            test_requirements=test_requirements
        )
        
        result = self.crew_manager.execute_sequential_crew([task])
        
        return {
            'task_name': 'Test Design',
            'status': 'completed',
            'output': str(result),
            'timestamp': time.time()
        }
    
    def _execute_test_execution(self, test_cases: List[Dict[str, Any]], target_system_desc: str) -> Dict[str, Any]:
        """执行测试执行"""
        task = self.test_execution_task.create_task(
            test_executor_agent=self.crew_manager.test_executor_agent,
            test_cases=test_cases,
            target_system_endpoint=target_system_desc
        )
        
        result = self.crew_manager.execute_sequential_crew([task])
        
        return {
            'task_name': 'Test Execution',
            'status': 'completed',
            'output': str(result),
            'timestamp': time.time(),
            'test_cases_executed': len(test_cases)
        }
    
    def _execute_result_analysis(self, test_execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行结果分析"""
        task = self.result_analysis_task.create_task(
            test_analyzer_agent=self.crew_manager.test_analyzer_agent,
            test_results=test_execution_result
        )
        
        result = self.crew_manager.execute_sequential_crew([task])
        
        return {
            'task_name': 'Result Analysis',
            'status': 'completed',
            'output': str(result),
            'timestamp': time.time()
        }
    
    def _execute_report_generation(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告生成"""
        task = self.report_generation_task.create_task(
            quality_assurance_agent=self.crew_manager.quality_assurance_agent,
            analysis_results=analysis_result
        )
        
        result = self.crew_manager.execute_sequential_crew([task])
        
        return {
            'task_name': 'Report Generation',
            'status': 'completed',
            'output': str(result),
            'timestamp': time.time()
        }
    
    def _extract_test_cases_from_design(self, design_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从设计结果中提取测试用例"""
        # 在实际实现中，这里会解析智能体生成的设计结果
        # 为了演示，我们返回一些模拟的测试用例
        return [
            {
                'name': 'Functional Test Case 1',
                'type': 'functional',
                'priority': 'high',
                'steps': '1. Input data 2. Execute function 3. Verify output',
                'expected': 'Correct output based on input'
            },
            {
                'name': 'Performance Test Case 1', 
                'type': 'performance',
                'priority': 'medium',
                'steps': '1. Send concurrent requests 2. Measure response time',
                'expected': 'Response time < 2 seconds'
            }
        ]
    
    def _calculate_overall_pass_rate(self, execution_result: Dict[str, Any]) -> float:
        """计算总体通过率"""
        # 在实际实现中，会从执行结果中提取通过率
        # 这里返回一个模拟值
        return 0.85  # 假设85%的通过率
    
    def _extract_metrics(self, execution_result: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键指标"""
        return {
            'pass_rate': self._calculate_overall_pass_rate(execution_result),
            'total_test_cases': execution_result.get('test_cases_executed', 0),
            'critical_issues': 2,  # 模拟值
            'high_issues': 5,      # 模拟值
            'medium_issues': 8,    # 模拟值
            'low_issues': 12,      # 模拟值
            'avg_response_time': 1.2,  # 秒
            'max_response_time': 3.5,  # 秒
            'success_rate': 0.85
        }
    
    def run_smoke_tests(self, target_system_description: str) -> Dict[str, Any]:
        """运行冒烟测试"""
        print("运行冒烟测试...")
        
        # 创建基本的健康检查测试
        smoke_tests = [
            {
                'name': 'System Health Check',
                'type': 'health',
                'priority': 'critical',
                'steps': 'Check if system responds to basic requests',
                'expected': 'System should respond without errors'
            }
        ]
        
        # 执行简化的测试流程
        execution_result = self._execute_test_execution(smoke_tests, target_system_description)
        
        # 简化的分析
        smoke_analysis = {
            'task_name': 'Smoke Test Analysis',
            'status': 'completed',
            'output': 'System health check passed',
            'timestamp': time.time()
        }
        
        return {
            'test_type': 'smoke',
            'target_system': target_system_description,
            'execution_result': execution_result,
            'analysis_result': smoke_analysis,
            'passed': True  # 假设冒烟测试通过
        }
    
    def run_regression_tests(self, baseline_data: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
        """运行回归测试"""
        print("运行回归测试对比...")
        
        # 简化的回归分析
        regression_analysis = {
            'baseline_metrics': baseline_data.get('metrics', {}),
            'current_metrics': current_data.get('metrics', {}),
            'regression_detected': False,  # 默认无回归
            'differences': {},
            'recommendations': []
        }
        
        # 比较关键指标
        baseline_metrics = regression_analysis['baseline_metrics']
        current_metrics = regression_analysis['current_metrics']
        
        # 检查是否有显著差异
        for metric in ['pass_rate', 'success_rate', 'avg_response_time']:
            baseline_val = baseline_metrics.get(metric, 0)
            current_val = current_metrics.get(metric, 0)
            
            if metric in ['avg_response_time']:
                # 响应时间越小越好
                if current_val > baseline_val * 1.2:  # 增加超过20%
                    regression_analysis['regression_detected'] = True
                    regression_analysis['differences'][metric] = {
                        'baseline': baseline_val,
                        'current': current_val,
                        'change': current_val - baseline_val
                    }
            else:
                # 通过率等越大越好
                if current_val < baseline_val * 0.95:  # 降低超过5%
                    regression_analysis['regression_detected'] = True
                    regression_analysis['differences'][metric] = {
                        'baseline': baseline_val,
                        'current': current_val,
                        'change': current_val - baseline_val
                    }
        
        # 生成建议
        if regression_analysis['regression_detected']:
            regression_analysis['recommendations'].append(
                "检测到性能回归，建议检查最近的代码变更"
            )
        else:
            regression_analysis['recommendations'].append(
                "未检测到显著回归，系统性能稳定"
            )
        
        return regression_analysis

def demonstrate_orchestration():
    """演示测试编排"""
    print("演示CrewAI测试编排器...")
    
    # 这里需要实际的组件实例，为简洁起见返回说明
    return {
        'orchestrator': 'TestOrchestrator',
        'capabilities': [
            'Campaign Execution',
            'Sequential Processing', 
            'Result Aggregation',
            'Metrics Extraction'
        ]
    }