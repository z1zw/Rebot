"""Chunk-level Code Operations - 块级代码操作系统.

核心理论:
将 git 的 line-level commit 升级为 semantic chunk-level commit.

传统方式: 
- git diff 是行级别的 +/- 
- 代码审查看到的是"行变化"

Chunk-level 方式:
- 以函数/类/模块为单位
- 理解"语义变化"而非"文本变化"
- 更智能的合并和冲突解决

优势:
1. LLM 更容易理解和生成
2. 更小的增量更新单位
3. 更好的版本回滚粒度
4. 支持语义层面的 diff
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional, 
    Set, Tuple, TypeVar, Union
)
from enum import Enum
from pathlib import Path
import threading
import logging
from collections import OrderedDict

from rebot.core.unified_cache import (
    CodeChunk, ChunkType, ChunkOperation, ChunkEdit, ChunkCommit,
    ChunkManager, get_unified_cache
)

logger = logging.getLogger(__name__)


# ============================================================================
# Part 1: Semantic Diff - 语义级别的差异比较
# ============================================================================

class SemanticChangeType(str, Enum):
    """语义变化类型 - 比行级别更有意义."""
    # 结构变化
    FUNCTION_ADDED = "function_added"
    FUNCTION_REMOVED = "function_removed"
    FUNCTION_RENAMED = "function_renamed"
    FUNCTION_SIGNATURE_CHANGED = "function_signature_changed"
    FUNCTION_BODY_CHANGED = "function_body_changed"
    
    CLASS_ADDED = "class_added"
    CLASS_REMOVED = "class_removed"
    CLASS_RENAMED = "class_renamed"
    CLASS_INHERITANCE_CHANGED = "class_inheritance_changed"
    
    METHOD_ADDED = "method_added"
    METHOD_REMOVED = "method_removed"
    METHOD_MOVED = "method_moved"  # 移到另一个类
    
    # 依赖变化
    IMPORT_ADDED = "import_added"
    IMPORT_REMOVED = "import_removed"
    IMPORT_CHANGED = "import_changed"
    
    # 逻辑变化
    LOGIC_REORDERED = "logic_reordered"
    CONDITION_CHANGED = "condition_changed"
    LOOP_MODIFIED = "loop_modified"
    ERROR_HANDLING_CHANGED = "error_handling_changed"
    
    # 优化/重构
    EXTRACTED_FUNCTION = "extracted_function"
    INLINED_FUNCTION = "inlined_function"
    VARIABLE_RENAMED = "variable_renamed"
    CODE_SIMPLIFIED = "code_simplified"
    
    # 文档
    DOCSTRING_ADDED = "docstring_added"
    DOCSTRING_CHANGED = "docstring_changed"
    COMMENT_CHANGED = "comment_changed"
    
    # 其他
    UNKNOWN = "unknown"


@dataclass
class SemanticChange:
    """语义变化描述."""
    change_type: SemanticChangeType
    chunk_id: str
    description: str
    
    # 变化详情
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    
    # 影响
    affected_symbols: Set[str] = field(default_factory=set)
    breaking: bool = False  # 是否是破坏性变更
    
    # 代码位置
    file_path: Optional[str] = None
    old_location: Optional[Tuple[int, int]] = None
    new_location: Optional[Tuple[int, int]] = None
    
    # 置信度
    confidence: float = 1.0


@dataclass
class SemanticDiff:
    """语义级别的差异."""
    changes: List[SemanticChange] = field(default_factory=list)
    
    # 摘要
    functions_added: int = 0
    functions_removed: int = 0
    functions_modified: int = 0
    classes_added: int = 0
    classes_removed: int = 0
    classes_modified: int = 0
    breaking_changes: int = 0
    
    # 元信息
    old_file: Optional[str] = None
    new_file: Optional[str] = None
    computed_at: float = field(default_factory=time.time)
    
    def has_breaking_changes(self) -> bool:
        return self.breaking_changes > 0
    
    def summary(self) -> str:
        """生成摘要."""
        parts = []
        if self.functions_added:
            parts.append(f"+{self.functions_added} functions")
        if self.functions_removed:
            parts.append(f"-{self.functions_removed} functions")
        if self.functions_modified:
            parts.append(f"~{self.functions_modified} functions modified")
        if self.classes_added:
            parts.append(f"+{self.classes_added} classes")
        if self.breaking_changes:
            parts.append(f"⚠️ {self.breaking_changes} breaking changes")
        return ", ".join(parts) if parts else "No significant changes"


class SemanticDiffer:
    """语义差异计算器."""
    
    def __init__(self):
        self._chunk_manager = ChunkManager()
    
    def diff(self, old_code: str, new_code: str, file_path: str = "") -> SemanticDiff:
        """计算语义差异."""
        result = SemanticDiff(old_file=file_path, new_file=file_path)
        
        # 解析AST
        try:
            old_ast = ast.parse(old_code)
            new_ast = ast.parse(new_code)
        except SyntaxError:
            # 非Python代码,回退到启发式
            return self._heuristic_diff(old_code, new_code, file_path)
        
        # 提取结构
        old_funcs = self._extract_functions(old_ast)
        new_funcs = self._extract_functions(new_ast)
        old_classes = self._extract_classes(old_ast)
        new_classes = self._extract_classes(new_ast)
        old_imports = self._extract_imports(old_ast)
        new_imports = self._extract_imports(new_ast)
        
        # 比较函数
        self._diff_functions(old_funcs, new_funcs, old_code, new_code, result)
        
        # 比较类
        self._diff_classes(old_classes, new_classes, old_code, new_code, result)
        
        # 比较导入
        self._diff_imports(old_imports, new_imports, result)
        
        return result
    
    def _extract_functions(self, tree: ast.AST) -> Dict[str, ast.FunctionDef]:
        """提取函数定义."""
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 只取顶层函数(非方法)
                funcs[node.name] = node
        return funcs
    
    def _extract_classes(self, tree: ast.AST) -> Dict[str, ast.ClassDef]:
        """提取类定义."""
        return {
            node.name: node 
            for node in ast.walk(tree) 
            if isinstance(node, ast.ClassDef)
        }
    
    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """提取导入."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        return imports
    
    def _diff_functions(
        self,
        old_funcs: Dict[str, ast.FunctionDef],
        new_funcs: Dict[str, ast.FunctionDef],
        old_code: str,
        new_code: str,
        result: SemanticDiff
    ):
        """比较函数变化."""
        old_names = set(old_funcs.keys())
        new_names = set(new_funcs.keys())
        
        # 新增的函数
        for name in new_names - old_names:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.FUNCTION_ADDED,
                chunk_id=f"func_{name}",
                description=f"Function '{name}' was added",
                new_value=name,
                affected_symbols={name}
            ))
            result.functions_added += 1
        
        # 删除的函数
        for name in old_names - new_names:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.FUNCTION_REMOVED,
                chunk_id=f"func_{name}",
                description=f"Function '{name}' was removed",
                old_value=name,
                affected_symbols={name},
                breaking=True
            ))
            result.functions_removed += 1
            result.breaking_changes += 1
        
        # 修改的函数
        for name in old_names & new_names:
            old_func = old_funcs[name]
            new_func = new_funcs[name]
            
            changes = self._compare_function(old_func, new_func, old_code, new_code)
            if changes:
                result.changes.extend(changes)
                result.functions_modified += 1
    
    def _compare_function(
        self,
        old_func: ast.FunctionDef,
        new_func: ast.FunctionDef,
        old_code: str,
        new_code: str
    ) -> List[SemanticChange]:
        """比较单个函数的变化."""
        changes = []
        name = old_func.name
        
        # 签名变化
        old_args = self._get_function_signature(old_func)
        new_args = self._get_function_signature(new_func)
        
        if old_args != new_args:
            changes.append(SemanticChange(
                change_type=SemanticChangeType.FUNCTION_SIGNATURE_CHANGED,
                chunk_id=f"func_{name}",
                description=f"Function '{name}' signature changed",
                old_value=old_args,
                new_value=new_args,
                breaking=True
            ))
        
        # 函数体变化
        old_body = ast.unparse(old_func) if hasattr(ast, 'unparse') else str(old_func.body)
        new_body = ast.unparse(new_func) if hasattr(ast, 'unparse') else str(new_func.body)
        
        if old_body != new_body:
            changes.append(SemanticChange(
                change_type=SemanticChangeType.FUNCTION_BODY_CHANGED,
                chunk_id=f"func_{name}",
                description=f"Function '{name}' body was modified"
            ))
        
        return changes
    
    def _get_function_signature(self, func: ast.FunctionDef) -> str:
        """获取函数签名字符串."""
        args = []
        for arg in func.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else '...'}"
            args.append(arg_str)
        
        return f"({', '.join(args)})"
    
    def _diff_classes(
        self,
        old_classes: Dict[str, ast.ClassDef],
        new_classes: Dict[str, ast.ClassDef],
        old_code: str,
        new_code: str,
        result: SemanticDiff
    ):
        """比较类变化."""
        old_names = set(old_classes.keys())
        new_names = set(new_classes.keys())
        
        for name in new_names - old_names:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.CLASS_ADDED,
                chunk_id=f"class_{name}",
                description=f"Class '{name}' was added",
                new_value=name
            ))
            result.classes_added += 1
        
        for name in old_names - new_names:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.CLASS_REMOVED,
                chunk_id=f"class_{name}",
                description=f"Class '{name}' was removed",
                old_value=name,
                breaking=True
            ))
            result.classes_removed += 1
            result.breaking_changes += 1
    
    def _diff_imports(
        self,
        old_imports: Set[str],
        new_imports: Set[str],
        result: SemanticDiff
    ):
        """比较导入变化."""
        for imp in new_imports - old_imports:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.IMPORT_ADDED,
                chunk_id=f"import_{imp}",
                description=f"Import '{imp}' was added",
                new_value=imp
            ))
        
        for imp in old_imports - new_imports:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.IMPORT_REMOVED,
                chunk_id=f"import_{imp}",
                description=f"Import '{imp}' was removed",
                old_value=imp
            ))
    
    def _heuristic_diff(
        self, 
        old_code: str, 
        new_code: str, 
        file_path: str
    ) -> SemanticDiff:
        """启发式差异 (非Python代码)."""
        result = SemanticDiff(old_file=file_path, new_file=file_path)
        
        # 简单的函数检测
        old_funcs = set(re.findall(r'(?:function|def|fn)\s+(\w+)', old_code))
        new_funcs = set(re.findall(r'(?:function|def|fn)\s+(\w+)', new_code))
        
        for name in new_funcs - old_funcs:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.FUNCTION_ADDED,
                chunk_id=f"func_{name}",
                description=f"Function '{name}' was added",
                confidence=0.8
            ))
            result.functions_added += 1
        
        for name in old_funcs - new_funcs:
            result.changes.append(SemanticChange(
                change_type=SemanticChangeType.FUNCTION_REMOVED,
                chunk_id=f"func_{name}",
                description=f"Function '{name}' was removed",
                confidence=0.8,
                breaking=True
            ))
            result.functions_removed += 1
            result.breaking_changes += 1
        
        return result


