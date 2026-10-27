# app/agents/bug_analyst.py
from crewai import Agent, Task, LLM
from app.core.config import settings

def create_bug_analyst_agent():
    """创建 Bug 分析专家 Agent"""
    
    llm = LLM(
        model=settings.OPENAI_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL
    )
    
    return Agent(
        role="Bug 分析专家 (Bug Analysis Expert)",
        goal="分析测试结果，生成高质量的 Bug 报告",
        backstory="""你是资深的 Bug 分析专家，擅长：
        1. 从日志中定位根本原因
        2. 准确描述问题现象
        3. 提供详细的复现步骤
        4. 评估问题严重级别
        5. 给出修复建议
        
        你有 10 年测试经验，提交过 1000+ 高质量 Bug 报告。
        你的报告总是被开发高效理解和修复。
        
        你相信：好的 Bug 报告是解决问题的一半。""",
        llm=llm,
        verbose=False,
        allow_delegation=False
    )

# app/tasks/bug_analysis.py
from crewai import Task

def create_bug_analysis_task(test_results: str, logs: str, agent):
    """创建 Bug 分析任务"""
    
    return Task(
        description=f"""请分析以下测试结果和日志，生成 Bug 报告：

## 测试结果
{test_results}

## 执行日志
{logs}

请完成以下任务：

1. **问题识别**
   - 列出所有失败的测试用例
   - 描述每个问题的现象

2. **原因分析**
   - 分析每个问题的可能原因
   - 指出最可能的根本原因

3. **严重级别评估**
   - 阻塞 (Blocker): 系统无法继续使用
   - 严重 (Critical): 主要功能失效
   - 一般 (Major): 次要功能问题
   - 轻微 (Minor): 界面/体验问题

4. **复现步骤**
   - 提供详细的复现步骤
   - 包含前置条件和测试数据

5. **修复建议**
   - 给出可能的修复方向
   - 评估修复风险

请按以下 JSON 格式输出：
{{
  "bugs": [
    {{
      "title": "Bug 标题",
      "severity": "严重级别",
      "description": "问题描述",
      "steps_to_reproduce": ["步骤 1", "步骤 2"],
      "expected_result": "期望结果",
      "actual_result": "实际结果",
      "root_cause": "根本原因",
      "suggestion": "修复建议",
      "evidence": "相关日志"
    }}
  ],
  "summary": "测试总结",
  "total_passed": 通过数量，
  "total_failed": 失败数量，
  "pass_rate": 通过率
}}
""",
        expected_output="JSON 格式的 Bug 分析报告",
        agent=agent
    )

# app/tools/log_parser.py
from crewai_tools import BaseTool
import re
from typing import List, Dict

class LogParserTool(BaseTool):
    """日志解析工具"""
    
    name: str = "日志解析器"
    description: str = "解析测试日志，提取关键信息"
    
    def _run(self, log_text: str) -> Dict:
        """解析日志"""
        
        result = {
            "errors": [],
            "warnings": [],
            "api_calls": [],
            "execution_time": 0
        }
        
        # 提取错误
        error_pattern = r'ERROR.*?(?=\n|$)'
        result["errors"] = re.findall(error_pattern, log_text, re.IGNORECASE)
        
        # 提取警告
        warning_pattern = r'WARNING.*?(?=\n|$)'
        result["warnings"] = re.findall(warning_pattern, log_text, re.IGNORECASE)
        
        # 提取 API 调用
        api_pattern = r'(GET|POST|PUT|DELETE)\s+(/\S+)'
        result["api_calls"] = re.findall(api_pattern, log_text)
        
        # 提取执行时间
        time_pattern = r'Execution time: (\d+\.?\d*)s'
        time_match = re.search(time_pattern, log_text)
        if time_match:
            result["execution_time"] = float(time_match.group(1))
        
        return result

# 使用
log_parser = LogParserTool()
parsed_result = log_parser.run(log_text)

