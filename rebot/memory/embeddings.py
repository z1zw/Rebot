from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union
import logging
import time

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    COHERE = "cohere"
    VOYAGE = "voyage"
    JINA = "jina"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    BEDROCK = "bedrock"
    GOOGLE = "google"
    DASHSCOPE = "dashscope"
    QIANFAN = "qianfan"
    ZHIPU = "zhipu"
    BAICHUAN = "baichuan"
    FASTEMBED = "fastembed"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    HASH = "hash"


@dataclass
class EmbeddingConfig:
    provider: EmbeddingProvider
    model: str = ""
    api_key: str = ""
    api_key_env: str = ""
    base_url: str = ""
    dim: int = 0
    batch_size: int = 100
    timeout: float = 60.0
    normalize: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 3600

    def resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env, "")
        
        env_map = {
            EmbeddingProvider.OPENAI: "OPENAI_API_KEY",
            EmbeddingProvider.COHERE: "COHERE_API_KEY",
            EmbeddingProvider.VOYAGE: "VOYAGE_API_KEY",
            EmbeddingProvider.JINA: "JINA_API_KEY",
            EmbeddingProvider.HUGGINGFACE: "HUGGINGFACE_API_KEY",
            EmbeddingProvider.DASHSCOPE: "DASHSCOPE_API_KEY",
            EmbeddingProvider.QIANFAN: "QIANFAN_API_KEY",
            EmbeddingProvider.ZHIPU: "ZHIPU_API_KEY",
            EmbeddingProvider.BAICHUAN: "BAICHUAN_API_KEY",
            EmbeddingProvider.GOOGLE: "GOOGLE_API_KEY",
        }
        env = env_map.get(self.provider, "")
        return os.environ.get(env, "") if env else ""

    def resolve_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        
        url_map = {
            EmbeddingProvider.OPENAI: "https://api.openai.com/v1",
            EmbeddingProvider.COHERE: "https://api.cohere.ai/v1",
            EmbeddingProvider.VOYAGE: "https://api.voyageai.com/v1",
            EmbeddingProvider.JINA: "https://api.jina.ai/v1",
            EmbeddingProvider.HUGGINGFACE: "https://api-inference.huggingface.co",
            EmbeddingProvider.DASHSCOPE: "https://dashscope.aliyuncs.com/api/v1",
            EmbeddingProvider.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
            EmbeddingProvider.OLLAMA: "http://localhost:11434",
            EmbeddingProvider.GOOGLE: "https://generativelanguage.googleapis.com/v1beta",
        }
        return url_map.get(self.provider, "")

    def get_default_model(self) -> str:
        if self.model:
            return self.model
        
        model_map = {
            EmbeddingProvider.OPENAI: "text-embedding-3-small",
            EmbeddingProvider.COHERE: "embed-english-v3.0",
            EmbeddingProvider.VOYAGE: "voyage-2",
            EmbeddingProvider.JINA: "jina-embeddings-v2-base-en",
            EmbeddingProvider.GOOGLE: "text-embedding-004",
            EmbeddingProvider.DASHSCOPE: "text-embedding-v2",
            EmbeddingProvider.ZHIPU: "embedding-2",
            EmbeddingProvider.OLLAMA: "nomic-embed-text",
            EmbeddingProvider.SENTENCE_TRANSFORMERS: "all-MiniLM-L6-v2",
        }
        return model_map.get(self.provider, "")


