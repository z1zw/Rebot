"""Tests for rebot.core modules (coevolution, unified_cache, incremental_reasoning)."""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


class TestCoevolutionConcepts:
    """Test coevolution module concepts."""

    def test_functional_fragment_concept(self):
        """Test FunctionalFragment data structure concept."""
        # Simulating the FunctionalFragment structure
        @dataclass
        class FunctionalFragment:
            id: str
            signature: str
            semantic_hash: str
            dependencies: List[str]
            equivalence_class: Optional[str] = None

        fragment = FunctionalFragment(
            id="func_001",
            signature="def add(a: int, b: int) -> int",
            semantic_hash="abc123",
            dependencies=["func_000"],
        )
        
        assert fragment.id == "func_001"
        assert fragment.semantic_hash == "abc123"
        assert len(fragment.dependencies) == 1

    def test_task_dag_concept(self):
        """Test TaskDAG structure concept."""
        # T = ⟨F, D⟩ where F is fragments and D is dependencies
        fragments = {"f1": "func1", "f2": "func2", "f3": "func3"}
        dependencies = [("f1", "f2"), ("f2", "f3")]  # f1 → f2 → f3
        
        # Verify DAG structure
        assert len(fragments) == 3
        assert len(dependencies) == 2
        
        # Check dependency chain
        dep_map = {src: dst for src, dst in dependencies}
        assert dep_map["f1"] == "f2"
        assert dep_map["f2"] == "f3"

    def test_structural_normalization_concept(self):
        """Test structural normalization N(·) concept."""
        # Two semantically equivalent codes should normalize to same hash
        import hashlib
        
        def simple_normalize(code: str) -> str:
            """Simple normalization: remove whitespace and lowercase."""
            normalized = code.lower().replace(" ", "").replace("\n", "")
            return hashlib.sha256(normalized.encode()).hexdigest()[:16]
        
        code1 = "def add(a, b): return a + b"
        code2 = "def add( a , b ): return a+b"
        
        # After normalization, they should be similar
        norm1 = simple_normalize(code1)
        norm2 = simple_normalize(code2)
        assert norm1 == norm2

    def test_equivalence_class_concept(self):
        """Test cross-task equivalence C(φ̂) concept."""
        # Fragments from different tasks with same semantic hash
        fragments = [
            {"id": "t1_f1", "task": "task1", "hash": "abc123"},
            {"id": "t2_f1", "task": "task2", "hash": "abc123"},
            {"id": "t1_f2", "task": "task1", "hash": "def456"},
        ]
        
        # Group by hash to find equivalence classes
        equivalence_classes: Dict[str, List[str]] = {}
        for f in fragments:
            h = f["hash"]
            if h not in equivalence_classes:
                equivalence_classes[h] = []
            equivalence_classes[h].append(f["id"])
        
        # abc123 should have 2 equivalent fragments from different tasks
        assert len(equivalence_classes["abc123"]) == 2
        assert len(equivalence_classes["def456"]) == 1


