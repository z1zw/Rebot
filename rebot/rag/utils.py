"""RAG utility functions."""

from __future__ import annotations

from typing import List
import re

from rebot.rag.schema import Document, Chunk


def chunk_document(
    doc: Document,
    chunk_size: int = 512,
    overlap: int = 50,
    separator: str = "\n"
) -> List[Chunk]:
    """将文档分割成块。
    
    Args:
        doc: 文档
        chunk_size: 块大小（字符数）
        overlap: 重叠大小
        separator: 分隔符
    
    Returns:
        分块列表
    """
    content = doc.content
    if not content:
        return []
    
    chunks = []
    start = 0
    chunk_idx = 0
    
    while start < len(content):
        end = start + chunk_size
        
        # 尝试在分隔符处切分
        if end < len(content):
            # 向后查找分隔符
            sep_pos = content.rfind(separator, start, end)
            if sep_pos > start:
                end = sep_pos + len(separator)
        
        chunk_content = content[start:end].strip()
        
        if chunk_content:
            chunks.append(Chunk(
                content=chunk_content,
                doc_id=doc.id,
                chunk_index=chunk_idx,
                start_char=start,
                end_char=end,
                metadata={**doc.metadata, "source": doc.source}
            ))
            chunk_idx += 1
        
        # 下一个起始位置
        start = end - overlap
        if start < 0:
            start = end
    
    return chunks


def chunk_code(
    doc: Document,
    chunk_size: int = 512,
    overlap: int = 50
) -> List[Chunk]:
    """将代码文档分割成块（保持函数/类完整性）。"""
    content = doc.content
    if not content:
        return []
    
    # 尝试按函数/类分割
    # 匹配 Python 函数和类
    pattern = r'^(class |def |async def )'
    
    lines = content.split('\n')
    chunks = []
    current_chunk_lines = []
    current_start = 0
    chunk_idx = 0
    
    for i, line in enumerate(lines):
        # 检查是否是新的函数/类定义
        if re.match(pattern, line) and current_chunk_lines:
            # 保存当前块
            chunk_content = '\n'.join(current_chunk_lines)
            if len(chunk_content) > chunk_size:
                # 块太大，需要进一步分割
                sub_chunks = _split_large_chunk(chunk_content, chunk_size, overlap, doc, chunk_idx)
                chunks.extend(sub_chunks)
                chunk_idx += len(sub_chunks)
            else:
                chunks.append(Chunk(
                    content=chunk_content,
                    doc_id=doc.id,
                    chunk_index=chunk_idx,
                    start_char=current_start,
                    end_char=current_start + len(chunk_content),
                    metadata={**doc.metadata, "source": doc.source}
                ))
                chunk_idx += 1
            
            current_chunk_lines = [line]
            current_start = sum(len(l) + 1 for l in lines[:i])
        else:
            current_chunk_lines.append(line)
    
    # 处理最后一块
    if current_chunk_lines:
        chunk_content = '\n'.join(current_chunk_lines)
        if len(chunk_content) > chunk_size:
            sub_chunks = _split_large_chunk(chunk_content, chunk_size, overlap, doc, chunk_idx)
            chunks.extend(sub_chunks)
        else:
            chunks.append(Chunk(
                content=chunk_content,
                doc_id=doc.id,
                chunk_index=chunk_idx,
                start_char=current_start,
                end_char=current_start + len(chunk_content),
                metadata={**doc.metadata, "source": doc.source}
            ))
    
    return chunks


def _split_large_chunk(
    content: str,
    chunk_size: int,
    overlap: int,
    doc: Document,
    start_idx: int
) -> List[Chunk]:
    """分割过大的块。"""
    chunks = []
    start = 0
    idx = start_idx
    
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk_content = content[start:end]
        
        chunks.append(Chunk(
            content=chunk_content,
            doc_id=doc.id,
            chunk_index=idx,
            metadata={**doc.metadata, "source": doc.source}
        ))
        idx += 1
        start = end - overlap
        if start < 0:
            break
    
    return chunks


def clean_text(text: str) -> str:
    """清理文本。"""
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 移除控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """提取关键词（简单实现）。"""
    # 分词
    words = re.findall(r'\w+', text.lower())
    
    # 过滤停用词
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'shall',
        'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
        'for', 'on', 'at', 'by', 'with', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'from', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
        'further', 'then', 'once', 'and', 'but', 'or', 'nor', 'so',
        'yet', 'both', 'either', 'neither', 'not', 'only', 'own', 'same',
        'than', 'too', 'very', 'just', 'i', 'me', 'my', 'myself', 'we',
        'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
        'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself',
        'it', 'its', 'itself', 'they', 'them', 'their', 'theirs',
        'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
        'these', 'those', 'am', 'as', 'if', 'because', 'until', 'while'
    }
    
    words = [w for w in words if w not in stopwords and len(w) > 2]
    
    # 计算词频
    from collections import Counter
    freq = Counter(words)
    
    return [word for word, _ in freq.most_common(top_k)]
