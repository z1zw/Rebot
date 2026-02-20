"""Base retriever interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Protocol, runtime_checkable

from rebot.rag.schema import Chunk, Document, RetrievalResult, RAGConfig


@runtime_checkable
class EmbeddingFunction(Protocol):
    """嵌入函数协议。"""
    def __call__(self, texts: List[str]) -> List[List[float]]:
        ...


class BaseRetriever(ABC):
    """检索器基类。"""
    
    def __init__(
        self,
        config: RAGConfig | None = None,
        embedding_fn: EmbeddingFunction | None = None
    ):
        self.config = config or RAGConfig()
        self.embedding_fn = embedding_fn
        self._initialized = False
    
    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        """添加文档。"""
        ...
    
    @abstractmethod
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """添加分块。"""
        ...
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """检索。"""
        ...
    
    @abstractmethod
    def delete(self, doc_ids: List[str]) -> None:
        """删除文档。"""
        ...
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量。"""
        if self.embedding_fn is None:
            raise ValueError("embedding_fn not set")
        return self.embedding_fn(texts)
    
    def search(self, query: str, top_k: int = 5) -> List[Chunk]:
        """简化搜索接口。"""
        result = self.retrieve(query, top_k)
        return result.top_k(top_k)
    
    def clear(self) -> None:
        """清空索引。"""
        pass
    
    def save(self, path: str) -> None:
        """保存索引。"""
        pass
    
    def load(self, path: str) -> None:
        """加载索引。"""
        pass
    
    def count(self) -> int:
        """返回文档/分块数量。"""
        return 0
