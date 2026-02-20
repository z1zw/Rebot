"""Unified Execution and Coordination over Rⁿ - Rⁿ上的统一执行与协调机制.

理论基础:
将节点级推理行为映射为Rⁿ空间中的可组合算子，
并通过统一的调度与协调策略实现全局一致推理。

核心概念:
1. 局部算子: Oᵥ: sᵥ(t) → πᵥ(t)⟨aᵥ, sᵥ(t)⟩
2. 算子的线性组合与时序叠加
3. 频域能量分布用于推理约束
4. 高频异常检测 → 调整权重πᵥ(t)
5. 低频稳定性 → 安全并行扩展

Agent层实现:
- 算子 = Agent的推理动作
- 可组合 = 多Agent推理可以并行/重排
- 频域协调 = 基于稳定性动态调整
"""

from __future__ import annotations

import asyncio
import math
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
import heapq

from rebot.core.spatiotemporal_closure import (
    StateVector, StateTrajectory, CollaborativeSignal,
    CollaborativeWeight, ProjectionVector,
    SpectralRepresentation, FourierAnalyzer,
    SpatiotemporalClosure, create_spatiotemporal_closure
)

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Local Operators - 局部算子
# ============================================================================

@dataclass
class OperatorResult:
    """算子执行结果."""
    operator_id: str
    input_state: StateVector
    output_value: float
    execution_time: float
    weight: float = 1.0
    
    # 元信息
    timestamp: float = field(default_factory=time.time)