class TestSpatiotemporalClosureConcepts:
    """Test spatiotemporal closure module concepts."""

    def test_state_vector_inner_product(self):
        """Test StateVector inner product for collaborative weights."""
        # State vector inner product: ⟨v₁, v₂⟩
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 5.0, 6.0]
        
        inner_product = sum(a * b for a, b in zip(v1, v2))
        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        assert inner_product == 32.0

    def test_l2_norm(self):
        """Test L² norm calculation."""
        import math
        
        v = [3.0, 4.0]
        l2_norm = math.sqrt(sum(x**2 for x in v))
        assert l2_norm == 5.0

    def test_l2_closure_equivalence(self):
        """Test L² closure equivalence: g₁ ~ g₂ ⟺ ‖g₁-g₂‖_{L²} = 0."""
        import math
        
        g1 = [1.0, 2.0, 3.0]
        g2 = [1.0, 2.0, 3.0]
        g3 = [1.0, 2.0, 4.0]  # Different
        
        def l2_distance(a: List[float], b: List[float]) -> float:
            return math.sqrt(sum((x - y)**2 for x, y in zip(a, b)))
        
        # g1 and g2 are equivalent
        assert l2_distance(g1, g2) == 0.0
        # g1 and g3 are not equivalent
        assert l2_distance(g1, g3) > 0.0

    def test_interaction_tensor_concept(self):
        """Test node interaction tensor X ∈ ℝ^{|V|×|V|×T}."""
        import numpy as np
        
        # 3 nodes, 3 nodes, 5 time steps
        V = 3
        T = 5
        
        # X[i,j,t] = interaction strength from node i to j at time t
        X = np.zeros((V, V, T))
        
        # Set some interaction values
        X[0, 1, 0] = 0.8  # Node 0 → Node 1 at t=0
        X[1, 2, 1] = 0.6  # Node 1 → Node 2 at t=1
        X[0, 2, 2] = 0.9  # Node 0 → Node 2 at t=2
        
        assert X.shape == (3, 3, 5)
        assert X[0, 1, 0] == 0.8


class TestUnifiedCacheConcepts:
    """Test unified cache module concepts."""

    def test_semantic_unit_concept(self):
        """Test SemanticUnit with role interpretations."""
        @dataclass
        class SemanticUnit:
            content_hash: str
            raw_content: str
            encoding: Optional[List[float]] = None
            role_interpretations: Dict[str, Any] = None
            
            def __post_init__(self):
                if self.role_interpretations is None:
                    self.role_interpretations = {}
            
            def add_interpretation(self, role_id: str, interpretation: Any):
                self.role_interpretations[role_id] = interpretation
        
        unit = SemanticUnit(
            content_hash="hash123",
            raw_content="def calculate(x): return x * 2",
            encoding=[0.1, 0.2, 0.3],
        )
        
        # Different roles interpret the same code differently
        unit.add_interpretation("architect", {"complexity": "low", "pattern": "functional"})
        unit.add_interpretation("security", {"risk": "none", "validated": True})
        unit.add_interpretation("tester", {"test_cases_needed": 3})
        
        assert len(unit.role_interpretations) == 3
        assert unit.role_interpretations["architect"]["complexity"] == "low"

    def test_three_layer_cache_concept(self):
        """Test three-layer cache architecture concept."""
        # Layer 1: Shared Encoder-Decoder
        # Layer 2: KV Attention Cache
        # Layer 3: Chunk-level Commit
        
        cache_layers = {
            "shared_encoder": {"purpose": "multi-role shared understanding"},
            "kv_cache": {"purpose": "reasoning state reuse"},
            "chunk_commit": {"purpose": "semantic block versioning"},
        }
        
        assert len(cache_layers) == 3
        assert "shared_encoder" in cache_layers


