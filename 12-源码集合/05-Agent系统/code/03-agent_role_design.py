"""
03-Agent 角色设计：专业角色 vs 通用角色
对应文章：Agent 角色设计方法论
"""

from crewai import Agent


def create_generic_agent():
    """通用 Agent（效果差）"""
    return Agent(
        role="助手",
        goal="帮助用户完成任务",
        backstory="你是一个有用的助手",
        verbose=True,
    )


def create_professional_agent():
    """专业 Agent（效果好）"""
    return Agent(
        role="高级性能测试工程师",
        goal="设计并执行性能测试方案，识别系统瓶颈",
        backstory=(
            "你是某电商平台的高级性能测试工程师，有 8 年性能测试经验。"
            "你擅长使用 JMeter、Locust 等工具进行压力测试，"
            "熟悉 TPS、响应时间、错误率等性能指标的分析。"
            "你曾经主导过双 11 大促的性能测试工作。"
        ),
        verbose=True,
    )


def compare_outputs():
    """对比两种角色的输出质量"""

    test_prompt = "请为秒杀系统设计性能测试方案"

    print("=" * 60)
    print("通用 Agent 输出：")
    print("=" * 60)
    generic = create_generic_agent()
    # 注意：实际运行需要配置 LLM
    print(f"角色: {generic.role}")
    print(f"目标: {generic.goal}")
    print(f"背景: {generic.backstory}")
    print("提示：角色定义越具体，输出越专业")

    print("\n" + "=" * 60)
    print("专业 Agent 输出：")
    print("=" * 60)
    pro = create_professional_agent()
    print(f"角色: {pro.role}")
    print(f"目标: {pro.goal}")
    print(f"背景: {pro.backstory}")


def main():
    compare_outputs()


if __name__ == "__main__":
    main()
