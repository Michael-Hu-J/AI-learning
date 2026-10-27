"""
05-调试与监控：Agent 运行追踪
对应文章：Agent 调试技巧大全
"""

import json
from crewai import Agent, Task, Crew


class TestResultTracker:
    """测试结果追踪器"""

    def __init__(self):
        self.events = []

    def on_agent_start(self, agent):
        self.events.append({
            "type": "agent_start",
            "agent": agent.role,
            "status": "running",
        })
        print(f"[追踪] Agent 开始: {agent.role}")

    def on_agent_end(self, agent, result):
        self.events.append({
            "type": "agent_end",
            "agent": agent.role,
            "status": "completed",
            "result_length": len(str(result)),
        })
        print(f"[追踪] Agent 完成: {agent.role} (输出 {len(str(result))} 字符)")

    def on_task_start(self, task):
        self.events.append({
            "type": "task_start",
            "task": task.description[:50],
        })
        print(f"[追踪] 任务开始: {task.description[:50]}...")

    def on_task_end(self, task, result):
        self.events.append({
            "type": "task_end",
            "task": task.description[:50],
            "status": "completed",
        })
        print(f"[追踪] 任务完成: {task.description[:50]}...")

    def get_report(self):
        return {
            "total_events": len(self.events),
            "events": self.events,
        }


def main():
    tracker = TestResultTracker()

    # 创建 Agent
    agents = [
        Agent(role="测试计划员", goal="制定计划", backstory="10年经验", verbose=True),
        Agent(role="测试执行员", goal="执行测试", backstory="5年经验", verbose=True),
    ]

    # 创建 Task
    tasks = [
        Task(description="生成测试计划", agent=agents[0]),
        Task(description="执行测试用例", agent=agents[1]),
    ]

    # 执行并追踪
    print("=" * 60)
    print("开始执行测试流程（带追踪）")
    print("=" * 60)

    tracker.on_agent_start(agents[0])
    tracker.on_task_start(tasks[0])

    crew = Crew(agents=agents, tasks=tasks, verbose=True)
    result = crew.kickoff()

    tracker.on_task_end(tasks[0], result)
    tracker.on_agent_end(agents[0], result)

    # 输出追踪报告
    print("\n" + "=" * 60)
    print("追踪报告")
    print("=" * 60)
    report = tracker.get_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
