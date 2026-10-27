def my_llm(prompt: str) -> str:
    # 替换为 openai / 本地模型调用
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

bot = QABot(kb, llm_call_func=my_llm)

from src.qa_retriever import KnowledgeDocument

kb.add_document(KnowledgeDocument(
    doc_id="DOC010", title="课程价格",
    content="每门课程价格在199-599元之间。",
    category="价格", tags=["价格", "费用"],
))

class IntentClassifierTester:
    """意图分类测试器"""
    
    INTENT_MAPPING = {
        'company_policy': {
            'standard': ['差旅费报销标准是多少', '请假流程是什么', '加班补贴政策'],
            'colloquial': ['出差能报多少钱', '怎么请假', '加班给多少钱'],
            'ambiguous': ['报销', '请假', '加班'],
        },
        'it_support': {
            'standard': ['怎么重置密码', '系统权限怎么申请', '网络连不上'],
            'colloquial': ['密码忘了怎么办', '怎么开通权限', '上不了网'],
            'ambiguous': ['密码', '权限', '网络'],
        },
        'hr': {
            'standard': ['年假有多少天', '社保怎么交', '公积金比例'],
            'colloquial': ['年假几天', '社保交多少', '公积金比例多少'],
            'ambiguous': ['年假', '社保', '公积金'],
        },
        'chat': {
            'standard': ['今天天气怎么样', '中午吃什么', '有什么好电影'],
            'colloquial': ['天气咋样', '吃啥', '推荐个电影'],
            'ambiguous': ['天气', '吃饭', '电影'],
        },
    }
    
    def test_intent_classification(self, classifier) -> dict:
        """测试意图分类"""
        results = []
        for intent, questions in self.INTENT_MAPPING.items():
            for q in questions['standard']:
                predicted = classifier.classify(q)
                results.append({
                    'question': q,
                    'expected_intent': intent,
                    'predicted_intent': predicted,
                    'question_type': 'standard',
                    'passed': predicted == intent
                })
            # 口语化和模糊问法的测试逻辑类似...
        
        return self._generate_report(results)

def test_retrieval_recall(retriever, test_set: list, k=3) -> dict:
    """测试知识库检索召回率"""
    results = []
    for case in test_set:
        query = case['question']
        expected_doc_ids = case['expected_doc_ids']
        retrieved = retriever.search(query, top_k=k)
        retrieved_doc_ids = [doc['id'] for doc in retrieved]
        
        # 计算召回率
        recall = len(set(expected_doc_ids) & set(retrieved_doc_ids)) / len(expected_doc_ids)
        results.append({
            'question': query,
            'expected': expected_doc_ids,
            'retrieved': retrieved_doc_ids,
            'recall': recall,
            'passed': recall > 0
        })
    
    avg_recall = sum(r['recall'] for r in results) / len(results)
    return {
        'k': k,
        'total': len(results),
        'avg_recall': avg_recall,
        'passed_cases': sum(1 for r in results if r['passed']),
        'details': results
    }

def evaluate_answer_quality(llm_judge, question: str, 
                            context: str, answer: str) -> dict:
    """用LLM评估答案质量"""
    prompt = f"""
    请评估以下回答的质量。
    
    问题：{question}
    参考文档：{context}
    回答：{answer}
    
    从以下维度评分（1-5分）：
    1. 准确性：回答是否与参考文档一致，有无幻觉
    2. 完整性：回答是否覆盖了问题的所有要点
    3. 相关性：回答是否与问题相关
    4. 简洁性：回答是否简洁明了
    
    请以JSON格式返回评分结果。
    """
    result = llm_judge.generate(prompt)
    return parse_json(result)

def test_refusal_strategy(test_cases: list) -> dict:
    """拒答策略测试"""
    results = []
    for tc in test_cases:
        response = call_qa_system(tc['input'])
        should_refuse = tc['should_refuse']
        actually_refused = is_refusal_response(response)
        passed = (should_refuse == actually_refused)
        results.append({
            'input': tc['input'],
            'should_refuse': should_refuse,
            'actually_refused': actually_refused,
            'passed': passed
        })
    
    return {
        'total': len(results),
        'pass_rate': sum(1 for r in results if r['passed']) / len(results),
        'false_positive': sum(1 for r in results if not r['passed'] and r['actually_refused']),
        'false_negative': sum(1 for r in results if not r['passed'] and not r['actually_refused']),
        'details': results
    }

def test_multi_turn(scenarios: list) -> dict:
    """多轮对话测试"""
    results = []
    for scenario in scenarios:
        context = []
        all_passed = True
        for turn in scenario['turns']:
            response = call_qa_system(turn['input'], context=context)
            passed = all(kw in response for kw in turn.get('expected_contains', []))
            all_passed = all_passed and passed
            context.append({'role': 'user', 'content': turn['input']})
            context.append({'role': 'assistant', 'content': response})
        results.append({'scenario': scenario['name'], 'passed': all_passed})
    
    return {'total': len(results), 'pass_rate': sum(1 for r in results if r['passed']) / len(results)}
