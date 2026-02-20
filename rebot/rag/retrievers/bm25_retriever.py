"""BM25-based keyword retriever."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import pickle
import time
import math
from collections import Counter

from rebot.rag.retrievers.base import BaseRetriever, EmbeddingFunction
from rebot.rag.schema import Chunk, Document, RetrievalResult, RAGConfig, RetrieverType, BM25Config

logger = logging.getLogger(__name__)


class BM25Retriever(BaseRetriever):
    """基于BM25的关键词检索器。"""
    
    def __init__(
        self,
        config: RAGConfig | None = None,
        bm25_config: BM25Config | None = None,
        embedding_fn: EmbeddingFunction | None = None,
    ):
        super().__init__(config, embedding_fn)
        self.bm25_config = bm25_config or BM25Config()
        
        # 文档存储
        self.chunks: List[Chunk] = []
        self.id_to_idx: Dict[str, int] = {}
        
        # BM25参数
        self.k1 = self.bm25_config.k1
        self.b = self.bm25_config.b
        self.epsilon = self.bm25_config.epsilon
        
        # 索引
        self.doc_freqs: Dict[str, int] = {}  # term -> doc frequency
        self.doc_lens: List[int] = []  # 文档长度
        self.avgdl: float = 0.0  # 平均文档长度
        self.term_freqs: List[Counter] = []  # 每个文档的词频
        
        self._initialized = False
    
    def _tokenize(self, text: str) -> List[str]:
        """分词。"""
        # 简单分词，可以替换为更复杂的分词器
        import re
        tokens = re.findall(r'\w+', text.lower())
        return tokens
    
    def _build_index(self) -> None:
        """构建BM25索引。"""
        self.doc_freqs = {}
        self.doc_lens = []
        self.term_freqs = []
        
        for chunk in self.chunks:
            tokens = self._tokenize(chunk.content)
            self.doc_lens.append(len(tokens))
            
            term_freq = Counter(tokens)
            self.term_freqs.append(term_freq)
            
            # 更新文档频率
            for term in set(tokens):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
        
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0
        self._initialized = True
    
    def add_documents(self, documents: List[Document]) -> None:
        """添加文档。"""
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
        if not chunks:
            return
        
        start_idx = len(self.chunks)
        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self.id_to_idx[chunk.id] = start_idx + i
        
        # 重建索引
        self._build_index()
        logger.info(f"Added {len(chunks)} chunks to BM25 index")
    
    def _score(self, query_terms: List[str], doc_idx: int) -> float:
        """计算BM25分数。"""
        score = 0.0
        doc_len = self.doc_lens[doc_idx]
        term_freq = self.term_freqs[doc_idx]
        n_docs = len(self.chunks)
        
        for term in query_terms:
            if term not in self.doc_freqs:
                continue
            
            df = self.doc_freqs[term]
            tf = term_freq.get(term, 0)
            
            if tf == 0:
                continue
            
            # IDF
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
            
            # TF normalization
            tf_norm = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            )
            
            score += idf * tf_norm
        
        return score
    
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """检索。"""
        if not self._initialized:
            return RetrievalResult(query=query, retriever_type=RetrieverType.BM25)
        
        if top_k is None:
            top_k = self.config.retriever_top_k
        
        start_time = time.time()
        
        query_terms = self._tokenize(query)
        
        # 计算所有文档的分数
        scores = []
        for i in range(len(self.chunks)):
            score = self._score(query_terms, i)
            scores.append((i, score))
        
        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 收集结果
        result_chunks = []
        for idx, score in scores[:top_k]:
            chunk = self.chunks[idx]
            chunk.score = score
            result_chunks.append(chunk)
        
        latency = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            query=query,
            chunks=result_chunks,
            retriever_type=RetrieverType.BM25,
            latency_ms=latency,
            total_docs=len(self.chunks)
        )
    
    def delete(self, doc_ids: List[str]) -> None:
        """删除文档。"""
        new_chunks = [c for c in self.chunks if c.doc_id not in doc_ids]
        if len(new_chunks) == len(self.chunks):
            return
        
        self.chunks = new_chunks
        self.id_to_idx = {c.id: i for i, c in enumerate(self.chunks)}
        self._build_index()
    
    def save(self, path: str) -> None:
        """保存索引。"""
        with open(f"{path}.bm25", 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'id_to_idx': self.id_to_idx,
                'doc_freqs': self.doc_freqs,
                'doc_lens': self.doc_lens,
                'avgdl': self.avgdl,
                'term_freqs': self.term_freqs,
            }, f)
    
    def load(self, path: str) -> None:
        """加载索引。"""
        with open(f"{path}.bm25", 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.id_to_idx = data['id_to_idx']
            self.doc_freqs = data['doc_freqs']
            self.doc_lens = data['doc_lens']
            self.avgdl = data['avgdl']
            self.term_freqs = data['term_freqs']
        self._initialized = True
    
    def clear(self) -> None:
        """清空索引。"""
        self.chunks = []
        self.id_to_idx = {}
        self.doc_freqs = {}
        self.doc_lens = []
        self.avgdl = 0.0
        self.term_freqs = []
        self._initialized = False
    
    def count(self) -> int:
        """返回分块数量。"""
        return len(self.chunks)
