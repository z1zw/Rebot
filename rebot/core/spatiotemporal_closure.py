"""Spatiotemporal Compositional Closure - 时空复合闭包.

理论基础:
模型推理通常基于多节点、多时间步与多状态的协同计算过程。
在该过程中，推理状态在不同节点之间传播、叠加与切换。

核心公式:
1. 协同推理信号的频域表示:
   ĝ(ξ) = F{g}(ξ) = ∫[0,T] (Σᵥπᵥ(t)⟨aᵥ,sᵥ(t)⟩) e^(-2πiξt) dt

2. 节点交互张量:
   X ∈ ℝ^{|V|×|V|×T}, X_{u,v}(t) = ψ(sᵤ(t), sᵥ(t))

3. 频谱能量:
   Eₘ = ∫|ĝ(ξ)|² dξ

4. L²闭包下的等价关系:
   g₁ ~ g₂ ⟺ ‖g₁-g₂‖_{L²} = 0

Agent层实现:
- 节点状态 sᵥ(t) = Agent的推理状态轨迹
- 协同权重 πᵥ(t) = Agent的可靠性/优先级
- 频域分析 = 检测推理稳定性/异常/幻觉
- L²闭包 = 不同推理路径的等价性判断
"""

from __future__ import annotations

import asyncio
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional, 
    Set, Tuple, TypeVar, Union
)
from enum import Enum
from collections import defaultdict
import threading
import logging

# 数值计算
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # 简单的numpy替代
    class np:
        @staticmethod
        def array(x):
            return list(x)
        @staticmethod
        def zeros(shape):
            if isinstance(shape, tuple):
                return [[0.0] * shape[1] for _ in range(shape[0])]
            return [0.0] * shape
        @staticmethod
        def sum(x):
            if isinstance(x, list):
                return sum(x)
            return x
        @staticmethod
        def sqrt(x):
            return math.sqrt(x)
        @staticmethod
        def abs(x):
            if isinstance(x, list):
                return [abs(i) for i in x]
            return abs(x)

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Reasoning State Trajectory - 推理状态轨迹
# ============================================================================

@dataclass
class StateVector:
    """状态向量 sᵥ(t) ∈ ℝᵈ.
    
    表示节点v在时刻t的推理状态.
    可以包含: 置信度, 风险, 残差等.
    """
    timestamp: float
    values: List[float]
    
    # 元信息
    node_id: str = ""
    state_type: str = "generic"
    
    @property
    def dimension(self) -> int:
        return len(self.values)
    
    def dot(self, other: "StateVector") -> float:
        """内积 ⟨a, s⟩."""
        if len(self.values) != len(other.values):
            raise ValueError("Dimension mismatch")
        return sum(a * b for a, b in zip(self.values, other.values))
    
    def norm(self) -> float:
        """范数 ‖s‖."""
        return math.sqrt(sum(v * v for v in self.values))
    
    def __sub__(self, other: "StateVector") -> "StateVector":
        """向量减法."""
        return StateVector(
            timestamp=self.timestamp,
            values=[a - b for a, b in zip(self.values, other.values)],
            node_id=self.node_id
        )


@dataclass
class StateTrajectory:
    """状态轨迹 {sᵥ(t) | t ∈ [0,T]}.
    
    节点在时间窗口内的状态演化.
    """
    node_id: str
    states: List[StateVector] = field(default_factory=list)
    
    # 时间窗口
    start_time: float = 0.0
    end_time: float = 0.0
    
    def add_state(self, state: StateVector):
        """添加状态点."""
        state.node_id = self.node_id
        self.states.append(state)
        
        if not self.start_time or state.timestamp < self.start_time:
            self.start_time = state.timestamp
        if state.timestamp > self.end_time:
            self.end_time = state.timestamp
    
    def get_state_at(self, t: float) -> Optional[StateVector]:
        """获取时刻t的状态(线性插值)."""
        if not self.states:
            return None
        
        # 找到最近的两个状态点
        before = None
        after = None
        
        for s in self.states:
            if s.timestamp <= t:
                before = s
            if s.timestamp >= t and after is None:
                after = s
        
        if before is None:
            return self.states[0]
        if after is None:
            return self.states[-1]
        if before.timestamp == after.timestamp:
            return before
        
        # 线性插值
        alpha = (t - before.timestamp) / (after.timestamp - before.timestamp)
        interpolated = [
            (1 - alpha) * b + alpha * a 
            for b, a in zip(before.values, after.values)
        ]
        
        return StateVector(
            timestamp=t,
            values=interpolated,
            node_id=self.node_id
        )
    
    def duration(self) -> float:
        """轨迹持续时间 T."""
        return self.end_time - self.start_time