# app/tools/error_classifier.py
from typing import List, Dict

class ErrorClassifierTool(BaseTool):
    """错误分类工具"""
    
    name: str = "错误分类器"
    description: str = "对错误进行分类和定级"
    
    error_categories = {
        "API_ERROR": {
            "keywords": ["404", "500", "502", "503", "timeout", "connection"],
            "severity": "严重"
        },
        "ASSERTION_ERROR": {
            "keywords": ["assert", "expect", "should", "mismatch"],
            "severity": "一般"
        },
        "DATA_ERROR": {
            "keywords": ["null", "undefined", "invalid data", "format"],
            "severity": "一般"
        },
        "UI_ERROR": {
            "keywords": ["element not found", "click failed", "visible"],
            "severity": "轻微"
        },
        "PERFORMANCE_ERROR": {
            "keywords": ["slow", "timeout", "exceeded", "performance"],
            "severity": "严重"
        }
    }
    
    def _run(self, error_message: str) -> Dict:
        """分类错误"""
        
        for category, info in self.error_categories.items():
            if any(kw in error_message.lower() for kw in info["keywords"]):
                return {
                    "category": category,
                    "severity": info["severity"],
                    "confidence": 0.8
                }
        
        # 默认分类
        return {
            "category": "UNKNOWN",
            "severity": "一般",
            "confidence": 0.5
        }

# app/reporters/bug_reporter.py
from datetime import datetime
from typing import List, Dict