class LocalOperator:
    """局部算子 Oᵥ.
    
    Oᵥ: sᵥ(t) → πᵥ(t)⟨aᵥ, sᵥ(t)⟩
    
    将节点的状态映射为标量贡献.
    """
    
    def __init__(
        self,
        node_id: str,
        weight: CollaborativeWeight,
        projection: ProjectionVector
    ):
        self.node_id = node_id
        self.weight = weight
        self.projection = projection
        
        # 执行统计
        self._execution_count = 0
        self._total_execution_time = 0.0
    
    def apply(self, state: StateVector, t: Optional[float] = None) -> OperatorResult:
        """应用算子.
        
        返回: πᵥ(t)⟨aᵥ, sᵥ(t)⟩
        """
        start_time = time.time()
        
        current_t = t or state.timestamp
        w = self.weight.get_weight(current_t)
        proj = self.projection.project(state)
        
        output = w * proj
        
        execution_time = time.time() - start_time
        self._execution_count += 1
        self._total_execution_time += execution_time
        
        return OperatorResult(
            operator_id=self.node_id,
            input_state=state,
            output_value=output,
            execution_time=execution_time,
            weight=w
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计."""
        return {
            "node_id": self.node_id,
            "execution_count": self._execution_count,
            "total_execution_time": self._total_execution_time,
            "avg_execution_time": (
                self._total_execution_time / self._execution_count
                if self._execution_count > 0 else 0
            )
        }


class CompositeOperator:
    """组合算子 - 多个局部算子的组合.
    
    支持:
    - 线性组合: Σᵢ αᵢOᵢ
    - 时序叠加: O₁ ∘ O₂
    - 并行执行: O₁ ‖ O₂
    """
    
    def __init__(self, operators: List[LocalOperator]):
        self.operators = operators
        self._composition_type = "linear"
    
    def linear_combine(
        self,
        states: Dict[str, StateVector],
        coefficients: Optional[Dict[str, float]] = None,
        t: Optional[float] = None
    ) -> Tuple[float, List[OperatorResult]]:
        """线性组合 Σᵢ αᵢOᵢ(sᵢ)."""
        if coefficients is None:
            coefficients = {op.node_id: 1.0 for op in self.operators}
        
        total = 0.0
        results = []
        
        for op in self.operators:
            if op.node_id in states:
                coeff = coefficients.get(op.node_id, 1.0)
                result = op.apply(states[op.node_id], t)
                total += coeff * result.output_value
                results.append(result)
        
        return total, results
    
    async def parallel_apply(
        self,
        states: Dict[str, StateVector],
        t: Optional[float] = None
    ) -> List[OperatorResult]:
        """并行应用所有算子."""
        async def apply_one(op: LocalOperator) -> Optional[OperatorResult]:
            if op.node_id in states:
                return op.apply(states[op.node_id], t)
            return None
        
        tasks = [apply_one(op) for op in self.operators]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    
    def sequential_apply(
        self,
        trajectory: StateTrajectory,
        time_points: List[float]
    ) -> List[float]:
        """时序叠加 - 沿时间轴应用算子."""
        if not self.operators:
            return []
        
        op = self.operators[0]  # 使用第一个算子
        outputs = []
        
        for t in time_points:
            state = trajectory.get_state_at(t)
            if state:
                result = op.apply(state, t)
                outputs.append(result.output_value)
            else:
                outputs.append(0.0)
        
        return outputs


# ============================================================================
# Part 2: Operator Scheduling - 算子调度
# ============================================================================

class SchedulingPolicy(str, Enum):
    """调度策略."""
    FIFO = "fifo"                    # 先进先出
    PRIORITY = "priority"            # 优先级
    SPECTRAL = "spectral"            # 频域感知
    ADAPTIVE = "adaptive"            # 自适应


@dataclass
class ScheduledTask:
    """调度任务."""
    task_id: str
    operator: LocalOperator
    state: StateVector
    priority: float = 0.0
    scheduled_time: float = field(default_factory=time.time)
    
    def __lt__(self, other):
        """优先级比较."""
        return self.priority > other.priority  # 高优先级先执行


class OperatorScheduler:
    """算子调度器.
    
    将算子执行映射到时间槽,支持重排和并行化.
    """
    
    def __init__(self, policy: SchedulingPolicy = SchedulingPolicy.ADAPTIVE):
        self.policy = policy
        self._task_queue: List[ScheduledTask] = []
        self._executing: Dict[str, ScheduledTask] = {}
        self._completed: List[ScheduledTask] = []
        self._lock = threading.RLock()
    
    def schedule(
        self,
        operator: LocalOperator,
        state: StateVector,
        priority: Optional[float] = None
    ) -> ScheduledTask:
        """调度算子执行."""
        task_id = f"task_{operator.node_id}_{int(time.time()*1000)}"
        
        task = ScheduledTask(
            task_id=task_id,
            operator=operator,
            state=state,
            priority=priority or 0.0
        )
        
        with self._lock:
            if self.policy == SchedulingPolicy.PRIORITY:
                heapq.heappush(self._task_queue, task)
            else:
                self._task_queue.append(task)
        
        return task
    
    def get_next(self) -> Optional[ScheduledTask]:
        """获取下一个要执行的任务."""
        with self._lock:
            if not self._task_queue:
                return None
            
            if self.policy == SchedulingPolicy.PRIORITY:
                task = heapq.heappop(self._task_queue)
            else:
                task = self._task_queue.pop(0)
            
            self._executing[task.task_id] = task
            return task
    
    def complete(self, task_id: str, result: OperatorResult):
        """标记任务完成."""
        with self._lock:
            if task_id in self._executing:
                task = self._executing.pop(task_id)
                self._completed.append(task)
    
    def reorder(self, new_priorities: Dict[str, float]):
        """重新排序任务队列."""
        with self._lock:
            for task in self._task_queue:
                if task.operator.node_id in new_priorities:
                    task.priority = new_priorities[task.operator.node_id]
            
            if self.policy == SchedulingPolicy.PRIORITY:
                heapq.heapify(self._task_queue)
    
    def get_queue_size(self) -> int:
        """获取队列大小."""
        return len(self._task_queue)


# ============================================================================
# Part 3: Spectral Coordination - 频域协调
# ============================================================================

@dataclass
class CoordinationDecision:
    """协调决策."""
    decision_type: str  # "adjust_weight", "pause", "continue", "redistribute"
    target_nodes: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    confidence: float = 1.0


class SpectralCoordinator:
    """频域协调器.
    
    基于频谱能量分布 Eₘ 进行推理约束:
    - 高频异常 → 调整权重 πᵥ(t)
    - 低频主导 → 安全并行扩展
    """
    
    def __init__(
        self,
        high_freq_threshold: float = 0.3,
        low_freq_threshold: float = 0.7,
        adjustment_rate: float = 0.1
    ):
        self.high_freq_threshold = high_freq_threshold
        self.low_freq_threshold = low_freq_threshold
        self.adjustment_rate = adjustment_rate
        
        self.fourier = FourierAnalyzer()
        self._history: List[Dict[str, Any]] = []
    
    def analyze_and_coordinate(
        self,
        signal: CollaborativeSignal,
        current_weights: Dict[str, CollaborativeWeight]
    ) -> CoordinationDecision:
        """分析并生成协调决策.
        
        基于公式中的频域约束机制.
        """
        # 频域分析
        spectral = self.fourier.transform(signal)
        
        # 记录历史
        analysis = {
            "timestamp": time.time(),
            "total_energy": spectral.total_energy,
            "high_freq_ratio": spectral.high_frequency_ratio,
            "low_freq_ratio": spectral.low_frequency_ratio
        }
        self._history.append(analysis)
        
        # 决策逻辑
        if spectral.high_frequency_ratio > self.high_freq_threshold:
            # 高频能量集中 → 推理不稳定
            return self._handle_instability(spectral, current_weights)
        
        elif spectral.low_frequency_ratio > self.low_freq_threshold:
            # 低频主导 → 稳定,可并行扩展
            return CoordinationDecision(
                decision_type="continue",
                target_nodes=[],
                parameters={"safe_to_parallelize": True},
                reason="Low frequency dominant, stable reasoning",
                confidence=spectral.low_frequency_ratio
            )
        
        else:
            # 中等情况
            return CoordinationDecision(
                decision_type="continue",
                target_nodes=[],
                parameters={"safe_to_parallelize": False},
                reason="Mixed frequency profile",
                confidence=0.5
            )
    
    def _handle_instability(
        self,
        spectral: SpectralRepresentation,
        weights: Dict[str, CollaborativeWeight]
    ) -> CoordinationDecision:
        """处理不稳定情况.
        
        当高频区域产生异常能量集中时,
        触发权重 πᵥ(t) 的自适应调整.
        """
        # 找出贡献最大的节点 (需要更多信息)
        # 简化: 降低所有节点的权重
        
        adjustment = {}
        target_nodes = list(weights.keys())
        
        for node_id in target_nodes:
            # 权重调整因子
            adjustment[node_id] = 1.0 - self.adjustment_rate * spectral.high_frequency_ratio
        
        return CoordinationDecision(
            decision_type="adjust_weight",
            target_nodes=target_nodes,
            parameters={
                "adjustment_factors": adjustment,
                "high_freq_ratio": spectral.high_frequency_ratio
            },
            reason="High frequency instability detected",
            confidence=spectral.high_frequency_ratio
        )
    
    def apply_decision(
        self,
        decision: CoordinationDecision,
        weights: Dict[str, CollaborativeWeight]
    ) -> Dict[str, CollaborativeWeight]:
        """应用协调决策."""
        if decision.decision_type != "adjust_weight":
            return weights
        
        new_weights = {}
        adjustments = decision.parameters.get("adjustment_factors", {})
        
        for node_id, weight in weights.items():
            factor = adjustments.get(node_id, 1.0)
            
            # 创建新的权重函数
            old_func = weight.weight_function
            new_weights[node_id] = CollaborativeWeight(
                node_id=node_id,
                weight_function=lambda t, f=factor, old=old_func: f * old(t)
            )
        
        return new_weights
    
    def get_stability_trend(self, window: int = 10) -> str:
        """获取稳定性趋势."""
        if len(self._history) < 2:
            return "unknown"
        
        recent = self._history[-window:]
        high_freq_values = [h["high_freq_ratio"] for h in recent]
        
        # 计算趋势
        if len(high_freq_values) >= 2:
            trend = high_freq_values[-1] - high_freq_values[0]
            if trend > 0.1:
                return "destabilizing"
            elif trend < -0.1:
                return "stabilizing"
        
        return "stable"


# ============================================================================
# Part 4: Unified Execution Framework - 统一执行框架
# ============================================================================

class ExecutionMode(str, Enum):
    """执行模式."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


@dataclass
class ExecutionContext:
    """执行上下文."""
    mode: ExecutionMode = ExecutionMode.ADAPTIVE
    max_parallel: int = 4
    enable_coordination: bool = True
    enable_reordering: bool = True
    
    # 运行时状态
    current_time: float = 0.0
    total_operations: int = 0
    coordination_decisions: int = 0


@dataclass
class ExecutionResult:
    """执行结果."""
    success: bool
    outputs: Dict[str, float]
    total_output: float
    execution_time: float
    
    # 详细信息
    operator_results: List[OperatorResult] = field(default_factory=list)
    coordination_decisions: List[CoordinationDecision] = field(default_factory=list)
    
    # 统计
    parallel_operations: int = 0
    reorderings: int = 0


class UnifiedExecutionEngine:
    """统一执行引擎 over Rⁿ.
    
    整合:
    1. 局部算子的组合与执行
    2. 时空复合闭包的验证
    3. 频域协调机制
    4. 自适应调度
    """
    
    def __init__(
        self,
        context: Optional[ExecutionContext] = None
    ):
        self.context = context or ExecutionContext()
        
        # 核心组件
        self.closure = create_spatiotemporal_closure()
        self.coordinator = SpectralCoordinator()
        self.scheduler = OperatorScheduler(SchedulingPolicy.ADAPTIVE)
        
        # 算子注册
        self._operators: Dict[str, LocalOperator] = {}
        self._weights: Dict[str, CollaborativeWeight] = {}
        self._projections: Dict[str, ProjectionVector] = {}
        
        # 状态追踪
        self._trajectories: Dict[str, StateTrajectory] = {}
        self._lock = threading.RLock()
    
    def register_operator(
        self,
        node_id: str,
        weight: Optional[CollaborativeWeight] = None,
        projection: Optional[ProjectionVector] = None,
        state_dim: int = 10
    ) -> LocalOperator:
        """注册局部算子."""
        with self._lock:
            if weight is None:
                weight = CollaborativeWeight(node_id)
            if projection is None:
                projection = ProjectionVector(
                    node_id,
                    [1.0 / state_dim] * state_dim
                )
            
            op = LocalOperator(node_id, weight, projection)
            self._operators[node_id] = op
            self._weights[node_id] = weight
            self._projections[node_id] = projection
            self._trajectories[node_id] = StateTrajectory(node_id)
            
            return op
    
    def record_state(self, node_id: str, state: StateVector):
        """记录节点状态."""
        with self._lock:
            if node_id in self._trajectories:
                self._trajectories[node_id].add_state(state)
    
    async def execute(
        self,
        states: Dict[str, StateVector],
        t: Optional[float] = None
    ) -> ExecutionResult:
        """执行推理 - 核心入口.
        
        1. 应用所有算子
        2. 检查时空闭包
        3. 频域协调
        4. 返回聚合结果
        """
        start_time = time.time()
        current_t = t or time.time()
        
        # 记录状态
        for node_id, state in states.items():
            self.record_state(node_id, state)
        
        # 创建组合算子
        operators = [
            self._operators[nid]
            for nid in states.keys()
            if nid in self._operators
        ]
        composite = CompositeOperator(operators)
        
        # 执行
        coordination_decisions = []
        
        if self.context.mode == ExecutionMode.PARALLEL:
            results = await composite.parallel_apply(states, current_t)
            total_output = sum(r.output_value for r in results)
        
        elif self.context.mode == ExecutionMode.SEQUENTIAL:
            total_output, results = composite.linear_combine(states, t=current_t)
        
        else:  # ADAPTIVE
            # 先检查是否需要协调
            if self.context.enable_coordination and self._has_enough_history():
                signal = self._build_signal()
                decision = self.coordinator.analyze_and_coordinate(
                    signal, self._weights
                )
                coordination_decisions.append(decision)
                
                if decision.decision_type == "adjust_weight":
                    # 应用权重调整
                    self._weights = self.coordinator.apply_decision(
                        decision, self._weights
                    )
                    # 更新算子权重
                    for nid, new_weight in self._weights.items():
                        if nid in self._operators:
                            self._operators[nid].weight = new_weight
                
                # 根据决策选择执行模式
                if decision.parameters.get("safe_to_parallelize"):
                    results = await composite.parallel_apply(states, current_t)
                    total_output = sum(r.output_value for r in results)
                else:
                    total_output, results = composite.linear_combine(states, t=current_t)
            else:
                total_output, results = composite.linear_combine(states, t=current_t)
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            success=True,
            outputs={r.operator_id: r.output_value for r in results},
            total_output=total_output,
            execution_time=execution_time,
            operator_results=results,
            coordination_decisions=coordination_decisions,
            parallel_operations=len(results) if self.context.mode == ExecutionMode.PARALLEL else 0
        )
    
    def _has_enough_history(self, min_points: int = 5) -> bool:
        """检查是否有足够的历史数据."""
        for traj in self._trajectories.values():
            if len(traj.states) >= min_points:
                return True
        return False
    
    def _build_signal(self) -> CollaborativeSignal:
        """构建协同推理信号."""
        return CollaborativeSignal(
            self._trajectories,
            self._weights,
            self._projections
        )
    
    async def execute_sequence(
        self,
        state_sequence: List[Dict[str, StateVector]],
        interval: float = 0.0
    ) -> List[ExecutionResult]:
        """执行状态序列."""
        results = []
        
        for i, states in enumerate(state_sequence):
            t = time.time() + i * interval
            result = await self.execute(states, t)
            results.append(result)
            
            if interval > 0:
                await asyncio.sleep(interval)
        
        return results
    
    def analyze_execution(self) -> Dict[str, Any]:
        """分析执行情况."""
        # 构建信号并分析
        if not self._has_enough_history():
            return {"error": "Not enough history"}
        
        signal = self._build_signal()
        element = self.closure.create_element("execution", self._trajectories)
        anomaly = self.closure.detect_anomalies("execution")
        
        stability_trend = self.coordinator.get_stability_trend()
        
        return {
            "l2_norm": element.l2_norm,
            "stability": "stable" if not anomaly.get("anomaly_detected") else "unstable",
            "stability_trend": stability_trend,
            "anomaly_details": anomaly,
            "operator_stats": {
                nid: op.get_stats()
                for nid, op in self._operators.items()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计."""
        return {
            "num_operators": len(self._operators),
            "execution_mode": self.context.mode.value,
            "total_operations": self.context.total_operations,
            "coordination_decisions": self.context.coordination_decisions,
            "scheduler_queue_size": self.scheduler.get_queue_size(),
            "closure_stats": self.closure.get_stats()
        }


# ============================================================================
# Part 5: Integration with Agent System - 与Agent系统集成
# ============================================================================

class AgentOperator:
    """Agent算子 - 将Agent动作映射为Rⁿ中的算子."""
    
    def __init__(
        self,
        agent_id: str,
        action_func: Callable[[StateVector], Awaitable[Any]],
        state_dim: int = 10
    ):
        self.agent_id = agent_id
        self.action_func = action_func
        self.state_dim = state_dim
        
        # 内部的LocalOperator
        self.weight = CollaborativeWeight(agent_id)
        self.projection = ProjectionVector(
            agent_id,
            [1.0 / state_dim] * state_dim
        )
        self._local_op = LocalOperator(agent_id, self.weight, self.projection)
        
        # 状态追踪
        self.trajectory = StateTrajectory(agent_id)
    
    async def execute(
        self,
        input_data: Any,
        t: Optional[float] = None
    ) -> Tuple[Any, OperatorResult]:
        """执行Agent动作并返回算子结果."""
        current_t = t or time.time()
        
        # 将输入转换为状态向量
        state = self._to_state_vector(input_data, current_t)
        self.trajectory.add_state(state)
        
        # 执行动作
        action_result = await self.action_func(state)
        
        # 计算算子输出
        op_result = self._local_op.apply(state, current_t)
        
        return action_result, op_result
    
    def _to_state_vector(self, data: Any, t: float) -> StateVector:
        """将数据转换为状态向量."""
        if isinstance(data, StateVector):
            return data
        
        if isinstance(data, (list, tuple)):
            values = [float(v) for v in data[:self.state_dim]]
        elif isinstance(data, dict):
            values = [float(v) for v in list(data.values())[:self.state_dim]]
        else:
            # 尝试转换为浮点数
            try:
                val = float(data)
                values = [val] + [0.0] * (self.state_dim - 1)
            except:
                values = [0.0] * self.state_dim
        
        # 填充或截断
        while len(values) < self.state_dim:
            values.append(0.0)
        values = values[:self.state_dim]
        
        return StateVector(
            timestamp=t,
            values=values,
            node_id=self.agent_id
        )


class MultiAgentExecutionEngine:
    """多Agent执行引擎.
    
    整合:
    - 多个AgentOperator
    - 统一执行框架
    - 频域协调
    """
    
    def __init__(self):
        self.engine = UnifiedExecutionEngine()
        self._agent_operators: Dict[str, AgentOperator] = {}
    
    def register_agent(
        self,
        agent_id: str,
        action_func: Callable[[StateVector], Awaitable[Any]],
        state_dim: int = 10
    ) -> AgentOperator:
        """注册Agent."""
        agent_op = AgentOperator(agent_id, action_func, state_dim)
        self._agent_operators[agent_id] = agent_op
        
        # 注册到执行引擎
        self.engine.register_operator(
            agent_id,
            agent_op.weight,
            agent_op.projection,
            state_dim
        )
        
        return agent_op
    
    async def execute_all(
        self,
        inputs: Dict[str, Any],
        t: Optional[float] = None
    ) -> Dict[str, Any]:
        """执行所有Agent."""
        current_t = t or time.time()
        
        # 收集状态
        states = {}
        for agent_id, agent_op in self._agent_operators.items():
            if agent_id in inputs:
                state = agent_op._to_state_vector(inputs[agent_id], current_t)
                states[agent_id] = state
        
        # 执行
        result = await self.engine.execute(states, current_t)
        
        # 返回输出
        return {
            "outputs": result.outputs,
            "total": result.total_output,
            "execution_time": result.execution_time,
            "coordination_decisions": [
                {
                    "type": d.decision_type,
                    "reason": d.reason,
                    "confidence": d.confidence
                }
                for d in result.coordination_decisions
            ]
        }
    
    def analyze(self) -> Dict[str, Any]:
        """分析执行."""
        return self.engine.analyze_execution()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计."""
        return {
            "num_agents": len(self._agent_operators),
            "engine_stats": self.engine.get_stats()
        }


# ============================================================================
# Part 6: Helper Functions
# ============================================================================

def create_unified_engine(
    mode: ExecutionMode = ExecutionMode.ADAPTIVE,
    enable_coordination: bool = True
) -> UnifiedExecutionEngine:
    """创建统一执行引擎."""
    context = ExecutionContext(
        mode=mode,
        enable_coordination=enable_coordination
    )
    return UnifiedExecutionEngine(context)


def create_multi_agent_engine() -> MultiAgentExecutionEngine:
    """创建多Agent执行引擎."""
    return MultiAgentExecutionEngine()


async def example_usage():
    """示例用法."""
    # 创建引擎
    engine = create_multi_agent_engine()
    
    # 定义Agent动作
    async def agent_action(state: StateVector) -> str:
        # 模拟推理
        await asyncio.sleep(0.01)
        return f"Processed state with norm {state.norm():.4f}"
    
    # 注册Agent
    engine.register_agent("agent_1", agent_action, state_dim=5)
    engine.register_agent("agent_2", agent_action, state_dim=5)
    engine.register_agent("agent_3", agent_action, state_dim=5)
    
    # 执行多次以累积历史
    for i in range(10):
        inputs = {
            "agent_1": [0.1 * i, 0.2, 0.3, 0.4, 0.5],
            "agent_2": [0.5, 0.1 * i, 0.3, 0.2, 0.1],
            "agent_3": [0.3, 0.3, 0.1 * i, 0.1, 0.0]
        }
        
        result = await engine.execute_all(inputs)
        print(f"Step {i}: total={result['total']:.4f}")
    
    # 分析
    analysis = engine.analyze()
    print(f"\nAnalysis: {analysis}")


if __name__ == "__main__":
    asyncio.run(example_usage())
