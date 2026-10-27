class DatabaseQueryTool(BaseTool):
    name: str = "数据库查询"
    description: str = "查询数据库"
    
    def _run(self, query: str) -> str:
        conn = sqlite3.connect("business.db")
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return str(results)

from crewai_tools import BaseTool
import sqlite3
import re

class DatabaseQueryTool(BaseTool):
    name: str = "数据库查询"
    description: str = """执行SQL查询，返回结果。
    输入应该是完整的SQL SELECT语句。
    示例：SELECT COUNT(*) FROM users WHERE created_at = '2024-05-14'
    注意：只支持SELECT查询，不支持INSERT、UPDATE、DELETE、DROP等操作。
    适用场景：查询用户数、订单数、销售额等统计数据。
    不适用场景：修改数据、删除数据、修改表结构。"""
    
    def _run(self, query: str) -> str:
        """执行SQL查询"""
        # 安全检查：只允许SELECT语句
        if not query.strip().upper().startswith("SELECT"):
            return "错误：只支持SELECT查询，不支持其他操作"
        
        # 安全检查：禁止危险关键字
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]
        for keyword in dangerous_keywords:
            if keyword in query.upper():
                return f"错误：禁止使用{keyword}操作"
        
        try:
            conn = sqlite3.connect("business.db")
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            return str(results)
        except Exception as e:
            return f"查询失败：{str(e)}"

class MyTool(BaseTool):
    name: str = "工具名称"  # 简短、描述性强
    description: str = """工具描述，告诉 Agent 什么时候用这个工具、
    输入参数格式是什么。描述越详细，Agent 选对的概率越高。"""
    
    def _run(self, input_param: str) -> str:
        """
        实现工具逻辑。
        返回结果要清晰，方便 Agent 理解和使用。
        """
        try:
            result = self._execute_logic(input_param)
            return f"成功：{result}"
        except Exception as e:
            return f"失败：{str(e)}"

from crewai_tools import BaseTool
import sqlite3

# 定义 SQL 查询工具
class DatabaseQueryTool(BaseTool):
    name: str = "数据库查询"
    description: str = "执行 SQL 查询，返回结果。输入应该是完整的 SQL SELECT 语句。"
    
    def _run(self, query: str) -> str:
        try:
            conn = sqlite3.connect("business.db")
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            return str(results)
        except Exception as e:
            return f"查询失败：{str(e)}"

# 定义计算器工具
class CalculatorTool(BaseTool):
    name: str = "计算器"
    description: str = "执行数学计算，如加减乘除、求平均值等。输入数学表达式。"
    
    def _run(self, expression: str) -> str:
        try:
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"计算失败：{str(e)}"

# 创建 Agent 并绑定工具
analyst_agent = Agent(
    role="数据分析师",
    goal="回答业务数据的查询",
    backstory="擅长 SQL 和数据分析",
    tools=[DatabaseQueryTool(), CalculatorTool()],
    verbose=True,
)

from pydantic import BaseModel, validator
from typing import List, Optional
import re

class SQLQueryParams(BaseModel):
    query: str
    
    @validator("query")
    def validate_query(cls, v):
        # 1. 格式验证：不能为空
        if not v or len(v.strip()) == 0:
            raise ValueError("查询语句不能为空")
        
        # 2. 类型验证：必须是字符串
        if not isinstance(v, str):
            raise ValueError("查询语句必须是字符串类型")
        
        # 3. 范围验证：只允许SELECT语句
        if not v.strip().upper().startswith("SELECT"):
            raise ValueError("只支持SELECT查询")
        
        # 4. 安全验证：禁止危险关键字
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]
        for keyword in dangerous_keywords:
            if keyword in v.upper():
                raise ValueError(f"禁止使用{keyword}操作")
        
        # 5. 安全验证：检测SQL注入特征
        if re.search(r"'.*OR\s+\d+=\d+", v, re.IGNORECASE):
            raise ValueError("检测到可能的SQL注入，请检查查询语句")
        
        return v

