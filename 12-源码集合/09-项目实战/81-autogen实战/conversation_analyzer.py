from typing import List, Dict, Any
import re
from collections import Counter, defaultdict

class ConversationAnalyzer:
    """对话分析器"""
    
    def __init__(self):
        self.patterns = {
            'issue_indicators': [
                r'bug', r'error', r'fail', r'problem', r'issue', 
                r'not working', r'doesn\'t work', r'broken', r'incorrect'
            ],
            'positive_indicators': [
                r'success', r'works', r'correct', r'good', r'great',
                r'effective', r'efficient', r'properly', r'validated'
            ],
            'security_terms': [
                r'security', r'vulnerability', r'exploit', r'hack', 
                r'attack', r'breach', r'leak', r'auth', r'permission'
            ],
            'performance_terms': [
                r'performance', r'speed', r'fast', r'slow', r'latency',
                r'response time', r'throughput', r'load', r'concurrent'
            ],
            'functionality_terms': [
                r'feature', r'function', r'capability', r'behavior',
                r'input', r'output', r'process', r'workflow'
            ]
        }
    
    def analyze_conversation(self, 
                           conversation_history: Dict[str, List[Dict]], 
                           test_objectives: List[str]) -> Dict[str, Any]:
        """分析对话历史"""
        # 合并所有消息
        all_messages = []
        for msg_list in conversation_history.values():
            all_messages.extend(msg_list)
        
        # 按时间排序
        all_messages.sort(key=lambda x: x.get('timestamp', 0))
        
        # 执行各种分析
        sentiment_analysis = self._analyze_sentiment(all_messages)
        topic_analysis = self._analyze_topics(all_messages)
        participation_analysis = self._analyze_participation(all_messages)
        issue_detection = self._detect_issues(all_messages)
        objective_alignment = self._analyze_objective_alignment(all_messages, test_objectives)
        
        # 计算整体评分
        overall_score = self._calculate_overall_score(
            sentiment_analysis, issue_detection, objective_alignment
        )
        
        return {
            'sentiment': sentiment_analysis,
            'topics': topic_analysis,
            'participation': participation_analysis,
            'issues': issue_detection,
            'objective_alignment': objective_alignment,
            'overall_score': overall_score,
            'summary': self._generate_summary(
                sentiment_analysis, issue_detection, topic_analysis
            )
        }
    
    def _analyze_sentiment(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析情感倾向"""
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for msg in messages:
            content = msg.get('content', '').lower()
            
            # 检查积极词汇
            for pattern in self.patterns['positive_indicators']:
                if re.search(r'\b' + pattern + r'\b', content):
                    positive_count += 1
                    break
            
            # 检查消极词汇
            for pattern in self.patterns['issue_indicators']:
                if re.search(r'\b' + pattern + r'\b', content):
                    negative_count += 1
                    break
            else:
                # 如果没有检测到积极或消极词汇，则为中性
                if not re.search(r'\b(' + '|'.join(self.patterns['positive_indicators'] + self.patterns['issue_indicators']) + r')\b', content):
                    neutral_count += 1
        
        total = len(messages)
        if total == 0:
            total = 1  # 避免除零错误
            
        return {
            'positive_ratio': positive_count / total,
            'negative_ratio': negative_count / total,
            'neutral_ratio': neutral_count / total,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count
        }
    
    def _analyze_topics(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析话题分布"""
        topic_counts = defaultdict(int)
        
        for msg in messages:
            content = msg.get('content', '').lower()
            
            # 检测各类话题
            for topic, patterns in self.patterns.items():
                for pattern in patterns:
                    if re.search(r'\b' + pattern + r'\b', content):
                        topic_counts[topic] += 1
                        break  # 每个消息只计入一个话题
        
        return {
            'distribution': dict(topic_counts),
            'dominant_topic': max(topic_counts, key=topic_counts.get) if topic_counts else 'none',
            'topic_diversity': len(topic_counts) / len(self.patterns) if self.patterns else 0
        }
    
    def _analyze_participation(self, messages: List[Dict]) -> Dict[str, Any]:
        """分析参与度"""
        participant_stats = defaultdict(lambda: {'messages': 0, 'words': 0})
        
        for msg in messages:
            sender = msg.get('name', 'unknown')
            content = msg.get('content', '')
            
            participant_stats[sender]['messages'] += 1
            participant_stats[sender]['words'] += len(content.split())
        
        # 计算参与均衡度
        message_counts = [stats['messages'] for stats in participant_stats.values()]
        if len(message_counts) > 1:
            avg_messages = sum(message_counts) / len(message_counts)
            participation_balance = 1 - (max(message_counts) - min(message_counts)) / avg_messages if avg_messages > 0 else 1
        else:
            participation_balance = 1.0
        
        return {
            'participants': dict(participant_stats),
            'total_participants': len(participant_stats),
            'total_messages': len(messages),
            'participation_balance': participation_balance
        }
    
    def _detect_issues(self, messages: List[Dict]) -> Dict[str, Any]:
        """检测问题"""
        issues = []
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for i, msg in enumerate(messages):
            content = msg.get('content', '').lower()
            sender = msg.get('name', 'unknown')
            
            # 检测问题关键词
            for pattern in self.patterns['issue_indicators']:
                if re.search(r'\b' + pattern + r'\b', content):
                    # 简单的严重程度判断（基于上下文关键词）
                    severity = 'medium'
                    if any(word in content for word in ['critical', 'urgent', 'major', 'severe']):
                        severity = 'high'
                    elif any(word in content for word in ['minor', 'small', 'trivial']):
                        severity = 'low'
                    
                    severity_counts[severity] += 1
                    
                    issues.append({
                        'message_idx': i,
                        'sender': sender,
                        'content': content[:100] + '...' if len(content) > 100 else content,
                        'severity': severity,
                        'detected_pattern': pattern
                    })
                    break  # 每条消息只记录一个问题
        
        return {
            'total_issues': len(issues),
            'issues': issues,
            'severity_distribution': severity_counts,
            'issue_density': len(issues) / len(messages) if messages else 0
        }
    
    def _analyze_objective_alignment(self, messages: List[Dict], objectives: List[str]) -> Dict[str, Any]:
        """分析目标对齐度"""
        aligned_messages = 0
        objective_coverage = {}
        
        for obj in objectives:
            obj_lower = obj.lower()
            obj_matches = 0
            
            for msg in messages:
                content = msg.get('content', '').lower()
                if obj_lower in content:
                    obj_matches += 1
                    aligned_messages += 1
            
            objective_coverage[obj] = {
                'matched_messages': obj_matches,
                'coverage_ratio': obj_matches / len(messages) if messages else 0
            }
        
        return {
            'aligned_message_count': aligned_messages,
            'alignment_ratio': aligned_messages / len(messages) if messages else 0,
            'objective_coverage': objective_coverage,
            'coverage_score': sum(obj['coverage_ratio'] for obj in objective_coverage.values()) / len(objectives) if objectives else 0
        }
    
    def _calculate_overall_score(self, sentiment: Dict, issues: Dict, alignment: Dict) -> float:
        """计算整体评分"""
        # 基于多个因素计算综合评分
        sentiment_factor = sentiment['positive_ratio'] * 0.3
        issue_factor = max(0, 1 - issues['issue_density']) * 0.4  # 问题越少分越高
        alignment_factor = alignment['alignment_ratio'] * 0.3
        
        return sentiment_factor + issue_factor + alignment_factor
    
    def _generate_summary(self, sentiment: Dict, issues: Dict, topics: Dict) -> str:
        """生成摘要"""
        summary_parts = []
        
        # 情感摘要
        if sentiment['positive_ratio'] > 0.6:
            summary_parts.append("对话整体呈积极态势")
        elif sentiment['negative_ratio'] > 0.3:
            summary_parts.append("检测到较多负面反馈")
        else:
            summary_parts.append("对话情感较为中性")
        
        # 问题摘要
        if issues['total_issues'] > 0:
            summary_parts.append(f"发现了{issues['total_issues']}个问题")
            high_severity = issues['severity_distribution']['high']
            if high_severity > 0:
                summary_parts.append(f"包含{high_severity}个高严重性问题")
        else:
            summary_parts.append("未发现明显问题")
        
        # 话题摘要
        dominant_topic = topics['dominant_topic']
        if dominant_topic != 'none':
            summary_parts.append(f"主要讨论集中在{dominant_topic.replace('_', ' ')}方面")
        
        return "；".join(summary_parts)

def demonstrate_conversation_analysis():
    """演示对话分析"""
    analyzer = ConversationAnalyzer()
    
    # 模拟对话历史
    mock_conversation = {
        'messages': [
            {'name': 'test_manager', 'content': '开始功能测试', 'timestamp': 1},
            {'name': 'functionality_tester', 'content': '功能测试正常通过', 'timestamp': 2},
            {'name': 'security_tester', 'content': '发现一个安全问题需要修复', 'timestamp': 3},
            {'name': 'performance_tester', 'content': '性能测试结果良好', 'timestamp': 4}
        ]
    }
    
    objectives = ["功能验证", "安全测试", "性能评估"]
    results = analyzer.analyze_conversation(mock_conversation, objectives)
    
    print("对话分析结果:")
    print(f"  整体评分: {results['overall_score']:.2f}")
    print(f"  情感倾向: {results['sentiment']['positive_ratio']:.1%} 积极")
    print(f"  发现问题: {results['issues']['total_issues']} 个")
    print(f"  目标对齐: {results['objective_alignment']['alignment_ratio']:.1%}")
    
    return results