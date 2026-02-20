"""LLM-based ranker."""

from __future__ import annotations

from typing import Any, Callable, List, Optional
import logging
import re

from rebot.rag.rankers.base import BaseRanker
from rebot.rag.schema import Chunk, RankerConfig

logger = logging.getLogger(__name__)


RANKING_PROMPT = """Given a query and a list of documents, rank the documents by relevance.
Return the document indices in order of relevance, most relevant first.

Query: {query}

Documents:
{documents}

Return ONLY a comma-separated list of document indices (0-indexed), e.g.: 2,0,3,1
Most relevant documents should come first.
"""


class LLMRanker(BaseRanker):
    """基于LLM的排序器。
    
    使用LLM理解查询意图并对文档进行排序。
    """
    
    def __init__(
        self,
        config: RankerConfig | None = None,
        llm: Any = None,
        llm_invoke: Callable[[str], str] | None = None
    ):
        super().__init__(config)
        self.llm = llm
        self.llm_invoke = llm_invoke
    
    def _invoke_llm(self, prompt: str) -> str:
        """调用LLM。"""
        if self.llm_invoke:
            return self.llm_invoke(prompt)
        
        if self.llm:
            from rebot.core.messages import Message
            response = self.llm.invoke([Message(role="user", content=prompt)], tools=[])
            return response.content
        
        raise ValueError("No LLM configured")
    
    def rank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int | None = None
    ) -> List[Chunk]:
        """使用LLM重新排序。"""
        if not chunks:
            return []
        
        if top_k is None:
            top_k = self.config.top_k
        
        # 限制文档数量（LLM上下文限制）
        max_docs = min(len(chunks), 10)
        chunks_to_rank = chunks[:max_docs]
        
        # 构建文档列表
        docs_text = "\n\n".join([
            f"[{i}]: {chunk.content[:500]}"
            for i, chunk in enumerate(chunks_to_rank)
        ])
        
        prompt = RANKING_PROMPT.format(query=query, documents=docs_text)
        
        try:
            response = self._invoke_llm(prompt)
            
            # 解析排序结果
            indices = self._parse_ranking(response, len(chunks_to_rank))
            
            # 按排序重组
            ranked = []
            for idx in indices:
                if 0 <= idx < len(chunks_to_rank):
                    chunk = chunks_to_rank[idx]
                    chunk.score = 1.0 - (len(ranked) / len(indices))  # 分数递减
                    ranked.append(chunk)
            
            # 添加未被LLM排序的文档
            ranked_ids = {c.id for c in ranked}
            for chunk in chunks:
                if chunk.id not in ranked_ids:
                    ranked.append(chunk)
            
            return ranked[:top_k]
        
        except Exception as e:
            logger.warning(f"LLM ranking failed: {e}, falling back to original order")
            return chunks[:top_k]
    
    def _parse_ranking(self, response: str, max_idx: int) -> List[int]:
        """解析LLM返回的排序结果。"""
        # 提取数字
        numbers = re.findall(r'\d+', response)
        indices = []
        
        for num_str in numbers:
            idx = int(num_str)
            if 0 <= idx < max_idx and idx not in indices:
                indices.append(idx)
        
        return indices
