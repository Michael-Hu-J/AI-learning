# Prompt 的核心结构
PLANNING_PROMPT = """
你是一个电商数据分析智能体。用户给你一个任务，你需要：

1. 将任务分解为多个子任务
2. 为每个子任务选择合适的工具
3. 建立子任务之间的依赖关系

可用工具：
- search: 知识库/业务检索（销售数据查询、报告生成等）
- calculator: 数学计算
- code_executor: 执行 Python 代码
- memory_store: 记忆存储/读取
- web_fetch: 获取网页内容
- safety_checker: 安全检测

输出格式（JSON）：
[
  {
    "id": "task_1",
    "description": "子任务描述",
    "depends_on": [],
    "tool": "search",
    "tool_input": "查询2024年6月各品类销售额"
  },
  {
    "id": "task_2",
    "description": "计算占比",
    "depends_on": ["task_1"],
    "tool": "calculator",
    "tool_input": "1250000 / 4710000"
  }
]

当前任务：分析2024年6月销售数据并生成报告
"""

def _parse_subtasks(self, content: str) -> List[SubTask]:
    try:
        json_str = self._extract_json(content)
        data = json.loads(json_str)
        if isinstance(data, list):
            return [SubTask(...) for item in data]
    except:
        pass
    return []  # 解析失败，返回空列表

# 空列表 → 退化为单任务
if not subtasks:
    subtasks = [SubTask(
        id="task_1",
        description=task,  # 原始任务
        depends_on=[],
        tool="none",
        tool_input="直接回答",
    )]

def _topological_sort(self, subtasks: List[SubTask]) -> List[str]:
    """确定执行顺序：依赖的先跑"""
    task_map = {s.id: s for s in subtasks}
    visited = set()
    order = []

    def visit(task_id):
        if task_id in visited:
            return
        visited.add(task_id)
        task = task_map.get(task_id)
        if task:
            for dep in task.depends_on:
                visit(dep)  # 先访问依赖
            order.append(task_id)  # 再访问自己

    for s in subtasks:
        visit(s.id)
    return order

if subtask.tool == "none":
    response = self._call_llm(f"请完成：{subtask.description}")
    subtask.result = response["content"]

result = ToolRegistry.execute(subtask.tool, subtask.tool_input, state)
subtask.result = result

@classmethod
def execute(cls, tool_name: str, tool_input: str, state: AgentState) -> str:
    if tool_name == "calculator":
        return cls._calculator(tool_input)
    elif tool_name == "search":
        return cls._search(tool_input)
    elif tool_name == "code_executor":
        return cls._code_executor(tool_input)
    # ... 其他工具

if not success:
    for attempt in range(subtask.max_retries - 1):
        if self._execute_subtask(subtask, state):
            subtask.status = "success"
            break
    else:
        subtask.status = "failed"  # 重试 3 次还是失败

REFLECTION_PROMPT = """
你是一个质量检查专家。一个智能体正在执行任务，已完成了一些子任务。

原始任务：分析2024年6月销售数据并生成报告
已完成子任务结果：
- task_1 (success): 查询销售数据 → 拿到各品类销售额
- task_2 (success): 计算占比 → 电子产品占26.5%
- task_3 (failed): 识别异常 → 工具调用失败

请检查：
1. 已完成的子任务结果是否合理
2. 是否需要调整后续计划
3. 当前进度是否足够生成最终答案

输出格式（JSON）：
{
  "status": "continue" | "replan" | "done",
  "reason": "判断理由",
  "adjustments": "调整内容"
}
"""

SUMMARY_PROMPT = """
你是一个任务总结专家。一个智能体已完成所有子任务，请汇总结果并给出最终答案。

原始任务：分析2024年6月销售数据并生成报告

子任务结果：
### task_1: 查询销售数据
状态: success
结果: 电子产品销售额1250000元，服装鞋帽890000元...

### task_2: 计算占比
状态: success
结果: 电子产品占比26.5%，服装鞋帽18.9%...

### task_3: 识别异常
状态: failed
结果: 错误: 工具调用失败

请给出清晰、完整的最终答案：
"""

TOOLS = {
    # ... 已有 6 个工具
    "email_sender": {
        "name": "email_sender",
        "description": "发送邮件。输入：收件人 + 主题 + 内容",
        "usage": "email_sender: 收件人@xxx.com, 销售报告, 附件已生成",
    },
}

elif tool_name == "email_sender":
    return cls._email_sender(tool_input)

@staticmethod
def _email_sender(input_str: str) -> str:
    # 解析收件人、主题、内容
    # 发送邮件（真实或 Mock）
    return f"[邮件发送] 已发送至 {recipient}"

BUSINESS_CONTEXT = """
你是一个医疗咨询智能体。你的职责是：
- 回答常见健康问题
- 根据症状推荐就诊科室
- 提供用药建议（非处方药）

注意：不提供诊断，不替代医生面诊。
"""

TOOLS = {
    "symptom_checker": {...},      # 症状查询
    "department_recommender": {...}, # 科室推荐
    "drug_database": {...},        # 药品查询
    "safety_checker": {...},       # 安全检测（保留）
}

self.api_base = "https://open.bigmodel.cn/api/paas/v4"  # 智谱
self.model = "glm-4"

class MyAgent:
    def __init__(self, api_key, model="qwen-plus"):
        self.api_key = api_key
        self.model = model

    def run(self, task, context=None):
        response = self._call_llm(task)
        return {"success": True, "output": response, "error": None}

    def reset(self):
        pass

#  危险写法
def _calculator(expression: str) -> str:
    return str(eval(expression))

#  安全写法
import ast

def _safe_eval_math(expression: str) -> float:
    tree = ast.parse(expression, mode='eval')
    # 只允许: 数字、加减乘除、幂、mod、abs/round/min/max/sum/pow
    # 禁止: 函数调用(除了白名单)、属性访问、导入
    return _walk_ast(tree.body)

#  失败时只知道"失败了"
response = requests.post(url, json=payload, timeout=60)
if response.status_code != 200:
    return None  # 为什么失败？不知道

#  失败时知道为什么失败
if response.status_code == 401:
    self._last_llm_error = "API Key 无效或已过期"
elif response.status_code == 429:
    self._last_llm_error = "请求频率超限，请稍后重试"
elif response.status_code >= 500:
    self._last_llm_error = f"服务端错误: {response.status_code}"
else:
    self._last_llm_error = f"HTTP {response.status_code}: {response.text[:200]}"

self.api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
self.model = "qwen-plus"
self.timeout = 60

self.api_base = kwargs.get("api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1")
self.model = kwargs.get("model", "qwen-plus")
self.llm_timeout = kwargs.get("llm_timeout", 60)
self.temperature = kwargs.get("temperature", 0.7)

agent = CustomAgent(temperature=0.1)  # 从 0.7 降到 0.1
