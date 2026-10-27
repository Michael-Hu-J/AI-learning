"""
02-多 Agent 协作：测试流程自动化
对应文章：多 Agent 协作模式详解
"""

from crewai import Agent, Task, Crew, Process


def create_test_team():
    """创建测试团队（4 个 Agent）"""

    # 1. 测试经理 - 制定计划
    manager = Agent(
        role="测试经理",
        goal="制定测试计划和策略",
        backstory="15 年测试经验，擅长测试策略设计",
        verbose=True,
    )

    # 2. 测试设计师 - 设计用例
    designer = Agent(
        role="测试设计师",
        goal="设计覆盖全面的测试用例",
        backstory="擅长边界值分析、等价类划分、因果图法",
        verbose=True,
    )

    # 3. 测试工程师 - 执行测试
    executor = Agent(
        role="测试工程师",
        goal="执行测试用例并记录结果",
        backstory="熟练使用自动化测试工具，善于发现 Bug",
        verbose=True,
    )

    # 4. 报告专员 - 生成报告
    reporter = Agent(
        role="报告专员",
        goal="生成专业测试报告",
        backstory="数据可视化专家，善于用数据说话",
        verbose=True,
    )

    return [manager, designer, executor, reporter]


def create_test_tasks(agents):
    """创建测试任务链"""
    manager, designer, executor, reporter = agents

    tasks = [
        Task(
            description="为电商秒杀系统设计测试计划，覆盖功能、性能、安全三个方面",
            expected_output="测试计划文档，包含测试范围、资源、时间表",
            agent=manager,
        ),
        Task(
            description="根据测试计划，设计功能测试用例（至少 10 条）",
            expected_output="JSON 格式的测试用例列表",
            agent=designer,
        ),
        Task(
            description="执行测试用例，记录每条用例的执行结果",
            expected_output="测试结果列表（通过/失败/阻塞）",
            agent=executor,
        ),
        Task(
            description="根据测试结果生成测试报告",
            expected_output="测试报告，包含通过率、缺陷统计、发布建议",
            agent=reporter,
        ),
    ]
    return tasks


def main():
    # 创建团队
    agents = create_test_team()

    # 创建任务
    tasks = create_test_tasks(agents)

    # 顺序执行
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
    )

    print("开始执行测试流程...")
    result = crew.kickoff()

    print("\n=== 最终输出 ===")
    print(result)


if __name__ == "__main__":
    main()
