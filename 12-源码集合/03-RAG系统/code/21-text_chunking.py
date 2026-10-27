def fixed_length_split(text, chunk_size=500, overlap=50):
    """固定长度切片：实现最简单，但可能在句子中间硬切"""
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks

def semantic_split(text):
    """按段落切片：保证语义完整，但 chunk 大小可能极不均匀"""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

def overlap_split(text, chunk_size=500, overlap=100):
    """重叠切片：与 fixed_length_split 相同思路，overlap 是防截断的安全网"""
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks

from langchain_text_splitters import CharacterTextSplitter

# 创建切片器
splitter = CharacterTextSplitter(
    separator="\n\n",     # 优先在双换行处切分（段落边界）
    chunk_size=500,       # 每个chunk的最大字符数
    chunk_overlap=50,     # 相邻chunk的重叠字符数
    length_function=len,  # 计算长度的函数，默认是len()
    is_separator_regex=False,  # 分隔符是否是正则表达式
)

# 切分文本
texts = splitter.split_text(long_text)
for i, text in enumerate(texts):
    print(f"Chunk {i+1} ({len(text)} chars): {text[:100]}...")

from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", "。", "；", "，", " ", ""],  # 按优先级尝试这些分隔符
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
    is_separator_regex=False,
)

texts = splitter.split_text(long_text)

from langchain_text_splitters import MarkdownHeaderTextSplitter

splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "Header 1"),      # 一级标题
        ("##", "Header 2"),     # 二级标题
        ("###", "Header 3"),    # 三级标题
    ]
)

texts = splitter.split_text(markdown_text)
for chunk in texts:
    print(f"标题路径: {chunk.metadata}")
    print(f"内容: {chunk.page_content[:200]}")
    print("---")

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

# 支持多种编程语言
supported_languages = [
    Language.PYTHON,
    Language.JAVASCRIPT,
    Language.JAVA,
    Language.CPP,
    Language.GO,
    Language.RUST,
]

for lang in supported_languages:
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=lang,
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_text(code_text)
    print(f"{lang.value}: {len(chunks)} chunks")

from langchain_text_splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,      # 每个chunk的最大token数
    chunk_overlap=50,    # 重叠token数
    encoding_name="cl100k_base",  # 使用的编码方式
)

texts = splitter.split_text(long_text)

import re

def chunk_by_semantic_paragraph(text, max_chunk_size=1000, overlap=100):
    """
    按语义段落切片
    尽量在段落边界处切分，同时控制chunk大小
    """
    # 先按段落分割
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 如果单个段落就超过了最大长度，需要进一步切分
        if len(para) > max_chunk_size:
            # 先保存当前chunk
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # 按句子切分大段落
            sentences = re.split(r'([。！？；])', para)
            temp_chunk = ""
            for i in range(0, len(sentences)-1, 2):
                sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                if len(temp_chunk) + len(sentence) > max_chunk_size:
                    chunks.append(temp_chunk)
                    temp_chunk = sentence
                else:
                    temp_chunk += sentence
            if temp_chunk:
                chunks.append(temp_chunk)
            continue
        
        # 如果当前段落加入后超过最大长度，保存当前chunk
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            # 保留重叠部分
            if overlap > 0 and len(current_chunk) >= overlap:
                current_chunk = current_chunk[-overlap:] + "\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # 添加最后一个chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

import re

def chunk_by_qa(text):
    """
    按问答对切片
    适用于FAQ类型的文档
    """
    # 匹配多种问答格式
    patterns = [
        r'(?:Q[：:]|问题[：:]|疑问[：:])(.*?)(?:A[：:]|回答[：:]|答案[：:]|回复[：:])(.*?)(?=(?:Q[：:]|问题[：:]|疑问[：:])|$)',
        r'(?:问[：:])(.*?)(?:答[：:])(.*?)(?=(?:问[：:])|$)',
    ]
    
    chunks = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if len(match) == 2:
                question, answer = match
                chunk = f"问题：{question.strip()}\n回答：{answer.strip()}"
                chunks.append(chunk)
    
    # 如果没有匹配到问答对，返回原文
    if not chunks:
        chunks = [text]
    
    return chunks

