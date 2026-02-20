"""Base ranker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from rebot.rag.schema import Chunk, RankerConfig


class BaseRanker(ABC):
    """排序器基类。"""
    
    def __init__(self, config: RankerConfig | None = None):
        self.config = config or RankerConfig()
    
    @abstractmethod
    def rank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int | None = None
    ) -> List[Chunk]:
        """对检索结果重新排序。
        
        Args:
            query: 查询
            chunks: 待排序的分块
            top_k: 返回数量
        
        Returns:
            排序后的分块列表
        """
        ...
    
    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int | None = None
    ) -> List[Chunk]:
        """rerank别名。"""
        return self.rank(query, chunks, top_k)
