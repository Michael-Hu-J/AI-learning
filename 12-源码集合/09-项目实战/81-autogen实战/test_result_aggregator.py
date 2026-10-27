from typing import Dict, Any, List
import statistics
from datetime import datetime

class TestResultAggregator:
    """测试结果聚合器"""
    
    def __init__(self):
        self.aggregated_results = {}
    
    def aggregate_results(self, 
                         chat_result: Any, 
                         analysis_result: Dict[str, Any],
                         test_objectives: List[str]) -> Dict[str, Any]:
        """聚合测试结果"""
        # 提取聊天结果的关键信息
        chat_summary = self._extract_chat_summary(chat_result)
        
        # 合并分析结果
        combined_results = {
            'timestamp': datetime.now().isoformat(),
            'chat_summary': chat_summary,
            'conversation_analysis': analysis_result,
            'test_objectives': test_objectives,
            'summary': self._create_comprehensive_summary(chat_summary, analysis_result, test_objectives)
        }
        
        # 计算综合评分
        combined_results['summary']['overall_score'] = self._calculate_comprehensive_score(combined_results)
        
        self.aggregated_results = combined_results
        return combined_results
    
    def _extract_chat_summary(self, chat_result: Any) -> Dict[str, Any]:
        """从聊天结果中提取摘要"""
        # 由于chat_result的结构可能因AutoGen版本而异，这里提供通用处理
        summary = {
            'total_turns': getattr(chat_result, 'turns', 0) if hasattr(chat_result, 'turns') else 0,
            'final_summary': getattr(chat_result, 'summary', 'No summary available'),
            'cost': getattr(chat_result, 'cost', 0) if hasattr(chat_result, 'cost') else 0,
            'start_time': getattr(chat_result, 'start_time', None),
            'end_time': getattr(chat_result, 'end_time', None)
        }
        
        # 如果chat_result有消息历史，也包含进来
        if hasattr(chat_result, 'chat_history'):
            summary['has_history'] = True
            summary['history_length'] = len(chat_result.chat_history) if chat_result.chat_history else 0
        else:
            summary['has_history'] = False
            summary['history_length'] = 0
        
        return summary
    
    def _create_comprehensive_summary(self, 
                                    chat_summary: Dict[str, Any], 
                                    analysis_result: Dict[str, Any],
                                    test_objectives: List[str]) -> Dict[str, Any]:
        """创建综合摘要"""
        # 从分析结果中提取关键指标
        sentiment = analysis_result.get('sentiment', {})
        issues = analysis_result.get('issues', {})
        topics = analysis_result.get('topics', {})
        participation = analysis_result.get('participation', {})
        alignment = analysis_result.get('objective_alignment', {})
        
        # 计算各项评分
        functionality_score = self._calculate_functionality_score(issues, topics)
        security_score = self._calculate_security_score(issues, topics)
        performance_score = self._calculate_performance_score(issues, topics)
        compatibility_score = self._calculate_compatibility_score(issues, topics)
        
        return {
            'functionality_pass_rate': functionality_score,
            'security_risk_level': self._determine_security_level(issues),
            'performance_score': performance_score,
            'compatibility_score': compatibility_score,
            'communication_effectiveness': participation.get('participation_balance', 0.5),
            'requirement_coverage': alignment.get('coverage_score', 0),
            'defect_density': issues.get('issue_density', 0),
            'test_completion_rate': min(1.0, len(issues.get('issues', [])) / max(1, len(test_objectives))),
            'risk_assessment': self._assess_overall_risk(issues, sentiment)
        }
    
    def _calculate_functionality_score(self, issues: Dict, topics: Dict) -> float:
        """计算功能测试评分"""
        # 基于问题数量和功能话题覆盖计算
        high_severity_issues = issues.get('severity_distribution', {}).get('high', 0)
        medium_severity_issues = issues.get('severity_distribution', {}).get('medium', 0)
        
        # 严重问题大幅降低分数
        deduction = high_severity_issues * 0.3 + medium_severity_issues * 0.1
        base_score = max(0, 1 - deduction)
        
        # 如果功能话题被充分讨论，略有加分
        functional_topic_ratio = topics.get('distribution', {}).get('functionality_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
        if functional_topic_ratio > 0.3:  # 如果功能话题占比超过30%
            base_score = min(1.0, base_score + 0.1)
        
        return round(base_score, 3)
    
    def _calculate_security_score(self, issues: Dict, topics: Dict) -> float:
        """计算安全测试评分"""
        # 安全问题严重影响评分
        security_issues = sum(issues.get('severity_distribution', {}).values())
        high_security_issues = issues.get('severity_distribution', {}).get('high', 0)
        
        if high_security_issues > 0:
            return 0.1  # 有高危安全问题直接评为低分
        elif security_issues > 0:
            return 0.4  # 有一般安全问题评为中等偏下
        else:
            # 没有安全问题，但要看是否充分讨论了安全话题
            security_topic_ratio = topics.get('distribution', {}).get('security_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
            if security_topic_ratio > 0.1:  # 安全话题占比超过10%
                return 0.9  # 充分讨论安全问题且无实际安全问题
            else:
                return 0.7  # 无安全问题但安全讨论较少
    
    def _calculate_performance_score(self, issues: Dict, topics: Dict) -> float:
        """计算性能测试评分"""
        # 性能相关问题影响评分
        performance_issues = issues.get('severity_distribution', {}).get('high', 0) + issues.get('severity_distribution', {}).get('medium', 0)
        
        if performance_issues > 0:
            return max(0.2, 0.8 - performance_issues * 0.1)  # 性能问题扣分
        else:
            # 没有性能问题，看性能话题讨论情况
            performance_topic_ratio = topics.get('distribution', {}).get('performance_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
            if performance_topic_ratio > 0.1:  # 性能话题占比超过10%
                return 0.9
            else:
                return 0.7
    
    def _calculate_compatibility_score(self, issues: Dict, topics: Dict) -> float:
        """计算兼容性测试评分"""
        # 兼容性问题影响评分
        compatibility_issues = issues.get('severity_distribution', {}).get('high', 0) + issues.get('severity_distribution', {}).get('medium', 0)
        
        if compatibility_issues > 0:
            return max(0.2, 0.8 - compatibility_issues * 0.15)  # 兼容性问题扣分较重
        else:
            # 没有兼容性问题，看兼容性话题讨论情况
            comp_topic_ratio = topics.get('distribution', {}).get('compatibility_terms', 0) / max(1, sum(topics.get('distribution', {}).values()))
            if comp_topic_ratio > 0.05:  # 兼容性话题占比超过5%
                return 0.85
            else:
                return 0.65
    
    def _determine_security_level(self, issues: Dict) -> str:
        """确定安全风险等级"""
        high_issues = issues.get('severity_distribution', {}).get('high', 0)
        medium_issues = issues.get('severity_distribution', {}).get('medium', 0)
        low_issues = issues.get('severity_distribution', {}).get('low', 0)
        
        if high_issues > 0:
            return "高危"
        elif medium_issues > 2:  # 中等风险超过2个
            return "中危"
        elif medium_issues > 0 or low_issues > 3:  # 有中等风险或低风险超过3个
            return "低危"
        else:
            return "安全"
    
    def _assess_overall_risk(self, issues: Dict, sentiment: Dict) -> Dict[str, Any]:
        """评估整体风险"""
        total_issues = issues.get('total_issues', 0)
        high_severity = issues.get('severity_distribution', {}).get('high', 0)
        negative_ratio = sentiment.get('negative_ratio', 0)
        
        if high_severity > 0:
            risk_level = "高"
            confidence = "中等" if total_issues > 5 else "低"
        elif total_issues > 5 or negative_ratio > 0.4:
            risk_level = "中"
            confidence = "高" if total_issues > 10 else "中等"
        else:
            risk_level = "低"
            confidence = "高" if total_issues == 0 else "中等"
        
        return {
            'level': risk_level,
            'confidence': confidence,
            'details': {
                'total_issues': total_issues,
                'high_severity_count': high_severity,
                'negative_sentiment_ratio': negative_ratio
            }
        }
    
    def _calculate_comprehensive_score(self, results: Dict[str, Any]) -> float:
        """计算综合评分"""
        summary = results.get('summary', {})
        
        # 各项指标权重
        weights = {
            'functionality_pass_rate': 0.3,
            'security_score': 0.25,
            'performance_score': 0.2,
            'compatibility_score': 0.15,
            'communication_effectiveness': 0.05,
            'requirement_coverage': 0.05
        }
        
        # 计算加权分数
        weighted_score = 0
        for metric, weight in weights.items():
            value = summary.get(metric, 0)
            if isinstance(value, (int, float)):
                weighted_score += value * weight
        
        return round(weighted_score, 3)
    
    def generate_metrics_dashboard(self) -> Dict[str, Any]:
        """生成指标仪表板"""
        if not self.aggregated_results:
            return {'error': 'No aggregated results available'}
        
        summary = self.aggregated_results.get('summary', {})
        
        return {
            'overall_score': summary.get('overall_score', 0),
            'key_metrics': {
                'Functionality': summary.get('functionality_pass_rate', 0),
                'Security': summary.get('security_score', 0) if 'security_score' in summary else 0,
                'Performance': summary.get('performance_score', 0),
                'Compatibility': summary.get('compatibility_score', 0)
            },
            'risk_level': summary.get('risk_assessment', {}).get('level', 'unknown'),
            'defect_density': summary.get('defect_density', 0),
            'requirement_coverage': summary.get('requirement_coverage', 0)
        }

def demonstrate_result_aggregation():
    """演示结果聚合"""
    aggregator = TestResultAggregator()
    
    # 模拟输入数据
    mock_chat_result = type('MockChatResult', (), {
        'turns': 25,
        'summary': 'Test session completed successfully',
        'cost': 0.45
    })()
    
    mock_analysis_result = {
        'sentiment': {'positive_ratio': 0.7, 'negative_ratio': 0.1},
        'issues': {'total_issues': 2, 'severity_distribution': {'high': 0, 'medium': 1, 'low': 1}},
        'topics': {'distribution': {'functionality_terms': 8, 'security_terms': 3}, 'dominant_topic': 'functionality'},
        'participation': {'participation_balance': 0.85},
        'objective_alignment': {'alignment_ratio': 0.92, 'coverage_score': 0.88},
        'overall_score': 0.78
    }
    
    test_objectives = ["功能验证", "安全测试", "性能评估"]
    
    results = aggregator.aggregate_results(mock_chat_result, mock_analysis_result, test_objectives)
    
    print("结果聚合演示:")
    print(f"  综合评分: {results['summary']['overall_score']:.3f}")
    print(f"  功能通过率: {results['summary']['functionality_pass_rate']:.1%}")
    print(f"  安全风险等级: {results['summary']['security_risk_level']}")
    print(f"  性能评分: {results['summary']['performance_score']:.2f}")
    
    return results