# ============================================================================
# Part 2: Collaborative Reasoning Signal - 协同推理信号
# ============================================================================

@dataclass
class CollaborativeWeight:
    """协同推理权重 πᵥ(t).
    
    表示节点在协同推理中的重要性.
    """
    node_id: str
    weight_function: Callable[[float], float] = field(default=lambda t: 1.0)
    
    # 预定义的权重值
    weights: Dict[float, float] = field(default_factory=dict)
    
    def get_weight(self, t: float) -> float:
        """获取时刻t的权重."""
        if t in self.weights:
            return self.weights[t]
        return self.weight_function(t)
    
    def set_weight(self, t: float, w: float):
        """设置特定时刻的权重."""
        self.weights[t] = w


@dataclass
class ProjectionVector:
    """投影向量 aᵥ ∈ ℝᵈ.
    
    用于将状态投影到标量信号.
    """
    node_id: str
    values: List[float]
    
    def project(self, state: StateVector) -> float:
        """投影 ⟨aᵥ, sᵥ(t)⟩."""
        return sum(a * s for a, s in zip(self.values, state.values))


class CollaborativeSignal:
    """协同推理信号 g(t).
    
    g(t) = Σᵥ πᵥ(t)⟨aᵥ, sᵥ(t)⟩
    """
    
    def __init__(
        self,
        trajectories: Dict[str, StateTrajectory],
        weights: Dict[str, CollaborativeWeight],
        projections: Dict[str, ProjectionVector]
    ):
        self.trajectories = trajectories
        self.weights = weights
        self.projections = projections
        
        # 确定时间窗口
        self.start_time = min(t.start_time for t in trajectories.values())
        self.end_time = max(t.end_time for t in trajectories.values())
    
    def evaluate(self, t: float) -> float:
        """计算 g(t) = Σᵥ πᵥ(t)⟨aᵥ, sᵥ(t)⟩."""
        total = 0.0
        
        for node_id, trajectory in self.trajectories.items():
            state = trajectory.get_state_at(t)
            if state is None:
                continue
            
            weight = self.weights.get(node_id, CollaborativeWeight(node_id)).get_weight(t)
            projection = self.projections.get(node_id)
            
            if projection:
                contribution = weight * projection.project(state)
            else:
                # 默认取状态范数
                contribution = weight * state.norm()
            
            total += contribution
        
        return total
    
    def sample(self, num_points: int = 100) -> Tuple[List[float], List[float]]:
        """采样信号."""
        times = [
            self.start_time + i * (self.end_time - self.start_time) / (num_points - 1)
            for i in range(num_points)
        ]
        values = [self.evaluate(t) for t in times]
        return times, values


# ============================================================================
# Part 3: Fourier Transform and Spectral Analysis - 傅里叶变换与频谱分析
# ============================================================================

@dataclass
class FrequencyComponent:
    """频率分量."""
    frequency: float  # ξ
    magnitude: float  # |ĝ(ξ)|
    phase: float = 0.0


@dataclass
class SpectralRepresentation:
    """频域表示 ĝ(ξ).
    
    ĝ(ξ) = ∫[0,T] g(t) e^(-2πiξt) dt
    """
    components: List[FrequencyComponent] = field(default_factory=list)
    
    # 频谱能量
    total_energy: float = 0.0
    
    # 分析结果
    dominant_frequency: Optional[float] = None
    high_frequency_ratio: float = 0.0
    low_frequency_ratio: float = 0.0
    
    def add_component(self, freq: float, mag: float, phase: float = 0.0):
        """添加频率分量."""
        self.components.append(FrequencyComponent(freq, mag, phase))
    
    def compute_energy(self) -> float:
        """计算频谱能量 Eₘ = ∫|ĝ(ξ)|² dξ."""
        self.total_energy = sum(c.magnitude ** 2 for c in self.components)
        return self.total_energy
    
    def analyze(self, high_freq_threshold: float = 0.5):
        """分析频谱特征."""
        if not self.components:
            return
        
        # 找主频
        max_mag = max(self.components, key=lambda c: c.magnitude)
        self.dominant_frequency = max_mag.frequency
        
        # 计算高低频能量比
        total = self.compute_energy()
        if total == 0:
            return
        
        max_freq = max(c.frequency for c in self.components)
        threshold_freq = max_freq * high_freq_threshold
        
        high_energy = sum(c.magnitude ** 2 for c in self.components if abs(c.frequency) > threshold_freq)
        low_energy = total - high_energy
        
        self.high_frequency_ratio = high_energy / total
        self.low_frequency_ratio = low_energy / total


