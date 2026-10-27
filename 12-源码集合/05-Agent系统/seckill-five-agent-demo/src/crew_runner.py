"""CrewAI 五 Agent 真实编排（需 DASHSCOPE_API_KEY 或 OPENAI_API_KEY）"""

import os
from pathlib import Path

from crewai import Agent, Task, Crew, Process

from src.tools.api_test_tool import SeckillAPITestTool


def _load_requirements(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_llm():
    """使用环境变量中的 OpenAI 兼容 API（默认通义千问）"""
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")

    from crewai import LLM

    base = os.environ.get("OPENAI_API_BASE") or os.environ.get(
        "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model = os.environ.get("CREWAI_MODEL", "qwen-plus")
    return LLM(model=model, base_url=base, api_key=api_key)


def run_crew_pipeline(reports_dir: Path, requirements_path: Path) -> str:
    reports_dir.mkdir(parents=True, exist_ok=True)
    req = _load_requirements(requirements_path)
    llm = _build_llm()
    api_tool = SeckillAPITestTool()

    manager = Agent(
        role="测试经理",
        goal="为秒杀系统制定测试计划，明确范围、优先级与风险",
        backstory="15 年测试管理经验，熟悉电商秒杀场景。",
        llm=llm,
        verbose=True,
    )
    designer = Agent(
        role="测试设计师",
        goal="设计覆盖 P0/P1 的秒杀测试用例",
        backstory="擅长边界值、并发与幂等场景设计。",
        llm=llm,
        verbose=True,
    )
    engineer = Agent(
        role="测试工程师",
        goal="执行 API 测试并记录结果",
        backstory="熟悉接口自动化与性能基线。",
        llm=llm,
        tools=[api_tool],
        verbose=True,
    )
    analyst = Agent(
        role="测试分析师",
        goal="对失败用例做根因分析（5 Why）",
        backstory="善于从测试结果定位架构与配置问题。",
        llm=llm,
        verbose=True,
    )
    reporter = Agent(
        role="测试报告专员",
        goal="汇总全流程输出发布建议",
        backstory="输出管理层可读的测试总结。",
        llm=llm,
        verbose=True,
    )

    t1 = Task(
        description=f"根据以下需求编写测试计划（Markdown 表格）：\n{req[:1500]}",
        expected_output="测试计划 Markdown，含范围、优先级、风险",
        agent=manager,
    )
    t2 = Task(
        description="基于测试计划设计至少 5 条秒杀测试用例（Markdown 表格）",
        expected_output="测试用例 Markdown 表格",
        agent=designer,
        context=[t1],
    )
    t3 = Task(
        description="使用 seckill_api_test 工具执行 check_stock、place_order、query_product，汇总结果",
        expected_output="测试执行结果 Markdown，含通过率",
        agent=engineer,
        context=[t2],
    )
    t4 = Task(
        description="对失败或风险项做 5 Why 根因分析",
        expected_output="缺陷分析 Markdown",
        agent=analyst,
        context=[t3],
    )
    t5 = Task(
        description="生成最终测试报告与发布建议（通过/有条件发布/不发布）",
        expected_output="测试总结 Markdown",
        agent=reporter,
        context=[t1, t2, t3, t4],
    )

    crew = Crew(
        agents=[manager, designer, engineer, analyst, reporter],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
    )

    print("\n🚀 启动 CrewAI 五 Agent 流水线（真实 LLM 调用，耗时约 1–3 分钟）...\n")
    result = crew.kickoff()

    summary = str(result)
    out = reports_dir / "05_final_report.md"
    out.write_text(summary, encoding="utf-8")
    return summary
