#!/usr/bin/env python3
"""秒杀五 Agent 测试演示 — 对应 CrewAI 系列 20/21 篇"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.mock_pipeline import run_mock_pipeline


def main():
    parser = argparse.ArgumentParser(description="秒杀系统五 Agent 测试演示")
    parser.add_argument(
        "--mode",
        choices=["demo", "crew", "test"],
        default="demo",
        help="demo=Mock 无需 Key；crew=真实 CrewAI；test=运行 pytest",
    )
    args = parser.parse_args()

    reports_dir = ROOT / "reports"
    req_path = ROOT / "samples" / "seckill_requirements.md"

    if args.mode == "test":
        import pytest
        raise SystemExit(pytest.main(["-q", str(ROOT / "tests")]))

    print("=" * 50)
    print("秒杀五 Agent 测试演示")
    print("=" * 50)
    print(f"模式: {args.mode}")
    print(f"需求: {req_path.name}")

    if args.mode == "demo":
        run_mock_pipeline(reports_dir, req_path)
        print("\n✅ Demo 完成！查看 reports/ 目录下 5 份 Markdown 产出。")
        print("💡 配置 DASHSCOPE_API_KEY 后可运行: ./run.sh crew")
        return

    try:
        from src.crew_runner import run_crew_pipeline
        summary = run_crew_pipeline(reports_dir, req_path)
        print("\n=== Crew 最终输出 ===")
        print(summary[:2000])
        print("\n✅ 完整报告已写入 reports/05_final_report.md")
    except RuntimeError as e:
        print(f"\n❌ {e}")
        print("💡 可先运行: ./run.sh demo")
        raise SystemExit(1)
    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
        print("请执行: pip install -r ../../requirements-crewai.txt")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
