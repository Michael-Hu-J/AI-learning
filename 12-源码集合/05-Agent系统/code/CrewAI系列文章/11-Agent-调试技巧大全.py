# 开发调试：verbose=True
agent = Agent(..., verbose=True)
crew = Crew(..., verbose=True)

# 输出示例：
# ╭─────────────────  Crew Execution Started ─────────────────╮
# ╭───────────────────  Task Started ────────────────────╮
# ╭─────────────────── AI Agent Started ────────────────────╮
# ╭─────────────────  Agent Final Answer ──────────────────╮

import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('crewai')

# 在关键位置添加断点
from crewai import Agent

agent = Agent(...)

# 在执行前断点
import pdb; pdb.set_trace()
result = agent.kickoff()

#  错误
task = Task(description="Generate test cases")

#  正确
task = Task(description="请生成测试用例")

# 限制迭代次数
agent = Agent(..., max_iter=10)

# 限制请求频率
crew = Crew(..., max_rpm=60)

# 添加超时控制
import asyncio

async def main():
    result = await asyncio.wait_for(crew.kickoff_async(), timeout=300)
    return result

# 运行
asyncio.run(main())

# 1. 启用 verbose
crew = Crew(..., verbose=True)

# 2. 检查 Agent 是否配置
print(f"Agents: {crew.agents}")
print(f"Tasks: {crew.tasks}")

# 3. 检查 API Key
import os
print(f"API Key: {os.getenv('DASHSCOPE_API_KEY')[:10]}...")

# 4. 单独测试 Agent
agent = crew.agents[0]
task = crew.tasks[0]
result = agent.kickoff(task=task)

# 1. 检查提示词
print(f"Task description: {task.description}")

# 2. 检查 backstory
print(f"Agent backstory: {agent.backstory}")

# 3. 添加示例
task = Task(
    description="""请生成测试用例

示例：
| 编号 | 场景 | 输入 | 预期 |
| 001  | 正常登录 | 正确密码 | 登录成功 |

请生成 10 条类似用例。"""
)

# 4. 调整 temperature
llm = LLM(..., temperature=0.7)  # 降低随机性

import time
from datetime import datetime

start = datetime.now()
result = crew.kickoff()
end = datetime.now()

print(f"执行时间：{(end - start).total_seconds()}秒")

# 记录每次 API 调用的 token
from crewai import Agent

class TrackedAgent(Agent):
    def kickoff(self, *args, **kwargs):
        start_tokens = self.llm.get_token_count()
        result = super().kickoff(*args, **kwargs)
        end_tokens = self.llm.get_token_count()
        print(f"消耗 Token: {end_tokens - start_tokens}")
        return result

import json
import time
from datetime import datetime
from typing import Dict, List
from crewai import Agent, Task, Crew

class ExecutionTracer:
    """执行链路追踪器"""
    
    def __init__(self):
        self.traces: List[Dict] = []
        self.start_time = None
    
    def start(self):
        """开始追踪"""
        self.start_time = datetime.now()
        self.traces = []
        print(f"🔍 执行链路追踪已启动 - {self.start_time.strftime('%H:%M:%S')}")
    
    def record(self, agent_name: str, action: str, data: str = "", duration: float = 0):
        """记录一个执行步骤"""
        trace = {
            "timestamp": datetime.now().strftime('%H:%M:%S.%f')[:-3],
            "agent": agent_name,
            "action": action,
            "data_preview": data[:200] + ("..." if len(data) > 200 else ""),
            "duration_ms": round(duration * 1000, 1)
        }
        self.traces.append(trace)
        
        # 实时输出
        icon = "🔄" if action == "开始" else "✅" if action == "完成" else "⚠️"
        print(f"  {icon} [{trace['timestamp']}] {agent_name}: {action} ({trace['duration_ms']}ms)")
    
    def generate_report(self) -> str:
        """生成追踪报告"""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        report = f"""
╔══════════════════════════════════════════╗
║         执行链路追踪报告                 ║
╠══════════════════════════════════════════╣
║ 总耗时: {elapsed:.1f}秒                          ║
║ 执行步骤: {len(self.traces)}                          ║
╚══════════════════════════════════════════╝

执行链路:
"""
        for i, trace in enumerate(self.traces, 1):
            report += f"  {i}. [{trace['timestamp']}] {trace['agent']} - {trace['action']} ({trace['duration_ms']}ms)\n"
            if trace['data_preview']:
                report += f"     数据: {trace['data_preview'][:100]}\n"
        
        return report


