from crewai import Agent

agent = Agent(
    role="测试专家",
    goal="设计测试用例",
    backstory="你有 10 年测试经验"
)

from langchain.agents import AgentExecutor
from langchain.prompts import PromptTemplate

prompt = PromptTemplate.from_template("""
你是测试专家，请设计测试用例。
你有 10 年测试经验。
{input}
""")

agent = AgentExecutor.from_agent_and_tools(
    agent=...,
    tools=[...],
    verbose=True
)

from crewai import Crew, Process

crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    process=Process.sequential
)
result = crew.kickoff()

# 需要自己实现协作逻辑
result1 = agent1.invoke(input)
result2 = agent2.invoke(result1)

from crewai import Tool

@tool
def api_test_tool(url: str, method: str = "GET") -> dict:
    """发送 API 请求并返回结果"""
    import requests
    response = requests.request(method, url, timeout=10)
    return {"status": response.status_code, "body": response.text}

agent = Agent(
    role="API 测试工程师",
    goal="测试接口功能",
    tools=[api_test_tool]
)

from langchain.tools import tool

@tool
def api_test_tool(url: str) -> str:
    """测试 API"""
    import requests
    response = requests.get(url)
    return f"Status: {response.status_code}"

from crewai import Agent, Task, Crew, Process

# 定义 4 个 Agent
planner = Agent(role="测试经理", goal="制定测试计划", backstory="10 年经验")
designer = Agent(role="测试设计师", goal="设计测试用例", backstory="擅长边界值分析")
executor = Agent(role="测试工程师", goal="执行测试", backstory="熟悉自动化测试")
reporter = Agent(role="报告专员", goal="生成测试报告", backstory="数据可视化专家")

# 定义 Task 和依赖关系
task1 = Task(description="生成测试计划", agent=planner)
task2 = Task(description="设计测试用例", agent=designer, expected_output="JSON 格式用例")
task3 = Task(description="执行测试", agent=executor)
task4 = Task(description="生成报告", agent=reporter)

# 顺序执行
crew = Crew(
    agents=[planner, designer, executor, reporter],
    tasks=[task1, task2, task3, task4],
    process=Process.sequential
)
result = crew.kickoff()

# 需要手动编排每个环节
plan = planner_chain.invoke({"requirement": "..."})
test_cases = designer_chain.invoke({"plan": plan})
execution_results = executor_chain.invoke({"test_cases": test_cases})
report = reporter_chain.invoke({"results": execution_results})

# ──────────────────────────────────────────────
# 步骤 1：使用 LangChain 构建测试知识库
# ──────────────────────────────────────────────
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# 加载测试规范文档
loader = TextLoader("test_specifications.txt", encoding="utf-8")
documents = loader.load()

# 分割文档
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = text_splitter.split_documents(documents)

# 构建向量数据库
embeddings = DashScopeEmbeddings(model="text-embedding-v3")
vectorstore = FAISS.from_documents(chunks, embeddings)

# 创建检索器
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})


# ──────────────────────────────────────────────
# 步骤 2：创建 LangChain RAG Chain
# ──────────────────────────────────────────────
from langchain.chains import RetrievalQA
from langchain_community.llms import Tongyi

llm = Tongyi(model_name="qwen-plus", temperature=0.3)

rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)


# ──────────────────────────────────────────────
# 步骤 3：将 LangChain Chain 封装为 CrewAI Tool
# ──────────────────────────────────────────────
from crewai_tools import BaseTool

class KnowledgeBaseTool(BaseTool):
    name: str = "测试知识库检索"
    description: str = "从测试知识库中检索相关的测试规范、标准和最佳实践"
    
    def __init__(self, rag_chain):
        super().__init__()
        self.rag_chain = rag_chain
    
    def _run(self, query: str) -> str:
        """检索知识库"""
        result = self.rag_chain.invoke({"query": query})
        
        output = f"## 知识库检索结果\n\n"
        output += f"**问题**: {query}\n\n"
        output += f"**答案**:\n{result['result']}\n\n"
        
        # 添加来源文档
        if result.get('source_documents'):
            output += "**来源文档**:\n"
            for i, doc in enumerate(result['source_documents'], 1):
                output += f"  {i}. {doc.metadata.get('source', 'N/A')} (相关性: {doc.metadata.get('score', 'N/A')})\n"
        
        return output