def evaluate_chunks(chunks, original_text):
    """
    评估切片质量
    返回多个维度的评估指标
    """
    if not chunks:
        return {"error": "没有生成任何chunk"}
    
    metrics = {}
    
    # 1. chunk数量
    metrics['chunk数量'] = len(chunks)
    
    # 2. chunk大小统计
    sizes = [len(c) for c in chunks]
    metrics['平均大小'] = round(sum(sizes) / len(sizes), 0)
    metrics['最小大小'] = min(sizes)
    metrics['最大大小'] = max(sizes)
    
    # 计算标准差
    mean_size = sum(sizes) / len(sizes)
    variance = sum((s - mean_size) ** 2 for s in sizes) / len(sizes)
    metrics['大小标准差'] = round(variance ** 0.5, 0)
    
    # 3. 内容覆盖率
    all_chunk_text = '\n'.join(chunks)
    metrics['内容覆盖率'] = round(len(all_chunk_text) / len(original_text), 2) if original_text else 0
    
    # 4. 重复率（由于重叠导致）
    metrics['冗余率'] = round((len(all_chunk_text) - len(original_text)) / len(original_text), 2) if original_text else 0
    
    # 5. 检查是否有chunk在句子中间切断
    sentence_endings = ['。', '！', '？', '}', '】', ')', '\n', '；']
    broken = 0
    for chunk in chunks[:-1]:  # 最后一个chunk不需要检查结尾
        if chunk and chunk[-1] not in sentence_endings:
            broken += 1
    metrics['断裂句子比例'] = round(broken / len(chunks), 2) if chunks else 0
    
    # 6. chunk大小分布
    size_ranges = {'0-200': 0, '200-500': 0, '500-1000': 0, '1000-2000': 0, '2000+': 0}
    for size in sizes:
        if size < 200:
            size_ranges['0-200'] += 1
        elif size < 500:
            size_ranges['200-500'] += 1
        elif size < 1000:
            size_ranges['500-1000'] += 1
        elif size < 2000:
            size_ranges['1000-2000'] += 1
        else:
            size_ranges['2000+'] += 1
    metrics['大小分布'] = size_ranges
    
    return metrics

from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import logging

logger = logging.getLogger(__name__)


class SmartChunker:
    """
    智能切片器
    根据文档类型自动选择最佳切片策略
    """
    
    def __init__(self):
        # 通用切片器配置
        self.general_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],
            chunk_size=800,
            chunk_overlap=150,
            length_function=len,
        )
    
    def chunk(self, text, doc_type="general"):
        """
        根据文档类型选择切片策略
        """
        if doc_type == "faq":
            chunks = self._chunk_faq(text)
        elif doc_type == "tech":
            chunks = self._chunk_tech_doc(text)
        elif doc_type == "contract":
            chunks = self._chunk_contract(text)
        elif doc_type == "report":
            chunks = self._chunk_report(text)
        else:
            chunks = self.general_splitter.split_text(text)
        
        # 评估切片质量
        metrics = evaluate_chunks(chunks, text)
        logger.info(f"切片质量评估: {metrics}")
        
        return chunks
    
    def _chunk_faq(self, text):
        """FAQ文档切片"""
        chunks = []
        pattern = r'(?:Q[：:]|问题[：:]|疑问[：:])(.*?)(?:A[：:]|回答[：:]|答案[：:]|回复[：:])(.*?)(?=(?:Q[：:]|问题[：:]|疑问[：:])|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        for question, answer in matches:
            chunk = f"问题：{question.strip()}\n回答：{answer.strip()}"
            chunks.append(chunk)
        
        # 如果没有匹配到问答对，使用通用切片器
        if not chunks:
            chunks = self.general_splitter.split_text(text)
        
        return chunks
    
    def _chunk_tech_doc(self, text):
        """技术文档切片"""
        # 技术文档通常有清晰的标题结构
        header_pattern = r'(\n#{1,6}\s+.+?\n)'
        parts = re.split(header_pattern, text)
        
        chunks = []
        current_header = ""
        
        for part in parts:
            if re.match(header_pattern, part):
                current_header = part.strip()
            else:
                if part.strip():
                    if current_header:
                        chunk = f"{current_header}\n{part.strip()}"
                    else:
                        chunk = part.strip()
                    
                    # 如果chunk太大，进一步切分
                    if len(chunk) > 1500:
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=800, chunk_overlap=150
                        )
                        sub_chunks = splitter.split_text(chunk)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(chunk)
        
        return chunks
    
    def _chunk_contract(self, text):
        """合同文档切片"""
        # 合同通常有条款编号，按条款切分
        clause_pattern = r'(第[一二三四五六七八九十百]+[条章节])'
        parts = re.split(clause_pattern, text)
        
        chunks = []
        current_clause = ""
        
        for part in parts:
            if re.match(clause_pattern, part):
                current_clause = part
            else:
                if part.strip() and current_clause:
                    chunks.append(f"{current_clause} {part.strip()}")
        
        return chunks
    
    def _chunk_report(self, text):
        """报告文档切片"""
        # 报告通常有章节结构，按章节切分
        chapter_pattern = r'(第[一二三四五六七八九十百]+章|Chapter\s+\d+)'
        parts = re.split(chapter_pattern, text)
        
        chunks = []
        current_chapter = ""
        
        for part in parts:
            if re.match(chapter_pattern, part):
                current_chapter = part.strip()
            else:
                if part.strip():
                    if current_chapter:
                        chunk = f"{current_chapter}\n{part.strip()}"
                    else:
                        chunk = part.strip()
                    
                    # 对大chunk进行二次切分
                    if len(chunk) > 2000:
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=1000, chunk_overlap=200
                        )
                        sub_chunks = splitter.split_text(chunk)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(chunk)
        
        return chunks