# 使用示例
tracer = ExecutionTracer()

# 包装 Agent 的 kickoff 方法
original_kickoff = Agent.kickoff

def traced_kickoff(self, *args, **kwargs):
    tracer.record(self.role, "开始执行")
    start = time.time()
    try:
        result = original_kickoff(self, *args, **kwargs)
        duration = time.time() - start
        tracer.record(self.role, "执行完成", str(result), duration)
        return result
    except Exception as e:
        duration = time.time() - start
        tracer.record(self.role, "执行失败", str(e), duration)
        raise

Agent.kickoff = traced_kickoff

# 执行追踪
tracer.start()
crew = Crew(agents=[...], tasks=[...])
result = crew.kickoff()
print(tracer.generate_report())

class PromptDebugger:
    """Prompt 调试器 - 分析和优化 Agent 的提示词"""
    
    @staticmethod
    def analyze_prompt(role: str, goal: str, backstory: str, task_desc: str) -> dict:
        """分析 Prompt 质量"""
        analysis = {
            "role_length": len(role),
            "goal_length": len(goal),
            "backstory_length": len(backstory),
            "task_length": len(task_desc),
            "issues": [],
            "suggestions": []
        }
        
        # 检查角色定义
        if len(role) < 5:
            analysis["issues"].append("⚠️ 角色定义过短，可能不够具体")
            analysis["suggestions"].append("建议添加角色级别和专业领域，如'高级测试经理'")
        
        if len(role) > 50:
            analysis["issues"].append("⚠️ 角色定义过长，可能包含冗余信息")
        
        # 检查目标定义
        if not any(kw in goal for kw in ["确保", "保证", "完成", "生成", "设计", "分析"]):
            analysis["issues"].append("⚠️ 目标缺少动作词，Agent 可能不知道要做什么")
            analysis["suggestions"].append("目标应包含明确的动作，如'生成测试用例'、'分析测试结果'")
        
        # 检查 backstory
        if len(backstory) < 20:
            analysis["issues"].append("⚠️ backstory 过短，Agent 缺乏足够的背景信息")
            analysis["suggestions"].append("添加经验描述、工作风格、专业领域等信息")
        
        if len(backstory) > 500:
            analysis["issues"].append("⚠️ backstory 过长，可能浪费 Token")
            analysis["suggestions"].append("精简 backstory，保留最相关的信息")
        
        # 检查任务描述
        if len(task_desc) < 10:
            analysis["issues"].append("⚠️ 任务描述过短，Agent 可能不理解具体要求")
        
        if "请" not in task_desc and "生成" not in task_desc and "分析" not in task_desc:
            analysis["issues"].append("⚠️ 任务描述缺少明确的指令词")
        
        # 评分
        total_issues = len(analysis["issues"])
        if total_issues == 0:
            analysis["score"] = "⭐⭐⭐⭐⭐ 优秀"
        elif total_issues <= 2:
            analysis["score"] = "⭐⭐⭐⭐ 良好"
        elif total_issues <= 4:
            analysis["score"] = "⭐⭐⭐ 一般"
        else:
            analysis["score"] = "⭐⭐ 需要改进"
        
        return analysis
    
    @staticmethod
    def print_analysis(analysis: dict):
        """打印分析结果"""
        print(f"\nPrompt 质量评分: {analysis['score']}")
        print(f"角色长度: {analysis['role_length']} 字符")
        print(f"目标长度: {analysis['goal_length']} 字符")
        print(f"背景长度: {analysis['backstory_length']} 字符")
        print(f"任务长度: {analysis['task_length']} 字符")
        
        if analysis["issues"]:
            print(f"\n发现的问题 ({len(analysis['issues'])}):")
            for issue in analysis["issues"]:
                print(f"  {issue}")
        
        if analysis["suggestions"]:
            print(f"\n优化建议 ({len(analysis['suggestions'])}):")
            for i, suggestion in enumerate(analysis["suggestions"], 1):
                print(f"  {i}. {suggestion}")