class EmbeddingCache:
    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[List[float], float]] = {}
        self._lock = threading.RLock()

    def _hash_key(self, text: str, model: str) -> str:
        return hashlib.md5(f"{model}:{text}".encode()).hexdigest()

    def get(self, text: str, model: str) -> Optional[List[float]]:
        key = self._hash_key(text, model)
        with self._lock:
            if key in self._cache:
                vec, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return vec
                del self._cache[key]
        return None

    def put(self, text: str, model: str, vector: List[float]) -> None:
        key = self._hash_key(text, model)
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest = min(self._cache.items(), key=lambda x: x[1][1])
                del self._cache[oldest[0]]
            self._cache[key] = (vector, time.time())

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class BaseEmbedder(ABC):
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.cache = EmbeddingCache() if config.cache_enabled else None
        self._http_client = None

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    async def aembed(self, text: str) -> List[float]:
        return await asyncio.to_thread(self.embed, text)

    async def aembed_batch(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.to_thread(self.embed_batch, texts)

    def _normalize(self, vec: List[float]) -> List[float]:
        if not self.config.normalize:
            return vec
        norm = math.sqrt(sum(x * x for x in vec))
        if norm < 1e-10:
            return vec
        return [x / norm for x in vec]

    def _ensure_http_client(self):
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.Client(timeout=self.config.timeout)
            except ImportError:
                self._http_client = "urllib"
        return self._http_client

    def _post_json(self, url: str, data: Dict, headers: Dict) -> Dict:
        client = self._ensure_http_client()
        if client == "urllib":
            import urllib.request
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={**headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode())
        else:
            resp = client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            return resp.json()


class OpenAIEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        if self.cache:
            cached = self.cache.get(text, self.config.model)
            if cached:
                return cached
        
        result = self.embed_batch([text])[0]
        return result

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.config.resolve_base_url()}/embeddings"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        model = self.config.get_default_model()
        
        body: Dict[str, Any] = {
            "model": model,
            "input": texts
        }
        if self.config.dim > 0 and "3" in model:
            body["dimensions"] = self.config.dim
        
        resp = self._post_json(url, body, headers)
        embeddings = [item["embedding"] for item in resp["data"]]
        embeddings = [self._normalize(e) for e in embeddings]
        
        if self.cache:
            for text, vec in zip(texts, embeddings):
                self.cache.put(text, model, vec)
        
        return embeddings


class CohereEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.config.resolve_base_url()}/embed"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        model = self.config.get_default_model()
        
        body = {
            "model": model,
            "texts": texts,
            "input_type": "search_document"
        }
        
        resp = self._post_json(url, body, headers)
        embeddings = resp.get("embeddings", [])
        return [self._normalize(e) for e in embeddings]


class VoyageEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.config.resolve_base_url()}/embeddings"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        model = self.config.get_default_model()
        
        body = {
            "model": model,
            "input": texts
        }
        
        resp = self._post_json(url, body, headers)
        embeddings = [item["embedding"] for item in resp["data"]]
        return [self._normalize(e) for e in embeddings]


class JinaEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.config.resolve_base_url()}/embeddings"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        model = self.config.get_default_model()
        
        body = {
            "model": model,
            "input": texts
        }
        
        resp = self._post_json(url, body, headers)
        embeddings = [item["embedding"] for item in resp["data"]]
        return [self._normalize(e) for e in embeddings]


class GoogleEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        model = self.config.get_default_model()
        api_key = self.config.resolve_api_key()
        base_url = self.config.resolve_base_url()
        
        embeddings = []
        for text in texts:
            url = f"{base_url}/models/{model}:embedContent?key={api_key}"
            body = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]}
            }
            resp = self._post_json(url, body, {})
            vec = resp.get("embedding", {}).get("values", [])
            embeddings.append(self._normalize(vec))
        
        return embeddings


class OllamaEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        base_url = self.config.resolve_base_url()
        model = self.config.get_default_model()
        
        embeddings = []
        for text in texts:
            url = f"{base_url}/api/embeddings"
            body = {"model": model, "prompt": text}
            resp = self._post_json(url, body, {})
            vec = resp.get("embedding", [])
            embeddings.append(self._normalize(vec))
        
        return embeddings


class DashScopeEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.config.resolve_base_url()}/services/embeddings/text-embedding/text-embedding"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        model = self.config.get_default_model()
        
        body = {
            "model": model,
            "input": {"texts": texts},
            "parameters": {"text_type": "document"}
        }
        
        resp = self._post_json(url, body, headers)
        embeddings = [item["embedding"] for item in resp.get("output", {}).get("embeddings", [])]
        return [self._normalize(e) for e in embeddings]


class ZhipuEmbedder(BaseEmbedder):
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.config.resolve_base_url()}/embeddings"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        model = self.config.get_default_model()
        
        embeddings = []
        for text in texts:
            body = {"model": model, "input": text}
            resp = self._post_json(url, body, headers)
            vec = resp.get("data", [{}])[0].get("embedding", [])
            embeddings.append(self._normalize(vec))
        
        return embeddings


class HashEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.dim = config.dim or 256

    def _tokenize(self, text: str) -> List[str]:
        import re
        tokens = re.findall(r'[a-zA-Z0-9_]+', text.lower())
        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
        return tokens + bigrams

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = self._tokenize(text)
        
        for i, tok in enumerate(tokens):
            h = hash(tok)
            idx1 = h % self.dim
            idx2 = (h >> 16) % self.dim
            weight = 1.0 / math.sqrt(i + 1)
            vec[idx1] += weight
            vec[idx2] -= weight * 0.5
        
        return self._normalize(vec)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class LocalTransformerEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._model = None
        self._tokenizer = None

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = self.config.get_default_model()
                self._model = SentenceTransformer(model_name)
            except ImportError:
                raise RuntimeError("sentence-transformers not installed")
        return self._model

    def embed(self, text: str) -> List[float]:
        model = self._ensure_model()
        vec = model.encode(text, normalize_embeddings=self.config.normalize)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        model = self._ensure_model()
        vecs = model.encode(texts, normalize_embeddings=self.config.normalize)
        return [v.tolist() for v in vecs]


EMBEDDER_MAP: Dict[EmbeddingProvider, type] = {
    EmbeddingProvider.OPENAI: OpenAIEmbedder,
    EmbeddingProvider.AZURE: OpenAIEmbedder,
    EmbeddingProvider.COHERE: CohereEmbedder,
    EmbeddingProvider.VOYAGE: VoyageEmbedder,
    EmbeddingProvider.JINA: JinaEmbedder,
    EmbeddingProvider.GOOGLE: GoogleEmbedder,
    EmbeddingProvider.OLLAMA: OllamaEmbedder,
    EmbeddingProvider.DASHSCOPE: DashScopeEmbedder,
    EmbeddingProvider.ZHIPU: ZhipuEmbedder,
    EmbeddingProvider.SENTENCE_TRANSFORMERS: LocalTransformerEmbedder,
    EmbeddingProvider.HASH: HashEmbedder,
}


class UniversalEmbedder:
    def __init__(
        self,
        provider: Union[str, EmbeddingProvider] = EmbeddingProvider.HASH,
        model: str = "",
        api_key: str = "",
        base_url: str = "",
        dim: int = 0,
        **kwargs
    ):
        if isinstance(provider, str):
            provider = EmbeddingProvider(provider.lower())
        
        self.config = EmbeddingConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            dim=dim,
            **{k: v for k, v in kwargs.items() if hasattr(EmbeddingConfig, k)}
        )
        
        embedder_class = EMBEDDER_MAP.get(provider, HashEmbedder)
        self._embedder = embedder_class(self.config)

    def embed(self, text: str) -> List[float]:
        return self._embedder.embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self._embedder.embed_batch(batch)
            all_embeddings.extend(embeddings)
        
        return all_embeddings

    async def aembed(self, text: str) -> List[float]:
        return await self._embedder.aembed(text)

    async def aembed_batch(self, texts: List[str]) -> List[List[float]]:
        return await self._embedder.aembed_batch(texts)

    @property
    def dim(self) -> int:
        return self.config.dim


class EmbeddingRegistry:
    _instances: Dict[str, UniversalEmbedder] = {}
    _lock = threading.RLock()

    @classmethod
    def register(cls, name: str, embedder: UniversalEmbedder) -> None:
        with cls._lock:
            cls._instances[name] = embedder

    @classmethod
    def get(cls, name: str) -> Optional[UniversalEmbedder]:
        return cls._instances.get(name)

    @classmethod
    def create(
        cls,
        name: str,
        provider: Union[str, EmbeddingProvider],
        **kwargs
    ) -> UniversalEmbedder:
        embedder = UniversalEmbedder(provider=provider, **kwargs)
        cls.register(name, embedder)
        return embedder

    @classmethod
    def list_providers(cls) -> List[str]:
        return [p.value for p in EmbeddingProvider]


def create_embedder(
    provider: str = "hash",
    model: str = "",
    api_key: str = "",
    dim: int = 256,
    **kwargs
) -> UniversalEmbedder:
    return UniversalEmbedder(
        provider=provider,
        model=model,
        api_key=api_key,
        dim=dim,
        **kwargs
    )
