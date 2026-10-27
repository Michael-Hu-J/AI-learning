class IntentClassifierTester:
    """意图识别测试器"""
    
    # 标准问法和口语化问法的映射
    INTENT_MAPPING = {
        'account_query': {
            'standard': ['我的账户余额是多少', '查询账户余额', '账户里还有多少钱'],
            'colloquial': ['我卡里还有多少钱', '看看我账户', '还有多少余额', '钱够不够'],
            'ambiguous': ['我的钱', '余额', '还有多少'],
            'dialect': ['查下户口余额', '户口里几多钱'],  # 粤语
            'typo': ['我的账户佘额是多少', '查寻账户余额'],  # 错别字
        },
        'transfer': {
            'standard': ['怎么转账', '转账流程', '如何转账'],
            'colloquial': ['钱怎么转出去', '给别人转点钱', '转一笔账', '打钱'],
            'ambiguous': ['转账', '转钱', '打款'],
            'dialect': ['转数快', '畀钱落去'],  # 粤语
            'typo': ['我要转帐', '转帐流程'],  # 错别字
        },
        # ... 其他意图类似
    }
    
    def test_intent_classification(self, classifier) -> dict:
        """测试意图识别，覆盖5种问法类型"""
        results = []
        
        for intent, questions in self.INTENT_MAPPING.items():
            for qtype in ['standard', 'colloquial', 'ambiguous', 'dialect', 'typo']:
                for q in questions.get(qtype, []):
                    predicted = classifier.classify(q)
                    passed = predicted == intent if qtype != 'ambiguous' else predicted in [intent, 'unknown']
                    results.append({
                        'question': q,
                        'expected_intent': intent,
                        'predicted_intent': predicted,
                        'question_type': qtype,
                        'passed': passed
                    })
        
        # 按问法类型统计
        stats = {}
        for qtype in ['standard', 'colloquial', 'ambiguous', 'dialect', 'typo']:
            type_results = [r for r in results if r['question_type'] == qtype]
            if type_results:
                stats[qtype] = {
                    'passed': sum(1 for r in type_results if r['passed']),
                    'total': len(type_results),
                    'rate': sum(1 for r in type_results if r['passed']) / len(type_results)
                }
        
        return {
            'overall_rate': sum(1 for r in results if r['passed']) / len(results),
            'by_type': stats,
            'details': results
        }

def evaluate_knowledge_retrieval(retriever, test_cases: list) -> dict:
    """评估知识库检索质量"""
    results = []
    
    for tc in test_cases:
        # tc包含：用户问题、正确答案所在的文档ID
        retrieved = retriever.retrieve(tc['question'], top_k=3)
        retrieved_ids = [doc['id'] for doc in retrieved]
        
        # Recall@3: 正确答案是否在top-3中
        recall_at_3 = tc['answer_doc_id'] in retrieved_ids
        
        # Precision@3: top-3中有多少是相关的
        precision_at_3 = sum(1 for doc_id in retrieved_ids 
                           if doc_id in tc['relevant_doc_ids']) / 3
        
        results.append({
            'question': tc['question'],
            'recall_at_3': recall_at_3,
            'precision_at_3': precision_at_3,
            'retrieved_ids': retrieved_ids
        })
    
    return {
        'recall_at_3_rate': sum(1 for r in results if r['recall_at_3']) / len(results),
        'avg_precision_at_3': sum(r['precision_at_3'] for r in results) / len(results),
        'details': results
    }

def evaluate_response_quality(response: str, question: str, expected_answer: str) -> dict:
    """四维评估回答质量"""
    from sentence_transformers import SentenceTransformer, util
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # 准确性：回答与标准答案的语义相似度
    emb_response = model.encode([response])
    emb_expected = model.encode([expected_answer])
    accuracy = util.cos_sim(emb_response, emb_expected)[0][0].item() * 5
    
    # 相关性：回答与问题的语义相似度
    emb_question = model.encode([question])
    relevance = util.cos_sim(emb_response, emb_question)[0][0].item() * 5
    
    # 完整性：ROUGE-L召回率
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(expected_answer, response)
    completeness = scores['rougeL'].recall * 5
    
    # 自然度：检查机械用语
    mechanical_phrases = ['您好，我是智能客服', '请问有什么可以帮您', '感谢您的反馈']
    mechanical_count = sum(1 for p in mechanical_phrases if p in response)
    naturalness = max(2.0, 5.0 - mechanical_count * 1.0)
    
    return {
        'accuracy': round(accuracy, 2),
        'relevance': round(relevance, 2),
        'completeness': round(completeness, 2),
        'naturalness': round(naturalness, 2),
        'avg': round((accuracy + relevance + completeness + naturalness) / 4, 2)
    }

def run_e2e_conversation_test(scenarios: list) -> dict:
    """端到端多轮对话测试"""
    results = []
    
    for scenario in scenarios:
        context = []
        turn_results = []
        
        for turn in scenario['turns']:
            user_input = turn['input']
            
            # 调用完整的客服系统链路
            response = customer_service_pipeline(
                user_input, 
                context=context
            )
            
            # 检查意图识别
            intent_ok = response['intent'] == turn['expected_intent']
            
            # 检查回答内容
            content_ok = all(kw in response['text'] 
                           for kw in turn.get('expected_keywords', []))
            
            # 检查是否应该转人工
            escalation_ok = (response['escalated'] == turn.get('should_escalate', False))
            
            turn_results.append({
                'input': user_input,
                'intent_ok': intent_ok,
                'content_ok': content_ok,
                'escalation_ok': escalation_ok,
                'response': response['text']
            })
            
            context.append({'role': 'user', 'content': user_input})
            context.append({'role': 'assistant', 'content': response['text']})
        
        results.append({
            'scenario': scenario['name'],
            'turns': turn_results,
            'all_passed': all(
                t['intent_ok'] and t['content_ok'] and t['escalation_ok'] 
                for t in turn_results
            )
        })
    
    return {
        'total_scenarios': len(results),
        'passed': sum(1 for r in results if r['all_passed']),
        'pass_rate': sum(1 for r in results if r['all_passed']) / len(results),
        'details': results
    }

def detect_hallucination(response: str, retrieved_docs: list) -> dict:
    """检测LLM回答中的幻觉——回答内容是否在检索到的文档中有依据"""
    from sentence_transformers import SentenceTransformer, util
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # 将回答拆分成句子
    sentences = split_sentences(response)
    
    hallucinated_sentences = []
    
    for sentence in sentences:
        # 检查每个句子是否在检索文档中有语义支撑
        doc_embeddings = model.encode([doc['content'] for doc in retrieved_docs])
        sentence_embedding = model.encode([sentence])
        
        similarities = util.cos_sim(sentence_embedding, doc_embeddings)[0]
        max_similarity = similarities.max().item()
        
        # 如果与所有文档的最大相似度低于阈值，可能是幻觉
        if max_similarity < 0.6:
            hallucinated_sentences.append({
                'sentence': sentence,
                'max_similarity': round(max_similarity, 3)
            })
    
    return {
        'total_sentences': len(sentences),
        'hallucinated_count': len(hallucinated_sentences),
        'hallucination_rate': len(hallucinated_sentences) / len(sentences) if sentences else 0,
        'hallucinated_sentences': hallucinated_sentences
    }