# 使用示例
debugger = PromptDebugger()
analysis = debugger.analyze_prompt(
    role="测试",
    goal="做测试",
    backstory="有测试经验",
    task_desc="测试一下"
)
debugger.print_analysis(analysis)

# 对比优化后的 Prompt
analysis2 = debugger.analyze_prompt(
    role="高级测试经理 (Senior Test Manager)",
    goal="制定全面的测试计划，设计高质量的测试用例，确保软件质量符合发布标准",
    backstory="""你是拥有 12 年经验的高级测试经理，曾在多家互联网公司负责核心系统的测试工作。
    你擅长：
    1. 基于风险驱动的方法制定测试策略
    2. 使用等价类划分和边界值分析设计测试用例
    3. 通过数据指标评估测试覆盖率
    4. 协调跨团队资源，推动测试进度
    
    你的工作理念：测试不是找 Bug，而是降低业务风险。""",
    task_desc="""请为以下功能模块生成完整的测试用例：
    
    功能：用户登录系统
    要求：
    1. 覆盖正常场景和异常场景
    2. 包含边界值测试
    3. 包含安全相关测试（如 SQL 注入、暴力破解）
    4. 输出格式：表格，包含编号、场景、前置条件、测试步骤、预期结果
    
    请至少生成 15 条测试用例。"""
)
debugger.print_analysis(analysis2)

import json
from collections import Counter, defaultdict
from datetime import datetime