# ============================================================================
# Part 2: Chunk-level Version Control - 块级版本控制
# ============================================================================

@dataclass
class ChunkVersion:
    """块的版本."""
    version_id: str
    chunk_id: str
    content: str
    content_hash: str
    
    # 版本信息
    version_number: int
    parent_version: Optional[str] = None
    
    # 元信息
    author: str = ""
    message: str = ""
    created_at: float = field(default_factory=time.time)
    
    # 语义信息
    semantic_type: Optional[str] = None
    symbols_defined: Set[str] = field(default_factory=set)


@dataclass
class ChunkBranch:
    """块的分支 - 支持并行开发."""
    name: str
    head_version: str
    created_at: float = field(default_factory=time.time)
    parent_branch: Optional[str] = None


class ChunkVersionControl:
    """块级版本控制系统.
    
    类似 git,但粒度是语义块而非文件行.
    """
    
    def __init__(self):
        self._versions: Dict[str, ChunkVersion] = {}
        self._chunk_heads: Dict[str, str] = {}  # chunk_id -> latest version_id
        self._branches: Dict[str, ChunkBranch] = {"main": ChunkBranch(name="main", head_version="")}
        self._current_branch = "main"
        self._lock = threading.RLock()
    
    def commit_chunk(
        self,
        chunk_id: str,
        content: str,
        author: str,
        message: str,
        semantic_type: Optional[str] = None
    ) -> ChunkVersion:
        """提交块的新版本."""
        with self._lock:
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # 获取父版本
            parent_version = self._chunk_heads.get(chunk_id)
            version_number = 1
            if parent_version and parent_version in self._versions:
                version_number = self._versions[parent_version].version_number + 1
            
            version_id = f"{chunk_id}_v{version_number}_{content_hash}"
            
            version = ChunkVersion(
                version_id=version_id,
                chunk_id=chunk_id,
                content=content,
                content_hash=content_hash,
                version_number=version_number,
                parent_version=parent_version,
                author=author,
                message=message,
                semantic_type=semantic_type
            )
            
            self._versions[version_id] = version
            self._chunk_heads[chunk_id] = version_id
            
            return version
    
    def get_version(self, version_id: str) -> Optional[ChunkVersion]:
        """获取版本."""
        return self._versions.get(version_id)
    
    def get_latest(self, chunk_id: str) -> Optional[ChunkVersion]:
        """获取块的最新版本."""
        version_id = self._chunk_heads.get(chunk_id)
        if version_id:
            return self._versions.get(version_id)
        return None
    
    def get_history(self, chunk_id: str, limit: int = 10) -> List[ChunkVersion]:
        """获取块的版本历史."""
        history = []
        version_id = self._chunk_heads.get(chunk_id)
        
        while version_id and len(history) < limit:
            version = self._versions.get(version_id)
            if not version:
                break
            history.append(version)
            version_id = version.parent_version
        
        return history
    
    def diff_versions(
        self,
        version_id_1: str,
        version_id_2: str
    ) -> Optional[SemanticDiff]:
        """比较两个版本."""
        v1 = self._versions.get(version_id_1)
        v2 = self._versions.get(version_id_2)
        
        if not v1 or not v2:
            return None
        
        differ = SemanticDiffer()
        return differ.diff(v1.content, v2.content)
    
    def rollback(self, chunk_id: str, target_version: str) -> bool:
        """回滚到指定版本."""
        with self._lock:
            if target_version not in self._versions:
                return False
            
            version = self._versions[target_version]
            if version.chunk_id != chunk_id:
                return False
            
            # 创建新版本指向旧内容
            self.commit_chunk(
                chunk_id=chunk_id,
                content=version.content,
                author="system",
                message=f"Rollback to version {target_version}"
            )
            
            return True
    
    def create_branch(self, name: str, from_branch: str = "main") -> ChunkBranch:
        """创建分支."""
        with self._lock:
            parent = self._branches.get(from_branch)
            if not parent:
                raise ValueError(f"Branch {from_branch} not found")
            
            branch = ChunkBranch(
                name=name,
                head_version=parent.head_version,
                parent_branch=from_branch
            )
            self._branches[name] = branch
            return branch
    
    def switch_branch(self, name: str) -> bool:
        """切换分支."""
        if name in self._branches:
            self._current_branch = name
            return True
        return False


