"""Rebot Core Module - 核心组件.

包含核心技术实现:
1. Unified Cache - 统一语义缓存 (Shared Encoder-Decoder)
2. Incremental Reasoning - 增量推理 (KV Attention Cache)
3. Chunk Operations - 块级代码操作 (Chunk-level Commit)
4. Advanced Coding - 高级代码引擎
5. Co-Evolution - 多Agent协同演化与一致性保证
6. Spatiotemporal Closure - 时空复合闭包 over R^n
7. Unified Execution - Rⁿ上的统一执行与协调机制
"""

# ============================================================================
# Unified Cache - 统一语义缓存
# ============================================================================
from rebot.core.unified_cache import (
    # 语义类型
    SemanticType,
    SemanticUnit,
    
    # 共享编码器
    SharedEncoder,
    
    # KV缓存
    CacheEntry,
    ReasoningKVCache,
    
    # 代码块
    ChunkType,
    CodeChunk,
    ChunkOperation,
    ChunkEdit,
    ChunkCommit,
    ChunkManager,
    
    # 统一缓存
    UnifiedCache,
    get_unified_cache,
    
    # 辅助
    CachedReasoning,
    chunk_aware_edit,
)

# ============================================================================
# Incremental Reasoning - 增量推理
# ============================================================================
from rebot.core.incremental_reasoning import (
    # 推理状态
    ReasoningState,
    ReasoningSnapshot,
    
    # 变更处理
    DeltaType,
    CodeDelta,
    DeltaSet,
    DeltaAnalyzer,
    
    # 增量推理器
    IncrementalReasoner,
    MultiRoleIncrementalEngine,
    
    # 注意力机制
    AttentionWeight,
    AttentionBasedReasoner,
    
    # 工厂函数
    create_incremental_engine,
    create_attention_reasoner,
    incremental_reasoning,
)

# ============================================================================
# Chunk Operations - 块级代码操作
# ============================================================================
from rebot.core.chunk_operations import (
    # 语义变化
    SemanticChangeType,
    SemanticChange,
    SemanticDiff,
    SemanticDiffer,
    
    # 版本控制
    ChunkVersion,
    ChunkBranch,
    ChunkVersionControl,
    
    # 合并
    MergeConflictType,
    MergeConflict,
    MergeResult,
    ChunkMerger,
    
    # 事务
    TransactionState,
    ChunkTransaction,
    ChunkTransactionManager,
    
    # 编辑器
    ChunkCodeEditor,
    create_chunk_editor,
)

# ============================================================================
# Advanced Coding - 高级代码引擎
# ============================================================================
from rebot.core.advanced_coding import (
    # 能力
    CodeAgentCapability,
    
    # 上下文
    CodeContext,
    CodeEditRequest,
    CodeEditResult,
    
    # 引擎
    AdvancedCodeEngine,
    MultiAgentCodeSystem,
    
    # 工厂函数
    create_code_agent,
    create_code_team,
)

# ============================================================================
# Messages - 消息系统
# ============================================================================
from rebot.core.messages import Message

# ============================================================================
# Co-Evolution - 多Agent协同演化
# ============================================================================
from rebot.core.coevolution import (
    # 功能片段
    FunctionalFragment,
    TaskDAG,
    
    # 结构规范化
    StructuralNormalizer,
    EquivalenceClass,
    
    # 资源调度
    ResourceBinding,
    ResourceScheduler,
    
    # 一致性保证
    ConsistencyGuarantee,
    DependencyPreserver,
    
    # 协同演化引擎
    CoEvolutionEngine,
    create_coevolution_engine,
)

# ============================================================================
# Spatiotemporal Closure - 时空复合闭包
# ============================================================================
from rebot.core.spatiotemporal_closure import (
    # 状态表示
    StateVector,
    StateTrajectory,
    
    # 协同信号
    CollaborativeWeight,
    ProjectionVector,
    CollaborativeSignal,
    
    # 傅里叶分析
    FourierAnalyzer,
    SpectralRepresentation,
    
    # 交互张量
    InteractionTensor,
    
    # L²空间
    L2Space,
    SpatiotemporalClosure,
    create_spatiotemporal_closure,
)

# ============================================================================
# Unified Execution - 统一执行框架
# ============================================================================
from rebot.core.unified_execution import (
    # 算子
    OperatorResult,
    LocalOperator,
    CompositeOperator,
    
    # 调度
    SchedulingPolicy,
    ScheduledTask,
    OperatorScheduler,
    
    # 频域协调
    CoordinationDecision,
    SpectralCoordinator,
    
    # 执行引擎
    ExecutionMode,
    ExecutionContext,
    ExecutionResult,
    UnifiedExecutionEngine,
    
    # Agent集成
    AgentOperator,
    MultiAgentExecutionEngine,
    
    # 工厂函数
    create_unified_engine,
    create_multi_agent_engine,
)

