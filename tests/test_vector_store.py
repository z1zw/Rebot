"""Tests for rebot.memory.vector_store module."""

from __future__ import annotations

import pytest
import math
from typing import List

from rebot.memory.vector_store import (
    VectorOps,
    DistanceMetric,
    IndexType,
    VectorMeta,
    SearchResult,
)


class TestVectorOps:
    """Test suite for VectorOps class."""

    def test_normalize_vector(self):
        """Test vector normalization."""
        v = [3.0, 4.0]
        normalized = VectorOps.normalize(v)
        
        # Norm should be 1
        norm = math.sqrt(sum(x**2 for x in normalized))
        assert abs(norm - 1.0) < 1e-6

    def test_normalize_zero_vector(self):
        """Test normalizing zero vector."""
        v = [0.0, 0.0, 0.0]
        normalized = VectorOps.normalize(v)
        assert normalized == v

    def test_dot_product(self):
        """Test dot product calculation."""
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        result = VectorOps.dot(a, b)
        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        assert result == 32.0

    def test_dot_product_orthogonal(self):
        """Test dot product of orthogonal vectors."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        result = VectorOps.dot(a, b)
        assert result == 0.0

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        result = VectorOps.cosine(a, b)
        assert abs(result - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal vectors."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        result = VectorOps.cosine(a, b)
        assert abs(result) < 1e-6

    def test_cosine_similarity_opposite(self):
        """Test cosine similarity of opposite vectors."""
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        result = VectorOps.cosine(a, b)
        assert abs(result - (-1.0)) < 1e-6

    def test_euclidean_distance(self):
        """Test Euclidean distance calculation."""
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        result = VectorOps.euclidean(a, b)
        assert abs(result - 5.0) < 1e-6

    def test_euclidean_distance_same_point(self):
        """Test Euclidean distance of same point."""
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        result = VectorOps.euclidean(a, b)
        assert result == 0.0

    def test_manhattan_distance(self):
        """Test Manhattan distance calculation."""
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        result = VectorOps.manhattan(a, b)
        assert result == 7.0

    def test_distance_cosine(self):
        """Test distance with cosine metric."""
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        result = VectorOps.distance(a, b, DistanceMetric.COSINE)
        assert abs(result) < 1e-6  # Same vectors = 0 distance

    def test_distance_euclidean(self):
        """Test distance with Euclidean metric."""
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        result = VectorOps.distance(a, b, DistanceMetric.EUCLIDEAN)
        assert abs(result - 5.0) < 1e-6


class TestDistanceMetric:
    """Test suite for DistanceMetric enum."""

    def test_cosine_value(self):
        """Test COSINE enum value."""
        assert DistanceMetric.COSINE.value == "cosine"

    def test_euclidean_value(self):
        """Test EUCLIDEAN enum value."""
        assert DistanceMetric.EUCLIDEAN.value == "euclidean"

    def test_dot_product_value(self):
        """Test DOT_PRODUCT enum value."""
        assert DistanceMetric.DOT_PRODUCT.value == "dot"

    def test_manhattan_value(self):
        """Test MANHATTAN enum value."""
        assert DistanceMetric.MANHATTAN.value == "manhattan"


class TestIndexType:
    """Test suite for IndexType enum."""

    def test_flat_value(self):
        """Test FLAT enum value."""
        assert IndexType.FLAT.value == "flat"

    def test_hnsw_value(self):
        """Test HNSW enum value."""
        assert IndexType.HNSW.value == "hnsw"

    def test_ivf_value(self):
        """Test IVF enum value."""
        assert IndexType.IVF.value == "ivf"

    def test_pq_value(self):
        """Test PQ enum value."""
        assert IndexType.PQ.value == "pq"

    def test_ivfpq_value(self):
        """Test IVFPQ enum value."""
        assert IndexType.IVFPQ.value == "ivfpq"


class TestVectorMeta:
    """Test suite for VectorMeta class."""

    def test_vector_meta_creation(self):
        """Test VectorMeta can be created."""
        meta = VectorMeta(id="vec_001")
        assert meta.id == "vec_001"
        assert meta.namespace == "default"

    def test_vector_meta_with_metadata(self):
        """Test VectorMeta with custom metadata."""
        meta = VectorMeta(
            id="vec_002",
            metadata={"source": "test", "page": 1},
        )
        assert meta.metadata["source"] == "test"
        assert meta.metadata["page"] == 1

    def test_vector_meta_custom_namespace(self):
        """Test VectorMeta with custom namespace."""
        meta = VectorMeta(id="vec_003", namespace="documents")
        assert meta.namespace == "documents"


class TestSearchResult:
    """Test suite for SearchResult class."""

    def test_search_result_creation(self):
        """Test SearchResult can be created."""
        result = SearchResult(id="vec_001", score=0.95)
        assert result.id == "vec_001"
        assert result.score == 0.95

    def test_search_result_with_vector(self):
        """Test SearchResult with vector."""
        vector = [0.1, 0.2, 0.3]
        result = SearchResult(id="vec_002", score=0.8, vector=vector)
        assert result.vector == vector

    def test_search_result_with_metadata(self):
        """Test SearchResult with metadata."""
        result = SearchResult(
            id="vec_003",
            score=0.75,
            metadata={"title": "Test Document"},
        )
        assert result.metadata["title"] == "Test Document"

    def test_search_result_sorting(self):
        """Test sorting search results by score."""
        results = [
            SearchResult(id="a", score=0.5),
            SearchResult(id="b", score=0.9),
            SearchResult(id="c", score=0.7),
        ]
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        assert sorted_results[0].id == "b"
        assert sorted_results[1].id == "c"
        assert sorted_results[2].id == "a"
