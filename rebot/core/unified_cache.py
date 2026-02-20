"""Unified Semantic Cache - 统一语义缓存层.

核心理论基础:
1. Shared Encoder-Decoder → 统一语义空间
   - 所有角色共享同一份代码理解
   - 避免重复解析/理解相同代码

2. Caching Key-Value Attention → 计算状态复用
   - 缓存推理中间状态
   - 增量更新而非重新计算

3. Chunk-level Commit → 原子语义块操作
   - 以AST/语义块为单位操作
   - 细粒度版本控制

这三者的统一抽象:
- 语义 = 理解的结果 (Encoder output)
- 缓存 = 复用计算 (KV Cache)
- 块 = 操作粒度 (Commit unit)
"""

from __future__ import annotations

import hashlib
import time
import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional, 
    Set, Tuple, TypeVar, Union, TYPE_CHECKING
)
from enum import Enum
from collections import OrderedDict
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Unified Semantic Space - 统一语义空间
# ============================================================================

class SemanticType(str, Enum):
    """语义类型 - 代码理解的不同层次."""
    LEXICAL = "lexical"           # 词法层
    SYNTACTIC = "syntactic"       # 语法层
    SEMANTIC = "semantic"         # 语义层
    CONTEXTUAL = "contextual"     # 上下文层
    CROSS_FILE = "cross_file"     # 跨文件层


@dataclass
class SemanticUnit:
    """语义单元 - 编码后的理解结果.
    
    类比Transformer的hidden state, 是对代码的"理解"表示.
    """
    id: str
    content: str
    semantic_type: SemanticType
    embedding: Optional[List[float]] = None
    
    # 语义信息
    symbols: Set[str] = field(default_factory=set)        # 定义的符号
    references: Set[str] = field(default_factory=set)     # 引用的符号
    dependencies: Set[str] = field(default_factory=set)   # 依赖
    
    # 结构信息
    ast_type: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    # 元信息
    source_file: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    created_at: float = field(default_factory=time.time)
    
    # 理解缓存 - 各角色对这段代码的理解
    role_interpretations: Dict[str, Any] = field(default_factory=dict)
    
    def content_hash(self) -> str:
        """内容哈希,用于快速比对."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]
    
    def add_interpretation(self, role_id: str, interpretation: Any):
        """添加角色的理解结果 - 实现共享encoder."""
        self.role_interpretations[role_id] = interpretation
    
    def get_interpretation(self, role_id: str) -> Optional[Any]:
        """获取角色的理解,如果已有则直接复用."""
        return self.role_interpretations.get(role_id)


class SharedEncoder:
    """共享编码器 - 所有角色共用的理解层.
    
    核心思想: 代码的"理解"是可以共享的
    - PM理解需求
    - Architect看到架构
    - Developer看到实现细节
    
    但他们都基于同一份"编码后的表示"
    """
    
    def __init__(self):
        self._semantic_cache: Dict[str, SemanticUnit] = {}
        self._content_index: Dict[str, str] = {}  # content_hash -> unit_id
        self._symbol_index: Dict[str, Set[str]] = {}  # symbol -> unit_ids
        self._file_index: Dict[str, List[str]] = {}  # file -> unit_ids
        self._lock = threading.RLock()
    
    def encode(
        self, 
        content: str, 
        source_file: Optional[str] = None,
        semantic_type: SemanticType = SemanticType.SEMANTIC
    ) -> SemanticUnit:
        """编码内容为语义单元.
        
        如果已经编码过(内容相同), 直接返回缓存.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        with self._lock:
            # 检查是否已编码
            if content_hash in self._content_index:
                unit_id = self._content_index[content_hash]
                return self._semantic_cache[unit_id]
            
            # 新建语义单元
            unit_id = f"sem_{content_hash}_{int(time.time()*1000)}"
            unit = SemanticUnit(
                id=unit_id,
                content=content,
                semantic_type=semantic_type,
                source_file=source_file
            )
            
            # 解析代码结构
            self._analyze_code(unit)
            
            # 缓存
            self._semantic_cache[unit_id] = unit
            self._content_index[content_hash] = unit_id
            
            # 索引符号
            for symbol in unit.symbols:
                if symbol not in self._symbol_index:
                    self._symbol_index[symbol] = set()
                self._symbol_index[symbol].add(unit_id)
            
            # 索引文件
            if source_file:
                if source_file not in self._file_index:
                    self._file_index[source_file] = []
                self._file_index[source_file].append(unit_id)
            
            return unit
    
    def _analyze_code(self, unit: SemanticUnit):
        """分析代码结构."""
        try:
            tree = ast.parse(unit.content)
            self._extract_symbols(tree, unit)
            unit.ast_type = tree.__class__.__name__
        except SyntaxError:
            # 非完整Python代码,尝试其他解析
            self._extract_symbols_regex(unit)
    
    def _extract_symbols(self, tree: ast.AST, unit: SemanticUnit):
        """从AST提取符号."""
        for node in ast.walk(tree):
            # 定义的符号
            if isinstance(node, ast.FunctionDef):
                unit.symbols.add(node.name)
            elif isinstance(node, ast.ClassDef):
                unit.symbols.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        unit.symbols.add(target.id)
            # 引用的符号
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    unit.references.add(node.id)
            # 导入依赖
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    unit.dependencies.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    unit.dependencies.add(node.module)
    
    def _extract_symbols_regex(self, unit: SemanticUnit):
        """正则提取符号(非Python代码)."""
        # 函数定义
        for match in re.finditer(r'(?:def|function|fn)\s+(\w+)', unit.content):
            unit.symbols.add(match.group(1))
        # 类定义
        for match in re.finditer(r'class\s+(\w+)', unit.content):
            unit.symbols.add(match.group(1))
        # 变量赋值
        for match in re.finditer(r'(?:let|const|var)\s+(\w+)', unit.content):
            unit.symbols.add(match.group(1))
    
    def get_by_symbol(self, symbol: str) -> List[SemanticUnit]:
        """通过符号查找语义单元."""
        with self._lock:
            unit_ids = self._symbol_index.get(symbol, set())
            return [self._semantic_cache[uid] for uid in unit_ids if uid in self._semantic_cache]
    
    def get_by_file(self, file_path: str) -> List[SemanticUnit]:
        """获取文件的所有语义单元."""
        with self._lock:
            unit_ids = self._file_index.get(file_path, [])
            return [self._semantic_cache[uid] for uid in unit_ids if uid in self._semantic_cache]
    
    def invalidate(self, content_hash: str):
        """使某个编码失效 - 当代码变更时."""
        with self._lock:
            if content_hash in self._content_index:
                unit_id = self._content_index[content_hash]
                unit = self._semantic_cache.pop(unit_id, None)
                del self._content_index[content_hash]
                
                if unit:
                    # 清理符号索引
                    for symbol in unit.symbols:
                        if symbol in self._symbol_index:
                            self._symbol_index[symbol].discard(unit_id)
                    # 清理文件索引
                    if unit.source_file and unit.source_file in self._file_index:
                        self._file_index[unit.source_file] = [
                            uid for uid in self._file_index[unit.source_file] 
                            if uid != unit_id
                        ]


