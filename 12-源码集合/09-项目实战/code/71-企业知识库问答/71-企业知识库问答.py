class PermissionFilter:
    """权限过滤器"""
    
    def __init__(self, vector_db):
        self.vector_db = vector_db
    
    def get_allowed_docs(self, user_role: str, user_dept: str) -> list:
        """获取用户有权限查看的文档"""
        allowed = []
        
        # 公开文档
        public_docs = self.vector_db.filter({"access_level": "public"})
        allowed.extend(public_docs)
        
        # 部门文档
        if user_dept:
            dept_docs = self.vector_db.filter({
                "access_level": "department",
                "department": user_dept
            })
            allowed.extend(dept_docs)
        
        # 管理层文档
        if user_role in ["manager", "director", "ceo"]:
            mgmt_docs = self.vector_db.filter({"access_level": "management"})
            allowed.extend(mgmt_docs)
        
        # 机密文档（需要额外检查）
        if user_role == "ceo":
            confidential_docs = self.vector_db.filter({"access_level": "confidential"})
            allowed.extend(confidential_docs)
        
        return allowed
    
    def retrieve_with_permission(self, query: str, user_role: str, user_dept: str, top_k: int = 5) -> list:
        """带权限过滤的检索"""
        allowed_docs = self.get_allowed_docs(user_role, user_dept)
        results = self.vector_db.search(query, docs=allowed_docs, top_k=top_k)
        return results


def test_permission_isolation():
    """权限隔离测试"""
    filter = PermissionFilter(vector_db)
    
    # 测试1：普通员工不能看到管理层文档
    results = filter.retrieve_with_permission(
        query="信贷审批内部标准",
        user_role="employee",
        user_dept="sales",
        top_k=5
    )
    assert len(results) == 0, "普通员工不应该看到管理层文档"
    
    # 测试2：管理层可以看到管理层文档
    results = filter.retrieve_with_permission(
        query="信贷审批内部标准",
        user_role="manager",
        user_dept="credit",
        top_k=5
    )
    assert len(results) > 0, "管理层应该看到管理层文档"
    
    # 测试3：A部门员工不能看到B部门文档
    results = filter.retrieve_with_permission(
        query="HR部门内部政策",
        user_role="manager",
        user_dept="sales",
        top_k=5
    )
    assert len(results) == 0, "销售部不应该看到HR部门文档"
    
    print("✅ 权限隔离测试通过")

def test_document_parsing(test_files: list) -> dict:
    """文档解析测试"""
    results = []
    
    for tf in test_files:
        parsed_text = parse_document(tf.path)
        
        original_chars = len(tf.original_text)
        parsed_chars = len(parsed_text)
        retention_rate = parsed_chars / original_chars if original_chars > 0 else 0
        
        key_info_retained = all(kw in parsed_text for kw in tf.key_info)
        
        results.append({
            'file': tf.path,
            'format': tf.format,
            'original_chars': original_chars,
            'parsed_chars': parsed_chars,
            'retention_rate': retention_rate,
            'key_info_retained': key_info_retained,
            'passed': retention_rate >= 0.90 and key_info_retained
        })
    
    pass_rate = sum(1 for r in results if r['passed']) / len(results)
    
    return {
        'total': len(results),
        'passed': sum(1 for r in results if r['passed']),
        'pass_rate': pass_rate,
        'details': results
    }

def test_knowledge_freshness(knowledge_base: list, max_age_days: int = 180) -> dict:
    """知识时效性测试"""
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    expired_docs = []
    
    for doc in knowledge_base:
        updated_at = datetime.fromisoformat(doc['updated_at'])
        if updated_at < cutoff:
            expired_docs.append({
                'doc_id': doc['id'],
                'title': doc['title'],
                'updated_at': doc['updated_at'],
                'days_since_update': (datetime.now() - updated_at).days
            })
    
    return {
        'total_docs': len(knowledge_base),
        'expired_docs': len(expired_docs),
        'expired_rate': len(expired_docs) / len(knowledge_base) if knowledge_base else 0,
        'details': expired_docs
    }

def evaluate_answer_accuracy(questions: list, expected_answers: list) -> dict:
    """答案准确性评估"""
    results = []
    
    for q, expected in zip(questions, expected_answers):
        actual = kb_system.answer(q)  # 调用知识库系统获取答案
        
        # 事实准确性：关键事实是否一致
        factual_match = check_factual_accuracy(actual, expected)
        
        # 完整性：是否覆盖了所有关键点
        completeness = check_completeness(actual, expected)
        
        # 合规性：是否包含违规内容
        compliance = check_compliance(actual)
        
        results.append({
            'question': q,
            'expected': expected,
            'actual': actual,
            'factual_match': factual_match,
            'completeness': completeness,
            'compliance': compliance,
            'overall_pass': factual_match and completeness and compliance
        })
    
    pass_rate = sum(1 for r in results if r['overall_pass']) / len(results)
    
    return {
        'total': len(results),
        'passed': sum(1 for r in results if r['overall_pass']),
        'pass_rate': pass_rate,
        'details': results
    }

def run_full_knowledge_base_test():
    """运行完整的知识库测试套件"""
    # 1. 文档解析测试
    print("=== 文档解析测试 ===")
    parsing_results = test_document_parsing(load_test_files())
    print(f"解析通过率: {parsing_results['pass_rate']:.1%}")
    
    # 2. 权限隔离测试
    print("\n=== 权限隔离测试 ===")
    test_permission_isolation()
    
    # 3. 知识时效性测试
    print("\n=== 知识时效性测试 ===")
    freshness_results = test_knowledge_freshness(load_knowledge_base())
    print(f"过期文档数: {freshness_results['expired_docs']}/{freshness_results['total_docs']}")
    
    # 4. 答案准确性测试
    print("\n=== 答案准确性测试 ===")
    accuracy_results = evaluate_answer_accuracy(load_questions(), load_expected_answers())
    print(f"答案准确率: {accuracy_results['pass_rate']:.1%}")
    
    # 5. 生成测试报告
    generate_test_report({
        'parsing': parsing_results,
        'permission': 'passed',
        'freshness': freshness_results,
        'accuracy': accuracy_results
    })
    
    print("\n✅ 全部测试完成")

# 修复前：新旧文档同时存在
results = vector_db.search(query, top_k=5)  # 可能检索到旧文档

# 修复后：只检索active文档
results = vector_db.search(query, top_k=5, filter={"status": "active"})

# 修复前：所有文档都是public
vector_db.insert(content)  # 没有设置权限标签

# 修复后：上传时设置权限标签
vector_db.insert(content, metadata={
    "department": "credit",
    "access_level": "department",
    "role": "manager"
})

import chardet

def detect_encoding(file_path: str) -> str:
    """检测文件编码"""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def load_text_file(file_path: str) -> str:
    """智能加载文本文件，自动检测编码"""
    encoding = detect_encoding(file_path)
    with open(file_path, 'r', encoding=encoding or 'utf-8') as f:
        return f.read()
