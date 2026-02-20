"""Incremental Reasoning Engine - 增量推理引擎.

核心理论:
将 Transformer 的 KV Attention Caching 抽象到 Agent 推理层面.

在 Transformer 中:
- KV Cache 让每个新 token 只需计算与已缓存 K/V 的注意力
- 避免重复计算整个序列

在 Agent 推理中:
- 代码变更通常是增量的
- 不需要每次都"从头理解"整个代码库
- 增量更新理解,复用之前的推理结果

实现策略:
1. 推理快照 (Reasoning Snapshot) - 相当于 KV Cache 的一个状态
2. 增量更新 (Delta Update) - 只处理变化的部分
3. 依赖图传播 (Dependency Propagation) - 变化沿依赖图传播
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional, 
    Set, Tuple, TypeVar, Union, Awaitable
)
from enum import Enum
from collections import defaultdict
import threading
import logging

from rebot.core.unified_cache import (
    UnifiedCache, SharedEncoder, SemanticUnit, 
    CodeChunk, ChunkManager, get_unified_cache
)

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Reasoning Snapshot - 推理快照
# ============================================================================

@dataclass
class ReasoningState:
    """推理状态 - 类比 KV Cache 中的一个 token 位置的状态."""
    chunk_id: str
    content_hash: str
    
    # 理解层次
    understanding: Optional[str] = None      # 文本理解
    intent: Optional[str] = None             # 意图分析
    structure: Optional[Dict] = None         # 结构分析
    dependencies: Optional[Set[str]] = None  # 依赖分析
    issues: Optional[List[str]] = None       # 问题分析
    
    # 决策状态
    decisions: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    
    # 元信息
    computed_at: float = field(default_factory=time.time)
    compute_cost_ms: float = 0.0
    
    def is_stale(self, current_hash: str) -> bool:
        """检查是否过期."""
        return self.content_hash != current_hash


@dataclass
class ReasoningSnapshot:
    """推理快照 - 类比整个 KV Cache.
    
    保存对代码库某个状态的完整理解.
    """
    id: str
    role_id: str
    created_at: float = field(default_factory=time.time)
    
    # 状态存储
    states: Dict[str, ReasoningState] = field(default_factory=dict)
    
    # 全局理解
    global_context: Optional[str] = None
    architecture_view: Optional[Dict] = None
    
    # 依赖图
    dependency_graph: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse_deps: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    def get_state(self, chunk_id: str) -> Optional[ReasoningState]:
        """获取某个块的推理状态."""
        return self.states.get(chunk_id)
    
    def set_state(self, chunk_id: str, state: ReasoningState):
        """设置块的推理状态."""
        self.states[chunk_id] = state
    
    def invalidate(self, chunk_id: str) -> Set[str]:
        """使某个块的状态失效,并返回所有受影响的块."""
        affected = {chunk_id}
        
        # BFS遍历依赖图,找到所有受影响的块
        queue = [chunk_id]
        while queue:
            current = queue.pop(0)
            for dep in self.reverse_deps.get(current, set()):
                if dep not in affected:
                    affected.add(dep)
                    queue.append(dep)
        
        # 移除失效状态
        for chunk in affected:
            self.states.pop(chunk, None)
        
        return affected
    
    def add_dependency(self, from_chunk: str, to_chunk: str):
        """添加依赖关系: from_chunk 依赖 to_chunk."""
        self.dependency_graph[from_chunk].add(to_chunk)
        self.reverse_deps[to_chunk].add(from_chunk)
    
    def get_affected_by_change(self, changed_chunks: Set[str]) -> Set[str]:
        """获取受变更影响的所有块."""
        affected = set()
        for chunk in changed_chunks:
            affected.update(self.invalidate(chunk))
        return affected
    
    def clone(self) -> "ReasoningSnapshot":
        """克隆快照."""
        new_snapshot = ReasoningSnapshot(
            id=f"{self.id}_clone_{int(time.time()*1000)}",
            role_id=self.role_id,
            global_context=self.global_context,
            architecture_view=copy.deepcopy(self.architecture_view)
        )
        new_snapshot.states = copy.deepcopy(self.states)
        new_snapshot.dependency_graph = copy.deepcopy(self.dependency_graph)
        new_snapshot.reverse_deps = copy.deepcopy(self.reverse_deps)
        return new_snapshot


# ============================================================================
# Part 2: Delta Processing - 增量处理
# ============================================================================

class DeltaType(str, Enum):
    """变更类型."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    MOVED = "moved"