from enum import Enum
from typing import Dict, List

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class PermissionManager:
    def __init__(self):
        # Agent权限映射
        self.agent_permissions: Dict[str, List[Permission]] = {
            "data_analyst": [Permission.READ],
            "security_tester": [Permission.READ, Permission.WRITE],
            "admin": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
        }
        # 工具权限要求
        self.tool_permissions: Dict[str, Permission] = {
            "DatabaseQueryTool": Permission.READ,
            "FileWriteTool": Permission.WRITE,
            "DatabaseDeleteTool": Permission.DELETE,
            "SystemConfigTool": Permission.ADMIN,
        }
    
    def check_permission(self, agent_id: str, tool_name: str) -> bool:
        """检查Agent是否有权限调用工具"""
        agent_perms = self.agent_permissions.get(agent_id, [])
        tool_perm = self.tool_permissions.get(tool_name)
        
        if tool_perm in agent_perms:
            return True
        
        print(f"权限不足：Agent {agent_id} 不能调用工具 {tool_name}")
        return False
    
    def add_agent_permission(self, agent_id: str, permission: Permission):
        """动态添加Agent权限"""
        if agent_id not in self.agent_permissions:
            self.agent_permissions[agent_id] = []
        if permission not in self.agent_permissions[agent_id]:
            self.agent_permissions[agent_id].append(permission)

class ApprovalManager:
    def __init__(self):
        self.approval_required_tools = ["DatabaseDeleteTool", "SystemConfigTool"]
    
    def needs_approval(self, tool_name: str) -> bool:
        return tool_name in self.approval_required_tools
    
    def request_approval(self, agent_id: str, tool_name: str, params: dict) -> bool:
        """请求人工审批"""
        print(f"⚠️ 审批请求：Agent {agent_id} 请求调用 {tool_name}")
        print(f"参数：{params}")
        # 实际场景中，这里会发送通知给管理员
        # 管理员确认后返回True，拒绝则返回False
        return False  # 默认拒绝，需要人工确认

import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        return f"重试{max_retries}次后仍然失败：{str(e)}"
                    print(f"第{i+1}次调用失败：{e}，{delay}秒后重试...")
                    time.sleep(delay)
        return wrapper
    return decorator

class ToolCaller:
    def __init__(self):
        self.tools = {}
        self.fallback_tools = {
            "DatabaseQueryTool": "CacheQueryTool",  # 数据库查询失败时降级到缓存查询
            "GoogleSearchTool": "BaiduSearchTool",   # Google搜索失败时降级到百度搜索
        }
        self.circuit_breakers = {}  # 熔断器
    
    def call_tool(self, agent_id, tool_name, params):
        """带错误处理的工具调用"""
        # 1. 熔断检查
        if self.is_circuit_open(tool_name):
            return {"status": "error", "message": f"工具{tool_name}已熔断，请稍后重试"}
        
        # 2. 权限检查
        if not self.pm.check_permission(agent_id, tool_name):
            return {"status": "error", "message": "权限不足"}
        
        # 3. 参数验证
        validated_params = self.validate_params(tool_name, params)
        if not validated_params:
            return {"status": "error", "message": "参数验证失败"}
        
        # 4. 调用工具（带重试）
        try:
            tool = self.tools[tool_name]
            result = self._retry_call(tool._run, **validated_params)
            self.record_success(tool_name)  # 记录成功，关闭熔断
            return {"status": "success", "result": result}
        except Exception as e:
            self.record_failure(tool_name)  # 记录失败，可能触发熔断
            # 5. 降级处理
            fallback_tool = self.fallback_tools.get(tool_name)
            if fallback_tool:
                print(f"工具{tool_name}调用失败，降级到{fallback_tool}")
                return self.call_tool(agent_id, fallback_tool, params)
            return {"status": "error", "message": str(e)}

def test_tool_calling(agent, test_cases):
    """
    test_cases: [{
        "task": "查询用户数",
        "expected_tool": "DatabaseQueryTool",
        "expected_params": "SELECT",
        "expected_result_contains": "1253"
    }]
    """
    passed = 0
    failures = []
    
    for case in test_cases:
        # Agent处理任务
        result = agent.execute(case["task"])
        
        # 检查是否调用了正确的工具
        if case["expected_tool"] in result["calls"]:
            # 检查参数是否正确
            if case["expected_params"] in result["calls"][case["expected_tool"]]:
                # 检查结果是否正确
                if "expected_result_contains" in case:
                    if case["expected_result_contains"] in result["output"]:
                        passed += 1
                    else:
                        failures.append((case["task"], "结果不正确"))
                else:
                    passed += 1
            else:
                failures.append((case["task"], "参数错误"))
        else:
            failures.append((case["task"], "调用了错误的工具"))
    
    pass_rate = passed / len(test_cases) if test_cases else 0
    
    return {
        "total": len(test_cases),
        "passed": passed,
        "failed": len(failures),
        "pass_rate": pass_rate,
        "failures": failures
    }