# ============================================================================
# Part 3: Intelligent Merge - 智能合并
# ============================================================================

class MergeConflictType(str, Enum):
    """合并冲突类型."""
    BOTH_MODIFIED = "both_modified"
    DELETE_MODIFY = "delete_modify"
    SEMANTIC_CONFLICT = "semantic_conflict"  # 语义冲突(如方法签名不兼容)


@dataclass
class MergeConflict:
    """合并冲突."""
    conflict_type: MergeConflictType
    chunk_id: str
    description: str
    
    # 冲突的内容
    base_content: Optional[str] = None
    ours_content: Optional[str] = None
    theirs_content: Optional[str] = None
    
    # 建议解决方案
    suggested_resolution: Optional[str] = None
    resolution_confidence: float = 0.0


@dataclass
class MergeResult:
    """合并结果."""
    success: bool
    merged_content: Optional[str] = None
    conflicts: List[MergeConflict] = field(default_factory=list)
    auto_resolved: int = 0
    manual_required: int = 0


class ChunkMerger:
    """块级合并器 - 语义感知的合并."""
    
    def __init__(self):
        self._differ = SemanticDiffer()
    
    def three_way_merge(
        self,
        base: str,
        ours: str,
        theirs: str,
        file_path: str = ""
    ) -> MergeResult:
        """三方合并.
        
        base: 共同祖先
        ours: 我们的修改
        theirs: 他们的修改
        """
        # 计算两个方向的变化
        ours_changes = self._differ.diff(base, ours)
        theirs_changes = self._differ.diff(base, theirs)
        
        # 检测冲突
        conflicts = self._detect_conflicts(ours_changes, theirs_changes)
        
        if conflicts:
            # 尝试自动解决
            resolved, remaining = self._auto_resolve(conflicts, ours, theirs)
            
            if remaining:
                return MergeResult(
                    success=False,
                    conflicts=remaining,
                    auto_resolved=len(resolved),
                    manual_required=len(remaining)
                )
        
        # 无冲突,合并
        merged = self._merge_content(base, ours, theirs, ours_changes, theirs_changes)
        
        return MergeResult(
            success=True,
            merged_content=merged,
            auto_resolved=len(conflicts)
        )
    
    def _detect_conflicts(
        self,
        ours: SemanticDiff,
        theirs: SemanticDiff
    ) -> List[MergeConflict]:
        """检测冲突."""
        conflicts = []
        
        # 找出双方都修改的块
        ours_modified = {c.chunk_id for c in ours.changes}
        theirs_modified = {c.chunk_id for c in theirs.changes}
        
        both_modified = ours_modified & theirs_modified
        
        for chunk_id in both_modified:
            ours_change = next((c for c in ours.changes if c.chunk_id == chunk_id), None)
            theirs_change = next((c for c in theirs.changes if c.chunk_id == chunk_id), None)
            
            if ours_change and theirs_change:
                conflicts.append(MergeConflict(
                    conflict_type=MergeConflictType.BOTH_MODIFIED,
                    chunk_id=chunk_id,
                    description=f"Both modified {chunk_id}",
                    ours_content=ours_change.new_value,
                    theirs_content=theirs_change.new_value
                ))
        
        return conflicts
    
    def _auto_resolve(
        self,
        conflicts: List[MergeConflict]
    ) -> Tuple[List[MergeConflict], List[MergeConflict]]:
        """尝试自动解决冲突."""
        resolved = []
        remaining = []
        
        for conflict in conflicts:
            if conflict.ours_content == conflict.theirs_content:
                # 内容相同,自动解决
                conflict.suggested_resolution = conflict.ours_content
                conflict.resolution_confidence = 1.0
                resolved.append(conflict)
            elif self._is_trivial_conflict(conflict):
                # 简单冲突,尝试解决
                resolution = self._resolve_trivial(conflict)
                if resolution:
                    conflict.suggested_resolution = resolution
                    conflict.resolution_confidence = 0.8
                    resolved.append(conflict)
                else:
                    remaining.append(conflict)
            else:
                remaining.append(conflict)
        
        return resolved, remaining
    
    def _is_trivial_conflict(self, conflict: MergeConflict) -> bool:
        """判断是否是简单冲突."""
        # 例如: 只是注释变化、空白变化等
        if not conflict.ours_content or not conflict.theirs_content:
            return False
        
        # 去除空白后比较
        ours_stripped = re.sub(r'\s+', ' ', conflict.ours_content.strip())
        theirs_stripped = re.sub(r'\s+', ' ', conflict.theirs_content.strip())
        
        return ours_stripped == theirs_stripped
    
    def _resolve_trivial(self, conflict: MergeConflict) -> Optional[str]:
        """解决简单冲突."""
        # 保留格式更好的版本
        if conflict.ours_content and conflict.theirs_content:
            # 简单策略: 保留更长的(假设更完整)
            if len(conflict.ours_content) >= len(conflict.theirs_content):
                return conflict.ours_content
            return conflict.theirs_content
        return None
    
    def _merge_content(
        self,
        base: str,
        ours: str,
        theirs: str,
        ours_changes: SemanticDiff,
        theirs_changes: SemanticDiff
    ) -> str:
        """合并内容."""
        # 简化实现: 使用 difflib
        merged_lines = list(difflib.Differ().compare(
            base.splitlines(keepends=True),
            ours.splitlines(keepends=True)
        ))
        
        # 应用 theirs 的变化
        # 实际实现需要更复杂的逻辑
        
        return ours  # 简化: 优先使用ours


