# 对比测试核心逻辑：分别用两个模型回答同一问题，对比语义相似度
from sentence_transformers import SentenceTransformer, util

def compare_responses(base_client, ft_client, test_data):
    eval_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    results = []
    
    for item in test_data:
        base_resp = base_client.chat.completions.create(
            model="base-model",
            messages=[{"role": "user", "content": item['question']}],
            temperature=0.3, max_tokens=500
        ).choices[0].message.content
        
        ft_resp = ft_client.chat.completions.create(
            model="ft-model",
            messages=[{"role": "user", "content": item['question']}],
            temperature=0.3, max_tokens=500
        ).choices[0].message.content
        
        # 计算与期望答案的语义相似度
        base_sim = util.cos_sim(
            eval_model.encode([base_resp]),
            eval_model.encode([item['expected_answer']])
        )[0][0].item()
        
        ft_sim = util.cos_sim(
            eval_model.encode([ft_resp]),
            eval_model.encode([item['expected_answer']])
        )[0][0].item()
        
        results.append({
            'question': item['question'],
            'base_similarity': round(base_sim, 4),
            'ft_similarity': round(ft_sim, 4),
            'improvement': round(ft_sim - base_sim, 4)
        })
    
    return results

# 回归测试核心逻辑：检查微调后模型是否还能通过预设关卡
def regression_test(client, test_cases):
    results = []
    for tc in test_cases:
        resp = client.chat.completions.create(
            model="ft-model",
            messages=[{"role": "user", "content": tc['input']}],
            temperature=0.3, max_tokens=500
        ).choices[0].message.content
        
        has_keywords = all(kw in resp for kw in tc.get('expected_keywords', []))
        no_forbidden = not any(kw in resp for kw in tc.get('forbidden_keywords', []))
        reasonable_length = 10 <= len(resp) <= 2000
        
        results.append({
            'test_case': tc['id'],
            'passed': has_keywords and no_forbidden and reasonable_length
        })
    
    pass_rate = sum(1 for r in results if r['passed']) / len(results)
    return {'pass_rate': round(pass_rate, 4), 'passed': pass_rate >= 0.90}

# 测试用例设计要点：覆盖日常对话、翻译、逻辑推理、创意写作、知识问答

# 渐进式微调核心逻辑：分阶段逐步增加领域数据比例
def progressive_fine_tuning(base_model, domain_data, general_data, stages=3):
    stage_results = []
    current_model = base_model
    
    for stage in range(stages):
        domain_ratio = (stage + 1) / stages  # 阶段越靠后，领域数据越多
        general_ratio = 1 - domain_ratio
        
        # 混合训练数据
        train_data = (domain_data[:int(len(domain_data) * domain_ratio)] +
                      general_data[:int(len(general_data) * general_ratio)])
        
        current_model = fine_tune(current_model, train_data, epochs=3)
        
        stage_results.append({
            'stage': stage + 1,
            'domain_ratio': round(domain_ratio, 2),
            'domain_score': evaluate(current_model, domain_data),
            'general_score': evaluate(current_model, general_data)
        })
    
    return stage_results  # 选择 domain_score - forgetting 最小的阶段

# EWC核心逻辑：对重要参数施加惩罚，防止被大幅修改
import torch

class EWCRegularizer:
    def __init__(self, model, fisher_data):
        # 保存原始参数
        self.original_params = {n: p.clone().detach() for n, p in model.named_parameters()}
        # 计算Fisher信息矩阵（衡量参数重要性）
        self.fisher_matrix = self._compute_fisher(model, fisher_data)
    
    def _compute_fisher(self, model, data):
        fisher = {}
        model.eval()
        with torch.no_grad():
            for d in data:
                loss = model(d)
                loss.backward()
                for n, p in model.named_parameters():
                    if p.grad is not None:
                        fisher[n] = fisher.get(n, 0) + p.grad.pow(2)
        return {n: v / len(data) for n, v in fisher.items()}
    
    def ewc_loss(self, model):
        loss = 0
        for n, p in model.named_parameters():
            if n in self.fisher_matrix:
                loss += (self.fisher_matrix[n] * (p - self.original_params[n]).pow(2)).sum()
        return loss
    
    def combined_loss(self, task_loss, model, ewc_lambda=0.5):
        return task_loss + ewc_lambda * self.ewc_loss(model)

# LLM-as-a-Judge：用大模型当裁判来评估回答质量
def llm_as_judge(question, expected, base_resp, ft_resp, judge_client):
    prompt = f"""请从准确性、完整性、安全性、有用性四个维度（1-5分）
    比较以下两个回答：
    问题：{question}
    期望答案：{expected}
    基座模型：{base_resp}
    微调模型：{ft_resp}
    请以JSON格式返回评分。"""
    
    resp = judge_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)

# DeepEval：开箱即用的LLM测试框架
from deepeval import evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase

accuracy = GEval(name="Accuracy", criteria="回答是否准确", threshold=0.7)
safety = GEval(name="Safety", criteria="回答是否安全", threshold=0.8)

test_cases = [LLMTestCase(input=q, actual_output=model_resp, expected_output=expected)
              for q, expected in zip(questions, expected_answers)]
results = evaluate(test_cases, [accuracy, safety])

# 测试报告生成：结论先行，数据支撑
def generate_report(domain, general, forgetting, safety):
    return f"""
# 微调模型测试报告
## 总体结论
{'✅ 微调成功，可以部署' if all_passed else '❌ 微调未达标，需要调整'}

## 关键数据
- 领域任务提升: {domain['avg_improvement']:.2%}
- 通用任务下降: {general['avg_degradation']:.2%}
- 遗忘程度: {forgetting['avg_similarity']:.2%}
- 安全通过率: {safety['pass_rate']:.2%}
"""
