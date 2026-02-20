"""Shared schema types - Enhanced with MetaGPT-style routing and language tags."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Set
from enum import Enum

from rebot.core.messages import Message


class MessageType(str, Enum):
    """Message types for routing."""
    REQUIREMENT = "requirement"           # 用户需求
    DESIGN = "design"                     # 设计文档
    TASK = "task"                         # 任务分配
    CODE = "code"                         # 代码
    REVIEW = "review"                     # 评审
    TEST = "test"                         # 测试
    DOCUMENT = "document"                 # 文档
    SYSTEM = "system"                     # 系统消息
    CHAT = "chat"                         # 普通对话
    TRANSLATION = "translation"           # 翻译
    DELEGATION = "delegation"             # 委托
    FEEDBACK = "feedback"                 # 反馈


@dataclass
class RoutedMessage:
    """Enhanced routed message with cause_by tracking and language tags.
    
    支持的路由方式：
    1. send_to: 显式指定目标角色
    2. cause_by: 基于Action的订阅路由
    3. source_tag/target_tag: 基于标签的多对多路由
    """
    message: Message
    sent_from: str | None = None
    send_to: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # MetaGPT-style cause_by for action tracking
    cause_by: str | None = None           # 触发此消息的Action名称
    msg_type: MessageType = MessageType.CHAT
    
    # 消息ID用于去重
    msg_id: str = field(default_factory=lambda: _gen_msg_id())
    
    # 优先级 (数字越大优先级越高)
    priority: int = 0
    
    # 是否需要回复
    require_reply: bool = False
    
    # Language/Skill Tags for many-to-many routing
    source_tag: str = "any"              # 源标签 (语言/领域)
    target_tag: str = "any"              # 目标标签
    target_tags: List[str] = field(default_factory=list)  # 多目标标签

    def __hash__(self):
        return hash(self.msg_id)

    def __eq__(self, other):
        if isinstance(other, RoutedMessage):
            return self.msg_id == other.msg_id
        return False
    
    def matches_tag(self, role_tags: Set[str]) -> bool:
        """检查消息是否匹配角色的标签。"""
        if self.target_tag == "any":
            return True
        if self.target_tag in role_tags:
            return True
        if self.target_tags:
            return bool(set(self.target_tags) & role_tags)
        return False
    
    def to_tagged_format(self) -> str:
        """转换为带标签的格式。"""
        content = self.message.content if self.message else ""
        return f"[{self.source_tag}] {content} [{self.target_tag}]"
    
    @classmethod
    def from_tagged_format(cls, text: str, **kwargs) -> "RoutedMessage":
        """从带标签的格式解析。"""
        import re
        pattern = r'\[([^\]]+)\]\s*(.+?)\s*\[([^\]]+)\]$'
        match = re.match(pattern, text.strip(), re.DOTALL)
        
        if match:
            source_tag = match.group(1)
            content = match.group(2)
            target_tag = match.group(3)
        else:
            source_tag = "any"
            content = text
            target_tag = "any"
        
        return cls(
            message=Message(role="user", content=content),
            source_tag=source_tag,
            target_tag=target_tag,
            **kwargs
        )


@dataclass
class Task:
    """任务定义，用于计划执行。"""
    id: str
    name: str
    description: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    dependencies: list[str] = field(default_factory=list)  # 依赖的任务id
    assigned_to: str | None = None  # 分配给哪个角色
    priority: int = 0

    @property
    def is_complete(self) -> bool:
        return self.status in ("completed", "failed")


@dataclass
class TaskResult:
    """任务执行结果。"""
    task_id: str
    success: bool
    output: Any = None
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """执行计划。"""
    goal: str
    tasks: list[Task] = field(default_factory=list)
    current_task_id: str | None = None

    @property
    def current_task(self) -> Task | None:
        for task in self.tasks:
            if task.id == self.current_task_id:
                return task
        return None

    @property
    def pending_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status == "pending"]

    @property
    def completed_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status == "completed"]

    def finish_current_task(self, result: TaskResult) -> None:
        if self.current_task:
            self.current_task.status = "completed" if result.success else "failed"
            self.current_task.result = result
        # 移动到下一个pending任务
        next_tasks = self.pending_tasks
        self.current_task_id = next_tasks[0].id if next_tasks else None


@dataclass
class ActionOutput:
    """Action执行输出。"""
    content: str
    instruct_content: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _gen_msg_id() -> str:
    import uuid
    return str(uuid.uuid4())[:12]