# ============================================================================
# Part 4: Chunk Transaction - 块级事务
# ============================================================================

class TransactionState(str, Enum):
    """事务状态."""
    PENDING = "pending"
    COMMITTED = "committed"
    ABORTED = "aborted"
    ROLLED_BACK = "rolled_back"


@dataclass
class ChunkTransaction:
    """块级事务 - 原子操作集合."""
    id: str
    operations: List[ChunkEdit] = field(default_factory=list)
    state: TransactionState = TransactionState.PENDING
    
    # 回滚信息
    rollback_info: Dict[str, str] = field(default_factory=dict)  # chunk_id -> original_content
    
    # 元信息
    author: str = ""
    message: str = ""
    created_at: float = field(default_factory=time.time)
    committed_at: Optional[float] = None
    
    def add_operation(self, edit: ChunkEdit):
        """添加操作."""
        if self.state != TransactionState.PENDING:
            raise ValueError("Cannot add operations to non-pending transaction")
        self.operations.append(edit)
    
    def save_rollback(self, chunk_id: str, content: str):
        """保存回滚信息."""
        if chunk_id not in self.rollback_info:
            self.rollback_info[chunk_id] = content


class ChunkTransactionManager:
    """块级事务管理器."""
    
    def __init__(self, vcs: Optional[ChunkVersionControl] = None):
        self._vcs = vcs or ChunkVersionControl()
        self._transactions: Dict[str, ChunkTransaction] = {}
        self._current_tx: Optional[str] = None
        self._lock = threading.RLock()
    
    def begin(self, author: str = "", message: str = "") -> ChunkTransaction:
        """开始事务."""
        with self._lock:
            tx_id = f"tx_{int(time.time()*1000)}"
            tx = ChunkTransaction(
                id=tx_id,
                author=author,
                message=message
            )
            self._transactions[tx_id] = tx
            self._current_tx = tx_id
            return tx
    
    def add_edit(
        self,
        operation: ChunkOperation,
        chunk_id: str,
        new_content: Optional[str] = None,
        original_content: Optional[str] = None
    ):
        """添加编辑操作到当前事务."""
        with self._lock:
            if not self._current_tx:
                raise ValueError("No active transaction")
            
            tx = self._transactions[self._current_tx]
            
            # 保存回滚信息
            if original_content:
                tx.save_rollback(chunk_id, original_content)
            
            edit = ChunkEdit(
                operation=operation,
                target_chunk_id=chunk_id,
                new_content=new_content
            )
            tx.add_operation(edit)
    
    def commit(self) -> Optional[ChunkTransaction]:
        """提交当前事务."""
        with self._lock:
            if not self._current_tx:
                return None
            
            tx = self._transactions[self._current_tx]
            
            # 执行所有操作
            for edit in tx.operations:
                if edit.operation in (ChunkOperation.INSERT, ChunkOperation.REPLACE):
                    if edit.new_content:
                        self._vcs.commit_chunk(
                            chunk_id=edit.target_chunk_id,
                            content=edit.new_content,
                            author=tx.author,
                            message=tx.message
                        )
            
            tx.state = TransactionState.COMMITTED
            tx.committed_at = time.time()
            self._current_tx = None
            
            return tx
    
    def rollback(self) -> Optional[ChunkTransaction]:
        """回滚当前事务."""
        with self._lock:
            if not self._current_tx:
                return None
            
            tx = self._transactions[self._current_tx]
            
            # 恢复原始内容
            for chunk_id, content in tx.rollback_info.items():
                self._vcs.commit_chunk(
                    chunk_id=chunk_id,
                    content=content,
                    author="system",
                    message=f"Rollback transaction {tx.id}"
                )
            
            tx.state = TransactionState.ROLLED_BACK
            self._current_tx = None
            
            return tx
    
    def abort(self) -> Optional[ChunkTransaction]:
        """放弃当前事务(不执行任何操作)."""
        with self._lock:
            if not self._current_tx:
                return None
            
            tx = self._transactions[self._current_tx]
            tx.state = TransactionState.ABORTED
            self._current_tx = None
            
            return tx