class FourierAnalyzer:
    """傅里叶分析器.
    
    将协同推理信号转换到频域.
    """
    
    def __init__(self, num_frequencies: int = 64):
        self.num_frequencies = num_frequencies
    
    def transform(self, signal: CollaborativeSignal) -> SpectralRepresentation:
        """离散傅里叶变换.
        
        ĝ(ξ) = ∫[0,T] g(t) e^(-2πiξt) dt
        """
        times, values = signal.sample(self.num_frequencies * 2)
        T = signal.end_time - signal.start_time
        
        result = SpectralRepresentation()
        
        # DFT
        N = len(values)
        for k in range(self.num_frequencies):
            freq = k / T  # 频率
            
            real_sum = 0.0
            imag_sum = 0.0
            
            for n, (t, v) in enumerate(zip(times, values)):
                angle = -2 * math.pi * freq * (t - signal.start_time)
                real_sum += v * math.cos(angle)
                imag_sum += v * math.sin(angle)
            
            magnitude = math.sqrt(real_sum ** 2 + imag_sum ** 2) / N
            phase = math.atan2(imag_sum, real_sum)
            
            result.add_component(freq, magnitude, phase)
        
        result.analyze()
        return result
    
    def detect_anomaly(
        self,
        spectral: SpectralRepresentation,
        high_freq_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """检测异常 - 基于频谱特征.
        
        高频能量集中 → 推理不稳定/幻觉
        低频主导 → 推理稳定
        """
        analysis = {
            "total_energy": spectral.total_energy,
            "dominant_frequency": spectral.dominant_frequency,
            "high_frequency_ratio": spectral.high_frequency_ratio,
            "low_frequency_ratio": spectral.low_frequency_ratio,
        }
        
        # 异常判断
        if spectral.high_frequency_ratio > high_freq_threshold:
            analysis["anomaly_detected"] = True
            analysis["anomaly_type"] = "high_frequency_instability"
            analysis["severity"] = spectral.high_frequency_ratio
        else:
            analysis["anomaly_detected"] = False
        
        return analysis


# ============================================================================
# Part 4: Interaction Tensor - 交互张量
# ============================================================================

class InteractionFunction:
    """交互函数 ψ(sᵤ(t), sᵥ(t))."""
    
    @staticmethod
    def cosine_similarity(s1: StateVector, s2: StateVector) -> float:
        """余弦相似度."""
        norm1 = s1.norm()
        norm2 = s2.norm()
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return s1.dot(s2) / (norm1 * norm2)
    
    @staticmethod
    def euclidean_distance(s1: StateVector, s2: StateVector) -> float:
        """欧氏距离."""
        diff = s1 - s2
        return diff.norm()
    
    @staticmethod
    def correlation(s1: StateVector, s2: StateVector) -> float:
        """相关性."""
        if len(s1.values) != len(s2.values):
            return 0.0
        
        n = len(s1.values)
        mean1 = sum(s1.values) / n
        mean2 = sum(s2.values) / n
        
        cov = sum((a - mean1) * (b - mean2) for a, b in zip(s1.values, s2.values))
        var1 = sum((a - mean1) ** 2 for a in s1.values)
        var2 = sum((b - mean2) ** 2 for b in s2.values)
        
        if var1 == 0 or var2 == 0:
            return 0.0
        
        return cov / math.sqrt(var1 * var2)


@dataclass
class InteractionTensor:
    """交互张量 X ∈ ℝ^{|V|×|V|×T}.
    
    X_{u,v}(t) = ψ(sᵤ(t), sᵥ(t))
    """
    node_ids: List[str]
    time_points: List[float]
    
    # 张量数据: [u_idx][v_idx][t_idx]
    data: List[List[List[float]]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.data:
            n = len(self.node_ids)
            t = len(self.time_points)
            self.data = [
                [[0.0 for _ in range(t)] for _ in range(n)]
                for _ in range(n)
            ]
    
    def set_interaction(self, u_idx: int, v_idx: int, t_idx: int, value: float):
        """设置交互值."""
        self.data[u_idx][v_idx][t_idx] = value
    
    def get_interaction(self, u_idx: int, v_idx: int, t_idx: int) -> float:
        """获取交互值."""
        return self.data[u_idx][v_idx][t_idx]
    
    def get_node_interactions(self, node_idx: int, t_idx: int) -> List[float]:
        """获取节点与其他所有节点的交互."""
        return [self.data[node_idx][v][t_idx] for v in range(len(self.node_ids))]
    
    def aggregate_over_time(self) -> List[List[float]]:
        """时间聚合 - 平均交互强度."""
        n = len(self.node_ids)
        t = len(self.time_points)
        
        result = [[0.0] * n for _ in range(n)]
        
        for u in range(n):
            for v in range(n):
                result[u][v] = sum(self.data[u][v]) / t
        
        return result


class InteractionAnalyzer:
    """交互分析器."""
    
    def __init__(
        self,
        interaction_func: Callable[[StateVector, StateVector], float] = None
    ):
        self.interaction_func = interaction_func or InteractionFunction.cosine_similarity
    
    def build_tensor(
        self,
        trajectories: Dict[str, StateTrajectory],
        time_points: List[float]
    ) -> InteractionTensor:
        """构建交互张量."""
        node_ids = list(trajectories.keys())
        tensor = InteractionTensor(node_ids=node_ids, time_points=time_points)
        
        for t_idx, t in enumerate(time_points):
            for u_idx, u_id in enumerate(node_ids):
                u_state = trajectories[u_id].get_state_at(t)
                if u_state is None:
                    continue
                
                for v_idx, v_id in enumerate(node_ids):
                    v_state = trajectories[v_id].get_state_at(t)
                    if v_state is None:
                        continue
                    
                    interaction = self.interaction_func(u_state, v_state)
                    tensor.set_interaction(u_idx, v_idx, t_idx, interaction)
        
        return tensor
    
    def analyze_structure(self, tensor: InteractionTensor) -> Dict[str, Any]:
        """分析交互结构."""
        n = len(tensor.node_ids)
        t = len(tensor.time_points)
        
        # 聚合
        avg_interactions = tensor.aggregate_over_time()
        
        # 找出主要交互
        max_interaction = 0.0
        main_pair = None
        
        for u in range(n):
            for v in range(n):
                if u != v and avg_interactions[u][v] > max_interaction:
                    max_interaction = avg_interactions[u][v]
                    main_pair = (tensor.node_ids[u], tensor.node_ids[v])
        
        # 计算中心性
        centrality = []
        for u in range(n):
            total = sum(avg_interactions[u][v] for v in range(n) if u != v)
            centrality.append((tensor.node_ids[u], total / max(1, n - 1)))
        
        centrality.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "num_nodes": n,
            "num_time_points": t,
            "main_interaction_pair": main_pair,
            "max_interaction_strength": max_interaction,
            "centrality_ranking": centrality,
            "most_central_node": centrality[0][0] if centrality else None
        }


# ============================================================================
# Part 5: L² Closure and Equivalence - L²闭包与等价关系
# ============================================================================

class L2Space:
    """L²([0,T]) 函数空间.
    
    支持:
    - 范数计算
    - 等价关系判断
    - 闭包验证
    """
    
    def __init__(self, tolerance: float = 1e-6):
        self.tolerance = tolerance
    
    def norm(self, signal: CollaborativeSignal, num_samples: int = 100) -> float:
        """计算L²范数 ‖g‖_{L²}.
        
        ‖g‖² = ∫[0,T] |g(t)|² dt
        """
        times, values = signal.sample(num_samples)
        dt = (signal.end_time - signal.start_time) / (num_samples - 1)
        
        # 数值积分 (梯形法则)
        integral = 0.0
        for i in range(len(values) - 1):
            integral += (values[i] ** 2 + values[i + 1] ** 2) / 2 * dt
        
        return math.sqrt(integral)
    
    def distance(
        self,
        signal1: CollaborativeSignal,
        signal2: CollaborativeSignal,
        num_samples: int = 100
    ) -> float:
        """计算L²距离 ‖g₁ - g₂‖_{L²}."""
        # 统一时间窗口
        start = min(signal1.start_time, signal2.start_time)
        end = max(signal1.end_time, signal2.end_time)
        
        dt = (end - start) / (num_samples - 1)
        times = [start + i * dt for i in range(num_samples)]
        
        integral = 0.0
        for i, t in enumerate(times[:-1]):
            v1 = signal1.evaluate(t)
            v2 = signal2.evaluate(t)
            diff_sq_1 = (v1 - v2) ** 2
            
            t_next = times[i + 1]
            v1_next = signal1.evaluate(t_next)
            v2_next = signal2.evaluate(t_next)
            diff_sq_2 = (v1_next - v2_next) ** 2
            
            integral += (diff_sq_1 + diff_sq_2) / 2 * dt
        
        return math.sqrt(integral)
    
    def are_equivalent(
        self,
        signal1: CollaborativeSignal,
        signal2: CollaborativeSignal
    ) -> bool:
        """判断等价关系 g₁ ~ g₂ ⟺ ‖g₁-g₂‖_{L²} = 0."""
        dist = self.distance(signal1, signal2)
        return dist < self.tolerance
    
    def verify_closure(
        self,
        signals: List[CollaborativeSignal],
        operation: str = "sum"
    ) -> bool:
        """验证闭包性质.
        
        验证: 有限个L²函数的线性组合仍在L²中.
        """
        # 所有信号的范数都有限 → 线性组合也有限
        for signal in signals:
            norm = self.norm(signal)
            if math.isinf(norm) or math.isnan(norm):
                return False
        
        return True


# ============================================================================
# Part 6: Spatiotemporal Closure System - 时空复合闭包系统
# ============================================================================

@dataclass
class ClosureElement:
    """闭包元素 - 可组合的推理单元."""
    id: str
    signal: CollaborativeSignal
    spectral: Optional[SpectralRepresentation] = None
    
    # 闭包性质
    l2_norm: float = 0.0
    equivalence_class: Optional[str] = None


class SpatiotemporalClosure:
    """时空复合闭包系统.
    
    核心功能:
    1. 将推理过程映射为L²空间中的元素
    2. 验证闭包性质
    3. 定义等价关系
    4. 频域分析
    """
    
    def __init__(self, tolerance: float = 1e-6):
        self.l2_space = L2Space(tolerance)
        self.fourier = FourierAnalyzer()
        self.interaction_analyzer = InteractionAnalyzer()
        
        self._elements: Dict[str, ClosureElement] = {}
        self._equivalence_classes: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
    
    def create_element(
        self,
        element_id: str,
        trajectories: Dict[str, StateTrajectory],
        weights: Optional[Dict[str, CollaborativeWeight]] = None,
        projections: Optional[Dict[str, ProjectionVector]] = None
    ) -> ClosureElement:
        """创建闭包元素."""
        # 默认权重和投影
        if weights is None:
            weights = {nid: CollaborativeWeight(nid) for nid in trajectories}
        
        if projections is None:
            projections = {}
            for nid, traj in trajectories.items():
                if traj.states:
                    dim = traj.states[0].dimension
                    projections[nid] = ProjectionVector(
                        nid,
                        [1.0 / dim] * dim  # 均匀投影
                    )
        
        # 构建信号
        signal = CollaborativeSignal(trajectories, weights, projections)
        
        # 频域分析
        spectral = self.fourier.transform(signal)
        
        # 计算范数
        l2_norm = self.l2_space.norm(signal)
        
        element = ClosureElement(
            id=element_id,
            signal=signal,
            spectral=spectral,
            l2_norm=l2_norm
        )
        
        with self._lock:
            self._elements[element_id] = element
        
        return element
    
    def find_equivalence_class(self, element: ClosureElement) -> str:
        """找到或创建等价类."""
        with self._lock:
            # 检查是否与现有元素等价
            for class_id, members in self._equivalence_classes.items():
                representative_id = next(iter(members))
                representative = self._elements.get(representative_id)
                
                if representative and self.l2_space.are_equivalent(
                    element.signal, representative.signal
                ):
                    self._equivalence_classes[class_id].add(element.id)
                    element.equivalence_class = class_id
                    return class_id
            
            # 创建新等价类
            class_id = f"eq_class_{len(self._equivalence_classes)}"
            self._equivalence_classes[class_id].add(element.id)
            element.equivalence_class = class_id
            return class_id
    
    def combine(
        self,
        element_ids: List[str],
        weights: Optional[List[float]] = None,
        new_id: Optional[str] = None
    ) -> ClosureElement:
        """组合元素 (线性组合).
        
        验证: 组合结果仍在L²空间中 (闭包性质).
        """
        if weights is None:
            weights = [1.0] * len(element_ids)
        
        elements = [self._elements[eid] for eid in element_ids]
        
        # 验证闭包
        if not self.l2_space.verify_closure([e.signal for e in elements]):
            raise ValueError("Closure violation: combined signal not in L²")
        
        # 组合轨迹
        combined_trajectories = {}
        combined_weights = {}
        combined_projections = {}
        
        for elem, w in zip(elements, weights):
            for nid, traj in elem.signal.trajectories.items():
                combined_key = f"{elem.id}_{nid}"
                combined_trajectories[combined_key] = traj
                combined_weights[combined_key] = CollaborativeWeight(
                    combined_key,
                    lambda t, w=w: w * elem.signal.weights[nid].get_weight(t)
                )
                if nid in elem.signal.projections:
                    combined_projections[combined_key] = elem.signal.projections[nid]
        
        new_element_id = new_id or f"combined_{int(time.time()*1000)}"
        
        return self.create_element(
            new_element_id,
            combined_trajectories,
            combined_weights,
            combined_projections
        )
    
    def detect_anomalies(
        self,
        element_id: str,
        high_freq_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """检测异常."""
        element = self._elements.get(element_id)
        if not element or not element.spectral:
            return {"error": "Element not found or no spectral data"}
        
        return self.fourier.detect_anomaly(element.spectral, high_freq_threshold)
    
    def compare_elements(
        self,
        id1: str,
        id2: str
    ) -> Dict[str, Any]:
        """比较两个元素."""
        e1 = self._elements.get(id1)
        e2 = self._elements.get(id2)
        
        if not e1 or not e2:
            return {"error": "Element not found"}
        
        distance = self.l2_space.distance(e1.signal, e2.signal)
        equivalent = self.l2_space.are_equivalent(e1.signal, e2.signal)
        
        return {
            "element_1": id1,
            "element_2": id2,
            "l2_distance": distance,
            "equivalent": equivalent,
            "norm_1": e1.l2_norm,
            "norm_2": e2.l2_norm,
            "equivalence_class_1": e1.equivalence_class,
            "equivalence_class_2": e2.equivalence_class
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计."""
        return {
            "num_elements": len(self._elements),
            "num_equivalence_classes": len(self._equivalence_classes),
            "elements": {
                eid: {
                    "l2_norm": e.l2_norm,
                    "equivalence_class": e.equivalence_class,
                    "has_spectral": e.spectral is not None
                }
                for eid, e in self._elements.items()
            }
        }


# ============================================================================
# Part 7: Helper Functions
# ============================================================================

def create_spatiotemporal_closure(tolerance: float = 1e-6) -> SpatiotemporalClosure:
    """创建时空复合闭包系统."""
    return SpatiotemporalClosure(tolerance)


def analyze_reasoning_stability(trajectories: Dict[str, StateTrajectory]) -> Dict[str, Any]:
    """分析推理稳定性.
    
    基于频域特征判断:
    - 高频能量高 → 不稳定/可能有幻觉
    - 低频主导 → 稳定
    """
    closure = create_spatiotemporal_closure()
    element = closure.create_element("analysis", trajectories)
    
    anomaly = closure.detect_anomalies("analysis")
    
    return {
        "l2_norm": element.l2_norm,
        "spectral_energy": element.spectral.total_energy if element.spectral else 0,
        "dominant_frequency": element.spectral.dominant_frequency if element.spectral else None,
        "stability": "unstable" if anomaly.get("anomaly_detected") else "stable",
        "high_frequency_ratio": anomaly.get("high_frequency_ratio", 0),
        "anomaly_details": anomaly
    }