def evaluate_chunks(chunks, original_text):
    """评估切片质量"""
    if not chunks:
        return {"error": "没有生成任何chunk"}
    
    sizes = [len(c) for c in chunks]
    sentence_endings = '。！？}】)\n；'
    broken = sum(1 for c in chunks[:-1] if c and c[-1] not in sentence_endings)
    
    return {
        "chunk数量": len(chunks),
        "平均大小": round(sum(sizes) / len(sizes), 0),
        "最小大小": min(sizes),
        "最大大小": max(sizes),
        "断裂句子比例": round(broken / len(chunks), 2),
        "内容覆盖率": round(len('\n'.join(chunks)) / len(original_text), 2) if original_text else 0,
    }

def run_chunking_experiment(text, test_questions, chunk_sizes=[200, 500, 800, 1000, 1500, 2000], overlaps=[0, 50, 100, 150, 200]):
    """
    切片参数调优实验
    测试不同chunk_size和chunk_overlap组合的效果
    """
    results = []
    
    for chunk_size in chunk_sizes:
        for overlap in overlaps:
            if overlap >= chunk_size:
                continue
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
            )
            chunks = splitter.split_text(text)
            
            # 模拟检索测试
            recall_scores = []
            
            for question in test_questions:
                # 检索top_k=5的结果
                relevant_chunks = retrieve(question, chunks, top_k=5)
                # 计算召回率
                recall = calculate_recall(question, relevant_chunks)
                recall_scores.append(recall)
            
            avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0
            
            results.append({
                "chunk_size": chunk_size,
                "chunk_overlap": overlap,
                "num_chunks": len(chunks),
                "avg_recall": round(avg_recall, 4),
            })
    
    # 按召回率排序
    results.sort(key=lambda x: x["avg_recall"], reverse=True)
    
    return results

from typing import List, Tuple

def evaluate_chunk_strategy(
    documents: List[str],
    test_queries: List[str],
    chunk_sizes: List[int] = [256, 512, 1024],
) -> List[Tuple[int, float, int]]:
    """
    对多种 chunk_size 做粗粒度对比。
    生产环境请替换为向量检索 + 标注 Recall@K（见 run_chunking_experiment）。
    """
    results = []
    for chunk_size in chunk_sizes:
        chunks = []
        overlap = max(1, chunk_size // 5)  # 约 20% overlap
        for doc in documents:
            chunks.extend(fixed_length_split(doc, chunk_size=chunk_size, overlap=overlap))
        recall_scores = []
        for query in test_queries:
            hits = [c for c in chunks if query in c]
            recall_scores.append(1.0 if hits else 0.0)
        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0
        results.append((chunk_size, avg_recall, len(chunks)))
    return results

# 示例
# for size, recall, count in evaluate_chunk_strategy(docs, queries, [256, 512, 1024]):
#     print(f"chunk_size={size}: 召回率={recall:.2%}, 切片数={count}")

# 增加重叠区域，防止关键信息被切断
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=150,  # 增加重叠到150字符，确保关键句子不会被完全切断
)

# 增大切片大小，保证相关上下文在同一个chunk中
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,    # 从200增大到800
    chunk_overlap=150,
)

# 对FAQ文档使用专门的问答对切片器
def chunk_faq(text):
    pattern = r'(?:Q[：:]|问题[：:]|疑问[：:])(.*?)(?:A[：:]|回答[：:]|答案[：:]|回复[：:])(.*?)(?=(?:Q[：:]|问题[：:]|疑问[：:])|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    return [f"问题：{q.strip()}\n回答：{a.strip()}" for q, a in matches]

# 减小重叠区域，同时增加去重逻辑
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,  # 从300减小到100
)

# 检索后去重
def deduplicate_chunks(chunks, similarity_threshold=0.9):
    """去除高度相似的chunk"""
    unique_chunks = []
    for chunk in chunks:
        is_duplicate = False
        for unique in unique_chunks:
            similarity = calculate_similarity(chunk, unique)
            if similarity > similarity_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_chunks.append(chunk)
    return unique_chunks

from langchain_core.documents import Document

def chunk_with_metadata(text, doc_name, page_num=None, section=None, doc_type="general"):
    """切片时保留文档元数据"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=150
    )
    chunks = splitter.split_text(text)
    
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "source": doc_name,
                "page": page_num,
                "section": section,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_type": doc_type,
            }
        )
        documents.append(doc)
    
    return documents