# ============================================================================
# Part 5: Integration - 集成接口
# ============================================================================

class ChunkCodeEditor:
    """块级代码编辑器 - 高级接口."""
    
    def __init__(self):
        self._vcs = ChunkVersionControl()
        self._tx_manager = ChunkTransactionManager(self._vcs)
        self._differ = SemanticDiffer()
        self._merger = ChunkMerger()
    
    def edit_function(
        self,
        file_content: str,
        function_name: str,
        new_body: str,
        author: str,
        message: str
    ) -> Tuple[str, ChunkTransaction]:
        """编辑函数 - 块级别操作."""
        # 开始事务
        tx = self._tx_manager.begin(author, message)
        
        try:
            # 找到函数
            tree = ast.parse(file_content)
            func_node = None
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    func_node = node
                    break
            
            if not func_node:
                self._tx_manager.abort()
                raise ValueError(f"Function {function_name} not found")
            
            # 获取原始内容
            lines = file_content.split('\n')
            original_func = '\n'.join(
                lines[func_node.lineno - 1:func_node.end_lineno]
            )
            
            # 保存并添加编辑
            chunk_id = f"func_{function_name}"
            self._tx_manager.add_edit(
                operation=ChunkOperation.REPLACE,
                chunk_id=chunk_id,
                new_content=new_body,
                original_content=original_func
            )
            
            # 生成新文件内容
            new_lines = (
                lines[:func_node.lineno - 1] +
                new_body.split('\n') +
                lines[func_node.end_lineno:]
            )
            new_content = '\n'.join(new_lines)
            
            # 提交
            self._tx_manager.commit()
            
            return new_content, tx
            
        except Exception as e:
            self._tx_manager.rollback()
            raise
    
    def add_function(
        self,
        file_content: str,
        function_code: str,
        after_function: Optional[str] = None,
        author: str = "",
        message: str = ""
    ) -> Tuple[str, ChunkTransaction]:
        """添加函数."""
        tx = self._tx_manager.begin(author, message)
        
        try:
            chunk_id = f"func_new_{int(time.time()*1000)}"
            
            self._tx_manager.add_edit(
                operation=ChunkOperation.INSERT,
                chunk_id=chunk_id,
                new_content=function_code
            )
            
            if after_function:
                # 找到插入位置
                tree = ast.parse(file_content)
                insert_line = len(file_content.split('\n'))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == after_function:
                        insert_line = node.end_lineno
                        break
                
                lines = file_content.split('\n')
                new_lines = (
                    lines[:insert_line] +
                    [''] + function_code.split('\n') +
                    lines[insert_line:]
                )
                new_content = '\n'.join(new_lines)
            else:
                new_content = file_content + '\n\n' + function_code
            
            self._tx_manager.commit()
            return new_content, tx
            
        except Exception as e:
            self._tx_manager.rollback()
            raise
    
    def semantic_diff(self, old_code: str, new_code: str) -> SemanticDiff:
        """获取语义差异."""
        return self._differ.diff(old_code, new_code)
    
    def merge(self, base: str, ours: str, theirs: str) -> MergeResult:
        """三方合并."""
        return self._merger.three_way_merge(base, ours, theirs)
    
    def get_history(self, chunk_id: str) -> List[ChunkVersion]:
        """获取块的版本历史."""
        return self._vcs.get_history(chunk_id)


# 便捷函数
def create_chunk_editor() -> ChunkCodeEditor:
    """创建块级代码编辑器."""
    return ChunkCodeEditor()
