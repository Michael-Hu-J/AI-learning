from crewai import Task
from agents.test_designer_agent import TestDesignerAgent
from typing import Any, Dict, List

class TestGenerationTask:
    """测试生成任务"""
    
    def create_task(self, test_designer_agent, target_system_description: str, test_requirements: List[str]):
        """创建测试生成任务"""
        return Task(
            description=f"""
            基于以下系统描述和测试需求，设计全面的测试用例和测试场景：

            系统描述：
            {target_system_description}

            测试需求：
            {chr(10).join([f"- {req}" for req in test_requirements])}

            请生成以下内容：
            1. 功能测试用例（包括正常流程和异常流程）
            2. 边界值测试用例
            3. 性能测试场景
            4. 安全性测试要点
            5. 用户体验测试检查点

            要求：
            - 每个测试用例应包含前置条件、测试步骤、预期结果
            - 考虑各种输入组合和边界条件
            - 优先考虑高风险区域的测试
            - 确保测试用例的可执行性和可重复性
            """,
            expected_output="""
            一个结构化的测试用例集合，包含：

            # 功能测试用例
            ## 用例1：[用例名称]
            - 前置条件：[条件描述]
            - 输入：[输入数据]
            - 步骤：[执行步骤]
            - 预期结果：[期望输出]
            - 优先级：高/中/低

            # 边界值测试用例
            ## 用例N：[边界条件描述]
            - 输入范围：[最小值, 最大值]
            - 测试值：[临界值测试数据]
            - 预期行为：[期望的边界处理]

            # 性能测试场景
            ## 场景1：[场景名称]
            - 并发用户数：[数值]
            - 请求频率：[次数/时间]
            - 预期响应时间：[时间]
            - 通过标准：[性能指标]

            # 安全性测试要点
            - 输入验证测试
            - 权限控制测试
            - 数据加密测试
            - 其他安全考虑

            # 用户体验测试检查点
            - 响应速度满意度
            - 界面友好性
            - 错误处理友好性
            - 其他UX要素
            """,
            agent=test_designer_agent,
            async_execution=False
        )

class TestExecutionTask:
    """测试执行任务"""
    
    def create_task(self, test_executor_agent, test_cases: List[Dict[str, Any]], target_system_endpoint: str = ""):
        """创建测试执行任务"""
        # 构建测试用例列表字符串
        test_cases_str = ""
        for i, tc in enumerate(test_cases[:5]):  # 只显示前5个作为示例
            test_cases_str += f"## 用例{i+1}: {tc.get('name', f'测试用例{i+1}')}\n"
            test_cases_str += f"- 类型：{tc.get('type', '功能测试')}\n"
            test_cases_str += f"- 优先级：{tc.get('priority', '中')}\n"
            test_cases_str += f"- 步骤：{tc.get('steps', 'N/A')}\n"
            test_cases_str += f"- 预期：{tc.get('expected', 'N/A')}\n"
            if i < min(4, len(test_cases)-1):  # 添加分隔符，但最后一个不加
                test_cases_str += "\n"

        return Task(
            description=f"""
            执行以下测试用例，并记录详细的执行结果：

            测试用例总数：{len(test_cases)}
            目标系统端点：{target_system_endpoint or '待定'}

            测试用例列表：
            {test_cases_str}

            请执行以下操作：
            1. 按照测试步骤执行每个测试用例
            2. 记录实际结果与预期结果的对比
            3. 捕获任何异常、错误或不符合预期的行为
            4. 测量性能相关指标（如响应时间）
            5. 记录测试执行环境信息

            执行要求：
            - 确保测试环境的纯净性
            - 按优先级顺序执行测试
            - 对失败的测试进行初步原因分析
            - 保持测试数据的隔离性
            """,
            expected_output="""
            详细的测试执行报告，包含：

            # 测试执行摘要
            - 总用例数：[总数]
            - 通过：[通过数]
            - 失败：[失败数]
            - 阻塞：[阻塞数]
            - 通过率：[百分比]

            # 详细执行结果
            ## 用例1：[名称]
            - 状态：通过/失败/阻塞
            - 实际结果：[实际输出]
            - 预期结果：[期望输出]
            - 差异分析：[如有差异则说明]
            - 执行时间：[耗时]
            - 环境信息：[执行环境详情]

            # 失败用例分析
            - 失败模式：[失败类型分类]
            - 根本原因：[初步分析]
            - 影响范围：[受影响的功能]

            # 性能指标
            - 平均响应时间：[时间]
            - 最大响应时间：[时间]
            - 最小响应时间：[时间]
            - 95th百分位响应时间：[时间]

            # 环境信息
            - 执行时间：[时间戳]
            - 测试环境：[环境描述]
            - 系统资源使用情况：[CPU、内存等]
            """,
            agent=test_executor_agent,
            async_execution=False
        )

