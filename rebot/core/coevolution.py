"""Multi-Agent Co-Evolution and Consistency Guarantees - 多智能体协同演化与一致性保证.

理论基础:
在多任务异构计算场景中，不同任务实例被并行的多个计算智能体执行。
它们在共享资源的同时，沿各自的任务依赖图推进执行进度。

核心概念:
1. 任务DAG: T = ⟨F, D⟩ - 功能片段集合与依赖关系
2. 结构归一化映射 N(·) - 将功能片段投影至等价类
3. 跨任务等价片段集合 C(φ̂) - 共享计算路径
4. 资源绑定映射 M: (φᵢ, R(t)) → (rⱼ, tₖ)
5. 依赖保持条件: φₐ ≺ φᵦ
6. 状态一致性: x_φᵢ^(k) = x_φⱼ^(k)

Agent层实现:
- 等价片段 = 相似代码块/相似推理任务
- 共享计算路径 = 缓存的推理结果
- 状态一致性 = 多Agent对同一代码的理解一致
"""

from __future__ import annotations

import asyncio
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
import numpy as np
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Task DAG - 任务有向无环图
# ============================================================================

@dataclass
class FunctionalFragment:
    """功能片段 φ - 任务的基本执行单元.
    
    在论文中: F = {φ₁, φ₂, ..., φₙ}
    在Agent中: 对应代码块、推理步骤、或子任务
    """
    id: str
    content: Any
    fragment_type: str = "generic"
    
    # 结构特征 - 用于归一化映射
    signature: Optional[str] = None
    semantic_hash: Optional[str] = None
    
    # 执行状态
    state: str = "pending"  # pending, running, completed, failed
    output: Optional[Any] = None
    
    # 元信息
    created_at: float = field(default_factory=time.time)
    executed_at: Optional[float] = None
    execution_count: int = 0
    
    def compute_signature(self) -> str:
        """计算结构签名 - 用于等价类判断."""
        if self.signature:
            return self.signature
        
        # 基于内容和类型计算
        content_str = str(self.content)
        sig = hashlib.sha256(
            f"{self.fragment_type}:{content_str}".encode()
        ).hexdigest()[:16]
        self.signature = sig
        return sig
    
    def compute_semantic_hash(self) -> str:
        """计算语义哈希 - 更深层的等价性."""
        if self.semantic_hash:
            return self.semantic_hash
        
        # 这里可以接入embedding模型
        # 简化实现：基于签名
        self.semantic_hash = self.compute_signature()
        return self.semantic_hash


