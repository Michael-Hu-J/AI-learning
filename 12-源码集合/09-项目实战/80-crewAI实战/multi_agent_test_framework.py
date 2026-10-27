from crewai import Agent, Task, Crew
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
from agents.test_designer_agent import TestDesignerAgent
from agents.test_executor_agent import TestExecutorAgent
from agents.test_analyzer_agent import TestAnalyzerAgent
from agents.quality_assurance_agent import QualityAssuranceAgent
from tasks.test_generation_task import TestGenerationTask
from tasks.test_execution_task import TestExecutionTask
from tasks.result_analysis_task import ResultAnalysisTask
from tasks.report_generation_task import ReportGenerationTask
from crew_manager import CrewManager
from test_orchestrator import TestOrchestrator

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import llm_env

class MultiAgentTestFramework:
    """多智能体协作测试框架"""
    
    def __init__(self, 
                 llm_model=None, 
                 verbose=False,
                 max_rpm=100):
        self.llm = llm_env.create_chat_openai(model=llm_model)
        self.verbose = verbose
        self.max_rpm = max_rpm
        self.crew_manager = None
        self.orchestrator = None
        self.test_results = {}
        
        # 初始化各组件
        self._initialize_agents()
        self._initialize_tasks()
        self._initialize_crew()
        self._initialize_orchestrator()
    
    def _initialize_agents(self):
        """初始化智能体"""
        self.test_designer_agent = TestDesignerAgent(self.llm, self.verbose)
        self.test_executor_agent = TestExecutorAgent(self.llm, self.verbose)
        self.test_analyzer_agent = TestAnalyzerAgent(self.llm, self.verbose)
        self.quality_assurance_agent = QualityAssuranceAgent(self.llm, self.verbose)
    
    def _initialize_tasks(self):
        """初始化任务"""
        self.test_generation_task = TestGenerationTask()
        self.test_execution_task = TestExecutionTask()
        self.result_analysis_task = ResultAnalysisTask()
        self.report_generation_task = ReportGenerationTask()
    
    def _initialize_crew(self):
        """初始化智能体编队"""
        self.crew_manager = CrewManager(
            test_designer_agent=self.test_designer_agent.get_agent(),
            test_executor_agent=self.test_executor_agent.get_agent(),
            test_analyzer_agent=self.test_analyzer_agent.get_agent(),
            quality_assurance_agent=self.quality_assurance_agent.get_agent(),
            max_rpm=self.max_rpm,
            verbose=self.verbose
        )
    
    def _initialize_orchestrator(self):
        """初始化测试编排器"""
        self.orchestrator = TestOrchestrator(
            crew_manager=self.crew_manager,
            test_generation_task=self.test_generation_task,
            test_execution_task=self.test_execution_task,
            result_analysis_task=self.result_analysis_task,
            report_generation_task=self.report_generation_task
        )
    
    def run_test_campaign(self, 
                         target_system_description: str, 
                         test_requirements: List[str],
                         test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行测试活动"""
        print(f"开始执行测试活动...")
        print(f"目标系统: {target_system_description[:50]}...")
        print(f"测试需求: {len(test_requirements)} 项")
        print(f"测试场景: {len(test_scenarios)} 个")
        
        # 执行测试活动
        campaign_results = self.orchestrator.execute_campaign(
            target_system_description=target_system_description,
            test_requirements=test_requirements,
            test_scenarios=test_scenarios
        )
        
        self.test_results = campaign_results
        return campaign_results
    
    def run_regression_tests(self, 
                           baseline_results: Dict[str, Any],
                           current_results: Dict[str, Any]) -> Dict[str, Any]:
        """运行回归测试"""
        regression_analysis = {
            'baseline_results': baseline_results,
            'current_results': current_results,
            'differences': self._compare_results(baseline_results, current_results),
            'regression_detected': self._detect_regressions(baseline_results, current_results),
            'recommendations': []
        }
        
        # 如果检测到回归，生成建议
        if regression_analysis['regression_detected']:
            regression_analysis['recommendations'] = self._generate_regression_recommendations(
                baseline_results, current_results
            )
        
        return regression_analysis
    
    def _compare_results(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """比较测试结果"""
        differences = {}
        
        # 比较关键指标
        baseline_metrics = baseline.get('metrics', {})
        current_metrics = current.get('metrics', {})
        
        for metric in ['pass_rate', 'success_rate', 'error_rate', 'avg_response_time']:
            baseline_value = baseline_metrics.get(metric, 0)
            current_value = current_metrics.get(metric, 0)
            
            if metric in ['pass_rate', 'success_rate']:  # 越高越好
                change = current_value - baseline_value
                if change < -0.05:  # 下降超过5%
                    differences[metric] = {
                        'baseline': baseline_value,
                        'current': current_value,
                        'change': change,
                        'status': 'DEGRADED'
                    }
            elif metric in ['error_rate']:  # 越低越好
                change = current_value - baseline_value
                if change > 0.05:  # 上升超过5%
                    differences[metric] = {
                        'baseline': baseline_value,
                        'current': current_value,
                        'change': change,
                        'status': 'DEGRADED'
                    }
            else:  # 其他指标，如响应时间
                change = current_value - baseline_value
                if change > 0.1:  # 显著上升
                    differences[metric] = {
                        'baseline': baseline_value,
                        'current': current_value,
                        'change': change,
                        'status': 'DEGRADED'
                    }
        
        return differences
    
    def _detect_regressions(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> bool:
        """检测回归"""
        differences = self._compare_results(baseline, current)
        return len([d for d in differences.values() if d['status'] == 'DEGRADED']) > 0
    
    def _generate_regression_recommendations(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
        """生成回归建议"""
        recommendations = []
        
        differences = self._compare_results(baseline, current)
        
        for metric, diff in differences.items():
            if diff['status'] == 'DEGRADED':
                if metric == 'pass_rate':
                    recommendations.append(
                        f"测试通过率下降 {diff['change']:.2%}，建议检查最近的代码变更"
                    )
                elif metric == 'success_rate':
                    recommendations.append(
                        f"成功率下降 {diff['change']:.2%}，可能存在功能缺陷"
                    )
                elif metric == 'error_rate':
                    recommendations.append(
                        f"错误率上升 {diff['change']:.2%}，需要调查错误原因"
                    )
                elif metric == 'avg_response_time':
                    recommendations.append(
                        f"平均响应时间增加 {diff['change']:.3f}s，可能存在性能问题"
                    )
        
        return recommendations
    
    def generate_test_report(self, filename: str = "crewai_test_report.html") -> str:
        """生成测试报告"""
        import json
        import datetime
        
        # 准备报告数据
        report_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'framework': 'Multi-Agent Test Framework (CrewAI)',
            'results': self.test_results,
            'summary': self._generate_summary()
        }
        
        # 生成HTML报告
        html_content = f"""
        <html>
        <head>
            <title>CrewAI多智能体测试报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }}
                .metric {{ display: inline-block; margin: 5px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .critical {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CrewAI多智能体测试报告</h1>
                <p>生成时间: {report_data['timestamp']}</p>
            </div>
            
            <div class="section">
                <h2>测试摘要</h2>
                <div>{self._format_summary_html(report_data['summary'])}</div>
            </div>
            
            <div class="section">
                <h2>详细结果</h2>
                <pre>{json.dumps(report_data['results'], indent=2, ensure_ascii=False)}</pre>
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"测试报告已生成: {filename}")
        return filename
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成测试摘要"""
        if not self.test_results:
            return {'status': 'NO_RESULTS', 'message': '暂无测试结果'}
        
        # 从测试结果中提取关键指标
        summary = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'success_rate': 0,
            'total_agents_involved': 4,  # 固定4个智能体
            'execution_time': 0,
            'critical_issues': 0,
            'warnings': 0
        }
        
        # 解析测试结果以生成摘要
        tasks = self.test_results.get('tasks', [])
        summary['total_tasks'] = len(tasks)
        summary['completed_tasks'] = len([t for t in tasks if t.get('status') == 'completed'])
        
        if summary['total_tasks'] > 0:
            summary['success_rate'] = summary['completed_tasks'] / summary['total_tasks']
        
        # 检查是否有问题
        for task in tasks:
            output = task.get('output', '')
            if 'error' in output.lower() or 'fail' in output.lower():
                summary['critical_issues'] += 1
            elif 'warning' in output.lower():
                summary['warnings'] += 1
        
        return summary
    
    def _format_summary_html(self, summary: Dict[str, Any]) -> str:
        """格式化摘要为HTML"""
        if summary.get('status') == 'NO_RESULTS':
            return '<p class="critical">暂无测试结果</p>'
        
        html_parts = []
        
        # 总体状态
        if summary['success_rate'] >= 0.9:
            status_class = 'good'
            status_text = '✅ 测试通过'
        elif summary['success_rate'] >= 0.7:
            status_class = 'warning'
            status_text = '⚠️ 部分通过'
        else:
            status_class = 'critical'
            status_text = '❌ 测试失败'
        
        html_parts.append(f'<p class="{status_class}"><strong>{status_text}</strong></p>')
        
        # 关键指标
        html_parts.append('<div>')
        html_parts.append(f'<span class="metric">总任务数: {summary["total_tasks"]}</span>')
        html_parts.append(f'<span class="metric">完成任务: {summary["completed_tasks"]}</span>')
        html_parts.append(f'<span class="metric">成功率: {summary["success_rate"]:.1%}</span>')
        html_parts.append(f'<span class="metric">智能体数: {summary["total_agents_involved"]}</span>')
        if summary['critical_issues'] > 0:
            html_parts.append(f'<span class="metric critical">严重问题: {summary["critical_issues"]}</span>')
        if summary['warnings'] > 0:
            html_parts.append(f'<span class="metric warning">警告: {summary["warnings"]}</span>')
        html_parts.append('</div>')
        
        return ''.join(html_parts)

def demonstrate_multi_agent_testing():
    """演示多智能体测试"""
    print("开始演示CrewAI多智能体测试框架...")
    
    # 创建测试框架实例
    framework = MultiAgentTestFramework(verbose=True)
    
    # 定义目标系统
    target_system = """
    一个基于大语言模型的客户服务机器人系统，具备以下功能：
    1. 理解客户问题
    2. 提供产品信息查询
    3. 处理订单状态查询
    4. 协助退换货流程
    5. 转接人工客服
    """
    
    # 定义测试需求
    test_requirements = [
        "验证客户服务机器人的问题理解能力",
        "测试产品信息查询功能的准确性",
        "检查订单状态查询的响应速度",
        "验证退换货流程的引导准确性",
        "确认人工客服转接功能正常"
    ]
    
    # 定义测试场景
    test_scenarios = [
        {
            "name": "产品咨询场景",
            "description": "客户询问产品特性",
            "inputs": ["这款手机的电池续航怎么样？", "支持快充吗？"],
            "expected_outcomes": ["提供准确的产品信息", "推荐相关配件"]
        },
        {
            "name": "订单查询场景", 
            "description": "客户查询订单状态",
            "inputs": ["我的订单Z123456789什么时候发货？"],
            "expected_outcomes": ["显示准确的订单状态", "提供预计送达时间"]
        }
    ]
    
    # 执行测试活动
    results = framework.run_test_campaign(
        target_system_description=target_system,
        test_requirements=test_requirements,
        test_scenarios=test_scenarios
    )
    
    print(f"测试活动完成！结果: {results}")
    
    # 生成报告
    framework.generate_test_report()
    
    return results