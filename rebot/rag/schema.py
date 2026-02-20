"""RAG schema definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid


class RetrieverType(str, Enum):
    """检索器类型。"""
    FAISS = "faiss"
    BM25 = "bm25"
    CHROMA = "chroma"
    ELASTICSEARCH = "elasticsearch"
    HYBRID = "hybrid"


class RankerType(str, Enum):
    """排序器类型。"""
    LLM = "llm"
    COLBERT = "colbert"
    BGE = "bge"
    CROSS_ENCODER = "cross_encoder"


@dataclass
class Document:
    """文档。"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    
    # 文档类型
    doc_type: str = "text"  # text, code, markdown, pdf, etc.
    
    # 嵌入向量（可选）
    embedding: Optional[List[float]] = None


@dataclass
class Chunk:
    """文档分块。"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 归属
    doc_id: str = ""
    chunk_index: int = 0
    
    # 位置信息
    start_char: int = 0
    end_char: int = 0
    
    # 嵌入向量
    embedding: Optional[List[float]] = None
    
    # 评分
    score: float = 0.0


@dataclass
class RetrievalResult:
    """检索结果。"""
    query: str = ""
    chunks: List[Chunk] = field(default_factory=list)
    
    # 元信息
    retriever_type: RetrieverType = RetrieverType.FAISS
    latency_ms: float = 0.0
    total_docs: int = 0
    
    def top_k(self, k: int) -> List[Chunk]:
        """获取Top K结果。"""
        return sorted(self.chunks, key=lambda x: x.score, reverse=True)[:k]
    
    def to_context(self, max_chunks: int = 5) -> str:
        """转换为上下文字符串。"""
        top = self.top_k(max_chunks)
        return "\n\n---\n\n".join(c.content for c in top)


@dataclass
class RAGConfig:
    """RAG配置。"""
    # 检索器
    retriever_type: RetrieverType = RetrieverType.FAISS
    retriever_top_k: int = 10
    
    # 排序器
    ranker_type: Optional[RankerType] = None
    ranker_top_k: int = 5
    
    # 分块
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # 嵌入
    embedding_model: str = "text-embedding-ada-002"
    embedding_batch_size: int = 32
    
    # Hybrid权重
    hybrid_alpha: float = 0.5  # 0=纯语义, 1=纯关键词
    
    # FAISS
    faiss_index_type: str = "flat"  # flat, ivf, hnsw
    faiss_nlist: int = 100
    faiss_nprobe: int = 10
    
    # Elasticsearch
    es_host: str = "localhost"
    es_port: int = 9200
    es_index: str = "rebot_rag"
    
    # Chroma
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "rebot"


@dataclass
class FAISSConfig:
    """FAISS检索器配置。"""
    index_type: str = "flat"  # flat, ivf, hnsw
    dimension: int = 1536  # 向量维度
    nlist: int = 100  # IVF聚类数
    nprobe: int = 10  # 搜索时探测的聚类数
    ef_search: int = 64  # HNSW搜索参数
    ef_construction: int = 200  # HNSW构建参数


@dataclass
class BM25Config:
    """BM25检索器配置。"""
    k1: float = 1.5
    b: float = 0.75
    epsilon: float = 0.25


@dataclass
class ChromaConfig:
    """Chroma检索器配置。"""
    persist_directory: str = "./chroma_db"
    collection_name: str = "rebot"
    embedding_function: str = "default"


@dataclass
class ElasticsearchConfig:
    """Elasticsearch检索器配置。"""
    host: str = "localhost"
    port: int = 9200
    index_name: str = "rebot_rag"
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False


@dataclass
class RankerConfig:
    """排序器配置。"""
    ranker_type: RankerType = RankerType.CROSS_ENCODER
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k: int = 5
    batch_size: int = 32
