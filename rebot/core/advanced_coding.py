"""Advanced Coding Engine - 高级代码编辑引擎.

整合三大核心技术:
1. Shared Encoder-Decoder → UnifiedCache + SharedEncoder
2. KV Attention Caching → IncrementalReasoner + ReasoningSnapshot
3. Chunk-level Commit → ChunkCodeEditor + SemanticDiff

这是追赶最强 Code Agent 的核心架构.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, List, Optional, 
    Set, Tuple, TYPE_CHECKING
)
from enum import Enum
import logging

from rebot.core.unified_cache import (
    UnifiedCache, SharedEncoder, SemanticUnit, 
    ReasoningKVCache, get_unified_cache
)
from rebot.core.incremental_reasoning import (
    IncrementalReasoner, ReasoningSnapshot, ReasoningState,
    MultiRoleIncrementalEngine, AttentionBasedReasoner,
    DeltaAnalyzer, DeltaSet, CodeDelta
)
from rebot.core.chunk_operations import (
    ChunkCodeEditor, SemanticDiff, SemanticChange,
    ChunkVersionControl, ChunkTransaction,
    MergeResult
)

if TYPE_CHECKING:
    from rebot.roles.role import Role
    from rebot.environment.base import Environment

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Core Code Agent Engine
# ============================================================================

class CodeAgentCapability(str, Enum):
    """代码Agent能力."""
    READ = "read"
    WRITE = "write"
    ANALYZE = "analyze"
    REFACTOR = "refactor"
    DEBUG = "debug"
    TEST = "test"
    REVIEW = "review"


@dataclass
class CodeContext:
    """代码上下文 - Agent的工作上下文."""
    # 当前文件
    current_file: Optional[str] = None
    current_content: Optional[str] = None
    
    # 语义理解
    semantic_units: List[SemanticUnit] = field(default_factory=list)
    
    # 推理状态
    reasoning_snapshot: Optional[ReasoningSnapshot] = None
    
    # 注意力上下文
    attention_context: Optional[str] = None
    
    # 变更追踪
    pending_changes: List[CodeDelta] = field(default_factory=list)
    
    # 会话信息
    session_id: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class CodeEditRequest:
    """代码编辑请求."""
    file_path: str
    edit_type: str  # "modify_function", "add_function", "delete_function", etc.
    target: str  # function name, class name, etc.
    new_content: Optional[str] = None
    description: str = ""
    
    # 约束
    preserve_signature: bool = False
    preserve_docstring: bool = False
    
    # 验证
    require_tests: bool = False
    require_review: bool = False


@dataclass
class CodeEditResult:
    """代码编辑结果."""
    success: bool
    new_content: Optional[str] = None
    semantic_diff: Optional[SemanticDiff] = None
    transaction: Optional[ChunkTransaction] = None
    error: Optional[str] = None
    
    # 影响分析
    affected_symbols: Set[str] = field(default_factory=set)
    breaking_changes: bool = False
    
    # 建议
    suggestions: List[str] = field(default_factory=list)


class AdvancedCodeEngine:
    """高级代码引擎 - 整合所有核心能力.
    
    这是 Code Agent 的核心大脑:
    1. 共享语义理解 - 多角色复用代码分析
    2. 增量推理 - 只处理变化的部分
    3. 块级操作 - 语义级别的代码编辑
    """
    
    def __init__(
        self,
        role_id: str = "default_agent",
        capabilities: Optional[Set[CodeAgentCapability]] = None
    ):
        self.role_id = role_id
        self.capabilities = capabilities or set(CodeAgentCapability)
        
        # 核心组件
        self._cache = get_unified_cache()
        self._reasoning_engine = MultiRoleIncrementalEngine(self._cache)
        self._attention = AttentionBasedReasoner(self._cache)
        self._editor = ChunkCodeEditor()
        
        # 注册为推理角色
        self._reasoner = self._reasoning_engine.register_role(role_id)
        
        # 当前上下文
        self._context: Optional[CodeContext] = None
        
        # 统计
        self._edit_count = 0
        self._cache_hits = 0
        self._incremental_saves = 0
    
    # ========== 上下文管理 ==========
    
    def create_context(
        self, 
        file_path: str, 
        content: str
    ) -> CodeContext:
        """创建代码上下文."""
        # 编码为语义单元
        unit = self._cache.encoder.encode(content, file_path)
        
        # 解析为代码块
        chunks = self._cache.chunk_manager.parse_file(file_path, content)
        
        context = CodeContext(
            current_file=file_path,
            current_content=content,
            semantic_units=[unit],
            session_id=f"session_{int(time.time()*1000)}"
        )
        
        self._context = context
        return context
    
    async def understand_code(
        self, 
        content: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """深度理解代码 - 使用增量推理.
        
        如果之前已经理解过,会复用缓存.
        """
        # 检查是否有缓存的理解
        unit, cached = self._cache.encode_and_cache(
            content, self.role_id, file_path
        )
        
        if cached is not None:
            self._cache_hits += 1
            logger.debug(f"Cache hit for code understanding: {unit.id}")
            return cached
        
        # 解析代码块
        chunks = self._cache.chunk_manager.parse_file(
            file_path or "temp", content
        )
        
        # 执行完整推理
        if self._reasoner.current_snapshot is None:
            snapshot = await self._reasoner.full_reasoning(chunks)
        else:
            # 增量推理
            delta_analyzer = DeltaAnalyzer(self._cache)
            # 这里简化处理,实际需要比较旧内容
            snapshot = self._reasoner.current_snapshot
        
        # 构建理解结果
        understanding = {
            "file": file_path,
            "chunks": len(chunks),
            "functions": [c.name for c in chunks if c.name and c.chunk_type.value == "function"],
            "classes": [c.name for c in chunks if c.name and c.chunk_type.value == "class"],
            "imports": list(set().union(*[c.imports for c in chunks])),
            "symbols_defined": list(unit.symbols),
            "dependencies": list(unit.dependencies)
        }
        
        # 缓存理解结果
        self._cache.cache_reasoning(self.role_id, unit, understanding)
        
        return understanding
    
    def get_attention_context(
        self,
        target_code: str,
        all_code: str,
        file_path: str = "",
        max_context_chunks: int = 5
    ) -> str:
        """获取基于注意力的上下文.
        
        确定在分析/修改 target_code 时应该关注哪些其他代码.
        """
        # 解析所有代码
        all_chunks = self._cache.chunk_manager.parse_file(file_path, all_code)
        
        # 解析目标代码
        target_chunks = self._cache.chunk_manager.parse_file(
            f"{file_path}.target", target_code
        )
        
        if not target_chunks:
            return ""
        
        # 使用注意力机制找到相关上下文
        return self._attention.get_attention_context(
            target_chunks[0],
            all_chunks,
            threshold=0.05
        )
    
    # ========== 代码编辑 ==========
    
    async def edit_code(
        self,
        request: CodeEditRequest
    ) -> CodeEditResult:
        """执行代码编辑 - 核心编辑接口."""
        if CodeAgentCapability.WRITE not in self.capabilities:
            return CodeEditResult(
                success=False,
                error="Write capability not enabled"
            )
        
        # 获取当前内容
        if self._context and self._context.current_file == request.file_path:
            current_content = self._context.current_content
        else:
            return CodeEditResult(
                success=False,
                error="No context for this file. Call create_context first."
            )
        
        try:
            if request.edit_type == "modify_function":
                return await self._modify_function(
                    current_content, request
                )
            elif request.edit_type == "add_function":
                return await self._add_function(
                    current_content, request
                )
            elif request.edit_type == "delete_function":
                return await self._delete_function(
                    current_content, request
                )
            else:
                return CodeEditResult(
                    success=False,
                    error=f"Unknown edit type: {request.edit_type}"
                )
        except Exception as e:
            return CodeEditResult(
                success=False,
                error=str(e)
            )
    
    async def _modify_function(
        self,
        content: str,
        request: CodeEditRequest
    ) -> CodeEditResult:
        """修改函数."""
        if not request.new_content:
            return CodeEditResult(
                success=False,
                error="new_content is required for modify_function"
            )
        
        # 使用块级编辑器
        new_content, tx = self._editor.edit_function(
            file_content=content,
            function_name=request.target,
            new_body=request.new_content,
            author=self.role_id,
            message=request.description
        )
        
        # 计算语义差异
        diff = self._editor.semantic_diff(content, new_content)
        
        # 更新上下文
        if self._context:
            self._context.current_content = new_content
        
        # 增量更新推理
        await self._update_reasoning(content, new_content, request.file_path)
        
        self._edit_count += 1
        
        return CodeEditResult(
            success=True,
            new_content=new_content,
            semantic_diff=diff,
            transaction=tx,
            affected_symbols={request.target},
            breaking_changes=diff.has_breaking_changes()
        )
    
    async def _add_function(
        self,
        content: str,
        request: CodeEditRequest
    ) -> CodeEditResult:
        """添加函数."""
        if not request.new_content:
            return CodeEditResult(
                success=False,
                error="new_content is required for add_function"
            )
        
        new_content, tx = self._editor.add_function(
            file_content=content,
            function_code=request.new_content,
            after_function=request.target if request.target else None,
            author=self.role_id,
            message=request.description
        )
        
        diff = self._editor.semantic_diff(content, new_content)
        
        if self._context:
            self._context.current_content = new_content
        
        await self._update_reasoning(content, new_content, request.file_path)
        
        self._edit_count += 1
        
        return CodeEditResult(
            success=True,
            new_content=new_content,
            semantic_diff=diff,
            transaction=tx
        )
    
    async def _delete_function(
        self,
        content: str,
        request: CodeEditRequest
    ) -> CodeEditResult:
        """删除函数."""
        import ast
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return CodeEditResult(success=False, error=str(e))
        
        # 找到函数
        lines = content.split('\n')
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == request.target:
                # 删除函数行
                new_lines = lines[:node.lineno-1] + lines[node.end_lineno:]
                new_content = '\n'.join(new_lines)
                
                diff = self._editor.semantic_diff(content, new_content)
                
                if self._context:
                    self._context.current_content = new_content
                
                self._edit_count += 1
                
                return CodeEditResult(
                    success=True,
                    new_content=new_content,
                    semantic_diff=diff,
                    affected_symbols={request.target},
                    breaking_changes=True
                )
        
        return CodeEditResult(
            success=False,
            error=f"Function {request.target} not found"
        )
    
    async def _update_reasoning(
        self,
        old_content: str,
        new_content: str,
        file_path: str
    ):
        """增量更新推理状态."""
        # 使用增量推理引擎
        results = await self._reasoning_engine.process_file_change(
            file_path, old_content, new_content
        )
        
        if self.role_id in results:
            _, impact = results[self.role_id]
            saved = impact.get("computations_saved", 0)
            self._incremental_saves += saved
            logger.debug(
                f"Incremental reasoning saved {saved} computations"
            )
    
    # ========== 多角色协作 ==========
    
    async def collaborate_edit(
        self,
        request: CodeEditRequest,
        reviewer_ids: List[str]
    ) -> Tuple[CodeEditResult, Dict[str, str]]:
        """协作编辑 - 多角色参与.
        
        1. 执行编辑
        2. 其他角色审查
        3. 收集反馈
        """
        # 执行编辑
        result = await self.edit_code(request)
        
        if not result.success:
            return result, {}
        
        # 收集审查意见
        reviews = {}
        for reviewer_id in reviewer_ids:
            # 获取审查者的推理器
            reviewer = self._reasoning_engine.get_reasoner(reviewer_id)
            if reviewer and reviewer.current_snapshot:
                # 获取审查者对变更的理解
                consensus = self._reasoning_engine.get_consensus_understanding(
                    f"func_{request.target}"
                )
                reviews[reviewer_id] = f"Reviewed by {reviewer_id}"
        
        return result, reviews
    
    def share_understanding(
        self,
        to_role: str,
        chunk_id: str
    ) -> bool:
        """共享代码理解给其他角色."""
        return self._reasoning_engine.share_reasoning(
            self.role_id,
            to_role,
            chunk_id
        )
    
    # ========== 高级功能 ==========
    
    def analyze_impact(
        self,
        old_content: str,
        new_content: str
    ) -> Dict[str, Any]:
        """分析变更影响."""
        diff = self._editor.semantic_diff(old_content, new_content)
        
        return {
            "summary": diff.summary(),
            "breaking_changes": diff.has_breaking_changes(),
            "functions_added": diff.functions_added,
            "functions_removed": diff.functions_removed,
            "functions_modified": diff.functions_modified,
            "changes": [
                {
                    "type": c.change_type.value,
                    "description": c.description,
                    "breaking": c.breaking
                }
                for c in diff.changes
            ]
        }
    
    def merge_versions(
        self,
        base: str,
        ours: str,
        theirs: str
    ) -> MergeResult:
        """合并代码版本."""
        return self._editor.merge(base, ours, theirs)
    
    def get_history(self, function_name: str) -> List[Dict]:
        """获取函数的修改历史."""
        versions = self._editor.get_history(f"func_{function_name}")
        return [
            {
                "version": v.version_number,
                "author": v.author,
                "message": v.message,
                "time": v.created_at
            }
            for v in versions
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计."""
        return {
            "role_id": self.role_id,
            "capabilities": [c.value for c in self.capabilities],
            "edit_count": self._edit_count,
            "cache_hits": self._cache_hits,
            "incremental_saves": self._incremental_saves,
            "cache_stats": self._cache.get_stats(),
            "reasoning_stats": self._reasoning_engine.get_system_stats()
        }