class BugReporter:
    """Bug 报告生成器"""
    
    def __init__(self, project_name: str = "默认项目"):
        self.project_name = project_name
    
    def generate_markdown(self, bugs: List[Dict], summary: Dict) -> str:
        """生成 Markdown 格式 Bug 报告"""
        
        report = f"""# Bug 分析报告

**项目**: {self.project_name}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**测试总结**: {summary.get('summary', '')}

## 测试概览

| 指标 | 数值 |
|------|------|
| 通过数量 | {summary.get('total_passed', 0)} |
| 失败数量 | {summary.get('total_failed', 0)} |
| 通过率 | {summary.get('pass_rate', 0):.1f}% |

---

## Bug 详情

"""
        
        for i, bug in enumerate(bugs, 1):
            report += f"""### Bug #{i}: {bug.get('title', '未命名')}

**严重级别**: {bug.get('severity', '未知')}

**问题描述**:
{bug.get('description', '')}

**复现步骤**:
"""
            for j, step in enumerate(bug.get('steps_to_reproduce', []), 1):
                report += f"{j}. {step}\n"
            
            report += f"""
**期望结果**: {bug.get('expected_result', '')}

**实际结果**: {bug.get('actual_result', '')}

**根本原因**: {bug.get('root_cause', '待分析')}

**修复建议**: {bug.get('suggestion', '待评估')}

**相关日志**:

# app/integrations/jira_client.py
from jira import JIRA
import os

class JiraClient:
    """Jira 客户端"""
    
    def __init__(self):
        self.jira = JIRA(
            server=os.getenv("JIRA_SERVER"),
            basic_auth=(
                os.getenv("JIRA_EMAIL"),
                os.getenv("JIRA_API_TOKEN")
            )
        )
    
    def create_bug(self, project_key: str, bug_data: Dict) -> str:
        """创建 Bug"""
        
        issue = self.jira.create_issue(
            fields={
                'project': {'key': project_key},
                'summary': bug_data['summary'],
                'description': bug_data['description'],
                'issuetype': bug_data['issuetype'],
                'priority': bug_data['priority'],
                'labels': ['auto-generated', 'crewai']
            }
        )
        
        return issue.key
    
    def batch_create_bugs(self, project_key: str, bugs: List[Dict]) -> List[str]:
        """批量创建 Bug"""
        
        issue_keys = []
        for bug in bugs:
            try:
                key = self.create_bug(project_key, bug)
                issue_keys.append(key)
            except Exception as e:
                print(f"创建 Bug 失败：{bug['summary']}, 错误：{e}")
        
        return issue_keys

# app/integrations/zentao_client.py
import requests
import os

class ZenTaoClient:
    """禅道客户端"""
    
    def __init__(self):
        self.base_url = os.getenv("ZENTAO_SERVER")
        self.username = os.getenv("ZENTAO_USERNAME")
        self.password = os.getenv("ZENTAO_PASSWORD")
        self.session = requests.Session()
        self._login()
    
    def _login(self):
        """登录禅道"""
        login_url = f"{self.base_url}/user-login.html"
        data = {
            'account': self.username,
            'password': self.password
        }
        self.session.post(login_url, data=data)
    
    def create_bug(self, product_id: int, bug_data: Dict) -> int:
        """创建 Bug"""
        
        url = f"{self.base_url}/bug-create-{product_id}-0-moduleID=0.html"
        
        data = {
            'productID': product_id,
            'title': bug_data['summary'],
            'steps': bug_data['description'],
            'pri': self._map_severity(bug_data.get('priority', {}).get('name', '')),
            'type': 'code'
        }
        
        response = self.session.post(url, data=data)
        
        # 提取 Bug ID
        bug_id = self._extract_bug_id(response.url)
        return bug_id
    
    def _map_severity(self, priority: str) -> int:
        """映射优先级到禅道级别"""
        mapping = {
            'Highest': 4,
            'High': 3,
            'Medium': 2,
            'Low': 1
        }
        return mapping.get(priority, 2)
    
    def _extract_bug_id(self, url: str) -> int:
        """从 URL 提取 Bug ID"""
        # 实现 URL 解析逻辑
        pass

# app/workflows/bug_reporting.py
from crewai import Crew, Process
from app.agents.bug_analyst import create_bug_analyst_agent
from app.tasks.bug_analysis import create_bug_analysis_task
from app.reporters.bug_reporter import BugReporter
from app.integrations.jira_client import JiraClient

async def generate_and_submit_bugs(
    test_results: str,
    logs: str,
    project_key: str = "TEST"
):
    """生成并提交 Bug 报告"""
    
    # 1. 创建 Bug 分析 Agent
    analyst = create_bug_analyst_agent()
    
    # 2. 创建分析任务
    analysis_task = create_bug_analysis_task(test_results, logs, analyst)
    
    # 3. 执行分析
    crew = Crew(
        agents=[analyst],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    
    # 4. 解析结果
    import json
    bug_report = json.loads(result.raw)
    
    # 5. 生成 Markdown 报告
    reporter = BugReporter(project_name=project_key)
    markdown_report = reporter.generate_markdown(
        bug_report['bugs'],
        bug_report['summary']
    )
    
    # 6. 保存到文件
    with open(f"bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", 'w') as f:
        f.write(markdown_report)
    
    # 7. 提交到 Jira
    jira_client = JiraClient()
    jira_bugs = reporter.generate_jira_format(bug_report['bugs'])
    issue_keys = jira_client.batch_create_bugs(project_key, jira_bugs)
    
    return {
        "markdown_report": markdown_report,
        "jira_issues": issue_keys,
        "bug_count": len(bug_report['bugs'])
    }

# 使用
result = asyncio.run(generate_and_submit_bugs(test_results, logs))
print(f"生成了 {result['bug_count']} 个 Bug")
print(f"Jira Issue: {result['jira_issues']}")

# app/schedulers/bug_report_scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job(CronTrigger(hour=18, minute=0))  # 每天 18:00
async def daily_bug_report():
    """每日 Bug 报告"""
    # 获取当天的测试结果
    test_results = get_today_test_results()
    logs = get_today_logs()
    
    # 生成并提交 Bug
    result = await generate_and_submit_bugs(test_results, logs)
    
    # 发送通知
    send_notification(f"生成了 {result['bug_count']} 个 Bug")

# 启动调度器
scheduler.start()