# ============================================================================
# Interaction Optimizer - 交互优化
# ============================================================================
from rebot.core.interaction_optimizer import (
    # 流式协议
    StreamingProtocol,
    StreamChunk,
    StreamMetrics,
    
    # 缓冲与去重
    ChunkBuffer,
    DeltaAccumulator,
    RequestDeduplicator,
    RequestCoalescer,
    
    # 缓存
    LRUCache,
    PrefetchScheduler,
    OptimisticUpdater,
    
    # 限流
    ThrottleConfig,
    TokenBucketThrottle,
    
    # 延迟追踪
    LatencyTracker,
    
    # 优化器
    InteractionOptimizer,
    StreamOptimizer,
    create_interaction_optimizer,
    create_stream_optimizer,
)

# ============================================================================
# Render Optimizer - 渲染优化
# ============================================================================
from rebot.core.render_optimizer import (
    # 渲染调度
    RenderPriority,
    RenderTask,
    RenderScheduler,
    
    # Virtual DOM
    VirtualNode,
    DiffType,
    DiffOp,
    VirtualDOMDiffer,
    PatchOperation,
    
    # 动画
    AnimationConfig,
    AnimationType,
    Animation,
    AnimationController,
    TypingAnimator,
    
    # 渲染器
    IncrementalRenderer,
    MessageStreamRenderer,
    RenderOptimizationSuite,
    create_render_scheduler,
    create_animation_controller,
    create_incremental_renderer,
    create_message_renderer,
)

# ============================================================================
# Streaming Pipeline - 流式管道
# ============================================================================
from rebot.core.streaming_pipeline import (
    # 流状态
    StreamState,
    StreamEvent,
    StreamConfig,
    StreamStats,
    
    # 缓冲与背压
    EventBuffer,
    BackpressureController,
    EventBatcher,
    EventDeduplicator,
    EventRouter,
    
    # 重试
    RetryPolicy,
    
    # 管道
    StreamPipeline,
    ChunkedTextStream,
    DeltaMerger,
    
    # 转换
    StreamTransformer,
    JsonParseTransformer,
    SSEParseTransformer,
    TransformPipeline,
    
    # 工厂函数
    create_stream_pipeline,
    create_sse_transform_pipeline,
    create_json_transform_pipeline,
    OptimizedStreamingPipeline,
    create_optimized_streaming_pipeline,
)

# ============================================================================
# Performance Tuning - 性能调优
# ============================================================================
from rebot.core.performance_tuning import (
    # 系统能力
    PerformanceLevel,
    SystemCapabilities,
    PerformanceConfig,
    
    # 指标
    MetricSample,
    MetricsRegistry,
    PerformanceProfiler,
    
    # 自适应
    AdaptiveThrottler,
    MemoryManager,
    ConcurrencyLimiter,
    ConnectionPool,
    BatchProcessor,
    
    # 报告
    PerformanceReport,
    PerformanceTuner,
    
    # 工厂函数
    detect_system_capabilities,
    create_performance_config,
    create_performance_tuner,
    create_profiler,
    create_batch_processor,
    PerformanceOptimizationSuite,
    create_optimization_suite,
)

# ============================================================================
# 其他核心组件
# ============================================================================
# from rebot.core.callbacks import ...
# from rebot.core.graph import ...
# from rebot.core.runnable import ...
# from rebot.core.serialization import ...
# from rebot.core.trace import ...