@dataclass
class TaskDAG:
    """任务DAG: T = ⟨F, D⟩.
    
    F: 功能片段集合
    D ⊆ F × F: 片段间的数据依赖关系
    """
    id: str
    fragments: Dict[str, FunctionalFragment] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse_deps: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # 任务元信息
    name: str = ""
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    
    def add_fragment(self, fragment: FunctionalFragment):
        """添加功能片段."""
        self.fragments[fragment.id] = fragment
    
    def add_dependency(self, from_id: str, to_id: str):
        """添加依赖: from_id 依赖 to_id (to_id 必须先执行)."""
        self.dependencies[from_id].add(to_id)
        self.reverse_deps[to_id].add(from_id)
    
    def get_ready_fragments(self) -> List[FunctionalFragment]:
        """获取就绪的片段 (所有依赖已完成)."""
        ready = []
        for fid, fragment in self.fragments.items():
            if fragment.state != "pending":
                continue
            
            deps = self.dependencies.get(fid, set())
            all_deps_done = all(
                self.fragments.get(dep, FunctionalFragment(id="")).state == "completed"
                for dep in deps
            )
            
            if all_deps_done:
                ready.append(fragment)
        
        return ready
    
    def topological_sort(self) -> List[str]:
        """拓扑排序 - 获取合法执行顺序."""
        in_degree = defaultdict(int)
        for fid in self.fragments:
            in_degree[fid] = len(self.dependencies.get(fid, set()))
        
        queue = [fid for fid, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for dependent in self.reverse_deps.get(current, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return result
    
    def is_valid(self) -> bool:
        """检查DAG是否有效(无环)."""
        return len(self.topological_sort()) == len(self.fragments)


# ============================================================================
# Part 2: Structural Normalization - 结构归一化映射
# ============================================================================

class NormalizationStrategy(str, Enum):
    """归一化策略."""
    EXACT = "exact"           # 精确匹配
    SIGNATURE = "signature"   # 结构签名
    SEMANTIC = "semantic"     # 语义等价
    FUZZY = "fuzzy"          # 模糊匹配


@dataclass
class EquivalenceClass:
    """等价类 - 跨任务等价片段集合.
    
    论文中: C(φ̂) = {φⱼ | N(φⱼ) = N(φ̂)}
    """
    representative_id: str
    representative_hash: str
    members: Set[str] = field(default_factory=set)
    
    # 共享计算结果
    cached_output: Optional[Any] = None
    execution_count: int = 0
    last_executed: Optional[float] = None
    
    def add_member(self, fragment_id: str):
        """添加成员."""
        self.members.add(fragment_id)
    
    def has_cached_result(self) -> bool:
        """是否有缓存结果."""
        return self.cached_output is not None
    
    def set_result(self, output: Any):
        """设置共享结果."""
        self.cached_output = output
        self.execution_count += 1
        self.last_executed = time.time()


class StructuralNormalizer:
    """结构归一化映射 N(·).
    
    将功能片段投影至等价类代表φ̂，实现跨任务共享.
    """
    
    def __init__(self, strategy: NormalizationStrategy = NormalizationStrategy.SIGNATURE):
        self.strategy = strategy
        self._equivalence_classes: Dict[str, EquivalenceClass] = {}
        self._fragment_to_class: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def normalize(self, fragment: FunctionalFragment) -> str:
        """归一化映射 N(φ) → φ̂.
        
        Returns:
            等价类代表的哈希
        """
        if self.strategy == NormalizationStrategy.EXACT:
            return fragment.id
        elif self.strategy == NormalizationStrategy.SIGNATURE:
            return fragment.compute_signature()
        elif self.strategy == NormalizationStrategy.SEMANTIC:
            return fragment.compute_semantic_hash()
        else:  # FUZZY
            # 模糊匹配需要更复杂的逻辑
            return fragment.compute_signature()
    
    def register(self, fragment: FunctionalFragment) -> EquivalenceClass:
        """注册片段到等价类."""
        with self._lock:
            norm_hash = self.normalize(fragment)
            
            if norm_hash in self._equivalence_classes:
                # 已存在等价类,添加为成员
                eq_class = self._equivalence_classes[norm_hash]
                eq_class.add_member(fragment.id)
            else:
                # 创建新等价类
                eq_class = EquivalenceClass(
                    representative_id=fragment.id,
                    representative_hash=norm_hash
                )
                eq_class.add_member(fragment.id)
                self._equivalence_classes[norm_hash] = eq_class
            
            self._fragment_to_class[fragment.id] = norm_hash
            return eq_class
    
    def get_equivalence_class(self, fragment: FunctionalFragment) -> Optional[EquivalenceClass]:
        """获取片段的等价类."""
        norm_hash = self.normalize(fragment)
        return self._equivalence_classes.get(norm_hash)
    
    def get_equivalent_fragments(self, fragment: FunctionalFragment) -> Set[str]:
        """获取等价片段集合 C(φ̂)."""
        eq_class = self.get_equivalence_class(fragment)
        return eq_class.members if eq_class else {fragment.id}
    
    def share_result(self, fragment: FunctionalFragment, output: Any):
        """共享计算结果到等价类."""
        eq_class = self.get_equivalence_class(fragment)
        if eq_class:
            eq_class.set_result(output)
    
    def get_cached_result(self, fragment: FunctionalFragment) -> Optional[Any]:
        """获取等价类的缓存结果."""
        eq_class = self.get_equivalence_class(fragment)
        if eq_class and eq_class.has_cached_result():
            return eq_class.cached_output
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息."""
        total_fragments = sum(len(ec.members) for ec in self._equivalence_classes.values())
        return {
            "num_equivalence_classes": len(self._equivalence_classes),
            "total_fragments": total_fragments,
            "average_class_size": total_fragments / max(1, len(self._equivalence_classes)),
            "cached_results": sum(1 for ec in self._equivalence_classes.values() if ec.has_cached_result())
        }


# ============================================================================
# Part 3: Resource Binding and Scheduling - 资源绑定与调度
# ============================================================================

@dataclass
class Resource:
    """计算资源."""
    id: str
    resource_type: str
    capacity: float = 1.0
    available: float = 1.0
    
    def allocate(self, amount: float) -> bool:
        """分配资源."""
        if amount <= self.available:
            self.available -= amount
            return True
        return False
    
    def release(self, amount: float):
        """释放资源."""
        self.available = min(self.capacity, self.available + amount)


@dataclass
class ResourceBinding:
    """资源绑定: M(φᵢ, R(t)) → (rⱼ, tₖ).
    
    将功能片段绑定到特定资源和时间槽.
    """
    fragment_id: str
    resource_id: str
    start_time: float
    end_time: Optional[float] = None
    
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class ResourceScheduler:
    """资源调度器 - 基于资源状态图R(t)进行调度."""
    
    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._bindings: Dict[str, ResourceBinding] = {}
        self._fragment_lifecycle: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()
    
    def register_resource(self, resource: Resource):
        """注册资源."""
        self._resources[resource.id] = resource
    
    def compute_binding(
        self,
        fragment: FunctionalFragment,
        resource_state: Dict[str, float]
    ) -> Optional[ResourceBinding]:
        """计算资源绑定 M(φᵢ, R(t)) → (rⱼ, tₖ).
        
        确保对共享计算路径的访问满足唯一性与互斥性约束.
        """
        with self._lock:
            # 找到可用资源
            for rid, resource in self._resources.items():
                if resource.available > 0:
                    # 创建绑定
                    binding = ResourceBinding(
                        fragment_id=fragment.id,
                        resource_id=rid,
                        start_time=time.time()
                    )
                    
                    # 分配资源
                    resource.allocate(1.0)
                    self._bindings[fragment.id] = binding
                    
                    # 记录生命周期
                    self._fragment_lifecycle[fragment.id] = {
                        "start": binding.start_time,
                        "resource": rid
                    }
                    
                    return binding
            
            return None
    
    def release_binding(self, fragment_id: str):
        """释放绑定."""
        with self._lock:
            if fragment_id in self._bindings:
                binding = self._bindings[fragment_id]
                binding.end_time = time.time()
                
                # 释放资源
                if binding.resource_id in self._resources:
                    self._resources[binding.resource_id].release(1.0)
                
                # 更新生命周期
                if fragment_id in self._fragment_lifecycle:
                    self._fragment_lifecycle[fragment_id]["end"] = binding.end_time
    
    def get_lifecycle(self, fragment_id: str) -> Optional[Dict[str, float]]:
        """获取片段生命周期表 L(φ)."""
        return self._fragment_lifecycle.get(fragment_id)


# ============================================================================
# Part 4: Consistency Guarantees - 一致性保证
# ============================================================================

@dataclass
class ExecutionState:
    """执行状态 x_φ^(k) - 片段在第k次执行后的状态输出."""
    fragment_id: str
    execution_index: int
    output: Any
    timestamp: float = field(default_factory=time.time)
    
    # 一致性校验
    state_hash: str = ""
    
    def compute_hash(self) -> str:
        """计算状态哈希."""
        output_str = str(self.output)
        self.state_hash = hashlib.sha256(output_str.encode()).hexdigest()[:16]
        return self.state_hash


class ConsistencyGuarantee:
    """一致性保证机制.
    
    确保: x_φᵢ^(k) = x_φⱼ^(k), ∀φᵢ,φⱼ ∈ C(φ̂)
    """
    
    def __init__(self, normalizer: StructuralNormalizer):
        self.normalizer = normalizer
        self._execution_states: Dict[str, List[ExecutionState]] = defaultdict(list)
        self._consistency_violations: List[Dict] = []
        self._lock = threading.RLock()
    
    def record_execution(
        self,
        fragment: FunctionalFragment,
        output: Any
    ) -> ExecutionState:
        """记录执行状态."""
        with self._lock:
            exec_index = len(self._execution_states[fragment.id])
            state = ExecutionState(
                fragment_id=fragment.id,
                execution_index=exec_index,
                output=output
            )
            state.compute_hash()
            
            self._execution_states[fragment.id].append(state)
            
            # 检查等价类一致性
            self._check_consistency(fragment, state)
            
            return state
    
    def _check_consistency(
        self,
        fragment: FunctionalFragment,
        state: ExecutionState
    ):
        """检查等价类内的一致性."""
        eq_class = self.normalizer.get_equivalence_class(fragment)
        if not eq_class:
            return
        
        # 检查同一执行索引下的状态是否一致
        for member_id in eq_class.members:
            if member_id == fragment.id:
                continue
            
            member_states = self._execution_states.get(member_id, [])
            if len(member_states) > state.execution_index:
                other_state = member_states[state.execution_index]
                
                if other_state.state_hash != state.state_hash:
                    self._consistency_violations.append({
                        "fragment_1": fragment.id,
                        "fragment_2": member_id,
                        "execution_index": state.execution_index,
                        "hash_1": state.state_hash,
                        "hash_2": other_state.state_hash,
                        "timestamp": time.time()
                    })
                    logger.warning(
                        f"Consistency violation detected: {fragment.id} vs {member_id}"
                    )
    
    def get_violations(self) -> List[Dict]:
        """获取一致性违规记录."""
        return self._consistency_violations.copy()
    
    def is_consistent(self, equivalence_class: EquivalenceClass) -> bool:
        """检查等价类是否一致."""
        for violation in self._consistency_violations:
            if (violation["fragment_1"] in equivalence_class.members or
                violation["fragment_2"] in equivalence_class.members):
                return False
        return True


# ============================================================================
# Part 5: Dependency Preservation - 依赖保持
# ============================================================================

class DependencyPreserver:
    """依赖保持机制.
    
    确保: 若 (φₐ, φᵦ) ∈ D, 则调度序列中必须满足 φₐ ≺ φᵦ
    """
    
    def __init__(self):
        self._execution_order: List[str] = []
        self._violations: List[Dict] = []
        self._lock = threading.RLock()
    
    def validate_execution(
        self,
        fragment: FunctionalFragment,
        dag: TaskDAG
    ) -> bool:
        """验证执行是否满足依赖条件."""
        with self._lock:
            # 检查所有依赖是否已执行
            deps = dag.dependencies.get(fragment.id, set())
            
            for dep_id in deps:
                if dep_id not in self._execution_order:
                    self._violations.append({
                        "fragment": fragment.id,
                        "missing_dependency": dep_id,
                        "timestamp": time.time()
                    })
                    return False
            
            return True
    
    def record_execution(self, fragment_id: str):
        """记录执行顺序."""
        with self._lock:
            self._execution_order.append(fragment_id)
    
    def get_execution_order(self) -> List[str]:
        """获取执行顺序."""
        return self._execution_order.copy()
    
    def get_violations(self) -> List[Dict]:
        """获取依赖违规."""
        return self._violations.copy()


# ============================================================================
# Part 6: Multi-Agent Co-Evolution Engine - 多智能体协同演化引擎
# ============================================================================

@dataclass
class AgentState:
    """智能体状态."""
    agent_id: str
    current_task: Optional[str] = None
    current_fragment: Optional[str] = None
    completed_fragments: Set[str] = field(default_factory=set)
    state: str = "idle"  # idle, working, blocked, done


class CoEvolutionEngine:
    """多智能体协同演化引擎.
    
    整合:
    1. 任务DAG管理
    2. 结构归一化与等价类
    3. 资源调度
    4. 一致性保证
    5. 依赖保持
    """
    
    def __init__(
        self,
        num_agents: int = 4,
        normalization_strategy: NormalizationStrategy = NormalizationStrategy.SIGNATURE
    ):
        self.num_agents = num_agents
        
        # 核心组件
        self.normalizer = StructuralNormalizer(normalization_strategy)
        self.scheduler = ResourceScheduler()
        self.consistency = ConsistencyGuarantee(self.normalizer)
        self.dependency_preserver = DependencyPreserver()
        
        # 任务管理
        self._tasks: Dict[str, TaskDAG] = {}
        self._agents: Dict[str, AgentState] = {}
        
        # 初始化资源
        for i in range(num_agents):
            self.scheduler.register_resource(Resource(
                id=f"agent_resource_{i}",
                resource_type="compute"
            ))
        
        # 初始化Agent
        for i in range(num_agents):
            self._agents[f"agent_{i}"] = AgentState(agent_id=f"agent_{i}")
        
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=num_agents)
    
    def register_task(self, task: TaskDAG):
        """注册任务."""
        with self._lock:
            self._tasks[task.id] = task
            
            # 注册所有片段到归一化器
            for fragment in task.fragments.values():
                self.normalizer.register(fragment)
    
    async def execute_fragment(
        self,
        fragment: FunctionalFragment,
        dag: TaskDAG,
        executor: Callable[[FunctionalFragment], Awaitable[Any]]
    ) -> Any:
        """执行功能片段 - 带一致性保证."""
        # 1. 检查等价类缓存
        cached = self.normalizer.get_cached_result(fragment)
        if cached is not None:
            logger.debug(f"Cache hit for fragment {fragment.id}")
            fragment.state = "completed"
            fragment.output = cached
            return cached
        
        # 2. 验证依赖
        if not self.dependency_preserver.validate_execution(fragment, dag):
            raise RuntimeError(f"Dependency violation for {fragment.id}")
        
        # 3. 获取资源绑定
        binding = self.scheduler.compute_binding(
            fragment, 
            {r.id: r.available for r in self.scheduler._resources.values()}
        )
        
        if binding is None:
            raise RuntimeError(f"No resource available for {fragment.id}")
        
        try:
            # 4. 执行
            fragment.state = "running"
            result = await executor(fragment)
            
            # 5. 记录状态
            fragment.state = "completed"
            fragment.output = result
            fragment.executed_at = time.time()
            fragment.execution_count += 1
            
            # 6. 一致性记录
            self.consistency.record_execution(fragment, result)
            
            # 7. 共享到等价类
            self.normalizer.share_result(fragment, result)
            
            # 8. 记录执行顺序
            self.dependency_preserver.record_execution(fragment.id)
            
            return result
            
        finally:
            # 释放资源
            self.scheduler.release_binding(fragment.id)
    
    async def execute_task(
        self,
        task: TaskDAG,
        executor: Callable[[FunctionalFragment], Awaitable[Any]]
    ) -> Dict[str, Any]:
        """执行整个任务DAG."""
        results = {}
        
        while True:
            # 获取就绪片段
            ready = task.get_ready_fragments()
            
            if not ready:
                # 检查是否全部完成
                all_done = all(
                    f.state == "completed" 
                    for f in task.fragments.values()
                )
                if all_done:
                    break
                else:
                    # 有片段未完成但无就绪 - 可能有错误
                    await asyncio.sleep(0.01)
                    continue
            
            # 并行执行就绪片段
            tasks = [
                self.execute_fragment(f, task, executor)
                for f in ready
            ]
            
            fragment_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for fragment, result in zip(ready, fragment_results):
                if isinstance(result, Exception):
                    fragment.state = "failed"
                    results[fragment.id] = {"error": str(result)}
                else:
                    results[fragment.id] = result
        
        return results
    
    async def execute_multi_task(
        self,
        tasks: List[TaskDAG],
        executor: Callable[[FunctionalFragment], Awaitable[Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """并行执行多个任务 - 协同演化."""
        # 注册所有任务
        for task in tasks:
            self.register_task(task)
        
        # 并行执行
        task_executions = [
            self.execute_task(task, executor)
            for task in tasks
        ]
        
        results_list = await asyncio.gather(*task_executions, return_exceptions=True)
        
        results = {}
        for task, result in zip(tasks, results_list):
            if isinstance(result, Exception):
                results[task.id] = {"error": str(result)}
            else:
                results[task.id] = result
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计."""
        return {
            "num_agents": self.num_agents,
            "num_tasks": len(self._tasks),
            "normalizer_stats": self.normalizer.get_stats(),
            "consistency_violations": len(self.consistency.get_violations()),
            "dependency_violations": len(self.dependency_preserver.get_violations()),
            "execution_order_length": len(self.dependency_preserver.get_execution_order())
        }


# ============================================================================
# Part 7: Helper Functions
# ============================================================================

def create_coevolution_engine(
    num_agents: int = 4,
    strategy: NormalizationStrategy = NormalizationStrategy.SIGNATURE
) -> CoEvolutionEngine:
    """创建协同演化引擎."""
    return CoEvolutionEngine(num_agents, strategy)


def create_task_dag(
    fragments: List[Dict[str, Any]],
    dependencies: List[Tuple[str, str]],
    task_id: Optional[str] = None
) -> TaskDAG:
    """创建任务DAG.
    
    Args:
        fragments: [{"id": "f1", "content": ..., "type": ...}, ...]
        dependencies: [("f2", "f1"), ...] 表示f2依赖f1
    """
    dag = TaskDAG(id=task_id or f"task_{int(time.time()*1000)}")
    
    for f in fragments:
        fragment = FunctionalFragment(
            id=f["id"],
            content=f.get("content"),
            fragment_type=f.get("type", "generic")
        )
        dag.add_fragment(fragment)
    
    for from_id, to_id in dependencies:
        dag.add_dependency(from_id, to_id)
    
    return dag