# ──────────────────────────────────────────────
# 步骤 4：创建 CrewAI Agent 并挂载知识库工具
# ──────────────────────────────────────────────
from crewai import Agent, Task, Crew

# 知识库工具
kb_tool = KnowledgeBaseTool(rag_chain)

# 测试专家 Agent - 使用知识库
test_expert = Agent(
    role="测试专家",
    goal="基于测试知识库设计高质量的测试方案",
    backstory="""你是资深测试专家，擅长利用测试规范和最佳实践来设计测试方案。
    你会先检索知识库中的相关规范，然后基于规范设计测试。""",
    tools=[kb_tool],
    verbose=True
)

# 测试执行 Agent
test_executor = Agent(
    role="测试执行工程师",
    goal="根据测试方案执行测试并记录结果",
    backstory="你熟悉各种测试执行工具和方法",
    verbose=True
)

# 创建任务
design_task = Task(
    description="""请检索测试知识库，了解登录功能的测试规范要求，
    然后设计完整的测试方案。""",
    agent=test_expert,
    expected_output="基于知识库的测试方案"
)

execute_task = Task(
    description="根据测试方案执行测试，记录测试结果",
    agent=test_executor,
    context=[design_task]
)

crew = Crew(
    agents=[test_expert, test_executor],
    tasks=[design_task, execute_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()

MIGRATION_CHECKLIST = {
    "团队规模": {
        "小团队 (< 5 人)": "CrewAI 上手更快，推荐",
        "大团队 (> 10 人)": "需要评估培训成本",
    },
    "项目类型": {
        "多 Agent 协作": "强烈建议迁移到 CrewAI",
        "单 Agent RAG 应用": "LangChain 更合适",
        "混合场景": "考虑混合架构",
    },
    "现有代码量": {
        "少量 (< 1000 行)": "可以直接重写",
        "中等 (1000-5000 行)": "逐步迁移",
        "大量 (> 5000 行)": "评估迁移成本，可能不值得",
    },
    "时间压力": {
        "紧急项目": "用熟悉的框架，不要临时换",
        "有充足时间": "可以学习和迁移",
    }
}

# 典型的 LangChain 多步骤编排
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# 步骤 A：生成测试计划
plan_prompt = PromptTemplate.from_template(
    "根据需求生成测试计划：{requirement}"
)
plan_chain = LLMChain(llm=llm, prompt=plan_prompt)

# 步骤 B：设计测试用例
case_prompt = PromptTemplate.from_template(
    "根据测试计划设计用例：{plan}"
)
case_chain = LLMChain(llm=llm, prompt=case_prompt)

# 步骤 C：执行测试
exec_prompt = PromptTemplate.from_template(
    "执行以下测试用例：{test_cases}"
)
exec_chain = LLMChain(llm=llm, prompt=exec_prompt)

# 手动编排执行流程
plan = plan_chain.run(requirement="登录功能测试")
test_cases = case_chain.run(plan=plan)
results = exec_chain.run(test_cases=test_cases)

from crewai import Agent, Task, Crew, Process

# Agent A：测试经理
planner = Agent(
    role="测试经理",
    goal="制定测试计划",
    backstory="10 年测试管理经验"
)

# Agent B：测试设计师
designer = Agent(
    role="测试设计师",
    goal="设计测试用例",
    backstory="擅长边界值分析和等价类划分"
)

# Agent C：测试工程师
executor = Agent(
    role="测试工程师",
    goal="执行测试",
    backstory="熟悉自动化测试工具"
)

# 定义任务（自动处理上下文传递）
task1 = Task(
    description="根据需求生成测试计划：{requirement}",
    agent=planner
)

task2 = Task(
    description="根据测试计划设计测试用例",
    agent=designer,
    context=[task1]  # 自动获取 task1 的输出作为上下文
)

task3 = Task(
    description="执行测试用例",
    agent=executor,
    context=[task2]  # 自动获取 task2 的输出作为上下文
)

# 一键执行
crew = Crew(
    agents=[planner, designer, executor],
    tasks=[task1, task2, task3],
    process=Process.sequential
)

result = crew.kickoff(inputs={"requirement": "登录功能测试"})