@dataclass
class CodeDelta:
    """代码变更描述."""
    delta_type: DeltaType
    chunk_id: str
    file_path: str
    
    # 内容变更
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    
    # 位置变更
    old_location: Optional[Tuple[int, int]] = None
    new_location: Optional[Tuple[int, int]] = None
    
    # 影响分析
    affected_symbols: Set[str] = field(default_factory=set)
    broken_references: Set[str] = field(default_factory=set)


@dataclass
class DeltaSet:
    """变更集合."""
    deltas: List[CodeDelta] = field(default_factory=list)
    base_commit: Optional[str] = None
    target_commit: Optional[str] = None
    
    @property
    def added(self) -> List[CodeDelta]:
        return [d for d in self.deltas if d.delta_type == DeltaType.ADDED]
    
    @property
    def modified(self) -> List[CodeDelta]:
        return [d for d in self.deltas if d.delta_type == DeltaType.MODIFIED]
    
    @property
    def deleted(self) -> List[CodeDelta]:
        return [d for d in self.deltas if d.delta_type == DeltaType.DELETED]
    
    def affected_chunks(self) -> Set[str]:
        return {d.chunk_id for d in self.deltas}
    
    def affected_files(self) -> Set[str]:
        return {d.file_path for d in self.deltas}


class DeltaAnalyzer:
    """变更分析器 - 分析代码变更的影响."""
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        self.cache = cache or get_unified_cache()
    
    def compute_delta(
        self,
        old_content: str,
        new_content: str,
        file_path: str
    ) -> DeltaSet:
        """计算两个版本之间的差异."""
        # 解析为块
        old_chunks = self.cache.chunk_manager.parse_file(
            f"{file_path}.old", old_content
        )
        new_chunks = self.cache.chunk_manager.parse_file(
            f"{file_path}.new", new_content
        )
        
        old_by_name = {c.name: c for c in old_chunks if c.name}
        new_by_name = {c.name: c for c in new_chunks if c.name}
        
        deltas = []
        
        # 新增
        for name, chunk in new_by_name.items():
            if name not in old_by_name:
                deltas.append(CodeDelta(
                    delta_type=DeltaType.ADDED,
                    chunk_id=chunk.id,
                    file_path=file_path,
                    new_content=chunk.content,
                    new_hash=chunk.content_hash,
                    affected_symbols=chunk.defines
                ))
        
        # 删除
        for name, chunk in old_by_name.items():
            if name not in new_by_name:
                deltas.append(CodeDelta(
                    delta_type=DeltaType.DELETED,
                    chunk_id=chunk.id,
                    file_path=file_path,
                    old_content=chunk.content,
                    old_hash=chunk.content_hash,
                    affected_symbols=chunk.defines
                ))
        
        # 修改
        for name in set(old_by_name.keys()) & set(new_by_name.keys()):
            old_chunk = old_by_name[name]
            new_chunk = new_by_name[name]
            
            if old_chunk.content_hash != new_chunk.content_hash:
                deltas.append(CodeDelta(
                    delta_type=DeltaType.MODIFIED,
                    chunk_id=old_chunk.id,
                    file_path=file_path,
                    old_content=old_chunk.content,
                    new_content=new_chunk.content,
                    old_hash=old_chunk.content_hash,
                    new_hash=new_chunk.content_hash,
                    affected_symbols=old_chunk.defines | new_chunk.defines
                ))
        
        return DeltaSet(deltas=deltas)
    
    def analyze_impact(
        self,
        delta_set: DeltaSet,
        snapshot: ReasoningSnapshot
    ) -> Dict[str, Any]:
        """分析变更对推理快照的影响."""
        affected_chunks = delta_set.affected_chunks()
        
        # 传播影响
        all_affected = snapshot.get_affected_by_change(affected_chunks)
        
        # 分析影响程度
        direct_impact = len(affected_chunks)
        indirect_impact = len(all_affected) - direct_impact
        
        # 找出需要重新推理的块
        chunks_to_recompute = []
        for chunk_id in all_affected:
            state = snapshot.get_state(chunk_id)
            if state is None or chunk_id in affected_chunks:
                chunks_to_recompute.append(chunk_id)
        
        return {
            "direct_changes": list(affected_chunks),
            "all_affected": list(all_affected),
            "direct_impact_count": direct_impact,
            "indirect_impact_count": indirect_impact,
            "total_impact_count": len(all_affected),
            "chunks_to_recompute": chunks_to_recompute,
            "recompute_ratio": len(chunks_to_recompute) / max(1, len(snapshot.states))
        }


