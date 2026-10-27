import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict, List
import io
import base64

class GraphVisualizer:
    """图可视化工具"""
    
    def __init__(self):
        self.graph_data = None
    
    def visualize_execution_flow(self, execution_trace: List[str], save_path: str = None):
        """可视化执行流程"""
        # 创建有向图
        G = nx.DiGraph()
        
        # 添加节点和边
        nodes = []
        edges = []
        
        for i, trace in enumerate(execution_trace):
            node_name = f"Step_{i}"
            G.add_node(node_name, label=f"{i+1}. {trace[:30]}...")
            
            if i > 0:
                G.add_edge(f"Step_{i-1}", node_name)
        
        # 设置图形布局
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # 绘制图形
        plt.figure(figsize=(12, 8))
        nx.draw(G, pos, with_labels=True, node_color='lightblue', 
                node_size=3000, font_size=8, font_weight='bold',
                arrows=True, arrowsize=20)
        
        plt.title("AI Agent Test Execution Flow")
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def visualize_test_results(self, test_results: Dict, save_path: str = None):
        """可视化测试结果"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 提取关键指标
        metrics = []
        values = []
        
        if 'overall' in test_results:
            overall = test_results['overall']
            metrics.extend(['Passed', 'Error Count', 'Score'])
            values.extend([
                1 if overall.get('passed', False) else 0,
                overall.get('error_count', 0),
                overall.get('score', 0)
            ])
        
        if 'input_validation' in test_results:
            input_val = test_results['input_validation']
            metrics.append('Input Valid')
            values.append(1 if input_val.get('input_valid', False) else 0)
        
        if 'response_validation' in test_results:
            resp_val = test_results['response_validation']
            for key, value in resp_val.items():
                if isinstance(value, bool):
                    metrics.append(key.replace('_', ' ').title())
                    values.append(1 if value else 0)
        
        # 创建柱状图
        y_pos = range(len(metrics))
        ax.bar(y_pos, values, color=['green' if v >= 0.5 else 'red' for v in values])
        
        ax.set_xlabel('Metrics')
        ax.set_ylabel('Value')
        ax.set_title('AI Agent Test Results Visualization')
        ax.set_xticks(y_pos)
        ax.set_xticklabels(metrics, rotation=45, ha='right')
        
        # 在柱子上显示数值
        for i, v in enumerate(values):
            ax.text(i, v + 0.05, str(v), ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def generate_report_summary(self, test_results: Dict) -> str:
        """生成测试报告摘要"""
        summary_parts = []
        
        if 'overall' in test_results:
            overall = test_results['overall']
            status = "✅ PASSED" if overall.get('passed', False) else "❌ FAILED"
            summary_parts.append(f"Overall Status: {status}")
            summary_parts.append(f"Score: {overall.get('score', 0):.2f}")
            summary_parts.append(f"Errors: {overall.get('error_count', 0)}")
        
        if 'input_validation' in test_results:
            input_val = test_results['input_validation']
            valid = "✅" if input_val.get('input_valid', False) else "❌"
            summary_parts.append(f"Input Validation: {valid}")
        
        if 'response_validation' in test_results:
            resp_val = test_results['response_validation']
            quality_score = resp_val.get('response_quality_score', 0)
            summary_parts.append(f"Response Quality: {quality_score:.2f}")
        
        return "\n".join(summary_parts)

def visualize_test_execution(state):
    """可视化测试执行状态"""
    visualizer = GraphVisualizer()
    
    # 可视化执行流程
    visualizer.visualize_execution_flow(
        state['execution_trace'], 
        "execution_flow.png"
    )
    
    # 可视化测试结果
    visualizer.visualize_test_results(
        state['test_results'],
        "test_results.png"
    )
    
    # 生成摘要
    summary = visualizer.generate_report_summary(state['test_results'])
    print("Test Report Summary:")
    print(summary)