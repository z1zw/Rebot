"""RAG Engine - combines retrieval and generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

from rebot.rag.schema import (
    Document,
    Chunk,
    RetrievalResult,
    RAGConfig,
    RetrieverType,
    RankerType,
)
from rebot.rag.retrievers.base import BaseRetriever, EmbeddingFunction
from rebot.rag.retrievers.faiss_retriever import FAISSRetriever
from rebot.rag.retrievers.bm25_retriever import BM25Retriever
from rebot.rag.retrievers.hybrid_retriever import HybridRetriever
from rebot.rag.rankers.base import BaseRanker
from rebot.rag.rankers.cross_encoder_ranker import CrossEncoderRanker
from rebot.rag.rankers.llm_ranker import LLMRanker

logger = logging.getLogger(__name__)


RAG_PROMPT_TEMPLATE = """Answer the question based on the following context.
If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {question}

Answer:"""


@dataclass
class RAGEngine:
    """RAG引擎，整合检索、排序和生成。
    
    Features:
    - 多种检索器支持
    - 可选的重排序
    - LLM生成
    - 上下文管理
    """
    
    config: RAGConfig = field(default_factory=RAGConfig)
    
    # 组件
    retriever: Optional[BaseRetriever] = None
    ranker: Optional[BaseRanker] = None
    
    # LLM
    llm: Any = None
    llm_invoke: Optional[Callable[[str], str]] = None
    
    # 嵌入函数
    embedding_fn: Optional[EmbeddingFunction] = None
    
    # 缓存
    _retrieval_cache: Dict[str, RetrievalResult] = field(default_factory=dict)
    use_cache: bool = True
    
    def __post_init__(self):
        self._setup_retriever()
        self._setup_ranker()
    
    def _setup_retriever(self) -> None:
        """设置检索器。"""
        if self.retriever is not None:
            return
        
        retriever_type = self.config.retriever_type
        
        if retriever_type == RetrieverType.FAISS:
            self.retriever = FAISSRetriever(self.config, self.embedding_fn)
        elif retriever_type == RetrieverType.BM25:
            self.retriever = BM25Retriever(self.config)
        elif retriever_type == RetrieverType.HYBRID:
            self.retriever = HybridRetriever(self.config, self.embedding_fn)
        else:
            self.retriever = FAISSRetriever(self.config, self.embedding_fn)
    
    def _setup_ranker(self) -> None:
        """设置排序器。"""
        if self.ranker is not None or self.config.ranker_type is None:
            return
        
        ranker_type = self.config.ranker_type
        
        if ranker_type == RankerType.CROSS_ENCODER:
            self.ranker = CrossEncoderRanker()
        elif ranker_type == RankerType.LLM:
            self.ranker = LLMRanker(llm=self.llm, llm_invoke=self.llm_invoke)
    
    def add_documents(self, documents: List[Document]) -> None:
        """添加文档到索引。"""
        if self.retriever is None:
            self._setup_retriever()
        self.retriever.add_documents(documents)
        logger.info(f"Added {len(documents)} documents to RAG engine")
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]] | None = None
    ) -> None:
        """添加文本到索引。"""
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            documents.append(Document(content=text, metadata=metadata))
        self.add_documents(documents)
    
    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        use_ranker: bool = True
    ) -> RetrievalResult:
        """检索相关文档。"""
        if top_k is None:
            top_k = self.config.retriever_top_k
        
        # 检查缓存
        cache_key = f"{query}_{top_k}_{use_ranker}"
        if self.use_cache and cache_key in self._retrieval_cache:
            return self._retrieval_cache[cache_key]
        
        # 检索
        result = self.retriever.retrieve(query, top_k * 2 if use_ranker else top_k)
        
        # 重排序
        if use_ranker and self.ranker and result.chunks:
            ranked_top_k = self.config.ranker_top_k or top_k
            result.chunks = self.ranker.rank(query, result.chunks, ranked_top_k)
        
        # 缓存
        if self.use_cache:
            self._retrieval_cache[cache_key] = result
        
        return result
    
    def query(
        self,
        question: str,
        top_k: int | None = None,
        prompt_template: str | None = None
    ) -> str:
        """检索并生成回答。"""
        # 检索
        result = self.retrieve(question, top_k)
        
        # 构建上下文
        context = result.to_context(top_k or self.config.ranker_top_k)
        
        # 生成
        template = prompt_template or RAG_PROMPT_TEMPLATE
        prompt = template.format(context=context, question=question)
        
        answer = self._invoke_llm(prompt)
        return answer
    
    def _invoke_llm(self, prompt: str) -> str:
        """调用LLM生成。"""
        if self.llm_invoke:
            return self.llm_invoke(prompt)
        
        if self.llm:
            from rebot.core.messages import Message
            response = self.llm.invoke([Message(role="user", content=prompt)], tools=[])
            return response.content
        
        raise ValueError("No LLM configured for generation")
    
    def clear_cache(self) -> None:
        """清空缓存。"""
        self._retrieval_cache.clear()
    
    def save(self, path: str) -> None:
        """保存索引。"""
        if self.retriever:
            self.retriever.save(path)
    
    def load(self, path: str) -> None:
        """加载索引。"""
        if self.retriever:
            self.retriever.load(path)
    
    def count(self) -> int:
        """返回索引中的文档数量。"""
        return self.retriever.count() if self.retriever else 0


def create_rag_engine(
    retriever_type: str = "faiss",
    embedding_fn: EmbeddingFunction | None = None,
    llm: Any = None,
    config: RAGConfig | None = None
) -> RAGEngine:
    """创建RAG引擎的工厂函数。"""
    if config is None:
        config = RAGConfig(retriever_type=RetrieverType(retriever_type))
    
    return RAGEngine(
        config=config,
        embedding_fn=embedding_fn,
        llm=llm
    )