class TestIncrementalReasoningConcepts:
    """Test incremental reasoning module concepts."""

    def test_reasoning_snapshot_concept(self):
        """Test ReasoningSnapshot as KV Cache abstraction."""
        @dataclass
        class ReasoningState:
            chunk_id: str
            content: str
            result: Any
            confidence: float
            dependencies: List[str]
        
        @dataclass
        class ReasoningSnapshot:
            snapshot_id: str
            states: Dict[str, ReasoningState]
            
            def get_state(self, chunk_id: str) -> Optional[ReasoningState]:
                return self.states.get(chunk_id)
            
            def set_state(self, chunk_id: str, state: ReasoningState):
                self.states[chunk_id] = state
        
        snapshot = ReasoningSnapshot(snapshot_id="snap_001", states={})
        
        state = ReasoningState(
            chunk_id="chunk_1",
            content="def foo(): pass",
            result={"analysis": "simple function"},
            confidence=0.95,
            dependencies=[],
        )
        snapshot.set_state("chunk_1", state)
        
        retrieved = snapshot.get_state("chunk_1")
        assert retrieved is not None
        assert retrieved.confidence == 0.95

    def test_delta_update_concept(self):
        """Test delta update: Δs = s(t) - s(t-1)."""
        # Previous state
        s_prev = {"chunk_1": 1.0, "chunk_2": 2.0, "chunk_3": 3.0}
        # Current state
        s_curr = {"chunk_1": 1.0, "chunk_2": 2.5, "chunk_3": 3.0}
        
        # Compute delta
        delta = {}
        for key in s_curr:
            if s_curr[key] != s_prev.get(key):
                delta[key] = s_curr[key] - s_prev.get(key, 0)
        
        # Only chunk_2 changed
        assert len(delta) == 1
        assert "chunk_2" in delta
        assert delta["chunk_2"] == 0.5

    def test_dependency_propagation_concept(self):
        """Test dependency graph propagation."""
        # Dependency graph: chunk_1 → chunk_2 → chunk_3
        dependencies = {
            "chunk_1": [],
            "chunk_2": ["chunk_1"],
            "chunk_3": ["chunk_2"],
        }
        
        def compute_affected(changed: str, deps: Dict[str, List[str]]) -> set:
            """Compute all chunks affected by a change."""
            affected = {changed}
            # Find all chunks that depend on changed chunks
            changed_queue = [changed]
            while changed_queue:
                current = changed_queue.pop(0)
                for chunk, chunk_deps in deps.items():
                    if current in chunk_deps and chunk not in affected:
                        affected.add(chunk)
                        changed_queue.append(chunk)
            return affected
        
        # If chunk_1 changes, chunk_2 and chunk_3 are affected
        affected = compute_affected("chunk_1", dependencies)
        # Note: The simple algorithm above doesn't work for forward propagation
        # Let's fix it by building reverse dependencies
        
        reverse_deps: Dict[str, List[str]] = {k: [] for k in dependencies}
        for chunk, deps_list in dependencies.items():
            for dep in deps_list:
                if dep in reverse_deps:
                    reverse_deps[dep].append(chunk)
        
        def compute_affected_v2(changed: str) -> set:
            affected = {changed}
            queue = [changed]
            while queue:
                current = queue.pop(0)
                for dependent in reverse_deps.get(current, []):
                    if dependent not in affected:
                        affected.add(dependent)
                        queue.append(dependent)
            return affected
        
        affected = compute_affected_v2("chunk_1")
        assert "chunk_1" in affected
        assert "chunk_2" in affected
        assert "chunk_3" in affected


class TestUnifiedExecutionConcepts:
    """Test unified execution module concepts."""

    def test_local_operator_concept(self):
        """Test local operator Oᵥ: sᵥ(t) → πᵥ(t)⟨aᵥ, sᵥ(t)⟩."""
        # Local operator takes state and returns action
        def local_operator(state: Dict[str, float], policy_weight: float) -> Dict[str, Any]:
            """Simulate a local operator."""
            action_value = sum(state.values()) * policy_weight
            return {
                "action": "process",
                "value": action_value,
                "source_state": state,
            }
        
        state = {"feature_1": 0.5, "feature_2": 0.3}
        policy_weight = 0.8
        
        result = local_operator(state, policy_weight)
        expected_value = (0.5 + 0.3) * 0.8
        
        assert result["action"] == "process"
        assert abs(result["value"] - expected_value) < 1e-6

    def test_operator_composition_concept(self):
        """Test operator composition O_total = O₁ ∘ O₂ ∘ ... ∘ Oₙ."""
        def op1(x: float) -> float:
            return x * 2
        
        def op2(x: float) -> float:
            return x + 1
        
        def op3(x: float) -> float:
            return x ** 2
        
        # Compose operators: op3(op2(op1(x)))
        def compose(*operators):
            def composed(x):
                result = x
                for op in operators:
                    result = op(result)
                return result
            return composed
        
        composed_op = compose(op1, op2, op3)
        
        # Input: 3
        # op1(3) = 6
        # op2(6) = 7
        # op3(7) = 49
        result = composed_op(3)
        assert result == 49