__all__ = [
    # Unified Cache
    "SemanticType",
    "SemanticUnit",
    "SharedEncoder",
    "CacheEntry",
    "ReasoningKVCache",
    "ChunkType",
    "CodeChunk",
    "ChunkOperation",
    "ChunkEdit",
    "ChunkCommit",
    "ChunkManager",
    "UnifiedCache",
    "get_unified_cache",
    "CachedReasoning",
    "chunk_aware_edit",
    
    # Incremental Reasoning
    "ReasoningState",
    "ReasoningSnapshot",
    "DeltaType",
    "CodeDelta",
    "DeltaSet",
    "DeltaAnalyzer",
    "IncrementalReasoner",
    "MultiRoleIncrementalEngine",
    "AttentionWeight",
    "AttentionBasedReasoner",
    "create_incremental_engine",
    "create_attention_reasoner",
    "incremental_reasoning",
    
    # Chunk Operations
    "SemanticChangeType",
    "SemanticChange",
    "SemanticDiff",
    "SemanticDiffer",
    "ChunkVersion",
    "ChunkBranch",
    "ChunkVersionControl",
    "MergeConflictType",
    "MergeConflict",
    "MergeResult",
    "ChunkMerger",
    "TransactionState",
    "ChunkTransaction",
    "ChunkTransactionManager",
    "ChunkCodeEditor",
    "create_chunk_editor",
    
    # Advanced Coding
    "CodeAgentCapability",
    "CodeContext",
    "CodeEditRequest",
    "CodeEditResult",
    "AdvancedCodeEngine",
    "MultiAgentCodeSystem",
    "create_code_agent",
    "create_code_team",
    
    # Messages
    "Message",
    
    # Co-Evolution
    "FunctionalFragment",
    "TaskDAG",
    "StructuralNormalizer",
    "EquivalenceClass",
    "ResourceBinding",
    "ResourceScheduler",
    "ConsistencyGuarantee",
    "DependencyPreserver",
    "CoEvolutionEngine",
    "create_coevolution_engine",
    
    # Spatiotemporal Closure
    "StateVector",
    "StateTrajectory",
    "CollaborativeWeight",
    "ProjectionVector",
    "CollaborativeSignal",
    "FourierAnalyzer",
    "SpectralRepresentation",
    "InteractionTensor",
    "L2Space",
    "SpatiotemporalClosure",
    "create_spatiotemporal_closure",
    
    # Unified Execution
    "OperatorResult",
    "LocalOperator",
    "CompositeOperator",
    "SchedulingPolicy",
    "ScheduledTask",
    "OperatorScheduler",
    "CoordinationDecision",
    "SpectralCoordinator",
    "ExecutionMode",
    "ExecutionContext",
    "ExecutionResult",
    "UnifiedExecutionEngine",
    "AgentOperator",
    "MultiAgentExecutionEngine",
    "create_unified_engine",
    "create_multi_agent_engine",
    
    # Interaction Optimizer
    "StreamingProtocol",
    "StreamChunk",
    "StreamMetrics",
    "ChunkBuffer",
    "DeltaAccumulator",
    "RequestDeduplicator",
    "RequestCoalescer",
    "LRUCache",
    "PrefetchScheduler",
    "OptimisticUpdater",
    "ThrottleConfig",
    "TokenBucketThrottle",
    "LatencyTracker",
    "InteractionOptimizer",
    "StreamOptimizer",
    "create_interaction_optimizer",
    "create_stream_optimizer",
    
    # Render Optimizer
    "RenderPriority",
    "RenderTask",
    "RenderScheduler",
    "VirtualNode",
    "DiffType",
    "DiffOp",
    "VirtualDOMDiffer",
    "PatchOperation",
    "AnimationConfig",
    "AnimationType",
    "Animation",
    "AnimationController",
    "TypingAnimator",
    "IncrementalRenderer",
    "MessageStreamRenderer",
    "RenderOptimizationSuite",
    "create_render_scheduler",
    "create_animation_controller",
    "create_incremental_renderer",
    "create_message_renderer",
    
    # Streaming Pipeline
    "StreamState",
    "StreamEvent",
    "StreamConfig",
    "StreamStats",
    "EventBuffer",
    "BackpressureController",
    "EventBatcher",
    "EventDeduplicator",
    "EventRouter",
    "RetryPolicy",
    "StreamPipeline",
    "ChunkedTextStream",
    "DeltaMerger",
    "StreamTransformer",
    "JsonParseTransformer",
    "SSEParseTransformer",
    "TransformPipeline",
    "create_stream_pipeline",
    "create_sse_transform_pipeline",
    "create_json_transform_pipeline",
    "OptimizedStreamingPipeline",
    "create_optimized_streaming_pipeline",
    
    # Performance Tuning
    "PerformanceLevel",
    "SystemCapabilities",
    "PerformanceConfig",
    "MetricSample",
    "MetricsRegistry",
    "PerformanceProfiler",
    "AdaptiveThrottler",
    "MemoryManager",
    "ConcurrencyLimiter",
    "ConnectionPool",
    "BatchProcessor",
    "PerformanceReport",
    "PerformanceTuner",
    "detect_system_capabilities",
    "create_performance_config",
    "create_performance_tuner",
    "create_profiler",
    "create_batch_processor",
    "PerformanceOptimizationSuite",
    "create_optimization_suite",
]
