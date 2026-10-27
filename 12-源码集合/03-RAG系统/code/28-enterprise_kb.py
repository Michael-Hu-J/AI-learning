from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma

# 1. 文档加载（生产用 pdfplumber + OCR 降级，见 20-文档加载与解析.md）
loader = PyPDFLoader("产品文档.pdf")
documents = loader.load()

# 2. 切片 + 元数据（权限/版本/部门）
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
chunks = splitter.split_documents(documents)
for chunk in chunks:
    chunk.metadata.update({
        "department": "产品部",
        "category": "产品手册",
        "version": "v2.1",
        "status": "active",
    })

# 3. 向量化存储
embeddings = DashScopeEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)

# 4. 带权限的检索生成
def answer_question(question, user_department="产品部"):
    docs = vectorstore.similarity_search(
        question,
        k=3,
        filter={"department": user_department, "status": "active"},
    )
    if not docs:
        return f"未找到 {user_department} 相关且有效的文档"
    context = "\n".join(doc.page_content for doc in docs)
    prompt = f"""你是公司内部知识助手。基于以下文档回答问题。
若文档无相关信息，明确告知用户，不要编造。

文档：
{context}

问题：{question}
回答："""
    return call_llm(prompt)  # 输出前再接 ComplianceChecker（§4.2）

class PermissionFilter:
    def __init__(self, vector_db):
        self.vector_db = vector_db
    
    def retrieve_with_permission(self, query, user_role, user_dept, top_k=5):
        filter_conditions = {"status": "active"}
        if user_dept:
            filter_conditions["department"] = user_dept
        results = self.vector_db.search(query, filter=filter_conditions, top_k=top_k)
        return results

class ComplianceChecker:
    FORBIDDEN_PHRASES = ["保本保息", "稳赚不赔", "无风险", "100%收益"]
    
    @classmethod
    def check(cls, text):
        violations = [p for p in cls.FORBIDDEN_PHRASES if p in text]
        return {"compliant": len(violations) == 0, "violations": violations}

def log_audit(user_id, query, answer, timestamp=None):
    audit_log = {
        "user_id": user_id,
        "query": query,
        "answer": answer[:500],
        "timestamp": timestamp or datetime.now().isoformat(),
        "ip_address": get_client_ip(),
    }
    with open("audit_log.jsonl", "a") as f:
        f.write(json.dumps(audit_log) + "\n")

def update_document(vector_db, doc_id, new_content):
    vector_db.update_metadata(doc_id, {"status": "expired"})
    new_doc_id = vector_db.insert(new_content)
    vector_db.update_metadata(new_doc_id, {
        "status": "active",
        "updated_at": datetime.now().isoformat(),
        "previous_version": doc_id
    })

def enterprise_kb_acceptance_test(kb_system):
    """功能 + 权限 + 边界 三类场景"""
    test_scenarios = [
        {"query": "产品的退款政策是什么？", "expected": "退款", "department": "产品部"},
        {"query": "今年的年假是多少天？", "expected": "年假", "department": "HR"},
        {"query": "产品 A 的定价策略", "department": "财务部", "should_deny": True},
        {"query": "", "expected_error": True},
        {"query": "a" * 1000, "expected_error": False},
    ]
    passed = 0
    for scenario in test_scenarios:
        try:
            result = kb_system.ask(
                scenario["query"],
                department=scenario.get("department"),
            )
            if scenario.get("should_deny"):
                ok = result is None or "未找到" in str(result) or "无权" in str(result)
            elif scenario.get("expected_error"):
                ok = result is None or "错误" in str(result)
            else:
                ok = scenario["expected"] in str(result)
        except Exception:
            ok = scenario.get("expected_error", False)
        passed += int(ok)
        print(f"{'✅' if ok else '❌'} {scenario.get('query', '')[:40]}")
    rate = passed / len(test_scenarios)
    print(f"\n通过率: {passed}/{len(test_scenarios)} = {rate:.0%}")
    return rate
