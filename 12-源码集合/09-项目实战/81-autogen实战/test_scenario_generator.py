import random
from typing import List, Dict, Any

class TestScenarioGenerator:
    """测试场景生成器"""
    
    def __init__(self):
        self.functional_scenarios = [
            {
                'name': '基本功能验证',
                'description': '验证系统核心功能是否正常工作',
                'category': 'functional',
                'complexity': 'low',
                'tags': ['smoke', 'core']
            },
            {
                'name': '边界值测试',
                'description': '测试输入参数的边界值情况',
                'category': 'functional',
                'complexity': 'medium',
                'tags': ['boundary', 'edge_case']
            },
            {
                'name': '异常流程测试',
                'description': '验证系统对异常情况的处理能力',
                'category': 'functional',
                'complexity': 'medium',
                'tags': ['error_handling', 'exception']
            },
            {
                'name': '多步骤业务流程',
                'description': '测试复杂的多步骤业务场景',
                'category': 'functional',
                'complexity': 'high',
                'tags': ['workflow', 'integration']
            }
        ]
        
        self.security_scenarios = [
            {
                'name': '输入验证测试',
                'description': '验证系统对恶意输入的过滤能力',
                'category': 'security',
                'complexity': 'medium',
                'tags': ['input_validation', 'injection']
            },
            {
                'name': '认证授权测试',
                'description': '验证访问控制和权限管理',
                'category': 'security',
                'complexity': 'high',
                'tags': ['auth', 'authorization']
            },
            {
                'name': '数据泄露防护',
                'description': '测试敏感数据的保护机制',
                'category': 'security',
                'complexity': 'high',
                'tags': ['privacy', 'data_protection']
            },
            {
                'name': 'Prompt注入测试',
                'description': '针对AI系统的特殊安全测试',
                'category': 'security',
                'complexity': 'high',
                'tags': ['prompt_injection', 'ai_specific']
            }
        ]
        
        self.performance_scenarios = [
            {
                'name': '负载压力测试',
                'description': '评估系统在高负载下的表现',
                'category': 'performance',
                'complexity': 'high',
                'tags': ['load', 'stress']
            },
            {
                'name': '并发性能测试',
                'description': '测试多用户同时访问的性能',
                'category': 'performance',
                'complexity': 'medium',
                'tags': ['concurrency', 'throughput']
            },
            {
                'name': '响应时间测试',
                'description': '测量系统响应时间指标',
                'category': 'performance',
                'complexity': 'low',
                'tags': ['latency', 'response_time']
            },
            {
                'name': '容量规划验证',
                'description': '评估系统容量和扩展性',
                'category': 'performance',
                'complexity': 'high',
                'tags': ['capacity', 'scalability']
            }
        ]
        
        self.compatibility_scenarios = [
            {
                'name': '跨平台兼容性',
                'description': '验证在不同平台上的兼容性',
                'category': 'compatibility',
                'complexity': 'medium',
                'tags': ['cross_platform', 'portability']
            },
            {
                'name': 'API兼容性',
                'description': '测试API接口的兼容性',
                'category': 'compatibility',
                'complexity': 'medium',
                'tags': ['api', 'interface']
            },
            {
                'name': '数据格式兼容性',
                'description': '验证数据格式的兼容性',
                'category': 'compatibility',
                'complexity': 'low',
                'tags': ['data_format', 'interoperability']
            },
            {
                'name': '版本升级兼容性',
                'description': '测试版本升级的兼容性',
                'category': 'compatibility',
                'complexity': 'high',
                'tags': ['upgrade', 'backward_compatibility']
            }
        ]
    
    def generate_scenarios(self, 
                          target_system: str, 
                          test_objectives: List[str],
                          count: int = 10) -> List[Dict[str, Any]]:
        """根据目标系统和测试目标生成测试场景"""
        all_scenarios = (
            self.functional_scenarios + 
            self.security_scenarios + 
            self.performance_scenarios + 
            self.compatibility_scenarios
        )
        
        # 根据测试目标筛选相关场景
        filtered_scenarios = []
        
        for obj in test_objectives:
            obj_lower = obj.lower()
            
            # 根据目标关键词匹配场景
            for scenario in all_scenarios:
                if (obj_lower in scenario['name'].lower() or 
                    obj_lower in scenario['description'].lower() or
                    any(tag in obj_lower for tag in scenario['tags'])):
                    if scenario not in filtered_scenarios:
                        filtered_scenarios.append(scenario)
        
        # 如果筛选后的场景不够，随机补充
        if len(filtered_scenarios) < count:
            remaining_count = count - len(filtered_scenarios)
            # 从所有场景中随机选择补充
            remaining_scenarios = [s for s in all_scenarios if s not in filtered_scenarios]
            selected_additional = random.sample(
                remaining_scenarios, 
                min(remaining_count, len(remaining_scenarios))
            )
            filtered_scenarios.extend(selected_additional)
        
        # 如果仍然不够，从所有场景中随机选择直到达到指定数量
        if len(filtered_scenarios) < count:
            remaining_count = count - len(filtered_scenarios)
            all_remaining = [s for s in all_scenarios if s not in filtered_scenarios]
            # 循环选择直到达到所需数量
            while len(filtered_scenarios) < count and all_remaining:
                filtered_scenarios.append(random.choice(all_remaining))
        
        # 返回前count个场景
        return filtered_scenarios[:count]
    
    def generate_custom_scenario(self, 
                                scenario_type: str, 
                                description: str, 
                                priority: str = 'medium') -> Dict[str, Any]:
        """生成自定义测试场景"""
        return {
            'name': f'Custom {scenario_type.title()} Test',
            'description': description,
            'category': scenario_type.lower(),
            'complexity': priority,
            'tags': ['custom', scenario_type.lower()],
            'custom': True
        }
    
    def get_scenario_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根据类别获取测试场景"""
        category_mapping = {
            'functional': self.functional_scenarios,
            'security': self.security_scenarios,
            'performance': self.performance_scenarios,
            'compatibility': self.compatibility_scenarios
        }
        
        return category_mapping.get(category, [])
    
    def create_regression_scenario(self, 
                                  previous_version_features: List[str],
                                  new_features: List[str]) -> Dict[str, Any]:
        """创建回归测试场景"""
        affected_features = list(set(previous_version_features) - set(new_features))
        
        return {
            'name': 'Regression Test Scenario',
            'description': f'Test previously working features: {", ".join(affected_features[:3])}',
            'category': 'regression',
            'complexity': 'medium',
            'tags': ['regression', 'existing_features'],
            'affected_features': affected_features
        }
    
    def create_exploratory_scenario(self, 
                                   target_system: str,
                                   exploration_depth: str = 'medium') -> Dict[str, Any]:
        """创建探索性测试场景"""
        depths = {
            'low': '表面功能验证',
            'medium': '深度功能交互测试', 
            'high': '极限边界和异常情况探索'
        }
        
        return {
            'name': 'Exploratory Test Scenario',
            'description': f'对{target_system[:50]}进行{depths.get(exploration_depth, "中等深度")}探索',
            'category': 'exploratory',
            'complexity': exploration_depth,
            'tags': ['exploratory', 'ad_hoc', 'discovery'],
            'depth': exploration_depth
        }

def demonstrate_scenario_generation():
    """演示场景生成"""
    generator = TestScenarioGenerator()
    
    # 示例目标系统和测试目标
    target_system = "智能客服AI系统"
    test_objectives = [
        "验证自然语言理解能力",
        "测试安全性",
        "评估响应性能"
    ]
    
    scenarios = generator.generate_scenarios(target_system, test_objectives, count=8)
    
    print(f"生成了 {len(scenarios)} 个测试场景:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario['name']} - {scenario['category']} ({scenario['complexity']})")
    
    return scenarios