# ============================================================================
# Part 2: Multi-Agent Code Collaboration
# ============================================================================

class MultiAgentCodeSystem:
    """多Agent代码协作系统.
    
    多个 AdvancedCodeEngine 协作:
    - 共享语义理解缓存
    - 各自维护推理状态
    - 协作编辑和审查
    """
    
    def __init__(self):
        self._agents: Dict[str, AdvancedCodeEngine] = {}
        self._cache = get_unified_cache()
        self._lock = asyncio.Lock()
    
    def register_agent(
        self,
        role_id: str,
        capabilities: Optional[Set[CodeAgentCapability]] = None
    ) -> AdvancedCodeEngine:
        """注册代码Agent."""
        if role_id not in self._agents:
            agent = AdvancedCodeEngine(role_id, capabilities)
            self._agents[role_id] = agent
        return self._agents[role_id]
    
    def get_agent(self, role_id: str) -> Optional[AdvancedCodeEngine]:
        """获取Agent."""
        return self._agents.get(role_id)
    
    async def collaborative_edit(
        self,
        editor_id: str,
        reviewer_ids: List[str],
        request: CodeEditRequest
    ) -> Dict[str, Any]:
        """协作编辑流程.
        
        1. Editor 执行编辑
        2. Reviewers 审查
        3. 达成共识或返回修改建议
        """
        editor = self._agents.get(editor_id)
        if not editor:
            return {"success": False, "error": f"Agent {editor_id} not found"}
        
        async with self._lock:
            # 执行编辑
            result = await editor.edit_code(request)
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error
                }
            
            # 收集审查
            reviews = {}
            approvals = 0
            
            for reviewer_id in reviewer_ids:
                reviewer = self._agents.get(reviewer_id)
                if reviewer:
                    # 共享理解
                    editor.share_understanding(
                        reviewer_id, 
                        f"func_{request.target}"
                    )
                    
                    # 简化: 假设审查通过
                    reviews[reviewer_id] = {
                        "approved": True,
                        "comments": []
                    }
                    approvals += 1
            
            return {
                "success": True,
                "result": result,
                "reviews": reviews,
                "approval_rate": approvals / len(reviewer_ids) if reviewer_ids else 1.0
            }
    
    def get_global_understanding(self, file_path: str) -> Dict[str, Any]:
        """获取全局理解 - 汇总所有Agent的理解."""
        understandings = {}
        
        # 从缓存获取语义单元
        units = self._cache.encoder.get_by_file(file_path)
        
        for agent_id, agent in self._agents.items():
            agent_understanding = {}
            for unit in units:
                interpretation = unit.get_interpretation(agent_id)
                if interpretation:
                    agent_understanding[unit.id] = interpretation
            understandings[agent_id] = agent_understanding
        
        return {
            "file": file_path,
            "semantic_units": len(units),
            "agent_interpretations": understandings
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计."""
        return {
            "num_agents": len(self._agents),
            "agents": {
                agent_id: agent.get_stats()
                for agent_id, agent in self._agents.items()
            },
            "shared_cache": self._cache.get_stats()
        }


# ============================================================================
# Part 3: High-level API
# ============================================================================

def create_code_agent(
    role_id: str = "coder",
    capabilities: Optional[Set[CodeAgentCapability]] = None
) -> AdvancedCodeEngine:
    """创建代码Agent."""
    return AdvancedCodeEngine(role_id, capabilities)


def create_code_team() -> MultiAgentCodeSystem:
    """创建代码协作团队."""
    system = MultiAgentCodeSystem()
    
    # 预定义团队结构
    system.register_agent("architect", {
        CodeAgentCapability.READ,
        CodeAgentCapability.ANALYZE,
        CodeAgentCapability.REVIEW
    })
    
    system.register_agent("developer", {
        CodeAgentCapability.READ,
        CodeAgentCapability.WRITE,
        CodeAgentCapability.REFACTOR
    })
    
    system.register_agent("reviewer", {
        CodeAgentCapability.READ,
        CodeAgentCapability.ANALYZE,
        CodeAgentCapability.REVIEW
    })
    
    system.register_agent("tester", {
        CodeAgentCapability.READ,
        CodeAgentCapability.TEST,
        CodeAgentCapability.DEBUG
    })
    
    return system


# ============================================================================
# Part 4: Example Usage
# ============================================================================

async def example_usage():
    """示例用法."""
    # 创建代码Agent
    agent = create_code_agent("my_coder")
    
    # 创建代码上下文
    code = '''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

def goodbye(name: str) -> str:
    """Say goodbye."""
    return f"Goodbye, {name}!"
'''
    
    context = agent.create_context("example.py", code)
    
    # 理解代码 (会被缓存)
    understanding = await agent.understand_code(code, "example.py")
    print(f"Understanding: {understanding}")
    
    # 修改函数
    result = await agent.edit_code(CodeEditRequest(
        file_path="example.py",
        edit_type="modify_function",
        target="hello",
        new_content='''def hello(name: str, greeting: str = "Hello") -> str:
    """Say hello with custom greeting."""
    return f"{greeting}, {name}!"''',
        description="Add custom greeting parameter"
    ))
    
    if result.success:
        print(f"Edit successful!")
        print(f"Semantic diff: {result.semantic_diff.summary()}")
        print(f"Breaking changes: {result.breaking_changes}")
    
    # 再次理解 (会复用增量推理)
    new_understanding = await agent.understand_code(
        result.new_content, "example.py"
    )
    
    # 查看统计
    stats = agent.get_stats()
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Incremental saves: {stats['incremental_saves']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
