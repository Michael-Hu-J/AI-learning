# Step 1: 生成接口定义
step1_prompt = """
你是一名 API 测试架构师。请分析以下需求，输出 API 接口定义清单。
需求：用户管理系统 REST API，包含注册、登录、获取用户信息三个接口。
输出格式：接口名称 | 方法 | URL | 请求参数 | 响应格式
"""
step1_result = call_llm(step1_prompt)

# Step 2: 生成测试用例（显式引用上一步输出）
step2_prompt = f"""
你是一名测试工程师。基于以下 API 定义，生成 pytest 测试用例。
{step1_result}
要求：每个接口至少 3 个用例（正常、异常、边界），使用 requests 库。
"""
step2_result = call_llm(step2_prompt)

# Step 3: 生成测试报告模板
step3_prompt = f"""
基于以下测试用例，生成测试执行报告模板。
{step2_result}
输出格式：Markdown 表格，包含用例 ID、执行结果、失败原因。
"""
step3_result = call_llm(step3_prompt)

def chained_execution(steps, initial_input):
    """链式执行，每步验证后再继续"""
    current_input = initial_input
    
    for i, step in enumerate(steps):
        print(f"--- 步骤 {i+1}: {step['name']} ---")
        
        # 执行当前步骤
        output = call_llm(step["prompt"].format(input=current_input))
        
        # 验证输出质量
        validation = step["validator"](output)
        if not validation["passed"]:
            print(f"❌ 步骤 {i+1} 验证失败: {validation['reason']}")
            print(f"   输出: {output[:200]}")
            # 可以选择重试或终止
            if step.get("retry", False):
                print(f"   重试中...")
                output = call_llm(step["prompt"].format(input=current_input))
            else:
                raise ValueError(f"步骤 {i+1} 验证失败，终止执行")
        else:
            print(f"✅ 步骤 {i+1} 验证通过")
        
        current_input = output
    
    return current_input

steps = [
    {
        "name": "分析需求",
        "prompt": "分析以下需求，输出功能点列表:\n{input}",
        "validator": lambda out: {
            "passed": len(out.split("\n")) >= 3,
            "reason": "功能点少于3个"
        },
        "retry": True,
    },
    {
        "name": "生成测试用例",
        "prompt": "基于以下功能点生成测试用例:\n{input}",
        "validator": lambda out: {
            "passed": "TC-" in out or "case" in out.lower(),
            "reason": "输出不包含测试用例"
        },
        "retry": True,
    },
    {
        "name": "生成测试报告",
        "prompt": "基于以下测试用例生成报告模板:\n{input}",
        "validator": lambda out: {
            "passed": "通过" in out or "pass" in out.lower(),
            "reason": "报告不包含执行结果字段"
        },
        "retry": False,
    },
]

import concurrent.futures

def parallel_decomposition(task, sub_tasks):
    """并行执行独立的子任务"""
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_task = {
            executor.submit(call_llm, f"{task['role']}\n{sub}"): name
            for name, sub in sub_tasks.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_task):
            name = future_to_task[future]
            try:
                results[name] = future.result()
                print(f"✅ {name} 完成")
            except Exception as e:
                print(f"❌ {name} 失败: {e}")
    
    # 合并结果
    merged = "\n\n".join([f"## {name}\n{result}" for name, result in results.items()])
    return merged

task = {"role": "你是一名测试架构师。"}
sub_tasks = {
    "功能测试": "为登录模块设计功能测试用例",
    "安全测试": "为登录模块设计安全测试用例",
    "性能测试": "为登录模块设计性能测试用例",
}
result = parallel_decomposition(task, sub_tasks)

def generate_dependency_graph(steps):
    """生成任务依赖图的 Mermaid 语法"""
    lines = ["graph LR"]
    
    for i, step in enumerate(steps):
        step_id = f"Step{i+1}"
        step_name = step["name"]
        lines.append(f'    {step_id}["{step_name}"]')
        
        # 添加依赖关系
        if "depends_on" in step:
            for dep in step["depends_on"]:
                dep_id = f"Step{dep}"
                lines.append(f"    {dep_id} --> {step_id}")
    
    return "\n".join(lines)

# 使用示例
steps_with_deps = [
    {"name": "需求分析", "depends_on": []},
    {"name": "接口分析", "depends_on": [1]},
    {"name": "测试范围", "depends_on": [1]},
    {"name": "测试策略", "depends_on": [3]},
    {"name": "测试用例", "depends_on": [4, 2]},
    {"name": "测试报告", "depends_on": [5]},
]

print(generate_dependency_graph(steps_with_deps))

import json
import os
from datetime import datetime

def save_step_result(step_name, result, output_dir="task_results"):
    """保存步骤结果到文件"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{step_name}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "step_name": step_name,
            "timestamp": timestamp,
            "result": result
        }, f, ensure_ascii=False, indent=2)
    
    return filename

def load_step_result(filename):
    """加载步骤结果"""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["result"]
