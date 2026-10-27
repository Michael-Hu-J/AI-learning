import re
from dataclasses import dataclass
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer, util

@dataclass
class ClaimVerification:
    claim: str
    verified: bool
    evidence: str
    confidence: float

def extract_claims(text: str) -> List[str]:
    """
    从文本中提取事实声明
    
    将回答拆分为独立的事实声明，每个声明是一个完整的陈述。
    """
    sentences = re.split(r'[。；！]', text)
    claims = []
    
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        if s.endswith('?') or s.endswith('？'):
            continue
        claims.append(s)
    
    return claims

def verify_claim_against_knowledge_base(
    claim: str, 
    knowledge_base: List[str],
    threshold: float = 0.75
) -> Tuple[bool, str, float]:
    """
    在知识库中验证事实声明
    """
    eval_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    claim_emb = eval_model.encode([claim])
    best_similarity = 0
    best_doc = ""
    
    for doc in knowledge_base:
        doc_sentences = re.split(r'[。；！]', doc)
        for sentence in doc_sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
            doc_emb = eval_model.encode([sentence])
            similarity = util.cos_sim(claim_emb, doc_emb)[0][0].item()
            if similarity > best_similarity:
                best_similarity = similarity
                best_doc = sentence
    
    return best_similarity >= threshold, best_doc, best_similarity

def fact_check(response: str, knowledge_base: List[str]) -> Dict:
    """
    事实核查——检测回答中是否存在幻觉
    """
    claims = extract_claims(response)
    results = []
    
    for claim in claims:
        supported, evidence, confidence = verify_claim_against_knowledge_base(
            claim, knowledge_base
        )
        results.append({
            'claim': claim,
            'supported': supported,
            'evidence': evidence[:200] if evidence else None,
            'confidence': round(confidence, 4)
        })
    
    hallucination_rate = (sum(1 for r in results if not r['supported']) / 
                         len(results)) if results else 0
    
    return {
        'total_claims': len(results),
        'supported': sum(1 for r in results if r['supported']),
        'unsupported': sum(1 for r in results if not r['supported']),
        'hallucination_rate': round(hallucination_rate, 4),
        'hallucination_free': hallucination_rate < 0.10,
        'details': results
    }

def multi_model_cross_validation(
    question: str,
    models: List[str],
    knowledge_base: List[str] = None
) -> Dict:
    """
    多模型交叉验证
    用多个模型回答同一个问题，对比答案的一致性。
    """
    responses = {}
    
    for model in models:
        if knowledge_base:
            responses[model] = generate_with_rag(question, knowledge_base, model)
        else:
            responses[model] = call_llm(question, model)
    
    eval_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    similarities = []
    model_list = list(responses.keys())
    
    for i in range(len(model_list)):
        for j in range(i + 1, len(model_list)):
            emb1 = eval_model.encode([responses[model_list[i]]])
            emb2 = eval_model.encode([responses[model_list[j]]])
            sim = util.cos_sim(emb1, emb2)[0][0].item()
            similarities.append(sim)
    
    avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
    
    high_risk = avg_similarity < 0.60
    medium_risk = 0.60 <= avg_similarity < 0.80
    
    return {
        'question': question,
        'responses': {m: r[:200] for m, r in responses.items()},
        'avg_similarity': round(avg_similarity, 4),
        'risk_level': 'high' if high_risk else ('medium' if medium_risk else 'low'),
        'hallucination_risk': high_risk or medium_risk,
        'passed': not high_risk
    }

def generate_with_rag(
    question: str, 
    knowledge_base: List[str],
    max_hallucination_risk: float = 0.2,
    model: str = "qwen-turbo"
) -> str:
    """
    带幻觉控制的RAG生成
    """
    # 1. 检索相关文档
    docs = retrieve(question, knowledge_base, top_k=5)
    
    # 2. 检查检索质量
    if not docs or len(docs) == 0:
        return "抱歉，知识库中没有找到相关信息。"
    
    # 3. 构建Prompt（强制基于检索到的文档）
    prompt = f"""你是一个专业的问答助手。请基于以下文档回答问题。

重要规则：
1. 只能基于以下文档回答问题，不要使用你的内部知识
2. 如果文档中没有相关信息，请说"知识库中没有找到相关信息"
3. 不要编造任何信息，包括法律条文编号、数据、人名等
4. 如果文档信息不完整，请明确说明

文档：
{chr(10).join([f"[{i+1}] {doc}" for i, doc in enumerate(docs)])}

问题：{question}

回答："""
    
    # 4. 生成回答
    response = call_llm(prompt, model)
    
    # 5. 检查回答是否基于文档
    hallucination_check = fact_check(response, docs)
    
    if hallucination_check['hallucination_rate'] > max_hallucination_risk:
        return "抱歉，我无法基于现有知识库回答这个问题。"
    
    return response