# ============================================================================
# Part 3: Incremental Reasoner - 增量推理器
# ============================================================================

ReasoningFunc = Callable[[str, Optional[ReasoningState]], Awaitable[ReasoningState]]


class IncrementalReasoner:
    """增量推理器 - 只重新推理变化的部分.
    
    核心算法:
    1. 接收代码变更 (DeltaSet)
    2. 分析影响范围
    3. 只对受影响的块重新推理
    4. 合并结果到现有快照
    """
    
    def __init__(
        self,
        role_id: str,
        reasoning_func: Optional[ReasoningFunc] = None,
        cache: Optional[UnifiedCache] = None
    ):
        self.role_id = role_id
        self.reasoning_func = reasoning_func
        self.cache = cache or get_unified_cache()
        self.delta_analyzer = DeltaAnalyzer(self.cache)
        
        # 当前快照
        self._current_snapshot: Optional[ReasoningSnapshot] = None
        self._snapshot_history: List[ReasoningSnapshot] = []
        
        # 统计
        self._total_computations = 0
        self._cache_hits = 0
        self._incremental_updates = 0
    
    @property
    def current_snapshot(self) -> Optional[ReasoningSnapshot]:
        return self._current_snapshot
    
    def create_snapshot(self) -> ReasoningSnapshot:
        """创建新的推理快照."""
        snapshot = ReasoningSnapshot(
            id=f"snapshot_{self.role_id}_{int(time.time()*1000)}",
            role_id=self.role_id
        )
        self._current_snapshot = snapshot
        return snapshot
    
    async def full_reasoning(
        self,
        chunks: List[CodeChunk]
    ) -> ReasoningSnapshot:
        """完整推理 - 对所有块进行推理."""
        snapshot = self.create_snapshot()
        
        for chunk in chunks:
            state = await self._reason_chunk(chunk, None)
            snapshot.set_state(chunk.id, state)
            
            # 建立依赖关系
            for dep in chunk.calls | chunk.imports:
                for other in chunks:
                    if dep in other.defines:
                        snapshot.add_dependency(chunk.id, other.id)
        
        self._total_computations += len(chunks)
        return snapshot
    
    async def incremental_reasoning(
        self,
        delta_set: DeltaSet
    ) -> Tuple[ReasoningSnapshot, Dict[str, Any]]:
        """增量推理 - 只重新推理受影响的部分.
        
        Returns:
            (更新后的快照, 影响分析报告)
        """
        if self._current_snapshot is None:
            raise ValueError("No current snapshot. Call full_reasoning first.")
        
        # 分析影响
        impact = self.delta_analyzer.analyze_impact(delta_set, self._current_snapshot)
        
        # 保存旧快照
        old_snapshot = self._current_snapshot.clone()
        self._snapshot_history.append(old_snapshot)
        
        # 只重新推理需要的块
        chunks_to_recompute = impact["chunks_to_recompute"]
        
        for chunk_id in chunks_to_recompute:
            # 找到对应的delta
            delta = next(
                (d for d in delta_set.deltas if d.chunk_id == chunk_id),
                None
            )
            
            if delta and delta.delta_type == DeltaType.DELETED:
                # 删除的块,直接移除状态
                self._current_snapshot.states.pop(chunk_id, None)
            elif delta and delta.new_content:
                # 新增或修改的块
                old_state = self._current_snapshot.get_state(chunk_id)
                
                # 创建临时chunk用于推理
                temp_chunk = CodeChunk(
                    id=chunk_id,
                    chunk_type="block",
                    content=delta.new_content,
                    file_path=delta.file_path,
                    line_start=0,
                    line_end=0
                )
                
                new_state = await self._reason_chunk(temp_chunk, old_state)
                self._current_snapshot.set_state(chunk_id, new_state)
        
        self._incremental_updates += 1
        self._total_computations += len(chunks_to_recompute)
        
        # 添加统计到报告
        impact["incremental_efficiency"] = 1 - impact["recompute_ratio"]
        impact["computations_saved"] = len(self._current_snapshot.states) - len(chunks_to_recompute)
        
        return self._current_snapshot, impact
    
    async def _reason_chunk(
        self,
        chunk: CodeChunk,
        previous_state: Optional[ReasoningState]
    ) -> ReasoningState:
        """对单个块进行推理."""
        start_time = time.time()
        
        if self.reasoning_func:
            state = await self.reasoning_func(chunk.content, previous_state)
        else:
            # 默认推理逻辑
            state = ReasoningState(
                chunk_id=chunk.id,
                content_hash=chunk.content_hash,
                understanding=f"Analyzed chunk: {chunk.name or chunk.id}",
                dependencies=chunk.imports | chunk.calls
            )
        
        state.compute_cost_ms = (time.time() - start_time) * 1000
        return state
    
    def set_reasoning_func(self, func: ReasoningFunc):
        """设置推理函数."""
        self.reasoning_func = func
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息."""
        total = self._total_computations
        if total == 0:
            efficiency = 0
        else:
            # 如果是纯增量模式,效率高
            if self._incremental_updates > 0:
                avg_snapshot_size = len(self._current_snapshot.states) if self._current_snapshot else 0
                efficiency = 1 - (self._total_computations / max(1, avg_snapshot_size * self._incremental_updates))
            else:
                efficiency = 0
        
        return {
            "role_id": self.role_id,
            "total_computations": self._total_computations,
            "incremental_updates": self._incremental_updates,
            "cache_hits": self._cache_hits,
            "snapshot_history_size": len(self._snapshot_history),
            "current_snapshot_size": len(self._current_snapshot.states) if self._current_snapshot else 0,
            "estimated_efficiency": efficiency
        }


# ============================================================================
# Part 4: Multi-Role Incremental System - 多角色增量系统
# ============================================================================

class MultiRoleIncrementalEngine:
    """多角色增量推理引擎.
    
    核心思想: 多个角色共享代码理解,但各自维护推理状态.
    
    当代码变更时:
    1. SharedEncoder 更新语义单元 (所有角色共享)
    2. 每个角色的 IncrementalReasoner 收到变更通知
    3. 各自增量更新自己的推理快照
    4. 可复用其他角色的部分推理结果
    """
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        self.cache = cache or get_unified_cache()
        self._reasoners: Dict[str, IncrementalReasoner] = {}
        self._change_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def register_role(
        self,
        role_id: str,
        reasoning_func: Optional[ReasoningFunc] = None
    ) -> IncrementalReasoner:
        """注册角色的推理器."""
        with self._lock:
            if role_id not in self._reasoners:
                reasoner = IncrementalReasoner(
                    role_id=role_id,
                    reasoning_func=reasoning_func,
                    cache=self.cache
                )
                self._reasoners[role_id] = reasoner
            return self._reasoners[role_id]
    
    def get_reasoner(self, role_id: str) -> Optional[IncrementalReasoner]:
        """获取角色的推理器."""
        return self._reasoners.get(role_id)
    
    async def process_file_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str
    ) -> Dict[str, Tuple[ReasoningSnapshot, Dict]]:
        """处理文件变更,更新所有角色的推理.
        
        Returns:
            {role_id: (updated_snapshot, impact_report)}
        """
        # 计算delta
        analyzer = DeltaAnalyzer(self.cache)
        delta_set = analyzer.compute_delta(old_content, new_content, file_path)
        
        # 更新共享语义
        self.cache.encoder.encode(new_content, file_path)
        
        # 通知所有角色
        results = {}
        for role_id, reasoner in self._reasoners.items():
            if reasoner.current_snapshot is not None:
                snapshot, impact = await reasoner.incremental_reasoning(delta_set)
                results[role_id] = (snapshot, impact)
        
        # 触发订阅者
        for callback in self._change_subscribers.get(file_path, []):
            callback(delta_set)
        
        return results
    
    def subscribe_to_changes(
        self,
        file_path: str,
        callback: Callable[[DeltaSet], None]
    ):
        """订阅文件变更."""
        self._change_subscribers[file_path].append(callback)
    
    def share_reasoning(
        self,
        from_role: str,
        to_role: str,
        chunk_id: str
    ) -> bool:
        """共享推理结果.
        
        将一个角色的推理结果共享给另一个角色.
        """
        from_reasoner = self._reasoners.get(from_role)
        to_reasoner = self._reasoners.get(to_role)
        
        if not from_reasoner or not to_reasoner:
            return False
        
        if not from_reasoner.current_snapshot:
            return False
        
        state = from_reasoner.current_snapshot.get_state(chunk_id)
        if state is None:
            return False
        
        if to_reasoner.current_snapshot is None:
            to_reasoner.create_snapshot()
        
        # 复制状态(可能需要适配角色视角)
        to_reasoner.current_snapshot.set_state(chunk_id, state)
        return True
    
    def get_consensus_understanding(
        self,
        chunk_id: str
    ) -> Dict[str, Any]:
        """获取对某个块的共识理解.
        
        汇总所有角色对该块的理解.
        """
        understandings = {}
        for role_id, reasoner in self._reasoners.items():
            if reasoner.current_snapshot:
                state = reasoner.current_snapshot.get_state(chunk_id)
                if state:
                    understandings[role_id] = {
                        "understanding": state.understanding,
                        "intent": state.intent,
                        "issues": state.issues
                    }
        
        return {
            "chunk_id": chunk_id,
            "role_understandings": understandings,
            "num_roles_analyzed": len(understandings)
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计."""
        return {
            "cache_stats": self.cache.get_stats(),
            "registered_roles": list(self._reasoners.keys()),
            "role_stats": {
                role_id: reasoner.get_stats()
                for role_id, reasoner in self._reasoners.items()
            }
        }


