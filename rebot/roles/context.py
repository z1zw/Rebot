"""Role context - Enhanced with MetaGPT-style memory and state management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Set
from enum import Enum

from rebot.schema import RoutedMessage, Plan


class RoleReactMode(str, Enum):
    """角色反应模式。"""
    REACT = "react"              # 标准ReAct循环: think->act->observe
    BY_ORDER = "by_order"        # 按顺序执行actions
    PLAN_AND_ACT = "plan_and_act"  # 先规划再执行


@dataclass
class Memory:
    """增强的记忆存储，支持按cause_by索引。"""
    storage: list[RoutedMessage] = field(default_factory=list)
    index: dict[str, list[RoutedMessage]] = field(default_factory=dict)

    def add(self, message: RoutedMessage) -> None:
        """添加消息到存储。"""
        if message in self.storage:
            return
        self.storage.append(message)
        if message.cause_by:
            if message.cause_by not in self.index:
                self.index[message.cause_by] = []
            self.index[message.cause_by].append(message)

    def add_batch(self, messages: list[RoutedMessage]) -> None:
        for msg in messages:
            self.add(msg)

    def get(self, k: int = 0) -> list[RoutedMessage]:
        """获取最近k条消息，k=0返回全部。"""
        return self.storage[-k:] if k > 0 else list(self.storage)

    def get_by_action(self, action_name: str) -> list[RoutedMessage]:
        """获取由指定Action触发的消息。"""
        return self.index.get(action_name, [])

    def get_by_actions(self, action_names: Set[str]) -> list[RoutedMessage]:
        """获取由指定Action集合触发的消息。"""
        result = []
        for name in action_names:
            result.extend(self.index.get(name, []))
        return result

    def clear(self) -> None:
        self.storage.clear()
        self.index.clear()

    def count(self) -> int:
        return len(self.storage)

    def find_news(self, observed: list[RoutedMessage]) -> list[RoutedMessage]:
        """找出未见过的新消息。"""
        return [m for m in observed if m not in self.storage]


@dataclass
class RoleContext:
    """增强的角色上下文。"""
    # 消息队列
    inbox: list[RoutedMessage] = field(default_factory=list)
    msg_buffer: list[RoutedMessage] = field(default_factory=list)
    # 记忆系统
    memory: Memory = field(default_factory=Memory)
    working_memory: Memory = field(default_factory=Memory)  # 工作记忆，任务完成后清空
    # 状态管理
    state: int = -1  # 当前状态索引，-1表示初始或终止
    todo: Any | None = None  # 当前要执行的Action
    # 订阅机制 (MetaGPT核心)
    watch: Set[str] = field(default_factory=set)  # 订阅的Action名称
    addresses: Set[str] = field(default_factory=set)  # 角色的地址集
    # 执行模式
    react_mode: RoleReactMode = RoleReactMode.REACT
    max_react_loop: int = 3
    # 计划
    plan: Plan | None = None
    # 新消息 (本轮观察到的)
    news: list[RoutedMessage] = field(default_factory=list)

    @property
    def important_memory(self) -> list[RoutedMessage]:
        """获取与订阅Action相关的记忆。"""
        return self.memory.get_by_actions(self.watch)

    @property
    def history(self) -> list[RoutedMessage]:
        """获取全部历史。"""
        return self.memory.get()

    def set_watch(self, *action_names: str) -> None:
        """设置订阅的Action。"""
        self.watch = set(action_names)

    def add_watch(self, action_name: str) -> None:
        """添加订阅的Action。"""
        self.watch.add(action_name)

    def remove_watch(self, action_name: str) -> None:
        """移除订阅的Action。"""
        self.watch.discard(action_name)
