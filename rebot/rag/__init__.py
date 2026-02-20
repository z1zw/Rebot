"""RAG (Retrieval Augmented Generation) module for Rebot.

This module provides:
- Retrievers: FAISS, BM25, Chroma, Elasticsearch
- Rankers: LLM-based, Colbert, BGE
- RAG Engine: Combines retrieval and generation
"""

from rebot.rag.base import Retriever
from rebot.rag.schema import (
    Document,
    Chunk,
    RetrievalResult,
    RAGConfig,
    RetrieverType,
    RankerType,
)

__all__ = [
    "Retriever",
    "Document",
    "Chunk",
    "RetrievalResult",
    "RAGConfig",
    "RetrieverType",
    "RankerType",
]
