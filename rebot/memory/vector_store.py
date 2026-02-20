from __future__ import annotations

import asyncio
import hashlib
import heapq
import json
import math
import mmap
import os
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, 
    Optional, Protocol, Sequence, Set, Tuple, TypeVar, Union
)
import logging
from collections import defaultdict
from functools import lru_cache
import random

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot"
    MANHATTAN = "manhattan"


class IndexType(str, Enum):
    FLAT = "flat"
    HNSW = "hnsw"
    IVF = "ivf"
    PQ = "pq"
    IVFPQ = "ivfpq"


@dataclass
class VectorMeta:
    id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    namespace: str = "default"


@dataclass
class SearchResult:
    id: str
    score: float
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorOps:
    @staticmethod
    def normalize(v: List[float]) -> List[float]:
        norm = math.sqrt(sum(x * x for x in v))
        if norm < 1e-10:
            return v
        return [x / norm for x in v]

    @staticmethod
    def dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        dot_prod = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0
        return dot_prod / (norm_a * norm_b)

    @staticmethod
    def euclidean(a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    @staticmethod
    def manhattan(a: List[float], b: List[float]) -> float:
        return sum(abs(x - y) for x, y in zip(a, b))

    @staticmethod
    def distance(a: List[float], b: List[float], metric: DistanceMetric) -> float:
        if metric == DistanceMetric.COSINE:
            return 1.0 - VectorOps.cosine(a, b)
        elif metric == DistanceMetric.EUCLIDEAN:
            return VectorOps.euclidean(a, b)
        elif metric == DistanceMetric.DOT_PRODUCT:
            return -VectorOps.dot(a, b)
        elif metric == DistanceMetric.MANHATTAN:
            return VectorOps.manhattan(a, b)
        return 0.0

    @staticmethod
    def batch_normalize(vectors: List[List[float]]) -> List[List[float]]:
        return [VectorOps.normalize(v) for v in vectors]


class BaseIndex(ABC):
    def __init__(self, dim: int, metric: DistanceMetric = DistanceMetric.COSINE):
        self.dim = dim
        self.metric = metric
        self._size = 0

    @abstractmethod
    def add(self, id: str, vector: List[float]) -> None:
        pass

    @abstractmethod
    def search(self, query: List[float], k: int) -> List[Tuple[str, float]]:
        pass

    @abstractmethod
    def remove(self, id: str) -> bool:
        pass

    @property
    def size(self) -> int:
        return self._size


class FlatIndex(BaseIndex):
    def __init__(self, dim: int, metric: DistanceMetric = DistanceMetric.COSINE):
        super().__init__(dim, metric)
        self._vectors: Dict[str, List[float]] = {}

    def add(self, id: str, vector: List[float]) -> None:
        if self.metric == DistanceMetric.COSINE:
            vector = VectorOps.normalize(vector)
        self._vectors[id] = vector
        self._size = len(self._vectors)

    def search(self, query: List[float], k: int) -> List[Tuple[str, float]]:
        if not self._vectors:
            return []
        if self.metric == DistanceMetric.COSINE:
            query = VectorOps.normalize(query)
        
        scores = []
        for vid, vec in self._vectors.items():
            dist = VectorOps.distance(query, vec, self.metric)
            scores.append((vid, dist))
        
        scores.sort(key=lambda x: x[1])
        return scores[:k]

    def remove(self, id: str) -> bool:
        if id in self._vectors:
            del self._vectors[id]
            self._size = len(self._vectors)
            return True
        return False


class HNSWNode:
    __slots__ = ['id', 'vector', 'neighbors', 'level']
    
    def __init__(self, id: str, vector: List[float], level: int):
        self.id = id
        self.vector = vector
        self.level = level
        self.neighbors: List[List[str]] = [[] for _ in range(level + 1)]


class HNSWIndex(BaseIndex):
    def __init__(
        self,
        dim: int,
        metric: DistanceMetric = DistanceMetric.COSINE,
        M: int = 16,
        ef_construction: int = 200,
        ef_search: int = 50,
        ml: float = 1.0 / math.log(16)
    ):
        super().__init__(dim, metric)
        self.M = M
        self.M_max = M
        self.M_max0 = M * 2
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.ml = ml
        
        self._nodes: Dict[str, HNSWNode] = {}
        self._entry_point: Optional[str] = None
        self._max_level = 0
        self._lock = threading.RLock()

    def _random_level(self) -> int:
        level = 0
        while random.random() < self.ml and level < 32:
            level += 1
        return level

    def _distance(self, a: List[float], b: List[float]) -> float:
        return VectorOps.distance(a, b, self.metric)

    def _search_layer(
        self,
        query: List[float],
        entry_points: Set[str],
        ef: int,
        layer: int
    ) -> List[Tuple[float, str]]:
        visited = set(entry_points)
        candidates = []
        results = []
        
        for ep in entry_points:
            if ep in self._nodes:
                dist = self._distance(query, self._nodes[ep].vector)
                heapq.heappush(candidates, (dist, ep))
                heapq.heappush(results, (-dist, ep))
        
        while candidates:
            dist_c, c = heapq.heappop(candidates)
            
            if results and -results[0][0] < dist_c:
                break
            
            node = self._nodes.get(c)
            if not node or layer >= len(node.neighbors):
                continue
            
            for neighbor_id in node.neighbors[layer]:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                
                neighbor = self._nodes.get(neighbor_id)
                if not neighbor:
                    continue
                
                dist_n = self._distance(query, neighbor.vector)
                
                if len(results) < ef or dist_n < -results[0][0]:
                    heapq.heappush(candidates, (dist_n, neighbor_id))
                    heapq.heappush(results, (-dist_n, neighbor_id))
                    if len(results) > ef:
                        heapq.heappop(results)
        
        return [(-dist, id) for dist, id in sorted(results, reverse=True)]

    def _select_neighbors(
        self,
        query: List[float],
        candidates: List[Tuple[float, str]],
        M: int
    ) -> List[str]:
        return [id for _, id in sorted(candidates)[:M]]

    def add(self, id: str, vector: List[float]) -> None:
        with self._lock:
            if id in self._nodes:
                self.remove(id)
            
            if self.metric == DistanceMetric.COSINE:
                vector = VectorOps.normalize(vector)
            
            level = self._random_level()
            node = HNSWNode(id, vector, level)
            self._nodes[id] = node
            self._size = len(self._nodes)
            
            if self._entry_point is None:
                self._entry_point = id
                self._max_level = level
                return
            
            ep = {self._entry_point}
            
            for lc in range(self._max_level, level, -1):
                candidates = self._search_layer(vector, ep, 1, lc)
                if candidates:
                    ep = {candidates[0][1]}
            
            for lc in range(min(level, self._max_level), -1, -1):
                candidates = self._search_layer(vector, ep, self.ef_construction, lc)
                
                M_level = self.M_max0 if lc == 0 else self.M_max
                neighbors = self._select_neighbors(vector, candidates, M_level)
                node.neighbors[lc] = neighbors
                
                for neighbor_id in neighbors:
                    neighbor = self._nodes.get(neighbor_id)
                    if neighbor and lc < len(neighbor.neighbors):
                        neighbor.neighbors[lc].append(id)
                        if len(neighbor.neighbors[lc]) > M_level:
                            dist_list = [
                                (self._distance(neighbor.vector, self._nodes[n].vector), n)
                                for n in neighbor.neighbors[lc]
                                if n in self._nodes
                            ]
                            neighbor.neighbors[lc] = self._select_neighbors(
                                neighbor.vector, dist_list, M_level
                            )
                
                ep = {n for _, n in candidates[:self.ef_construction]}
            
            if level > self._max_level:
                self._max_level = level
                self._entry_point = id

    def search(self, query: List[float], k: int) -> List[Tuple[str, float]]:
        with self._lock:
            if not self._nodes or not self._entry_point:
                return []
            
            if self.metric == DistanceMetric.COSINE:
                query = VectorOps.normalize(query)
            
            ep = {self._entry_point}
            
            for lc in range(self._max_level, 0, -1):
                candidates = self._search_layer(query, ep, 1, lc)
                if candidates:
                    ep = {candidates[0][1]}
            
            candidates = self._search_layer(query, ep, max(self.ef_search, k), 0)
            
            return [(id, dist) for dist, id in candidates[:k]]

    def remove(self, id: str) -> bool:
        with self._lock:
            if id not in self._nodes:
                return False
            
            node = self._nodes[id]
            
            for level, neighbors in enumerate(node.neighbors):
                for neighbor_id in neighbors:
                    neighbor = self._nodes.get(neighbor_id)
                    if neighbor and level < len(neighbor.neighbors):
                        neighbor.neighbors[level] = [
                            n for n in neighbor.neighbors[level] if n != id
                        ]
            
            del self._nodes[id]
            self._size = len(self._nodes)
            
            if id == self._entry_point:
                if self._nodes:
                    self._entry_point = next(iter(self._nodes))
                    self._max_level = self._nodes[self._entry_point].level
                else:
                    self._entry_point = None
                    self._max_level = 0
            
            return True


class ProductQuantizer:
    def __init__(self, dim: int, n_subvectors: int = 8, n_bits: int = 8):
        self.dim = dim
        self.n_subvectors = n_subvectors
        self.n_bits = n_bits
        self.n_centroids = 2 ** n_bits
        self.subvector_dim = dim // n_subvectors
        
        self.centroids: Optional[List[List[List[float]]]] = None
        self._trained = False

    def train(self, vectors: List[List[float]], n_iter: int = 20) -> None:
        if not vectors:
            return
        
        self.centroids = []
        
        for m in range(self.n_subvectors):
            start = m * self.subvector_dim
            end = start + self.subvector_dim
            subvecs = [v[start:end] for v in vectors]
            
            centroids = self._kmeans(subvecs, self.n_centroids, n_iter)
            self.centroids.append(centroids)
        
        self._trained = True

    def _kmeans(
        self,
        vectors: List[List[float]],
        k: int,
        n_iter: int
    ) -> List[List[float]]:
        if len(vectors) <= k:
            return vectors + [[0.0] * len(vectors[0]) for _ in range(k - len(vectors))]
        
        indices = random.sample(range(len(vectors)), k)
        centroids = [vectors[i][:] for i in indices]
        
        for _ in range(n_iter):
            assignments = [[] for _ in range(k)]
            
            for vec in vectors:
                min_dist = float('inf')
                min_idx = 0
                for i, c in enumerate(centroids):
                    dist = sum((a - b) ** 2 for a, b in zip(vec, c))
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = i
                assignments[min_idx].append(vec)
            
            for i, cluster in enumerate(assignments):
                if cluster:
                    dim = len(cluster[0])
                    centroids[i] = [
                        sum(v[d] for v in cluster) / len(cluster)
                        for d in range(dim)
                    ]
        
        return centroids

    def encode(self, vector: List[float]) -> bytes:
        if not self._trained or not self.centroids:
            raise RuntimeError("PQ not trained")
        
        codes = []
        for m in range(self.n_subvectors):
            start = m * self.subvector_dim
            end = start + self.subvector_dim
            subvec = vector[start:end]
            
            min_dist = float('inf')
            min_idx = 0
            for i, c in enumerate(self.centroids[m]):
                dist = sum((a - b) ** 2 for a, b in zip(subvec, c))
                if dist < min_dist:
                    min_dist = dist
                    min_idx = i
            codes.append(min_idx)
        
        return bytes(codes)

    def decode(self, codes: bytes) -> List[float]:
        if not self._trained or not self.centroids:
            raise RuntimeError("PQ not trained")
        
        vector = []
        for m, code in enumerate(codes):
            vector.extend(self.centroids[m][code])
        return vector

    def asymmetric_distance(
        self,
        query: List[float],
        codes: bytes
    ) -> float:
        if not self._trained or not self.centroids:
            return float('inf')
        
        distance = 0.0
        for m, code in enumerate(codes):
            start = m * self.subvector_dim
            end = start + self.subvector_dim
            query_sub = query[start:end]
            centroid = self.centroids[m][code]
            distance += sum((a - b) ** 2 for a, b in zip(query_sub, centroid))
        return math.sqrt(distance)


class PQIndex(BaseIndex):
    def __init__(
        self,
        dim: int,
        metric: DistanceMetric = DistanceMetric.EUCLIDEAN,
        n_subvectors: int = 8,
        n_bits: int = 8,
        train_size: int = 10000
    ):
        super().__init__(dim, metric)
        self.pq = ProductQuantizer(dim, n_subvectors, n_bits)
        self.train_size = train_size
        
        self._codes: Dict[str, bytes] = {}
        self._training_buffer: List[List[float]] = []
        self._trained = False

    def add(self, id: str, vector: List[float]) -> None:
        if not self._trained:
            self._training_buffer.append(vector)
            if len(self._training_buffer) >= self.train_size:
                self.pq.train(self._training_buffer)
                self._trained = True
                for i, v in enumerate(self._training_buffer):
                    self._codes[f"_train_{i}"] = self.pq.encode(v)
                self._training_buffer = []
            else:
                return
        
        self._codes[id] = self.pq.encode(vector)
        self._size = len(self._codes)

    def search(self, query: List[float], k: int) -> List[Tuple[str, float]]:
        if not self._trained:
            return []
        
        scores = []
        for vid, codes in self._codes.items():
            dist = self.pq.asymmetric_distance(query, codes)
            scores.append((vid, dist))
        
        scores.sort(key=lambda x: x[1])
        return scores[:k]

    def remove(self, id: str) -> bool:
        if id in self._codes:
            del self._codes[id]
            self._size = len(self._codes)
            return True
        return False


class IVFIndex(BaseIndex):
    def __init__(
        self,
        dim: int,
        metric: DistanceMetric = DistanceMetric.COSINE,
        n_lists: int = 100,
        n_probe: int = 10
    ):
        super().__init__(dim, metric)
        self.n_lists = n_lists
        self.n_probe = n_probe
        
        self._centroids: List[List[float]] = []
        self._lists: List[Dict[str, List[float]]] = [
            {} for _ in range(n_lists)
        ]
        self._id_to_list: Dict[str, int] = {}
        self._trained = False

    def train(self, vectors: List[List[float]], n_iter: int = 20) -> None:
        if len(vectors) < self.n_lists:
            self._centroids = vectors[:] + [
                [0.0] * self.dim for _ in range(self.n_lists - len(vectors))
            ]
        else:
            indices = random.sample(range(len(vectors)), self.n_lists)
            self._centroids = [vectors[i][:] for i in indices]
            
            for _ in range(n_iter):
                assignments = [[] for _ in range(self.n_lists)]
                
                for vec in vectors:
                    min_dist = float('inf')
                    min_idx = 0
                    for i, c in enumerate(self._centroids):
                        dist = VectorOps.distance(vec, c, self.metric)
                        if dist < min_dist:
                            min_dist = dist
                            min_idx = i
                    assignments[min_idx].append(vec)
                
                for i, cluster in enumerate(assignments):
                    if cluster:
                        dim = self.dim
                        self._centroids[i] = [
                            sum(v[d] for v in cluster) / len(cluster)
                            for d in range(dim)
                        ]
        
        self._trained = True

    def _find_list(self, vector: List[float]) -> int:
        if not self._trained:
            return 0
        
        min_dist = float('inf')
        min_idx = 0
        for i, c in enumerate(self._centroids):
            dist = VectorOps.distance(vector, c, self.metric)
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        return min_idx

    def add(self, id: str, vector: List[float]) -> None:
        if not self._trained:
            self._lists[0][id] = vector
            self._id_to_list[id] = 0
        else:
            list_idx = self._find_list(vector)
            self._lists[list_idx][id] = vector
            self._id_to_list[id] = list_idx
        
        self._size = sum(len(lst) for lst in self._lists)

    def search(self, query: List[float], k: int) -> List[Tuple[str, float]]:
        if not self._trained:
            candidates = []
            for lst in self._lists:
                for vid, vec in lst.items():
                    dist = VectorOps.distance(query, vec, self.metric)
                    candidates.append((vid, dist))
            candidates.sort(key=lambda x: x[1])
            return candidates[:k]
        
        list_dists = []
        for i, c in enumerate(self._centroids):
            dist = VectorOps.distance(query, c, self.metric)
            list_dists.append((i, dist))
        
        list_dists.sort(key=lambda x: x[1])
        probe_lists = [idx for idx, _ in list_dists[:self.n_probe]]
        
        candidates = []
        for list_idx in probe_lists:
            for vid, vec in self._lists[list_idx].items():
                dist = VectorOps.distance(query, vec, self.metric)
                candidates.append((vid, dist))
        
        candidates.sort(key=lambda x: x[1])
        return candidates[:k]

    def remove(self, id: str) -> bool:
        if id not in self._id_to_list:
            return False
        
        list_idx = self._id_to_list[id]
        del self._lists[list_idx][id]
        del self._id_to_list[id]
        self._size = sum(len(lst) for lst in self._lists)
        return True


@dataclass
class VectorStoreConfig:
    dim: int
    index_type: IndexType = IndexType.HNSW
    metric: DistanceMetric = DistanceMetric.COSINE
    persist_path: Optional[str] = None
    
    hnsw_m: int = 16
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 50
    
    pq_n_subvectors: int = 8
    pq_n_bits: int = 8
    
    ivf_n_lists: int = 100
    ivf_n_probe: int = 10


class OptimizedVectorStore:
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self._index = self._create_index()
        self._metadata: Dict[str, VectorMeta] = {}
        self._vectors: Dict[str, List[float]] = {}
        self._namespaces: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def _create_index(self) -> BaseIndex:
        if self.config.index_type == IndexType.FLAT:
            return FlatIndex(self.config.dim, self.config.metric)
        elif self.config.index_type == IndexType.HNSW:
            return HNSWIndex(
                self.config.dim,
                self.config.metric,
                M=self.config.hnsw_m,
                ef_construction=self.config.hnsw_ef_construction,
                ef_search=self.config.hnsw_ef_search
            )
        elif self.config.index_type == IndexType.PQ:
            return PQIndex(
                self.config.dim,
                self.config.metric,
                n_subvectors=self.config.pq_n_subvectors,
                n_bits=self.config.pq_n_bits
            )
        elif self.config.index_type == IndexType.IVF:
            return IVFIndex(
                self.config.dim,
                self.config.metric,
                n_lists=self.config.ivf_n_lists,
                n_probe=self.config.ivf_n_probe
            )
        else:
            return FlatIndex(self.config.dim, self.config.metric)

    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> None:
        with self._lock:
            self._index.add(id, vector)
            self._vectors[id] = vector
            self._metadata[id] = VectorMeta(
                id=id,
                metadata=metadata or {},
                namespace=namespace
            )
            self._namespaces[namespace].add(id)

    def add_batch(
        self,
        ids: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default"
    ) -> None:
        if metadatas is None:
            metadatas = [{}] * len(ids)
        
        with self._lock:
            for id, vec, meta in zip(ids, vectors, metadatas):
                self._index.add(id, vec)
                self._vectors[id] = vec
                self._metadata[id] = VectorMeta(
                    id=id,
                    metadata=meta,
                    namespace=namespace
                )
                self._namespaces[namespace].add(id)

    def search(
        self,
        query: List[float],
        k: int = 10,
        namespace: Optional[str] = None,
        filter_fn: Optional[Callable[[VectorMeta], bool]] = None,
        include_vectors: bool = False
    ) -> List[SearchResult]:
        with self._lock:
            results = self._index.search(query, k * 3 if filter_fn or namespace else k)
            
            search_results = []
            for vid, score in results:
                meta = self._metadata.get(vid)
                if not meta:
                    continue
                
                if namespace and meta.namespace != namespace:
                    continue
                
                if filter_fn and not filter_fn(meta):
                    continue
                
                result = SearchResult(
                    id=vid,
                    score=1.0 - score if self.config.metric == DistanceMetric.COSINE else -score,
                    vector=self._vectors.get(vid) if include_vectors else None,
                    metadata=meta.metadata
                )
                search_results.append(result)
                
                if len(search_results) >= k:
                    break
            
            return search_results

    def get(self, id: str) -> Optional[Tuple[List[float], VectorMeta]]:
        with self._lock:
            if id not in self._vectors:
                return None
            return self._vectors[id], self._metadata[id]

    def delete(self, id: str) -> bool:
        with self._lock:
            if id not in self._vectors:
                return False
            
            self._index.remove(id)
            del self._vectors[id]
            meta = self._metadata.pop(id)
            self._namespaces[meta.namespace].discard(id)
            return True

    def delete_namespace(self, namespace: str) -> int:
        with self._lock:
            ids = list(self._namespaces.get(namespace, set()))
            for id in ids:
                self.delete(id)
            return len(ids)

    def save(self, path: Optional[str] = None) -> None:
        save_path = Path(path or self.config.persist_path or "./vectorstore")
        save_path.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "dim": self.config.dim,
            "index_type": self.config.index_type.value,
            "metric": self.config.metric.value,
            "size": len(self._vectors)
        }
        (save_path / "config.json").write_text(json.dumps(config_data))
        
        metadata_data = {
            id: {
                "id": m.id,
                "metadata": m.metadata,
                "timestamp": m.timestamp,
                "namespace": m.namespace
            }
            for id, m in self._metadata.items()
        }
        (save_path / "metadata.json").write_text(json.dumps(metadata_data))
        
        with open(save_path / "vectors.bin", "wb") as f:
            for id, vec in self._vectors.items():
                id_bytes = id.encode('utf-8')
                f.write(struct.pack('I', len(id_bytes)))
                f.write(id_bytes)
                f.write(struct.pack('I', len(vec)))
                f.write(struct.pack(f'{len(vec)}f', *vec))

    def load(self, path: Optional[str] = None) -> None:
        load_path = Path(path or self.config.persist_path or "./vectorstore")
        
        if not load_path.exists():
            return
        
        config_path = load_path / "config.json"
        if config_path.exists():
            config_data = json.loads(config_path.read_text())
            self.config.dim = config_data.get("dim", self.config.dim)
        
        metadata_path = load_path / "metadata.json"
        if metadata_path.exists():
            metadata_data = json.loads(metadata_path.read_text())
            for id, m in metadata_data.items():
                self._metadata[id] = VectorMeta(
                    id=m["id"],
                    metadata=m.get("metadata", {}),
                    timestamp=m.get("timestamp", time.time()),
                    namespace=m.get("namespace", "default")
                )
                self._namespaces[m.get("namespace", "default")].add(id)
        
        vectors_path = load_path / "vectors.bin"
        if vectors_path.exists():
            with open(vectors_path, "rb") as f:
                while True:
                    id_len_bytes = f.read(4)
                    if not id_len_bytes:
                        break
                    id_len = struct.unpack('I', id_len_bytes)[0]
                    id = f.read(id_len).decode('utf-8')
                    vec_len = struct.unpack('I', f.read(4))[0]
                    vec = list(struct.unpack(f'{vec_len}f', f.read(vec_len * 4)))
                    self._vectors[id] = vec
                    self._index.add(id, vec)

    @property
    def size(self) -> int:
        return len(self._vectors)


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> List[float]: ...
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
    async def aembed(self, text: str) -> List[float]: ...
    async def aembed_batch(self, texts: List[str]) -> List[List[float]]: ...