from crewai import Agent, Task, Crew
from crewai_tools import BaseTool
from pydantic import BaseModel, validator

# 定义工具
class SearchTool(BaseTool):
    name: str = "搜索引擎"
    description: str = "搜索互联网获取实时信息"
    
    def _run(self, query: str) -> str:
        # 模拟搜索
        return f"搜索结果：{query}"

# 定义Agent
researcher = Agent(
    role="研究分析师",
    goal="收集和分析相关信息",
    backstory="你是一名专业的研究分析师",
    tools=[SearchTool()],
    allow_delegation=False
)

# 定义任务
task = Task(
    description="搜索最新的AI发展趋势",
    expected_output="一份AI发展趋势报告",
    agent=researcher
)

# 执行
crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_openai import ChatOpenAI

# 定义工具
@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误：{str(e)}"

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气"""
    # 模拟天气查询
    return f"{city}的天气：晴天，25°C"

# 初始化Agent
llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = [calculate, get_weather]
agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

# 测试
result = agent.run("北京今天天气怎么样？")
print(result)

import autogen

# 定义工具函数
def get_stock_price(symbol: str) -> dict:
    """获取股票价格
    Args:
        symbol: 股票代码，如" AAPL"
    Returns:
        包含价格和信息的字典
    """
    return {"symbol": symbol, "price": 150.25, "change": "+2.3%"}

# 配置Agent
config_list = [{"model": "gpt-4", "api_key": "your-key"}]
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

# 注册工具
user_proxy.register_function(
    function_map={"get_stock_price": get_stock_price},
)

# 测试
user_proxy.initiate_chat(
    assistant,
    message="帮我查一下AAPL的股票价格",
)

class ToolCallingTester:
    """通用工具调用测试器"""
    
    def __init__(self, agent, tools):
        self.agent = agent
        self.tools = {t.name: t for t in tools}
        self.results = []
    
    def test_tool_selection(self, task, expected_tool_name):
        """测试工具选择"""
        result = self.agent.execute(task)
        called_tools = result.get("called_tools", [])
        
        if expected_tool_name in called_tools:
            return {"status": "pass", "message": f"正确选择了{expected_tool_name}"}
        else:
            return {
                "status": "fail",
                "message": f"预期选择{expected_tool_name}，实际选择了{called_tools}"
            }
    
    def test_parameter_correctness(self, task, expected_tool_name, expected_params):
        """测试参数正确性"""
        result = self.agent.execute(task)
        tool_call = result.get("tool_calls", {}).get(expected_tool_name, {})
        
        errors = []
        for param_name, expected_value in expected_params.items():
            actual_value = tool_call.get("params", {}).get(param_name)
            if actual_value != expected_value:
                errors.append(f"参数{param_name}：预期{expected_value}，实际{actual_value}")
        
        if errors:
            return {"status": "fail", "message": "; ".join(errors)}
        return {"status": "pass", "message": "所有参数正确"}
    
    def test_error_handling(self, task, error_scenario):
        """测试错误处理"""
        # 模拟错误场景
        self.simulate_error(error_scenario)
        result = self.agent.execute(task)
        
        if result.get("status") == "error":
            if "message" in result and len(result["message"]) > 0:
                return {"status": "pass", "message": "错误处理正确，返回了错误信息"}
        return {"status": "fail", "message": "错误处理不正确"}
    
    def run_full_test(self, test_cases):
        """运行完整测试"""
        all_results = []
        for case in test_cases:
            if case["test_type"] == "selection":
                r = self.test_tool_selection(case["task"], case["expected_tool"])
            elif case["test_type"] == "parameter":
                r = self.test_parameter_correctness(
                    case["task"], case["expected_tool"], case["expected_params"]
                )
            elif case["test_type"] == "error":
                r = self.test_error_handling(case["task"], case["error_scenario"])
            all_results.append({"case": case, "result": r})
        return all_results