# ============================================================================
# Part 5: Attention-like Reasoning - 注意力式推理
# ============================================================================

@dataclass
class AttentionWeight:
    """注意力权重 - 描述块之间的关注程度."""
    from_chunk: str
    to_chunk: str
    weight: float
    reason: str = ""


class AttentionBasedReasoner:
    """基于注意力的推理器.
    
    模拟 Transformer 的注意力机制:
    - Query: 当前正在分析的块
    - Key: 其他相关的块
    - Value: 其他块的信息
    
    用于确定在推理时应该"关注"哪些其他代码块.
    """
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        self.cache = cache or get_unified_cache()
        self._attention_cache: Dict[str, List[AttentionWeight]] = {}
    
    def compute_attention(
        self,
        query_chunk: CodeChunk,
        context_chunks: List[CodeChunk]
    ) -> List[AttentionWeight]:
        """计算注意力权重.
        
        确定 query_chunk 应该关注 context_chunks 中的哪些块.
        """
        weights = []
        
        for ctx_chunk in context_chunks:
            if ctx_chunk.id == query_chunk.id:
                continue
            
            weight = 0.0
            reasons = []
            
            # 依赖关系 - 高权重
            if ctx_chunk.name and ctx_chunk.name in query_chunk.calls:
                weight += 0.5
                reasons.append(f"calls {ctx_chunk.name}")
            
            if ctx_chunk.name and ctx_chunk.name in query_chunk.imports:
                weight += 0.4
                reasons.append(f"imports {ctx_chunk.name}")
            
            # 同文件 - 中等权重
            if query_chunk.file_path == ctx_chunk.file_path:
                weight += 0.2
                reasons.append("same file")
            
            # 符号重叠 - 低权重
            symbol_overlap = len(query_chunk.calls & ctx_chunk.defines)
            if symbol_overlap > 0:
                weight += 0.1 * min(symbol_overlap, 3)
                reasons.append(f"{symbol_overlap} symbol overlap")
            
            if weight > 0:
                weights.append(AttentionWeight(
                    from_chunk=query_chunk.id,
                    to_chunk=ctx_chunk.id,
                    weight=min(weight, 1.0),
                    reason=", ".join(reasons)
                ))
        
        # 归一化
        total_weight = sum(w.weight for w in weights)
        if total_weight > 0:
            for w in weights:
                w.weight /= total_weight
        
        # 按权重排序
        weights.sort(key=lambda w: w.weight, reverse=True)
        
        # 缓存
        self._attention_cache[query_chunk.id] = weights
        
        return weights
    
    def get_top_k_context(
        self,
        query_chunk: CodeChunk,
        context_chunks: List[CodeChunk],
        k: int = 5
    ) -> List[CodeChunk]:
        """获取 top-k 最相关的上下文块."""
        weights = self.compute_attention(query_chunk, context_chunks)
        top_k_ids = {w.to_chunk for w in weights[:k]}
        return [c for c in context_chunks if c.id in top_k_ids]
    
    def get_attention_context(
        self,
        query_chunk: CodeChunk,
        context_chunks: List[CodeChunk],
        threshold: float = 0.1
    ) -> str:
        """获取基于注意力的上下文文本.
        
        用于构建 LLM prompt.
        """
        weights = self.compute_attention(query_chunk, context_chunks)
        
        context_parts = []
        for w in weights:
            if w.weight < threshold:
                break
            
            chunk = next((c for c in context_chunks if c.id == w.to_chunk), None)
            if chunk:
                context_parts.append(
                    f"# Relevant code (attention={w.weight:.2f}, reason: {w.reason}):\n"
                    f"# From: {chunk.file_path}\n"
                    f"{chunk.content}"
                )
        
        return "\n\n".join(context_parts)


# ============================================================================
# Part 6: Integration - 集成接口
# ============================================================================

def create_incremental_engine() -> MultiRoleIncrementalEngine:
    """创建多角色增量推理引擎."""
    return MultiRoleIncrementalEngine()


def create_attention_reasoner() -> AttentionBasedReasoner:
    """创建基于注意力的推理器."""
    return AttentionBasedReasoner()


# 便捷装饰器
def incremental_reasoning(role_id: str):
    """装饰器: 为函数添加增量推理能力."""
    def decorator(func: Callable):
        engine = create_incremental_engine()
        reasoner = engine.register_role(role_id)
        
        async def reasoning_wrapper(content: str, prev: Optional[ReasoningState]) -> ReasoningState:
            result = await func(content, prev)
            if isinstance(result, ReasoningState):
                return result
            return ReasoningState(
                chunk_id="dynamic",
                content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
                understanding=str(result)
            )
        
        reasoner.set_reasoning_func(reasoning_wrapper)
        
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        wrapper._reasoner = reasoner
        wrapper._engine = engine
        return wrapper
    
    return decorator