class HallucinationTestSuite:
    """幻觉检测自动化测试框架"""
    
    def __init__(self, model_client, knowledge_base):
        self.client = model_client
        self.kb = knowledge_base
        self.results = []
    
    def add_test_case(self, question: str, expected_claims: List[str]):
        """添加测试用例"""
        self.results.append({
            'question': question,
            'expected_claims': expected_claims,
            'actual_claims': [],
            'hallucination_claims': [],
            'passed': None
        })
    
    def run_test(self, tc_index: int) -> Dict:
        """运行单个测试用例"""
        tc = self.results[tc_index]
        response = generate_with_rag(tc['question'], self.kb)
        claims = extract_claims(response)
        tc['actual_claims'] = claims
        
        hallucination_claims = []
        for claim in claims:
            supported, evidence, confidence = verify_claim_against_knowledge_base(
                claim, self.kb
            )
            if not supported:
                hallucination_claims.append({
                    'claim': claim,
                    'evidence': evidence,
                    'confidence': confidence
                })
        
        tc['hallucination_claims'] = hallucination_claims
        tc['passed'] = len(hallucination_claims) == 0
        
        return {
            'question': tc['question'],
            'total_claims': len(claims),
            'hallucination_claims': len(hallucination_claims),
            'passed': tc['passed']
        }
    
    def run_all(self) -> Dict:
        """运行所有测试用例"""
        for i in range(len(self.results)):
            self.run_test(i)
        
        pass_rate = sum(1 for tc in self.results if tc['passed']) / len(self.results)
        
        return {
            'total': len(self.results),
            'passed': sum(1 for tc in self.results if tc['passed']),
            'failed': sum(1 for tc in self.results if not tc['passed']),
            'pass_rate': round(pass_rate, 4),
            'passed': pass_rate >= 0.90,
            'details': self.results
        }

from langchain.evaluation import load_evaluator
from langchain.chat_models import ChatOpenAI

# 加载幻觉检测评估器
evaluator = load_evaluator("embedding_distance")

# 检测回答是否与参考文档一致
def detect_hallucination_langchain(question, answer, reference_doc):
    """
    使用LangChain检测幻觉
    """
    result = evaluator.evaluate_strings(
        input=question,
        prediction=answer,
        reference=reference_doc,
    )
    return {
        'score': result['score'],
        'is_hallucination': result['score'] < 0.7,
        'reasoning': result.get('reasoning', '')
    }

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# 构建评估数据集
dataset = [
    {
        'question': '离婚冷静期是多久？',
        'answer': '根据《民法典》第1077条，离婚冷静期为30天。',
        'contexts': ['《民法典》第一千零七十七条规定：...'],
        'ground_truth': '离婚冷静期为30天。'
    },
    # ... 更多测试用例
]

# 运行评估
results = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision]
)

print(results)

from deepeval import evaluate
from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase

# 定义幻觉检测指标
metric = HallucinationMetric(
    threshold=0.7,
    include_reason=True
)

# 创建测试用例
test_case = LLMTestCase(
    input="离婚冷静期是多久？",
    actual_output="根据《民法典》第1077条，离婚冷静期为30天。",
    context=["《民法典》第一千零七十七条规定：..."]
)

# 运行检测
result = metric.measure(test_case)
print(f"幻觉得分: {metric.score}")
print(f"检测原因: {metric.reason}")

class HallucinationDetectionPipeline:
    """
    完整的幻觉检测Pipeline
    组合多种检测方法，逐级过滤
    """
    
    def __init__(self):
        self.semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.thresholds = {
            'semantic_similarity': 0.75,
            'keyword_match': 0.80,
            'key_entity_match': 0.90
        }
    
    def check_semantic_similarity(self, claim, reference):
        """语义相似度检查"""
        emb1 = self.semantic_model.encode([claim])
        emb2 = self.semantic_model.encode([reference])
        sim = util.cos_sim(emb1, emb2)[0][0].item()
        return sim >= self.thresholds['semantic_similarity'], sim
    
    def check_keyword_match(self, claim, reference):
        """关键词匹配检查"""
        claim_words = set(jieba.cut(claim))
        ref_words = set(jieba.cut(reference))
        overlap = claim_words & ref_words
        match_rate = len(overlap) / len(claim_words) if claim_words else 0
        return match_rate >= self.thresholds['keyword_match'], match_rate
    
    def check_key_entities(self, claim, reference):
        """关键实体匹配检查"""
        claim_entities = extract_entities(claim)  # 提取数字、名称、条文编号等
        ref_entities = extract_entities(reference)
        
        matched = 0
        for entity in claim_entities:
            if entity in ref_entities:
                matched += 1
        
        match_rate = matched / len(claim_entities) if claim_entities else 1.0
        return match_rate >= self.thresholds['key_entity_match'], match_rate
    
    def detect(self, response, knowledge_base):
        """
        完整的幻觉检测流程
        """
        claims = extract_claims(response)
        hallucinations = []
        
        for claim in claims:
            # 第一步：语义相似度检查
            best_sim = 0
            best_ref = ""
            for doc in knowledge_base:
                sim, _ = self.check_semantic_similarity(claim, doc)
                if sim > best_sim:
                    best_sim = sim
                    best_ref = doc
            
            if best_sim < self.thresholds['semantic_similarity']:
                hallucinations.append({
                    'claim': claim,
                    'type': 'semantic_mismatch',
                    'similarity': best_sim
                })
                continue
            
            # 第二步：关键词匹配检查
            kw_match, kw_rate = self.check_keyword_match(claim, best_ref)
            if not kw_match:
                hallucinations.append({
                    'claim': claim,
                    'type': 'keyword_mismatch',
                    'match_rate': kw_rate
                })
                continue
            
            # 第三步：关键实体匹配检查
            ent_match, ent_rate = self.check_key_entities(claim, best_ref)
            if not ent_match:
                hallucinations.append({
                    'claim': claim,
                    'type': 'entity_mismatch',
                    'match_rate': ent_rate
                })
                continue
        
        return {
            'total_claims': len(claims),
            'hallucinations': len(hallucinations),
            'hallucination_rate': len(hallucinations) / len(claims) if claims else 0,
            'details': hallucinations
        }