class AgentBehaviorAnalyzer:
    """Agent 行为分析器"""
    
    def __init__(self):
        self.tool_calls = []
        self.thoughts = []
        self.errors = []
    
    def record_tool_call(self, agent: str, tool: str, input_data: str, output: str, duration: float):
        """记录工具调用"""
        self.tool_calls.append({
            "agent": agent,
            "tool": tool,
            "input_preview": input_data[:100],
            "output_preview": output[:100],
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_thought(self, agent: str, thought: str):
        """记录 Agent 思考过程"""
        self.thoughts.append({
            "agent": agent,
            "thought": thought[:200],
            "timestamp": datetime.now().isoformat()
        })
    
    def record_error(self, agent: str, error: str, context: str):
        """记录错误"""
        self.errors.append({
            "agent": agent,
            "error": error,
            "context": context[:200],
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_behavior_report(self) -> str:
        """生成行为分析报告"""
        report = "### Agent 行为分析报告\n\n"
        
        # 工具调用统计
        if self.tool_calls:
            tool_counts = Counter(tc["tool"] for tc in self.tool_calls)
            agent_tool_counts = defaultdict(Counter)
            for tc in self.tool_calls:
                agent_tool_counts[tc["agent"]][tc["tool"]] += 1
            
            report += "**工具调用统计:**\n"
            for tool, count in tool_counts.most_common():
                report += f"  - {tool}: {count} 次\n"
            
            report += "\n**各 Agent 的工具使用:**\n"
            for agent, tools in agent_tool_counts.items():
                report += f"  {agent}:\n"
                for tool, count in tools.most_common():
                    report += f"    - {tool}: {count} 次\n"
        
        # 错误分析
        if self.errors:
            error_types = Counter(e["error"].split(":")[0] for e in self.errors)
            report += f"\n**错误分析 ({len(self.errors)} 个错误):**\n"
            for error_type, count in error_types.most_common():
                report += f"  - {error_type}: {count} 次\n"
        
        # Token 估算
        total_chars = sum(len(tc["input_preview"]) + len(tc["output_preview"]) 
                         for tc in self.tool_calls)
        estimated_tokens = total_chars // 2  # 粗略估算
        report += f"\n**Token 估算:** 约 {estimated_tokens} tokens (工具调用相关)\n"
        
        return report


# 使用示例 - 集成到 CrewAI 的事件系统
analyzer = AgentBehaviorAnalyzer()

@crew_event_handler("tool_usage")
def on_tool_usage(source, event):
    """工具使用事件处理器"""
    analyzer.record_tool_call(
        agent=source.role if hasattr(source, 'role') else str(source),
        tool=event.get("tool_name", "unknown"),
        input_data=str(event.get("input", "")),
        output=str(event.get("output", ""))[:100],
        duration=event.get("duration", 0)
    )

@crew_event_handler("error")
def on_error(source, event):
    """错误事件处理器"""
    analyzer.record_error(
        agent=source.role if hasattr(source, 'role') else str(source),
        error=str(event.get("error", "")),
        context=str(event.get("context", ""))
    )

class MultiAgentDebugger:
    """多 Agent 协作调试器"""
    
    def __init__(self):
        self.handoffs = []  # Agent 之间的交接记录
        self.conflicts = []  # 冲突检测
    
    def record_handoff(self, from_agent: str, to_agent: str, data: str):
        """记录 Agent 交接"""
        self.handoffs.append({
            "from": from_agent,
            "to": to_agent,
            "data_preview": data[:300],
            "data_length": len(data),
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"📦 交接: {from_agent} → {to_agent} ({len(data)} 字符)")
    
    def detect_conflicts(self) -> List[dict]:
        """检测协作冲突"""
        conflicts = []
        
        # 检测循环依赖
        agent_graph = defaultdict(set)
        for handoff in self.handoffs:
            agent_graph[handoff["from"]].add(handoff["to"])
        
        for agent, targets in agent_graph.items():
            if agent in targets:
                conflicts.append({
                    "type": "循环依赖",
                    "agents": [agent, agent],
                    "severity": "高",
                    "message": f"Agent '{agent}' 存在自循环"
                })
        
        # 检测数据量异常
        for handoff in self.handoffs:
            if handoff["data_length"] > 10000:
                conflicts.append({
                    "type": "数据量过大",
                    "agents": [handoff["from"], handoff["to"]],
                    "severity": "中",
                    "message": f"从 {handoff['from']} 到 {handoff['to']} 的数据量过大 ({handoff['data_length']} 字符)"
                })
            
            if handoff["data_length"] < 10:
                conflicts.append({
                    "type": "数据量过小",
                    "agents": [handoff["from"], handoff["to"]],
                    "severity": "低",
                    "message": f"从 {handoff['from']} 到 {handoff['to']} 的数据量过小 ({handoff['data_length']} 字符)，可能信息不足"
                })
        
        self.conflicts = conflicts
        return conflicts
    
    def print_collaboration_report(self):
        """打印协作报告"""
        print("\n" + "="*50)
        print("多 Agent 协作调试报告")
        print("="*50)
        
        print(f"\n交接记录 ({len(self.handoffs)} 次):")
        for i, h in enumerate(self.handoffs, 1):
            print(f"  {i}. {h['from']} → {h['to']} ({h['data_length']} 字符)")
        
        if self.conflicts:
            print(f"\n发现冲突 ({len(self.conflicts)} 个):")
            for c in self.conflicts:
                severity_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(c["severity"], "⚪")
                print(f"  {severity_icon} [{c['severity']}] {c['type']}: {c['message']}")
        else:
            print("\n✅ 未发现协作冲突")


# 使用示例
debugger = MultiAgentDebugger()

# 模拟 Agent 协作流程
def simulate_collaboration():
    planner = Agent(role="测试经理", goal="制定测试计划", backstory="10年经验")
    designer = Agent(role="测试设计师", goal="设计测试用例", backstory="擅长边界值分析")
    executor = Agent(role="测试工程师", goal="执行测试", backstory="熟悉自动化测试")
    
    # 模拟交接
    plan = "测试计划：优先测试核心功能..."
    debugger.record_handoff("测试经理", "测试设计师", plan)
    
    test_cases = "测试用例：1. 正常登录 2. 密码错误..."
    debugger.record_handoff("测试设计师", "测试工程师", test_cases)
    
    results = "测试结果：通过 8/10..."
    debugger.record_handoff("测试工程师", "测试经理", results)
    
    # 检测冲突
    conflicts = debugger.detect_conflicts()
    debugger.print_collaboration_report()

import psutil
import os
import time
from typing import Dict, List

class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, threshold_mb: int = 500):
        self.threshold_mb = threshold_mb
        self.snapshots: List[Dict] = []
        self.process = psutil.Process(os.getpid())
    
    def take_snapshot(self, label: str = "") -> Dict:
        """拍摄内存快照"""
        memory_info = self.process.memory_info()
        snapshot = {
            "label": label,
            "timestamp": time.time(),
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "cpu_percent": self.process.cpu_percent()
        }
        self.snapshots.append(snapshot)
        
        # 检查是否超过阈值
        if snapshot["rss_mb"] > self.threshold_mb:
            print(f"⚠️ 内存警告: {snapshot['rss_mb']:.1f}MB > {self.threshold_mb}MB 阈值")
        
        return snapshot
    
    def generate_memory_report(self) -> str:
        """生成内存报告"""
        if not self.snapshots:
            return "无内存快照数据"
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        memory_growth = last["rss_mb"] - first["rss_mb"]
        
        report = f"""内存使用报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
初始内存: {first['rss_mb']:.1f}MB
当前内存: {last['rss_mb']:.1f}MB
内存增长: {memory_growth:+.1f}MB
虚拟内存: {last['vms_mb']:.1f}MB
CPU 使用: {last['cpu_percent']:.1f}%

快照历史:
"""
        for s in self.snapshots:
            report += f"  [{s['label']}] RSS: {s['rss_mb']:.1f}MB, VMS: {s['vms_mb']:.1f}MB\n"
        
        # 内存趋势分析
        if memory_growth > 100:
            report += "\n⚠️ 内存增长较快，可能存在内存泄漏"
        elif memory_growth > 50:
            report += "\n🟡 内存增长适中，建议持续观察"
        else:
            report += "\n✅ 内存使用稳定"
        
        return report
    
    def start_monitoring(self, interval: int = 30):
        """启动持续监控"""
        print(f"📊 内存监控已启动 (间隔: {interval}s, 阈值: {self.threshold_mb}MB)")
        self.take_snapshot("监控启动")
    
    def stop_monitoring(self):
        """停止监控并生成报告"""
        self.take_snapshot("监控停止")
        print(self.generate_memory_report())


# 使用示例
monitor = MemoryMonitor(threshold_mb=400)
monitor.start_monitoring(interval=10)

# 执行 CrewAI 任务
crew = Crew(agents=[...], tasks=[...])
result = crew.kickoff()

monitor.take_snapshot("任务执行后")
monitor.stop_monitoring()

import logging
import os
from typing import Optional

class DebugConfig:
    """调试配置管理器"""
    
    def __init__(self, 
                 verbose: bool = True,
                 log_level: str = "DEBUG",
                 trace_enabled: bool = True,
                 memory_monitoring: bool = True,
                 prompt_debug: bool = True,
                 log_file: Optional[str] = None):
        
        self.verbose = verbose
        self.trace_enabled = trace_enabled
        self.memory_monitoring = memory_monitoring
        self.prompt_debug = prompt_debug
        
        # 配置日志
        self._setup_logging(log_level, log_file)
        
        # 初始化调试工具
        self.tracer = ExecutionTracer() if trace_enabled else None
        self.memory_monitor = MemoryMonitor() if memory_monitoring else None
        self.prompt_debugger = PromptDebugger() if prompt_debug else None
        self.behavior_analyzer = AgentBehaviorAnalyzer()
        
        print("🔧 调试配置已加载:")
        print(f"  - Verbose: {verbose}")
        print(f"  - 链路追踪: {trace_enabled}")
        print(f"  - 内存监控: {memory_monitoring}")
        print(f"  - Prompt 调试: {prompt_debug}")
    
    def _setup_logging(self, level: str, log_file: Optional[str] = None):
        """配置日志系统"""
        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        
        handlers = [logging.StreamHandler()]
        if log_file:
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format,
            handlers=handlers
        )
    
    def start_debug_session(self):
        """开始调试会话"""
        print("\n" + "="*50)
        print("🔍 调试会话开始")
        print("="*50)
        
        if self.tracer:
            self.tracer.start()
        if self.memory_monitor:
            self.memory_monitor.start_monitoring()
    
    def end_debug_session(self) -> str:
        """结束调试会话并生成报告"""
        report = "\n" + "="*50 + "\n"
        report += "📊 调试会话报告\n"
        report += "="*50 + "\n"
        
        if self.tracer:
            report += self.tracer.generate_report()
        
        if self.memory_monitor:
            self.memory_monitor.stop_monitoring()
            report += self.memory_monitor.generate_memory_report()
        
        report += self.behavior_analyzer.generate_behavior_report()
        
        print(report)
        return report


# 使用示例 - 一行代码启动完整调试
debug = DebugConfig(
    verbose=True,
    log_level="DEBUG",
    trace_enabled=True,
    memory_monitoring=True,
    log_file="crewai_debug.log"
)

debug.start_debug_session()

# 执行你的 CrewAI 代码
crew = Crew(agents=[...], tasks=[...])
result = crew.kickoff()

debug.end_debug_session()

# 1. 检查 temperature 设置
# 过高的 temperature 会导致输出不稳定
llm = LLM(
    model="qwen-plus",
    temperature=0.9,  # ← 问题：temperature 太高
)

# 修复：降低 temperature
llm = LLM(
    model="qwen-plus",
    temperature=0.3,  # 确定性任务使用低 temperature
)

# 2. 检查 prompt 是否足够明确
# 模糊的 prompt 会导致 LLM "自由发挥"
task = Task(description="写测试用例")  # ← 问题：太模糊

# 修复：添加详细的约束和格式要求
task = Task(description="""请为登录功能生成 10 条测试用例。
要求：
1. 覆盖正常登录、密码错误、账号锁定三种场景
2. 每条用例包含：编号、场景、输入、预期结果
3. 使用表格格式输出""")

# 3. 添加 seed 参数（如果模型支持）
llm = LLM(
    model="qwen-plus",
    temperature=0.1,
    seed=42,  # 固定随机种子，提高可重复性
)

import signal
import traceback
from threading import Thread
import time

def debug_hang_issue():
    """调试卡死问题"""
    
    # 步骤 1：设置超时
    def timeout_handler(signum, frame):
        print("⏰ 执行超时！打印调用栈：")
        for thread_id, stack in sys._current_frames().items():
            print(f"\n线程 {thread_id}:")
            for line in traceback.format_stack(stack):
                print(line.strip())
        sys.exit(1)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)  # 2 分钟超时
    
    # 步骤 2：启用详细日志
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # 步骤 3：单独测试每个 Agent
    for agent in crew.agents:
        print(f"测试 Agent: {agent.role}")
        try:
            result = agent.kickoff(task=crew.tasks[0])
            print(f"✅ {agent.role} 执行成功")
        except Exception as e:
            print(f"❌ {agent.role} 执行失败: {e}")
    
    # 步骤 4：检查 Task 依赖
    for i, task in enumerate(crew.tasks):
        print(f"Task {i}: {task.description[:50]}...")
        if hasattr(task, 'context') and task.context:
            print(f"  上下文: {task.context}")
    
    # 步骤 5：检查 API 限制
    print(f"当前 RPM 限制: {getattr(crew, 'max_rpm', '未设置')}")
    
    signal.alarm(0)  # 取消超时


# 常见卡死原因及解决方案
HANG_SOLUTIONS = {
    "API 限流": "设置 max_rpm 参数，控制请求频率",
    "Agent 陷入循环": "设置 max_iter 参数限制迭代次数",
    "Task 依赖死锁": "检查 Task 的 context 依赖是否有循环",
    "网络问题": "检查网络连接，添加重试机制",
    "模型响应慢": "切换到更快的模型，或增加超时时间",
}

print("\n常见卡死原因及解决方案:")
for cause, solution in HANG_SOLUTIONS.items():
    print(f"  • {cause}: {solution}")
