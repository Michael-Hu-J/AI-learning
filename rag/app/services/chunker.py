"""切片：Section -> Chunk。

为什么按字符数而不是按 token：切片阶段还没引入 tokenizer，字符数是零依赖的近似值；
中文场景下 1 字约 1 token，500 字对 Qwen3-Embedding（32k 上下文）非常安全。

策略分两层：
1. 段内合并：把短段落拼到接近 max_chars，避免碎片化（碎片太多会稀释语义）；
2. 超长段落：单段就超过 max_chars 时按窗口硬切，窗口之间留 overlap，
   防止答案正好落在切口处被劈成两半。
"""

import re
from dataclasses import dataclass

from .loader import Section


@dataclass
class Chunk:
    """一个待入库的切片。

    index 在文档内全局递增（跨 Section 连续），用于生成 chunk_id 和展示顺序；
    heading/page 从所属 Section 继承，作为检索结果的溯源信息。
    """

    index: int
    text: str
    heading: str = ""
    page: int | None = None


def split(sections: list[Section], max_chars: int = 500, overlap: int = 50) -> list[Chunk]:
    """把章节列表切成切片列表。

    index 用 len(chunks) 动态生成，保证跨章节连续且从 0 开始，
    这样 chunk_id = f"{doc_id}:{index}" 在整个文档内唯一。
    """
    chunks: list[Chunk] = []
    for section in sections:
        for piece in _split_text(section.text, max_chars, overlap):
            chunks.append(
                Chunk(index=len(chunks), text=piece, heading=section.heading, page=section.page)
            )
    return chunks


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """单章节内的切分：优先按段落边界，段落过长才退化为字符窗口。"""
    pieces: list[str] = []
    buffer = ""

    for para in _paragraphs(text):
        if len(para) > max_chars:
            # 单段就超长（常见于 PDF 整页文字、表格）：先把已累积的结算掉，
            # 再对这一段做硬切，避免长段拖着一个短段一起超限
            if buffer:
                pieces.append(buffer)
                buffer = ""
            pieces.extend(_windows(para, max_chars, overlap))
            continue

        # +1 是拼接时补的 "\n"，计入长度才不会轻微超限
        if buffer and len(buffer) + len(para) + 1 > max_chars:
            pieces.append(buffer)
            buffer = para
        else:
            buffer = f"{buffer}\n{para}" if buffer else para

    if buffer:
        pieces.append(buffer)
    return pieces


def _paragraphs(text: str) -> list[str]:
    """按空行分段。

    用空行（\n\s*\n）而不是单个换行：Markdown 里单换行往往只是折行，
    按它切会把一句话切碎；PDF 抽取的文本则常是单换行，会在超长时才硬切。
    """
    parts = (p.strip() for p in re.split(r"\n\s*\n", text))
    return [p for p in parts if p]


def _windows(text: str, max_chars: int, overlap: int) -> list[str]:
    """超长文本的滑窗切分。

    step 是窗口每次前进的距离 = max_chars - overlap；
    若 overlap >= max_chars（配置错误）会退化为不重叠，防止 range 步长为 0 死循环。
    """
    step = max_chars - overlap if max_chars > overlap else max_chars
    return [text[i : i + max_chars] for i in range(0, len(text), step)]
