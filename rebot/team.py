"""Team orchestration for roles - Enhanced with MetaGPT patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type
from enum import Enum
import logging
import json

from rebot.context import Context
from rebot.environment.base import Environment
from rebot.roles.role import Role
from rebot.schema import RoutedMessage, MessageType
from rebot.core.serialization import to_dict
from rebot.core.messages import Message

logger = logging.getLogger(__name__)


class ScheduleStrategy(str, Enum):
    """调度策略。"""
    ROUND_ROBIN = "round_robin"      # 轮询
    PRIORITY = "priority"            # 优先级（根据todo数量）
    DEPENDENCY = "dependency"        # 依赖感知
    PARALLEL = "parallel"            # 并行执行


class IdeaSource(str, Enum):
    """需求来源。"""
    HUMAN = "human"
    INTERNET = "internet"
    AI = "ai"


@dataclass
class TeamConfig:
    """团队配置。"""
    budget: float | None = None
    max_rounds: int = 50
    schedule: ScheduleStrategy = ScheduleStrategy.ROUND_ROBIN
    auto_archive: bool = True
    enable_cost_tracking: bool = True
    investment: float = 10.0


@dataclass
class Team:
    """增强的团队类，支持多角色协作调度。
    
    Features:
    - 多种调度策略
    - 预算管理
    - 状态序列化/反序列化
    - 归档与恢复
    - 钩子系统
    """
    # 核心组件
    context: Context
    environment: Environment = field(default_factory=Environment)
    roles: List[Role] = field(default_factory=list)
    
    # 配置
    config: TeamConfig = field(default_factory=TeamConfig)
    
    # 兼容性属性（保持向后兼容）
    budget: float | None = None
    max_rounds: int = 50
    schedule: str = "round_robin"
    
    # 归档
    archive: List[dict] = field(default_factory=list)
    
    # 投资 (类似MetaGPT)
    investment: float = 10.0
    idea: str = ""
    idea_source: IdeaSource = IdeaSource.HUMAN
    
    # 钩子
    on_round_start: Optional[Callable[[int], None]] = None
    on_round_end: Optional[Callable[[int, dict], None]] = None
    on_finish: Optional[Callable[[dict], None]] = None

    def __post_init__(self):
        # 同步兼容性属性到config
        if self.budget is not None:
            self.config.budget = self.budget
        if self.max_rounds != 50:
            self.config.max_rounds = self.max_rounds
        if self.schedule != "round_robin":
            self.config.schedule = ScheduleStrategy(self.schedule)

    def hire(self, *roles: Role) -> None:
        """雇佣角色加入团队。"""
        for role in roles:
            self.roles.append(role)
            self.environment.register_role(role)
            logger.info(f"Hired role: {role.address}")

    def fire(self, address: str) -> bool:
        """解雇角色。"""
        for i, role in enumerate(self.roles):
            if role.address == address:
                self.roles.pop(i)
                self.environment.unregister_role(address)
                logger.info(f"Fired role: {address}")
                return True
        return False

    def invest(self, amount: float) -> None:
        """设置投资预算。"""
        self.investment = amount
        self.config.budget = amount

    def run_project(self, idea: str, source: IdeaSource = IdeaSource.HUMAN) -> dict:
        """启动项目并运行到完成。"""
        self.idea = idea
        self.idea_source = source
        
        # 发布初始需求
        init_msg = RoutedMessage(
            message=Message(role="user", content=idea),
            sent_from="user",
            send_to=[],  # 广播
            cause_by="UserRequirement",
            msg_type=MessageType.REQUIREMENT,
        )
        self.environment.publish(init_msg)
        
        # 运行
        return self.run()

    def run(self) -> dict:
        """执行团队协作。"""
        for round_num in range(self.config.max_rounds):
            # 触发钩子
            if self.on_round_start:
                self.on_round_start(round_num)
            
            # 检查是否有活跃角色
            any_active = self._has_active_roles()
            
            # 检查预算
            if self._is_over_budget():
                logger.info("Budget exhausted, stopping")
                break
            
            # 检查是否所有角色都空闲
            if not any_active:
                logger.info("All roles idle, stopping")
                break
            
            # 按调度策略运行
            self._run_round()
            
            # 收集轮次信息
            round_info = {
                "round": round_num,
                "history_length": len(self.environment.history),
                "cost": self._get_current_cost(),
            }
            
            # 触发钩子
            if self.on_round_end:
                self.on_round_end(round_num, round_info)
        
        # 完成
        result = self.snapshot()
        
        if self.config.auto_archive:
            self.archive.append(result)
        
        if self.on_finish:
            self.on_finish(result)
        
        return result

    def _has_active_roles(self) -> bool:
        """检查是否有活跃角色。"""
        return any(not role.is_idle() for role in self.roles)

    def _is_over_budget(self) -> bool:
        """检查是否超预算。"""
        if self.config.budget is None:
            return False
        return self._get_current_cost() >= self.config.budget

    def _get_current_cost(self) -> float:
        """获取当前总花费。"""
        if hasattr(self.context, 'cost_manager') and self.context.cost_manager:
            return self.context.cost_manager.total_cost
        return 0.0

    def _run_round(self) -> None:
        """执行一轮调度。"""
        strategy = self.config.schedule
        
        if strategy == ScheduleStrategy.ROUND_ROBIN:
            self._run_round_robin()
        elif strategy == ScheduleStrategy.PRIORITY:
            self._run_priority()
        elif strategy == ScheduleStrategy.DEPENDENCY:
            self._run_dependency()
        elif strategy == ScheduleStrategy.PARALLEL:
            self._run_parallel()
        else:
            self._run_round_robin()

    def _run_round_robin(self) -> None:
        """轮询调度。"""
        self.environment.run(max_steps=1)

    def _run_priority(self) -> None:
        """优先级调度（消息多的优先）。"""
        roles = sorted(
            self.roles,
            key=lambda r: len(r.rc.inbox),
            reverse=True
        )
        for role in roles:
            if not role.is_idle():
                role.run(self.environment)

    def _run_dependency(self) -> None:
        """依赖感知调度。"""
        # 建立依赖图
        executed = set()
        pending = list(self.roles)
        
        while pending:
            ready = []
            for role in pending:
                # 检查是否所有依赖都已满足
                if role.leader is None or role.leader in executed:
                    ready.append(role)
            
            if not ready:
                # 没有可执行的，跳出避免死循环
                break
            
            # 执行就绪的角色
            for role in ready:
                if not role.is_idle():
                    role.run(self.environment)
                executed.add(role.address)
                pending.remove(role)

    def _run_parallel(self) -> None:
        """并行调度（同时执行所有非空闲角色）。"""
        # 注：实际上是模拟并行，收集所有结果后再分发
        results: List[RoutedMessage] = []
        
        for role in self.roles:
            if not role.is_idle():
                # 保存当前inbox
                messages = list(role.rc.inbox)
                role.rc.inbox.clear()
                
                # 执行
                for msg in messages:
                    role.put_message(msg)
                role.run(self.environment)

    def snapshot(self) -> dict:
        """创建当前状态快照。"""
        return {
            "idea": self.idea,
            "investment": self.investment,
            "roles": [r.serialize() for r in self.roles],
            "history": [
                {
                    "msg_id": m.msg_id,
                    "sent_from": m.sent_from,
                    "send_to": m.send_to,
                    "cause_by": m.cause_by,
                    "content": m.message.content if m.message else "",
                }
                for m in self.environment.history
            ],
            "budget": self.config.budget,
            "cost": self._get_current_cost(),
            "config": {
                "max_rounds": self.config.max_rounds,
                "schedule": self.config.schedule.value,
            },
        }

    def serialize(self) -> str:
        """序列化为JSON字符串。"""
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2)

    @classmethod
    def deserialize(
        cls,
        data: dict | str,
        context: Context,
        role_factory: Optional[Callable[[dict], Role]] = None
    ) -> "Team":
        """从快照反序列化。"""
        if isinstance(data, str):
            data = json.loads(data)
        
        team = cls(
            context=context,
            config=TeamConfig(
                budget=data.get("budget"),
                max_rounds=data.get("config", {}).get("max_rounds", 50),
                schedule=ScheduleStrategy(data.get("config", {}).get("schedule", "round_robin")),
            )
        )
        team.idea = data.get("idea", "")
        team.investment = data.get("investment", 10.0)
        
        # 恢复角色
        if role_factory:
            for role_data in data.get("roles", []):
                role = role_factory(role_data)
                team.hire(role)
        
        return team

    def get_role(self, address: str) -> Optional[Role]:
        """获取指定角色。"""
        for role in self.roles:
            if role.address == address:
                return role
        return None

    def list_roles(self) -> List[str]:
        """列出所有角色地址。"""
        return [r.address for r in self.roles]

    def export_conversation(self) -> List[dict]:
        """导出对话历史。"""
        return [
            {
                "from": m.sent_from,
                "to": m.send_to,
                "content": m.message.content if m.message else "",
                "cause_by": m.cause_by,
            }
            for m in self.environment.history
        ]