class ResultAnalysisTask:
    """结果分析任务"""
    
    def create_task(self, test_analyzer_agent, test_results: Dict[str, Any]):
        """创建结果分析任务"""
        return Task(
            description=f"""
            深入分析以下测试结果数据，提供有价值的洞察和改进建议：

            测试执行摘要：
            - 总用例数：{test_results.get('total_cases', 0)}
            - 通过数：{test_results.get('passed', 0)}
            - 失败数：{test_results.get('failed', 0)}
            - 通过率：{test_results.get('pass_rate', 0):.2%}

            详细结果数据：
            {str(test_results)[:2000]}  # 限制长度以避免过长

            请进行以下分析：
            1. 识别失败模式和根本原因
            2. 分析测试覆盖率和有效性
            3. 评估系统稳定性和可靠性
            4. 识别性能瓶颈和优化机会
            5. 提供改进建议和风险评估

            分析要求：
            - 使用统计方法分析数据趋势
            - 识别异常模式和潜在问题
            - 区分功能缺陷和环境问题
            - 提供可操作的改进建议
            """,
            expected_output="""
            全面的结果分析报告，包含：

            # 执行概览
            - 通过率：[百分比] (高于/低于预期)
            - 主要成就：[突出的正面结果]
            - 关键问题：[最重要的发现]

            # 失败分析
            ## 失败分类
            - 功能缺陷：[数量及描述]
            - 性能问题：[数量及描述]  
            - 环境问题：[数量及描述]
            - 其他：[数量及描述]

            ## 根本原因分析
            - 代码层面：[具体问题]
            - 设计层面：[架构问题]
            - 数据层面：[数据相关问题]
            - 环境层面：[配置或依赖问题]

            # 质量评估
            - 功能完整性：[评估分数及说明]
            - 性能表现：[评估分数及说明]
            - 稳定性：[评估分数及说明]
            - 安全性：[评估分数及说明]

            # 改进建议
            ## 紧急修复
            - [具体问题] -> [修复建议]
            - [具体问题] -> [修复建议]

            ## 优化建议
            - [改进建议1]
            - [改进建议2]
            - [改进建议3]

            ## 风险评估
            - 高风险：[风险描述及影响]
            - 中风险：[风险描述及影响]
            - 低风险：[风险描述及影响]

            # 后续步骤
            - 立即行动：[需要立即执行的步骤]
            - 短期计划：[1-2周内的计划]
            - 长期规划：[长期改进建议]
            """,
            agent=test_analyzer_agent,
            async_execution=False
        )

class ReportGenerationTask:
    """报告生成任务"""
    
    def create_task(self, quality_assurance_agent, analysis_results: Dict[str, Any]):
        """创建报告生成任务"""
        return Task(
            description=f"""
            基于以下分析结果，生成最终的测试质量报告：

            分析结果摘要：
            - 通过率：{analysis_results.get('pass_rate', 0):.2%}
            - 主要发现：{analysis_results.get('key_findings', [])[:3]}
            - 关键风险：{analysis_results.get('key_risks', [])[:3]}

            完整分析数据：
            {str(analysis_results)[:2000]}  # 限制长度

            请生成一份专业的测试质量报告，面向不同的受众：
            1. 管理层：高层次的质量状况和风险
            2. 开发团队：具体的技术问题和修复建议
            3. 测试团队：测试过程的改进建议
            4. 产品经理：功能可用性和用户体验评估

            报告要求：
            - 结构清晰，重点突出
            - 数据驱动，结论客观
            - 建议具体，可操作性强
            - 风险评估充分，应对措施明确
            """,
            expected_output="""
            专业的测试质量报告，包含：

            # 执行摘要
            - 测试范围：[测试了哪些功能]
            - 整体质量：[质量等级评价]
            - 关键结论：[最重要的3-5个结论]
            - 建议行动：[需要采取的关键措施]

            # 详细质量评估
            ## 功能质量
            - 测试覆盖：[覆盖率百分比及说明]
            - 缺陷密度：[每千行代码的缺陷数]
            - 关键功能验证：[重要功能的测试结果]

            ## 性能质量
            - 响应时间：[满足/不满足性能要求]
            - 并发能力：[系统并发处理能力]
            - 资源利用：[CPU、内存等使用情况]

            ## 可靠性评估
            - 稳定性：[系统运行稳定性]
            - 容错能力：[错误处理能力]
            - 恢复能力：[故障恢复能力]

            # 风险评估
            ## 高风险项
            - [风险1]：[影响描述] -> [缓解措施]
            - [风险2]：[影响描述] -> [缓解措施]

            ## 中风险项
            - [风险3]：[影响描述] -> [缓解措施]

            # 建议和后续步骤
            ## 立即行动项
            - [紧急修复1]
            - [紧急修复2]

            ## 短期改进计划
            - [改进计划1]
            - [改进计划2]

            ## 长期优化方向
            - [优化方向1]
            - [优化方向2]

            # 附录
            - 详细的测试数据
            - 使用的测试工具和环境
            - 参考标准和规范
            """,
            agent=quality_assurance_agent,
            async_execution=False
        )