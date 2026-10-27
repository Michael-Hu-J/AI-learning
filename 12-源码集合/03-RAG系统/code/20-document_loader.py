import re
from collections import Counter

def clean_pdf_text(text):
    lines = text.split('\n')
    line_counter = Counter(lines)
    # 重复出现 3 次以上且较短的行，判定为页眉页脚
    repeated_lines = {line for line, count in line_counter.items()
                      if count > 2 and len(line) < 50}
    cleaned = [line for line in lines if line not in repeated_lines]
    return '\n'.join(cleaned)

def extract_double_column(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            width = page.width
            left = page.crop((0, 0, width/2, page.height))
            right = page.crop((width/2, 0, width, page.height))
            full_text += left.extract_text() + "\n"
            full_text += right.extract_text() + "\n"
        return full_text

def detect_columns(page):
    """检测页面中的栏位置"""
    words = page.extract_words()
    if not words:
        return [(0, page.width)]
    
    x_positions = [w['x0'] for w in words]
    # 用聚类算法找栏的边界
    # 简化版：按x坐标中位数分割
    median_x = sorted(x_positions)[len(x_positions)//2]
    return [(0, median_x), (median_x, page.width)]

def smart_extract_page(page):
    """智能提取：文字版直接提取，扫描件OCR"""
    text = page.extract_text()
    if len(text.strip()) < 50:
        # 文字太少，可能是扫描件，用OCR
        image = page.to_image(resolution=300)
        import pytesseract
        text = pytesseract.image_to_string(image.original, lang='chi_sim+eng')
    return text

def extract_tables_as_markdown(pdf_path: str):
    with pdfplumber.open(pdf_path) as pdf:
        all_tables = []
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for i, table in enumerate(tables):
                markdown = table_to_markdown(table)
                all_tables.append({
                    'page': page_num + 1,
                    'index': i,
                    'markdown': markdown
                })
        return all_tables

import PyPDF2

with open("document.pdf", "rb") as f:
    reader = PyPDF2.PdfReader(f)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

import pdfplumber

# 基本文本提取
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)

# 表格提取
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)

# 区域裁剪（处理多栏排版）
with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]
    width = page.width
    left = page.crop((0, 0, width/2, page.height))
    right = page.crop((width/2, 0, width, page.height))
    print("左栏:", left.extract_text())
    print("右栏:", right.extract_text())

from unstructured.partition.auto import partition

# 自动检测格式并解析
elements = partition(filename="document.pdf")

# 提取文本
for element in elements:
    print(f"[{type(element).__name__}] {element.text}")

# 按类型过滤
from unstructured.documents.elements import Title, NarrativeText, Table

titles = [e.text for e in elements if isinstance(e, Title)]
narratives = [e.text for e in elements if isinstance(e, NarrativeText)]
tables = [e.metadata.text_as_html for e in elements if isinstance(e, Table)]

from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredPDFLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader,
    CSVLoader,
    TextLoader
)

# PDF加载
loader = PyPDFLoader("document.pdf")
documents = loader.load()

# Word加载
loader = Docx2txtLoader("document.docx")
documents = loader.load()

# HTML加载
loader = UnstructuredHTMLLoader("page.html")
documents = loader.load()

# 批量加载
from langchain_community.document_loaders import DirectoryLoader

loader = DirectoryLoader("./documents/", glob="**/*.pdf")
documents = loader.load()

import pytesseract
from pdf2image import convert_from_path

# 单张图片OCR
text = pytesseract.image_to_string(image, lang='chi_sim+eng')

# PDF每页OCR
images = convert_from_path("scanned.pdf", dpi=300)
full_text = ""
for img in images:
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
    full_text += text + "\n"

# 更高质量的OCR：使用PaddleOCR（中文更好）
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='ch')
result = ocr.ocr(image)
for line in result:
    print(line[1][0])  # 识别的文字

def smart_parse(file_path: str) -> str:
    """智能解析：根据文件类型和特征选择最佳解析策略"""
    ext = file_path.rsplit('.', 1)[-1].lower()
    
    if ext == 'pdf':
        # 先尝试pdfplumber直接提取
        text = extract_with_pdfplumber(file_path)
        
        # 如果文字太少，可能是扫描件，用OCR
        if len(text.strip()) < 100:
            text = extract_with_ocr(file_path)
        
        # 检测多栏排版
        if is_double_column(file_path):
            text = extract_double_column(file_path)
        
        # 提取表格
        tables = extract_tables_as_markdown(file_path)
        text += "\n\n## 表格\n\n" + "\n\n".join(t['markdown'] for t in tables)
        
        return text
    
    elif ext in ('docx', 'doc'):
        return extract_with_docx(file_path)
    
    elif ext in ('xlsx', 'xls'):
        return extract_with_excel(file_path)
    
    elif ext == 'html':
        return extract_with_html(file_path)
    
    elif ext in ('png', 'jpg', 'jpeg', 'bmp'):
        return extract_with_ocr_image(file_path)
    
    else:
        # 回退到纯文本读取
        return read_as_text(file_path)

import re

def document_clean_pipeline(text):
    text = remove_headers_footers(text)  # 见 §3.0 clean_pdf_text
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)  # 合并被截断的段落
    text = re.sub(r'\s+', ' ', text)              # 去除多余空白
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)  # 过滤乱码
    text = re.sub(r'[◆●○□■△▲※→⇒]', '', text)     # 去除装饰符号
    return text.strip()
