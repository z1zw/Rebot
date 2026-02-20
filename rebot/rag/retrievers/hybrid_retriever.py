"""Hybrid retriever combining semantic and keyword search."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import time

from rebot.rag.retrievers.base import BaseRetriever, EmbeddingFunction
from rebot.rag.retrievers.faiss_retriever import FAISSRetriever
from rebot.rag.retrievers.bm25_retriever import BM25Retriever
from rebot.rag.schema import Chunk, Document, RetrievalResult, RAGConfig, RetrieverType

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """混合检索器，结合语义检索和关键词检索。
    
    使用Reciprocal Rank Fusion (RRF)组合两种检索结果。
    """
    
    def __init__(
        self,
        config: RAGConfig | None = None,
        embedding_fn: EmbeddingFunction | None = None,
        alpha: float = 0.5,
        rrf_k: int = 60,
    ):
        super().__init__(config, embedding_fn)
        
        # 权重：0=纯语义, 1=纯关键词
        self.alpha = alpha
        self.rrf_k = rrf_k  # RRF参数
        
        # 子检索器
        self.semantic_retriever = FAISSRetriever(config, embedding_fn)
        self.keyword_retriever = BM25Retriever(config)
        
        self._initialized = False
    
    def add_documents(self, documents: List[Document]) -> None:
        """添加文档到两个检索器。"""
        self.semantic_retriever.add_documents(documents)
        self.keyword_retriever.add_documents(documents)
        self._initialized = True
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """添加分块到两个检索器。"""
        self.semantic_retriever.add_chunks(chunks)
        self.keyword_retriever.add_chunks(chunks)
        self._initialized = True
    
    def _rrf_fusion(
        self,
        semantic_chunks: List[Chunk],
        keyword_chunks: List[Chunk],
        top_k: int
    ) -> List[Chunk]:
        """使用RRF组合两个检索结果。"""
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}
        
        # 语义检索结果
        for rank, chunk in enumerate(semantic_chunks):
            rrf_score = (1 - self.alpha) / (self.rrf_k + rank + 1)
            scores[chunk.id] = scores.get(chunk.id, 0) + rrf_score
            chunk_map[chunk.id] = chunk
        
        # 关键词检索结果
        for rank, chunk in enumerate(keyword_chunks):
            rrf_score = self.alpha / (self.rrf_k + rank + 1)
            scores[chunk.id] = scores.get(chunk.id, 0) + rrf_score
            if chunk.id not in chunk_map:
                chunk_map[chunk.id] = chunk
        
        # 按组合分数排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        result = []
        for chunk_id in sorted_ids[:top_k]:
            chunk = chunk_map[chunk_id]
            chunk.score = scores[chunk_id]
            result.append(chunk)
        
        return result
    
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """混合检索。"""
        if not self._initialized:
            return RetrievalResult(query=query, retriever_type=RetrieverType.HYBRID)
        
        if top_k is None:
            top_k = self.config.retriever_top_k
        
        start_time = time.time()
        
        # 从两个检索器获取更多结果
        fetch_k = top_k * 2
        
        semantic_result = self.semantic_retriever.retrieve(query, fetch_k)
        keyword_result = self.keyword_retriever.retrieve(query, fetch_k)
        
        # 融合
        fused_chunks = self._rrf_fusion(
            semantic_result.chunks,
            keyword_result.chunks,
            top_k
        )
        
        latency = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            query=query,
            chunks=fused_chunks,
            retriever_type=RetrieverType.HYBRID,
            latency_ms=latency,
            total_docs=self.semantic_retriever.count()
        )
    
    def delete(self, doc_ids: List[str]) -> None:
        """从两个检索器删除。"""
        self.semantic_retriever.delete(doc_ids)
        self.keyword_retriever.delete(doc_ids)
    
    def save(self, path: str) -> None:
        """保存两个索引。"""
        self.semantic_retriever.save(f"{path}_semantic")
        self.keyword_retriever.save(f"{path}_keyword")
    
    def load(self, path: str) -> None:
        """加载两个索引。"""
        self.semantic_retriever.load(f"{path}_semantic")
        self.keyword_retriever.load(f"{path}_keyword")
        self._initialized = True
    
    def clear(self) -> None:
        """清空两个索引。"""
        self.semantic_retriever.clear()
        self.keyword_retriever.clear()
        self._initialized = False
    
    def count(self) -> int:
        """返回分块数量。"""
        return self.semantic_retriever.count()
