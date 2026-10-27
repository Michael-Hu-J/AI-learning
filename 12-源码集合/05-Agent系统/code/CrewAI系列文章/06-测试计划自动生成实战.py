requirement = """
秒杀系统需求文档

## 1. 系统概述
秒杀系统是一个高并发、低延迟的电商促销系统，在指定时间开放限量商品购买。

## 2. 核心功能

### 2.1 秒杀活动管理
- 创建秒杀活动（时间、商品、库存）
- 编辑/删除秒杀活动
- 上下架秒杀商品

### 2.2 秒杀参与
- 用户查询秒杀活动列表
- 用户查询秒杀商品详情
- 用户在秒杀时间开始后参与秒杀
- 系统校验用户资格（限购规则）
- 系统扣减库存
- 系统生成订单

### 2.3 订单管理
- 查询秒杀订单
- 取消秒杀订单
- 秒杀订单退款

### 2.4 库存管理
- 库存预热
- 库存扣减
- 库存回滚（订单取消时）

## 3. 业务规则

### 3.1 时间规则
- 秒杀开始前：用户可以浏览，不能购买
- 秒杀进行中：用户可以参与购买
- 秒杀结束后：不能购买，已生成订单有效

### 3.2 限购规则
- 每个用户每个活动限购 1 件
- 同一用户重复请求返回"已购买"

### 3.3 库存规则
- 库存有限，先到先得
- 库存为 0 时返回"已售罄"
- 订单取消后库存回滚

### 3.4 并发控制
- 防止超卖（库存不能为负）
- 防止重复购买
- 保证数据一致性

## 4. 性能要求
- 支持 10000+ QPS
- 接口响应时间 < 100ms
- 系统可用性 > 99.9%
"""

from crewai import Agent, Task, Crew, LLM
from app.core.config import settings
import asyncio


def create_manager_agent():
    """创建测试经理 Agent"""
    llm = LLM(
        model=settings.OPENAI_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL
    )
    
    return Agent(
        role="测试经理 (Test Manager)",
        goal="制定测试计划，分配测试任务，管理测试进度，保证测试质量",
        backstory="""你是拥有 15 年经验的测试经理，擅长：
        1. 根据需求评估测试范围和工作量
        2. 制定合理的测试计划和优先级
        3. 识别高风险区域并重点测试
        4. 协调资源，保证测试按时完成
        
        你的工作风格：
        - 结果导向，关注测试覆盖率
        - 风险推动，优先测试核心功能
        - 数据分析，用指标说话
        
        你曾经在多个大型电商系统负责测试管理，对秒杀系统、订单系统、支付系统
        的测试有丰富经验。你深知测试的价值不在于找 bug，而在于降低业务风险。""",
        llm=llm,
        verbose=False,
        allow_delegation=False
    )


async def run_manager_agent(requirement: str, client_id: str) -> str:
    """
    运行测试经理 Agent
    
    Args:
        requirement: 需求文档
        client_id: WebSocket 客户端 ID
        
    Returns:
        生成的测试计划
    """
    agent = create_manager_agent()
    
    task = Task(
        description=f"""
作为测试经理，请根据以下需求文档制定测试计划：

{requirement}

请输出以下内容：

## 1. 测试范围
列出需要测试的功能模块，标注哪些需要测试、哪些不需要测试及原因。

## 2. 测试优先级
按 P0(核心)/P1(重要)/P2(一般)/P3(可选) 分级，说明分级理由。

## 3. 测试类型
标注每个功能需要的测试类型：功能测试/性能测试/安全测试/兼容性测试。

## 4. 工作量评估
预计需要多少人天完成测试。

## 5. 风险识别
列出哪些地方容易出问题，需要重点测试。

## 输出格式要求
使用 Markdown 格式，结构清晰，便于后续任务使用。
""",
        expected_output="完整的测试计划文档，包含测试范围、优先级、类型、工作量评估和风险识别",
        agent=agent
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=False
    )
    
    # 执行并获取结果
    result = await asyncio.to_thread(crew.kickoff)
    
    return str(result)

# 阶段 1：测试经理
# send_log(task_id, "agent_start", " 测试经理开始制定测试计划...")  # 异步调用示例

from app.agents.manager import run_manager_agent
# test_plan = await run_manager_agent(requirement, task_id)  # 异步调用示例

# 保存测试计划
plan_file = os.path.join(output_dir, "01_test_plan.md")
with open(plan_file, "w", encoding="utf-8") as f:
    f.write(test_plan)

# send_log(task_id, "agent_complete", " 测试经理完成测试计划", {
    # "output_file": "01_test_plan.md",
    # "word_count": len(test_plan)
# # })

# 发送开始日志
# send_log(task_id, "agent_start", " 测试经理开始制定测试计划...")  # 异步调用示例

# Agent 执行中...

# 发送完成日志
# send_log(task_id, "agent_complete", " 测试经理完成测试计划", {
    # "output_file": "01_test_plan.md",
    # "word_count": len(test_plan)
# # })
