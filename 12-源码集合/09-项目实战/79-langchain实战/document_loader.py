from langchain.schema import Document
from langchain.document_loaders import (
    TextLoader, PDFPlumberLoader, UnstructuredWordDocumentLoader,
    CSVLoader, JSONLoader
)
from typing import List, Dict, Any
import os
from pathlib import Path
import time

class DocumentLoader:
    """文档加载器"""
    
    SUPPORTED_FORMATS = {
        '.txt': TextLoader,
        '.pdf': PDFPlumberLoader,
        '.docx': UnstructuredWordDocumentLoader,
        '.csv': CSVLoader,
        '.json': JSONLoader,
    }
    
    def __init__(self):
        self.documents = []
    
    def load_from_directory(self, directory_path: str, recursive: bool = True) -> List[Document]:
        """从目录加载所有支持格式的文档"""
        directory = Path(directory_path)
        all_documents = []
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory {directory_path} does not exist")
        
        # 遍历目录
        if recursive:
            file_paths = [f for f in directory.rglob('*') if f.is_file()]
        else:
            file_paths = [f for f in directory.iterdir() if f.is_file()]
        
        for file_path in file_paths:
            ext = file_path.suffix.lower()
            if ext in self.SUPPORTED_FORMATS:
                try:
                    documents = self.load_document(str(file_path))
                    all_documents.extend(documents)
                    print(f"Loaded {len(documents)} documents from {file_path}")
                except Exception as e:
                    print(f"Failed to load {file_path}: {str(e)}")
        
        self.documents.extend(all_documents)
        return all_documents
    
    def load_document(self, file_path: str) -> List[Document]:
        """加载单个文档"""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")
        
        loader_class = self.SUPPORTED_FORMATS[ext]
        
        # 特殊处理JSON文件
        if ext == '.json':
            loader = loader_class(
                file_path=file_path,
                jq_schema=".[]",  # 假设JSON是数组格式
                content_key="content"  # 假设内容字段名为content
            )
        else:
            loader = loader_class(str(file_path))
        
        documents = loader.load()
        
        # 添加元数据
        for doc in documents:
            doc.metadata['source_file'] = str(file_path)
            doc.metadata['file_type'] = ext
            doc.metadata['loaded_at'] = time.time()
        
        return documents
    
    def load_from_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """从纯文本加载文档"""
        if metadata is None:
            metadata = {}
        
        doc = Document(page_content=text, metadata=metadata)
        self.documents.append(doc)
        return [doc]
    
    def validate_documents(self) -> Dict[str, Any]:
        """验证加载的文档"""
        stats = {
            'total_documents': len(self.documents),
            'total_chars': sum(len(doc.page_content) for doc in self.documents),
            'avg_doc_length': 0,
            'file_types': {},
            'empty_docs': 0
        }
        
        if stats['total_documents'] > 0:
            stats['avg_doc_length'] = stats['total_chars'] / stats['total_documents']
        
        # 统计文件类型
        for doc in self.documents:
            file_type = doc.metadata.get('file_type', 'unknown')
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
            if len(doc.page_content.strip()) == 0:
                stats['empty_docs'] += 1
        
        return stats

def create_sample_documents():
    """创建示例文档用于测试"""
    sample_docs = [
        Document(
            page_content="""
            人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
            它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
            该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
            """,
            metadata={'title': '人工智能概述', 'category': 'tech', 'source': 'sample'}
        ),
        Document(
            page_content="""
            机器学习（Machine Learning，ML）是人工智能的一个子领域，
            它使计算机能够在没有明确编程的情况下学习和改进。
            机器学习算法通过数据构建模型，从而做出预测或决策。
            """,
            metadata={'title': '机器学习基础', 'category': 'tech', 'source': 'sample'}
        ),
        Document(
            page_content="""
            深度学习（Deep Learning）是机器学习的一个分支，
            它基于人工神经网络的结构和功能。
            深度学习模型通常具有多个隐藏层，可以学习数据的层次化特征表示。
            """,
            metadata={'title': '深度学习原理', 'category': 'tech', 'source': 'sample'}
        )
    ]
    return sample_docs