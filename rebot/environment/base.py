"""Environment for routing messages between roles - Enhanced with MetaGPT patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, TYPE_CHECKING
from enum import Enum
import logging

from rebot.schema import RoutedMessage, MessageType

if TYPE_CHECKING:
    from rebot.roles.role import Role

logger = logging.getLogger(__name__)


class EnvType(str, Enum):
    """环境类型。"""
    ANDROID = "Android"
    WEREWOLF = "werewolf"
    CREATIVE_GAME = "creative_game"
    SOFTWARE_COMPANY = "software_company"
    CUSTOM = "custom"


@dataclass
class Environment:
    """增强的环境类，支持多角色协作。
    
    Features:
    - 基于cause_by的消息路由
    - 角色地址注册
    - gym风格的step接口
    - 消息历史与快照
    - 审计日志
    """
    # 角色管理
    roles: Dict[str, "Role"] = field(default_factory=dict)
    member_addrs: Dict["Role", Set[str]] = field(default_factory=dict)
    
    # 消息历史
    history: List[RoutedMessage] = field(default_factory=list)
    snapshots: List[List[RoutedMessage]] = field(default_factory=list)
    
    # 审计
    audit_log: List[dict] = field(default_factory=list)
    
    # 回放
    replay_cursor: int = 0
    
    # 环境配置
    env_type: EnvType = EnvType.CUSTOM
    desc: str = ""
    
    # gym风格接口
    _is_done: bool = False
    _obs: List[RoutedMessage] = field(default_factory=list)
    
    # 钩子
    on_message_publish: Optional[Callable[[RoutedMessage], None]] = None

    def register_role(self, role: "Role") -> None:
        """注册角色到环境。"""
        self.roles[role.address] = role
        # 注册所有地址
        self.member_addrs[role] = role.addresses.copy()
        logger.debug(f"Registered role: {role.address} with addresses: {role.addresses}")

    def unregister_role(self, address: str) -> None:
        """注销角色。"""
        if address in self.roles:
            role = self.roles.pop(address)
            self.member_addrs.pop(role, None)

    def set_addresses(self, role: "Role", addresses: Set[str]) -> None:
        """设置角色的地址集合。"""
        role.addresses = addresses
        self.member_addrs[role] = addresses

    def get_roles_by_address(self, address: str) -> List["Role"]:
        """根据地址获取角色。"""
        roles = []
        for role, addrs in self.member_addrs.items():
            if address in addrs:
                roles.append(role)
        return roles

    def get_role(self, address: str) -> Optional["Role"]:
        """获取指定地址的角色。"""
        return self.roles.get(address)

    def publish(self, routed: RoutedMessage) -> None:
        """发布消息，根据cause_by和地址路由到订阅者。"""
        self.history.append(routed)
        
        # 记录审计日志
        self._log_audit(routed)
        
        # 触发钩子
        if self.on_message_publish:
            self.on_message_publish(routed)
        
        # 确定目标
        if routed.send_to:
            # 显式指定目标
            targets = routed.send_to
        else:
            # 广播到所有订阅者
            targets = None
        
        # 分发消息
        for role in self.roles.values():
            if self._should_deliver(role, routed, targets):
                role.put_message(routed)
                logger.debug(f"Delivered message to {role.address}")

    def _should_deliver(self, role: "Role", routed: RoutedMessage, targets: List[str] | None) -> bool:
        """判断是否应该将消息投递给角色。"""
        # 不投递给自己
        if routed.sent_from == role.address:
            return False
        
        # 检查角色是否订阅了cause_by
        if role.rc.watch and routed.cause_by:
            if routed.cause_by in role.rc.watch:
                return True
        
        # 检查标签匹配 (多对多路由)
        if hasattr(routed, 'target_tag') or hasattr(routed, 'target_tags'):
            role_tags = self._get_role_tags(role)
            if routed.matches_tag(role_tags):
                return True
        
        # 检查地址匹配
        if targets:
            # 显式目标
            if role.address in targets:
                return True
            if role.addresses & set(targets):
                return True
            return False
        else:
            # 广播：检查watch
            if not role.rc.watch:
                return True  # 没有watch订阅=接收所有广播
            if routed.sent_from in role.rc.watch:
                return True
            if routed.cause_by and routed.cause_by in role.rc.watch:
                return True
            return False

    def _get_role_tags(self, role: "Role") -> set:
        """获取角色的标签集合。"""
        tags = set()
        
        # 从角色编码获取
        try:
            from rebot.roles.encoding import RoleEncoder
            encoder = RoleEncoder()
            encoding = encoder.encode(role)
            
            # 添加语言标签
            for lang in encoding.languages:
                tags.add(lang.value if hasattr(lang, 'value') else str(lang))
            
            # 添加技能标签
            for skill in encoding.skills:
                tags.add(skill.value if hasattr(skill, 'value') else str(skill))
            
        except Exception:
            pass
        
        # 添加角色基本信息作为标签
        if role.profile:
            tags.add(role.profile.lower())
        if role.name:
            tags.add(role.name.lower())
        
        # 默认接收any
        tags.add("any")
        tags.add("any_XX")
        
        return tags

    def _log_audit(self, routed: RoutedMessage) -> None:
        """记录审计日志。"""
        self.audit_log.append({
            "msg_id": routed.msg_id,
            "sent_from": routed.sent_from,
            "send_to": routed.send_to,
            "cause_by": routed.cause_by,
            "msg_type": routed.msg_type.value if routed.msg_type else None,
            "content": routed.message.content[:200] if routed.message else "",
            "source_tag": getattr(routed, 'source_tag', None),
            "target_tag": getattr(routed, 'target_tag', None),
            "timestamp": routed.metadata.get("timestamp") if routed.metadata else None,
        })

    # ========== Gym-style Interface ==========
    
    def reset(self) -> List[RoutedMessage]:
        """重置环境。"""
        for role in self.roles.values():
            role.rc.inbox.clear()
            role.rc.msg_buffer.clear()
            role.rc.memory.clear()
            role.rc.working_memory.clear()
            role.rc.state = -1
            role.rc.todo = None
        self.history.clear()
        self.audit_log.clear()
        self._is_done = False
        self._obs = []
        return self._obs

    def step(self, actions: List[RoutedMessage] | None = None) -> tuple:
        """执行一步环境更新。
        
        Args:
            actions: 外部注入的消息（可选）
        
        Returns:
            (observations, rewards, done, info)
        """
        # 注入外部消息
        if actions:
            for msg in actions:
                self.publish(msg)
        
        # 运行所有非空闲角色
        active = False
        for role in self.roles.values():
            if not role.is_idle():
                role.run(self)
                active = True
        
        # 收集观察
        self._obs = list(self.history[-10:])  # 最近10条消息
        
        # 检查是否完成
        if not active:
            self._is_done = True
        
        # 计算奖励（可被子类覆盖）
        rewards = self._compute_rewards()
        
        info = {
            "history_length": len(self.history),
            "active_roles": sum(1 for r in self.roles.values() if not r.is_idle()),
        }
        
        return self._obs, rewards, self._is_done, info

    def _compute_rewards(self) -> Dict[str, float]:
        """计算奖励（可被子类覆盖）。"""
        return {addr: 0.0 for addr in self.roles}

    def observe(self, role_address: str | None = None) -> List[RoutedMessage]:
        """获取观察。"""
        if role_address and role_address in self.roles:
            return list(self.roles[role_address].rc.inbox)
        return self._obs

    # ========== Run Methods ==========

    def run(self, *, max_steps: int = 20) -> None:
        """执行多步运行。"""
        steps = 0
        while steps < max_steps:
            _, _, done, _ = self.step()
            if done:
                break
            steps += 1
        self.snapshots.append(list(self.history))

    def run_one_step(self) -> bool:
        """执行单步。"""
        _, _, done, _ = self.step()
        return not done

    # ========== Snapshot & Replay ==========

    def save_snapshot(self) -> int:
        """保存当前状态快照，返回索引。"""
        self.snapshots.append(list(self.history))
        return len(self.snapshots) - 1

    def restore_snapshot(self, index: int) -> None:
        """恢复到指定快照。"""
        if index < 0 or index >= len(self.snapshots):
            raise IndexError("snapshot index out of range")
        self.history = list(self.snapshots[index])

    def replay(self, snapshot_index: int, *, deliver: bool = True) -> None:
        """回放快照。"""
        if snapshot_index < 0 or snapshot_index >= len(self.snapshots):
            raise IndexError("snapshot_index out of range")
        self.history = list(self.snapshots[snapshot_index])
        self.replay_cursor = 0
        if deliver:
            for routed in self.history:
                for role in self.roles.values():
                    if self._should_deliver(role, routed, routed.send_to):
                        role.put_message(routed)

    def replay_step(self) -> bool:
        """回放单步。"""
        if self.replay_cursor >= len(self.history):
            return False
        routed = self.history[self.replay_cursor]
        self.replay_cursor += 1
        for role in self.roles.values():
            if self._should_deliver(role, routed, routed.send_to):
                role.put_message(routed)
        return True

    def replay_pause(self) -> None:
        """暂停回放。"""
        pass

    # ========== Export ==========

    def export_audit(self) -> List[dict]:
        """导出审计日志。"""
        return list(self.audit_log)

    def export_history(self) -> List[dict]:
        """导出消息历史。"""
        return [
            {
                "msg_id": m.msg_id,
                "sent_from": m.sent_from,
                "send_to": m.send_to,
                "cause_by": m.cause_by,
                "content": m.message.content if m.message else "",
            }
            for m in self.history
        ]

    def serialize(self) -> dict:
        """序列化环境状态。"""
        return {
            "env_type": self.env_type.value,
            "desc": self.desc,
            "roles": [r.serialize() for r in self.roles.values()],
            "history": self.export_history(),
        }


# 导入Role以解决循环依赖
from rebot.roles.role import Role  # noqa: E402

