"""Cross-encoder based ranker."""

from __future__ import annotations

from typing import List, Optional
import logging

from rebot.rag.rankers.base import BaseRanker
from rebot.rag.schema import Chunk, RankerConfig

logger = logging.getLogger(__name__)


class CrossEncoderRanker(BaseRanker):
    """基于Cross-Encoder的排序器。
    
    使用预训练的cross-encoder模型对query-document对进行评分。
    """
    
    def __init__(
        self,
        config: RankerConfig | None = None,
        model_name: str | None = None
    ):
        super().__init__(config)
        self.model_name = model_name or self.config.model_name
        self.model = None
        self._initialized = False
    
    def _ensure_model(self) -> None:
        """确保模型已加载。"""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            self._initialized = True
            logger.info(f"Loaded cross-encoder model: {self.model_name}")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    
    def rank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int | None = None
    ) -> List[Chunk]:
        """使用cross-encoder重新排序。"""
        if not chunks:
            return []
        
        self._ensure_model()
        
        if top_k is None:
            top_k = self.config.top_k
        
        # 准备输入对
        pairs = [(query, chunk.content) for chunk in chunks]
        
        # 批量评分
        batch_size = self.config.batch_size
        scores = []
        
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            batch_scores = self.model.predict(batch)
            scores.extend(batch_scores)
        
        # 更新分数并排序
        for chunk, score in zip(chunks, scores):
            chunk.score = float(score)
        
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        
        return sorted_chunks[:top_k]
