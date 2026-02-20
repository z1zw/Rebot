"""FAISS-based vector retriever."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import pickle
import time

from rebot.rag.retrievers.base import BaseRetriever, EmbeddingFunction
from rebot.rag.schema import Chunk, Document, RetrievalResult, RAGConfig, RetrieverType

logger = logging.getLogger(__name__)


class FAISSRetriever(BaseRetriever):
    """基于FAISS的向量检索器。"""
    
    def __init__(
        self,
        config: RAGConfig | None = None,
        embedding_fn: EmbeddingFunction | None = None,
        dimension: int = 1536,
    ):
        super().__init__(config, embedding_fn)
        self.dimension = dimension
        self.index = None
        self.chunks: List[Chunk] = []
        self.id_to_idx: Dict[str, int] = {}
        
    def _ensure_index(self) -> None:
        """确保索引已初始化。"""
        if self.index is not None:
            return
        
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss not installed. Run: pip install faiss-cpu")
        
        index_type = getattr(self.config, 'faiss_index_type', 'flat')
        
        if index_type == "flat":
            self.index = faiss.IndexFlatL2(self.dimension)
        elif index_type == "ivf":
            nlist = getattr(self.config, 'faiss_nlist', 100)
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        elif index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
        
        self._initialized = True
    
    def add_documents(self, documents: List[Document]) -> None:
        """添加文档（自动分块）。"""
        from rebot.rag.utils import chunk_document
        
        all_chunks = []
        for doc in documents:
            chunks = chunk_document(
                doc,
                chunk_size=self.config.chunk_size,
                overlap=self.config.chunk_overlap
            )
            all_chunks.extend(chunks)
        
        self.add_chunks(all_chunks)
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """添加分块。"""
        import numpy as np
        
        self._ensure_index()
        
        if not chunks:
            return
        
        # 生成嵌入
        texts = [c.content for c in chunks]
        embeddings = self.embed(texts)
        
        # 存储
        start_idx = len(self.chunks)
        for i, chunk in enumerate(chunks):
            chunk.embedding = embeddings[i]
            self.chunks.append(chunk)
            self.id_to_idx[chunk.id] = start_idx + i
        
        # 添加到索引
        vectors = np.array(embeddings, dtype=np.float32)
        
        # IVF索引需要训练
        if hasattr(self.index, 'is_trained') and not self.index.is_trained:
            self.index.train(vectors)
        
        self.index.add(vectors)
        logger.info(f"Added {len(chunks)} chunks to FAISS index")
    
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """检索。"""
        import numpy as np
        
        self._ensure_index()
        
        if top_k is None:
            top_k = self.config.retriever_top_k
        
        start_time = time.time()
        
        # 生成查询嵌入
        query_embedding = self.embed([query])[0]
        query_vector = np.array([query_embedding], dtype=np.float32)
        
        # 搜索
        if hasattr(self.index, 'nprobe'):
            self.index.nprobe = self.config.faiss_nlist
        
        k = min(top_k, len(self.chunks))
        if k == 0:
            return RetrievalResult(query=query, retriever_type=RetrieverType.FAISS)
        
        distances, indices = self.index.search(query_vector, k)
        
        # 收集结果
        result_chunks = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx]
            # 转换距离为相似度分数
            chunk.score = 1.0 / (1.0 + distances[0][i])
            result_chunks.append(chunk)
        
        latency = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            query=query,
            chunks=result_chunks,
            retriever_type=RetrieverType.FAISS,
            latency_ms=latency,
            total_docs=len(self.chunks)
        )
    
    def delete(self, doc_ids: List[str]) -> None:
        """删除文档（需要重建索引）。"""
        # FAISS不支持直接删除，需要重建
        new_chunks = [c for c in self.chunks if c.doc_id not in doc_ids]
        if len(new_chunks) == len(self.chunks):
            return
        
        # 重建
        self.chunks = []
        self.id_to_idx = {}
        self.index = None
        self.add_chunks(new_chunks)
    
    def save(self, path: str) -> None:
        """保存索引。"""
        import faiss
        
        # 保存FAISS索引
        if self.index is not None:
            faiss.write_index(self.index, f"{path}.faiss")
        
        # 保存元数据
        with open(f"{path}.meta", 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'id_to_idx': self.id_to_idx,
                'dimension': self.dimension,
            }, f)
    
    def load(self, path: str) -> None:
        """加载索引。"""
        import faiss
        
        self.index = faiss.read_index(f"{path}.faiss")
        
        with open(f"{path}.meta", 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.id_to_idx = data['id_to_idx']
            self.dimension = data['dimension']
        
        self._initialized = True
    
    def clear(self) -> None:
        """清空索引。"""
        self.index = None
        self.chunks = []
        self.id_to_idx = {}
        self._initialized = False
    
    def count(self) -> int:
        """返回分块数量。"""
        return len(self.chunks)