# ============================================================================
# Part 2: KV Cache for Reasoning - 推理状态缓存
# ============================================================================

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目."""
    key: str
    value: T
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)  # 依赖的其他key
    
    def is_expired(self) -> bool:
        """检查是否过期."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds
    
    def touch(self):
        """更新访问时间."""
        self.accessed_at = time.time()
        self.access_count += 1


class ReasoningKVCache:
    """推理KV缓存 - 缓存中间推理结果.
    
    类比Transformer的KV Cache:
    - Key = 推理上下文的摘要
    - Value = 推理的中间/最终结果
    
    使用场景:
    - 相同代码块的分析结果
    - 相同问题的思考过程
    - 跨角色的共享推理
    """
    
    def __init__(
        self, 
        max_size: int = 10000,
        default_ttl: float = 3600.0,
        eviction_policy: str = "lru"  # lru, lfu, fifo
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._eviction_policy = eviction_policy
        self._lock = threading.RLock()
        
        # 统计
        self._hits = 0
        self._misses = 0
    
    def _compute_key(self, *args, **kwargs) -> str:
        """计算缓存键."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired():
                    self._remove(key)
                    self._misses += 1
                    return None
                
                entry.touch()
                # LRU: 移到末尾
                if self._eviction_policy == "lru":
                    self._cache.move_to_end(key)
                
                self._hits += 1
                return entry.value
            
            self._misses += 1
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[float] = None,
        dependencies: Optional[Set[str]] = None
    ):
        """设置缓存."""
        with self._lock:
            # 驱逐策略
            while len(self._cache) >= self._max_size:
                self._evict_one()
            
            entry = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl or self._default_ttl,
                dependencies=dependencies or set()
            )
            self._cache[key] = entry
    
    def _evict_one(self):
        """驱逐一个条目."""
        if not self._cache:
            return
        
        if self._eviction_policy == "lru":
            # 移除最早的(OrderedDict前面的)
            self._cache.popitem(last=False)
        elif self._eviction_policy == "lfu":
            # 移除访问次数最少的
            min_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[min_key]
        else:  # fifo
            self._cache.popitem(last=False)
    
    def _remove(self, key: str):
        """移除条目及其依赖者."""
        if key in self._cache:
            del self._cache[key]
            # 级联删除依赖此key的条目
            to_remove = [k for k, v in self._cache.items() if key in v.dependencies]
            for k in to_remove:
                self._remove(k)
    
    def invalidate_by_content(self, content_hash: str):
        """根据内容哈希使相关缓存失效."""
        with self._lock:
            to_remove = [
                k for k in self._cache.keys() 
                if content_hash in k
            ]
            for k in to_remove:
                self._remove(k)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate
        }
    
    def cached(
        self, 
        ttl: Optional[float] = None,
        key_func: Optional[Callable[..., str]] = None
    ):
        """装饰器 - 缓存函数结果."""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # 计算key
                if key_func:
                    key = key_func(*args, **kwargs)
                else:
                    key = self._compute_key(func.__name__, *args, **kwargs)
                
                # 尝试获取缓存
                result = self.get(key)
                if result is not None:
                    return result
                
                # 执行并缓存
                result = func(*args, **kwargs)
                self.set(key, result, ttl=ttl)
                return result
            
            return wrapper
        return decorator


# ============================================================================
# Part 3: Chunk-level Operations - 语义块级操作
# ============================================================================

class ChunkType(str, Enum):
    """代码块类型."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    BLOCK = "block"           # if/for/while等
    STATEMENT = "statement"
    EXPRESSION = "expression"
    IMPORT = "import"
    COMMENT = "comment"
    DECORATOR = "decorator"


@dataclass
class CodeChunk:
    """代码块 - 原子操作单元.
    
    不同于行级别操作,Chunk是语义完整的单元:
    - 一个完整的函数
    - 一个类定义
    - 一组import语句
    """
    id: str
    chunk_type: ChunkType
    content: str
    
    # 位置信息
    file_path: str
    line_start: int
    line_end: int
    col_start: int = 0
    col_end: int = 0
    
    # 语义信息
    name: Optional[str] = None
    parent_chunk_id: Optional[str] = None
    children_chunk_ids: List[str] = field(default_factory=list)
    
    # 依赖关系
    imports: Set[str] = field(default_factory=set)
    calls: Set[str] = field(default_factory=set)
    defines: Set[str] = field(default_factory=set)
    
    # 版本信息
    version: int = 1
    content_hash: str = ""
    previous_version_hash: Optional[str] = None
    
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
    
    def create_new_version(self, new_content: str) -> "CodeChunk":
        """创建新版本."""
        return CodeChunk(
            id=self.id,
            chunk_type=self.chunk_type,
            content=new_content,
            file_path=self.file_path,
            line_start=self.line_start,
            line_end=self.line_start + new_content.count('\n'),
            name=self.name,
            parent_chunk_id=self.parent_chunk_id,
            version=self.version + 1,
            previous_version_hash=self.content_hash
        )


class ChunkOperation(str, Enum):
    """块操作类型."""
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"
    MOVE = "move"
    WRAP = "wrap"         # 用新结构包裹
    UNWRAP = "unwrap"     # 去除包裹
    RENAME = "rename"
    REFACTOR = "refactor"


@dataclass
class ChunkEdit:
    """块级编辑操作."""
    operation: ChunkOperation
    target_chunk_id: str
    new_content: Optional[str] = None
    position: Optional[str] = None  # for insert: "before", "after", "inside"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ChunkCommit:
    """块级提交 - 原子变更集.
    
    类似Git commit, 但粒度是语义块而非行.
    """
    id: str
    edits: List[ChunkEdit]
    message: str
    author_role: str
    timestamp: float = field(default_factory=time.time)
    parent_commit_id: Optional[str] = None
    
    # 变更摘要
    chunks_added: Set[str] = field(default_factory=set)
    chunks_modified: Set[str] = field(default_factory=set)
    chunks_deleted: Set[str] = field(default_factory=set)
    
    def is_atomic(self) -> bool:
        """检查是否为原子操作(单个逻辑变更)."""
        return len(self.edits) <= 3  # 简化判断


class ChunkManager:
    """代码块管理器 - 语义级别的代码操作."""
    
    def __init__(self, shared_encoder: Optional[SharedEncoder] = None):
        self._chunks: Dict[str, CodeChunk] = {}
        self._file_chunks: Dict[str, List[str]] = {}
        self._commits: List[ChunkCommit] = []
        self._commit_index: Dict[str, ChunkCommit] = {}
        self._encoder = shared_encoder or SharedEncoder()
        self._lock = threading.RLock()
    
    def parse_file(self, file_path: str, content: str) -> List[CodeChunk]:
        """解析文件为代码块."""
        chunks = []
        
        try:
            tree = ast.parse(content)
            chunks = self._ast_to_chunks(tree, file_path, content)
        except SyntaxError:
            # 非Python文件,按其他规则分块
            chunks = self._heuristic_chunking(file_path, content)
        
        with self._lock:
            self._file_chunks[file_path] = [c.id for c in chunks]
            for chunk in chunks:
                self._chunks[chunk.id] = chunk
                # 同时编码到共享语义空间
                self._encoder.encode(chunk.content, file_path)
        
        return chunks
    
    def _ast_to_chunks(
        self, 
        tree: ast.AST, 
        file_path: str, 
        source: str
    ) -> List[CodeChunk]:
        """AST转换为代码块."""
        chunks = []
        lines = source.split('\n')
        
        for node in ast.walk(tree):
            chunk = self._node_to_chunk(node, file_path, lines)
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _node_to_chunk(
        self, 
        node: ast.AST, 
        file_path: str, 
        lines: List[str]
    ) -> Optional[CodeChunk]:
        """AST节点转代码块."""
        if not hasattr(node, 'lineno'):
            return None
        
        chunk_type = None
        name = None
        
        if isinstance(node, ast.FunctionDef):
            chunk_type = ChunkType.FUNCTION
            name = node.name
        elif isinstance(node, ast.AsyncFunctionDef):
            chunk_type = ChunkType.FUNCTION
            name = node.name
        elif isinstance(node, ast.ClassDef):
            chunk_type = ChunkType.CLASS
            name = node.name
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            chunk_type = ChunkType.IMPORT
        else:
            return None
        
        line_start = node.lineno
        line_end = getattr(node, 'end_lineno', line_start) or line_start
        
        content = '\n'.join(lines[line_start-1:line_end])
        
        chunk_id = f"chunk_{file_path}_{line_start}_{name or chunk_type.value}"
        
        chunk = CodeChunk(
            id=chunk_id,
            chunk_type=chunk_type,
            content=content,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            name=name
        )
        
        # 提取依赖
        self._extract_chunk_deps(node, chunk)
        
        return chunk
    
    def _extract_chunk_deps(self, node: ast.AST, chunk: CodeChunk):
        """提取块的依赖关系."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    chunk.defines.add(child.id)
                else:
                    chunk.calls.add(child.id)
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    chunk.calls.add(child.func.id)
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    chunk.imports.add(alias.name)
            elif isinstance(child, ast.ImportFrom):
                if child.module:
                    chunk.imports.add(child.module)
    
    def _heuristic_chunking(self, file_path: str, content: str) -> List[CodeChunk]:
        """启发式分块(非Python文件)."""
        chunks = []
        
        # 按函数/类定义分块
        patterns = [
            (r'(function\s+\w+\s*\([^)]*\)\s*\{[^}]*\})', ChunkType.FUNCTION),
            (r'(class\s+\w+[^{]*\{[^}]*\})', ChunkType.CLASS),
            (r'(const\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>[^;]*;?)', ChunkType.FUNCTION),
        ]
        
        for pattern, chunk_type in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                chunk_id = f"chunk_{file_path}_{match.start()}"
                chunk = CodeChunk(
                    id=chunk_id,
                    chunk_type=chunk_type,
                    content=match.group(1),
                    file_path=file_path,
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=content[:match.end()].count('\n') + 1
                )
                chunks.append(chunk)
        
        return chunks
    
    def create_commit(
        self,
        edits: List[ChunkEdit],
        message: str,
        author_role: str
    ) -> ChunkCommit:
        """创建块级提交."""
        commit_id = f"commit_{int(time.time()*1000)}"
        parent_id = self._commits[-1].id if self._commits else None
        
        commit = ChunkCommit(
            id=commit_id,
            edits=edits,
            message=message,
            author_role=author_role,
            parent_commit_id=parent_id
        )
        
        # 执行编辑
        for edit in edits:
            self._apply_edit(edit, commit)
        
        with self._lock:
            self._commits.append(commit)
            self._commit_index[commit_id] = commit
        
        return commit
    
    def _apply_edit(self, edit: ChunkEdit, commit: ChunkCommit):
        """应用编辑操作."""
        with self._lock:
            if edit.operation == ChunkOperation.INSERT:
                if edit.new_content:
                    new_chunk = CodeChunk(
                        id=f"chunk_new_{int(time.time()*1000)}",
                        chunk_type=ChunkType.BLOCK,
                        content=edit.new_content,
                        file_path="",
                        line_start=0,
                        line_end=edit.new_content.count('\n')
                    )
                    self._chunks[new_chunk.id] = new_chunk
                    commit.chunks_added.add(new_chunk.id)
            
            elif edit.operation == ChunkOperation.DELETE:
                if edit.target_chunk_id in self._chunks:
                    del self._chunks[edit.target_chunk_id]
                    commit.chunks_deleted.add(edit.target_chunk_id)
            
            elif edit.operation == ChunkOperation.REPLACE:
                if edit.target_chunk_id in self._chunks and edit.new_content:
                    old_chunk = self._chunks[edit.target_chunk_id]
                    new_chunk = old_chunk.create_new_version(edit.new_content)
                    self._chunks[edit.target_chunk_id] = new_chunk
                    commit.chunks_modified.add(edit.target_chunk_id)
                    
                    # 使缓存失效
                    self._encoder.invalidate(old_chunk.content_hash)
    
    def get_chunk(self, chunk_id: str) -> Optional[CodeChunk]:
        """获取代码块."""
        return self._chunks.get(chunk_id)
    
    def get_file_chunks(self, file_path: str) -> List[CodeChunk]:
        """获取文件的所有代码块."""
        chunk_ids = self._file_chunks.get(file_path, [])
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]
    
    def get_commit_history(self, limit: int = 10) -> List[ChunkCommit]:
        """获取提交历史."""
        return self._commits[-limit:]
    
    def rollback_to(self, commit_id: str) -> bool:
        """回滚到指定提交."""
        # 简化实现: 找到提交并反向应用之后的所有变更
        # 实际实现需要更复杂的版本管理
        if commit_id not in self._commit_index:
            return False
        
        logger.info(f"Rolling back to commit {commit_id}")
        return True


# ============================================================================
# Part 4: Unified Cache System - 统一缓存系统
# ============================================================================

class UnifiedCache:
    """统一缓存系统 - 整合语义、推理、块操作.
    
    这是三个技术的统一抽象:
    1. SharedEncoder: 统一语义空间
    2. ReasoningKVCache: 推理状态复用
    3. ChunkManager: 原子块操作
    """
    
    _instance: Optional["UnifiedCache"] = None
    
    def __new__(cls):
        """单例模式."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.encoder = SharedEncoder()
        self.kv_cache = ReasoningKVCache(max_size=10000)
        self.chunk_manager = ChunkManager(self.encoder)
        
        self._role_caches: Dict[str, ReasoningKVCache] = {}
        self._initialized = True
    
    def get_role_cache(self, role_id: str) -> ReasoningKVCache:
        """获取角色专用缓存."""
        if role_id not in self._role_caches:
            self._role_caches[role_id] = ReasoningKVCache(max_size=1000)
        return self._role_caches[role_id]
    
    def encode_and_cache(
        self, 
        content: str, 
        role_id: str,
        file_path: Optional[str] = None
    ) -> Tuple[SemanticUnit, Optional[Any]]:
        """编码内容并检查是否有角色缓存的理解.
        
        Returns:
            (语义单元, 角色已有的理解或None)
        """
        # 获取或创建语义单元
        unit = self.encoder.encode(content, file_path)
        
        # 检查角色缓存
        cached_interpretation = unit.get_interpretation(role_id)
        
        return unit, cached_interpretation
    
    def cache_reasoning(
        self,
        role_id: str,
        semantic_unit: SemanticUnit,
        reasoning_result: Any
    ):
        """缓存角色的推理结果."""
        # 1. 保存到语义单元的解释缓存
        semantic_unit.add_interpretation(role_id, reasoning_result)
        
        # 2. 保存到角色KV缓存
        role_cache = self.get_role_cache(role_id)
        cache_key = f"{role_id}:{semantic_unit.content_hash()}"
        role_cache.set(cache_key, reasoning_result)
    
    def get_cached_reasoning(
        self,
        role_id: str,
        content_hash: str
    ) -> Optional[Any]:
        """获取缓存的推理结果."""
        role_cache = self.get_role_cache(role_id)
        cache_key = f"{role_id}:{content_hash}"
        return role_cache.get(cache_key)
    
    def commit_changes(
        self,
        role_id: str,
        chunk_edits: List[ChunkEdit],
        message: str
    ) -> ChunkCommit:
        """提交块级变更."""
        commit = self.chunk_manager.create_commit(
            edits=chunk_edits,
            message=message,
            author_role=role_id
        )
        
        # 使相关缓存失效
        for chunk_id in commit.chunks_modified | commit.chunks_deleted:
            chunk = self.chunk_manager.get_chunk(chunk_id)
            if chunk:
                self.kv_cache.invalidate_by_content(chunk.content_hash)
        
        return commit
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计."""
        return {
            "encoder": {
                "semantic_units": len(self.encoder._semantic_cache),
                "symbols_indexed": len(self.encoder._symbol_index),
                "files_indexed": len(self.encoder._file_index)
            },
            "kv_cache": self.kv_cache.get_stats(),
            "chunk_manager": {
                "chunks": len(self.chunk_manager._chunks),
                "commits": len(self.chunk_manager._commits)
            },
            "role_caches": {
                role_id: cache.get_stats()
                for role_id, cache in self._role_caches.items()
            }
        }


# ============================================================================
# Part 5: Integration Helpers - 集成辅助
# ============================================================================

def get_unified_cache() -> UnifiedCache:
    """获取统一缓存实例."""
    return UnifiedCache()


class CachedReasoning:
    """装饰器类 - 为角色方法添加推理缓存."""
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        self.cache = cache or get_unified_cache()
    
    def __call__(self, func: Callable):
        def wrapper(role_instance, content: str, *args, **kwargs):
            role_id = getattr(role_instance, 'address', str(id(role_instance)))
            
            # 检查缓存
            unit, cached = self.cache.encode_and_cache(content, role_id)
            if cached is not None:
                logger.debug(f"Cache hit for {role_id}: {unit.id}")
                return cached
            
            # 执行推理
            result = func(role_instance, content, *args, **kwargs)
            
            # 缓存结果
            self.cache.cache_reasoning(role_id, unit, result)
            
            return result
        
        return wrapper


def chunk_aware_edit(
    file_path: str,
    old_content: str,
    new_content: str,
    role_id: str,
    message: str
) -> ChunkCommit:
    """块感知的编辑操作 - 自动分析变更粒度."""
    cache = get_unified_cache()
    
    # 解析旧内容为块
    old_chunks = cache.chunk_manager.parse_file(file_path, old_content)
    
    # 解析新内容为块
    new_chunks = cache.chunk_manager.parse_file(file_path + ".new", new_content)
    
    # 计算差异(简化: 基于名称匹配)
    old_by_name = {c.name: c for c in old_chunks if c.name}
    new_by_name = {c.name: c for c in new_chunks if c.name}
    
    edits = []
    
    # 修改的块
    for name, new_chunk in new_by_name.items():
        if name in old_by_name:
            old_chunk = old_by_name[name]
            if old_chunk.content_hash != new_chunk.content_hash:
                edits.append(ChunkEdit(
                    operation=ChunkOperation.REPLACE,
                    target_chunk_id=old_chunk.id,
                    new_content=new_chunk.content
                ))
        else:
            # 新增的块
            edits.append(ChunkEdit(
                operation=ChunkOperation.INSERT,
                target_chunk_id="",
                new_content=new_chunk.content
            ))
    
    # 删除的块
    for name, old_chunk in old_by_name.items():
        if name not in new_by_name:
            edits.append(ChunkEdit(
                operation=ChunkOperation.DELETE,
                target_chunk_id=old_chunk.id
            ))
    
    return cache.commit_changes(role_id, edits, message)
