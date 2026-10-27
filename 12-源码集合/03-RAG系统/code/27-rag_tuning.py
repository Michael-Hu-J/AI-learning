class TestDataset:
    """测试数据集"""
    def __init__(self):
        self.questions = []
        self.relevant_docs = []
        self.expected_answers = []

    def add_question(self, question, relevant_doc_ids, expected_answer=None):
        self.questions.append(question)
        self.relevant_docs.append(relevant_doc_ids)
        self.expected_answers.append(expected_answer)

    def get_recall_at_k(self, retrieved_docs, k=5):
        hit_count = 0
        for q_rel, q_ret in zip(self.relevant_docs, retrieved_docs):
            if len(set(q_ret[:k]) & set(q_rel)) > 0:
                hit_count += 1
        return hit_count / len(self.questions)

    def get_precision_at_k(self, retrieved_docs, k=5):
        prec_sum = 0
        for q_rel, q_ret in zip(self.relevant_docs, retrieved_docs):
            prec = len(set(q_ret[:k]) & set(q_rel)) / k
            prec_sum += prec
        return prec_sum / len(self.questions)

def ab_test(old_params, new_params, test_dataset, run_search_fn):
    old_results = run_search_fn(test_dataset.questions, **old_params)
    old_recall = test_dataset.get_recall_at_k(old_results, k=old_params.get('top_k', 5))
    new_results = run_search_fn(test_dataset.questions, **new_params)
    new_recall = test_dataset.get_recall_at_k(new_results, k=new_params.get('top_k', 5))
    print(f"旧Recall: {old_recall:.4f} → 新Recall: {new_recall:.4f} (变化: {new_recall-old_recall:+.4f})")
    return new_recall > old_recall

def tune_chunk_size(questions, relevant_docs, documents, run_search_fn):
    best_recall = 0
    best_size = 500
    for size in [200, 500, 1000, 2000]:
        overlap = int(size * 0.2)
        chunks = split_documents(documents, chunk_size=size, chunk_overlap=overlap)
        retrieved = [run_search_fn([q], top_k=5, threshold=0.7)[0] for q in questions]
        recall = calculate_recall(relevant_docs, retrieved, k=5)
        print(f"chunk_size={size}, overlap={overlap}: Recall@5={recall:.4f}")
        if recall > best_recall:
            best_recall = recall
            best_size = size
    print(f"最佳chunk_size: {best_size}, Recall@5={best_recall:.4f}")
    return best_size

def tune_with_cost(questions, relevant_docs, run_search_fn):
    configs = [
        {'top_k': 3, 'threshold': 0.9},
        {'top_k': 5, 'threshold': 0.7},
        {'top_k': 10, 'threshold': 0.5},
    ]
    for cfg in configs:
        retrieved = [run_search_fn([q], **cfg)[0] for q in questions]
        recall = calculate_recall(relevant_docs, retrieved, k=cfg['top_k'])
        tokens = sum(r.get('tokens', 0) for r in retrieved) / len(questions)
        efficiency = recall / (tokens / 1000)
        print(f"top_k={cfg['top_k']}: Recall={recall:.4f}, Tokens={tokens:.0f}, 性价比={efficiency:.4f}")

from itertools import product

def tune_rag_parameters(documents, test_queries, evaluate_rag_fn):
    """网格搜索——仅建议在 slice 阶段固定后再扫 retrieval/generation 子集"""
    param_grid = {
        "chunk_size": [256, 512, 1024],
        "chunk_overlap": [0, 50, 100],
        "top_k": [3, 5, 10],
        "temperature": [0.1, 0.3, 0.7],
    }
    best_params, best_score = {}, 0
    for values in product(*param_grid.values()):
        params = dict(zip(param_grid.keys(), values))
        score = evaluate_rag_fn(documents, test_queries, params)
        print(f"Params {params}: score={score:.3f}")
        if score > best_score:
            best_score, best_params = score, params
    print(f"\nBest: {best_params} with score={best_score:.3f}")
    return best_params

def automated_param_tuning(build_rag_fn, evaluate_rag_system_fn, test_dataset):
    """
    自动化调参：在有限组合中选最优（非全网格）
    build_rag_fn(params) -> rag; evaluate_rag_system_fn(rag, test_dataset) -> score
    """
    param_combos = [
        {"chunk_size": 512, "top_k": 5, "temperature": 0.3},
        {"chunk_size": 512, "top_k": 10, "temperature": 0.3},
        {"chunk_size": 1024, "top_k": 5, "temperature": 0.1},
        {"chunk_size": 1024, "top_k": 10, "temperature": 0.7},
    ]
    best = {"score": 0, "params": None}
    for params in param_combos:
        rag = build_rag_fn(params)
        score = evaluate_rag_system_fn(rag, test_dataset)
        print(f"Params {params}: score={score}")
        if score > best["score"]:
            best = {"score": score, "params": params}
    return best