class HashEmbedding:
    def __init__(self, dim: int = 256):
        self.dim = dim

    def _tokenize(self, text: str) -> List[str]:
        import re
        return re.findall(r'[a-z0-9_]+', text.lower())

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in self._tokenize(text):
            idx = hash(tok) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    async def aembed(self, text: str) -> List[float]:
        return self.embed(text)

    async def aembed_batch(self, texts: List[str]) -> List[List[float]]:
        return self.embed_batch(texts)


class OpenAIEmbedding:
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        dim: int = 1536
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url
        self.dim = dim
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.Client(timeout=60.0)
            except ImportError:
                self._client = "urllib"
        return self._client

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        client = self._ensure_client()
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {"model": self.model, "input": texts}
        
        if client == "urllib":
            import urllib.request
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode(),
                headers={**headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
        else:
            resp = client.post(url, json=body, headers=headers)
            data = resp.json()
        
        return [item["embedding"] for item in data["data"]]

    async def aembed(self, text: str) -> List[float]:
        return await asyncio.to_thread(self.embed, text)

    async def aembed_batch(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.to_thread(self.embed_batch, texts)


class VectorDB:
    def __init__(
        self,
        dim: int = 256,
        index_type: IndexType = IndexType.HNSW,
        metric: DistanceMetric = DistanceMetric.COSINE,
        embedding_provider: Optional[EmbeddingProvider] = None,
        persist_path: Optional[str] = None
    ):
        self.config = VectorStoreConfig(
            dim=dim,
            index_type=index_type,
            metric=metric,
            persist_path=persist_path
        )
        self.store = OptimizedVectorStore(self.config)
        self.embedding = embedding_provider or HashEmbedding(dim)

    def add_text(
        self,
        id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> None:
        vector = self.embedding.embed(text)
        metadata = metadata or {}
        metadata["_text"] = text
        self.store.add(id, vector, metadata, namespace)

    def add_texts(
        self,
        ids: List[str],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default"
    ) -> None:
        vectors = self.embedding.embed_batch(texts)
        if metadatas is None:
            metadatas = [{}] * len(texts)
        for i, text in enumerate(texts):
            metadatas[i]["_text"] = text
        self.store.add_batch(ids, vectors, metadatas, namespace)

    async def aadd_text(
        self,
        id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> None:
        vector = await self.embedding.aembed(text)
        metadata = metadata or {}
        metadata["_text"] = text
        self.store.add(id, vector, metadata, namespace)

    def search_text(
        self,
        query: str,
        k: int = 10,
        namespace: Optional[str] = None,
        filter_fn: Optional[Callable[[VectorMeta], bool]] = None
    ) -> List[SearchResult]:
        query_vec = self.embedding.embed(query)
        return self.store.search(query_vec, k, namespace, filter_fn)

    async def asearch_text(
        self,
        query: str,
        k: int = 10,
        namespace: Optional[str] = None,
        filter_fn: Optional[Callable[[VectorMeta], bool]] = None
    ) -> List[SearchResult]:
        query_vec = await self.embedding.aembed(query)
        return self.store.search(query_vec, k, namespace, filter_fn)

    def save(self, path: Optional[str] = None) -> None:
        self.store.save(path)

    def load(self, path: Optional[str] = None) -> None:
        self.store.load(path)

    @property
    def size(self) -> int:
        return self.store.size


def create_vector_db(
    dim: int = 256,
    index_type: str = "hnsw",
    metric: str = "cosine",
    embedding: str = "hash",
    persist_path: Optional[str] = None,
    **kwargs
) -> VectorDB:
    embedding_provider: EmbeddingProvider
    if embedding == "openai":
        embedding_provider = OpenAIEmbedding(
            model=kwargs.get("embedding_model", "text-embedding-3-small"),
            api_key=kwargs.get("api_key", ""),
            dim=kwargs.get("embedding_dim", 1536)
        )
        dim = kwargs.get("embedding_dim", 1536)
    else:
        embedding_provider = HashEmbedding(dim)
    
    return VectorDB(
        dim=dim,
        index_type=IndexType(index_type),
        metric=DistanceMetric(metric),
        embedding_provider=embedding_provider,
        persist_path=persist_path
    )
