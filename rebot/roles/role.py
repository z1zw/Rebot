"""Role abstraction with observe-think-act loop - Enhanced with MetaGPT patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Set, Type, Optional
import logging

from rebot.actions.action import Action
from rebot.roles.context import RoleContext, RoleReactMode, Memory
from rebot.schema import RoutedMessage, ActionOutput, MessageType, Plan, Task
from rebot.core.messages import Message

logger = logging.getLogger(__name__)


# 模板定义
PREFIX_TEMPLATE = """You are a {profile}, named {name}, your goal is {goal}. """
CONSTRAINT_TEMPLATE = "The constraint is {constraints}. "
STATE_TEMPLATE = """Here are your conversation records. You can decide which stage you should enter or stay in based on these records.
===
{history}
===

Your previous stage: {previous_state}

Now choose one of the following stages you need to go to in the next step:
{states}

Just answer a number between 0-{n_states}, choose the most suitable stage according to the understanding of the conversation.
If you think you have completed your goal and don't need to go to any of the stages, return -1.
"""


def _any_to_str(obj: Any) -> str:
    """将对象转换为字符串标识。"""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, type):
        return obj.__name__
    return type(obj).__name__


def _any_to_str_set(objs: Iterable) -> Set[str]:
    """将对象集合转换为字符串集合。"""
    return {_any_to_str(obj) for obj in objs}


@dataclass
class Role:
    """增强的角色类，支持MetaGPT风格的多角色协作。"""
    # 基本属性
    name: str = ""
    profile: str = ""  # 角色描述，如 "Product Manager"
    goal: str = ""
    constraints: str = ""
    desc: str = ""
    
    # 地址与路由
    address: str = ""
    addresses: Set[str] = field(default_factory=set)
    
    # Actions
    actions: list[Action] = field(default_factory=list)
    states: list[str] = field(default_factory=list)  # Action描述列表
    
    # 上下文
    rc: RoleContext = field(default_factory=RoleContext)
    
    # 协作
    leader: str | None = None  # 上级角色
    subordinates: list[str] = field(default_factory=list)  # 下属角色
    
    # LLM (可选)
    llm: Any = None
    
    # 配置
    enable_memory: bool = True
    recovered: bool = False  # 是否从恢复状态

    def __post_init__(self):
        if not self.address:
            self.address = f"{self.profile}_{self.name}" if self.name else self.profile
        if not self.addresses:
            self.addresses = {self.address, self.name, self.profile}
        self._init_actions()

    def _init_actions(self) -> None:
        """初始化Actions并生成states描述。"""
        self.states = []
        for i, action in enumerate(self.actions):
            self.states.append(f"{i}. {_any_to_str(action)}")

    def set_actions(self, actions: list[Action | Type[Action]]) -> None:
        """设置角色的Actions。"""
        self.actions = []
        self.states = []
        for i, action in enumerate(actions):
            if isinstance(action, type):
                action = action()  # 实例化
            self.actions.append(action)
            self.states.append(f"{i}. {_any_to_str(action)}")

    def _watch(self, actions: Iterable[str | Type[Action]]) -> None:
        """订阅感兴趣的Actions，角色将从msg_buffer中筛选这些Action触发的消息。"""
        self.rc.watch = _any_to_str_set(actions)

    def watch(self, *action_names: str) -> None:
        """订阅Action名称。"""
        for name in action_names:
            self.rc.add_watch(name)

    def unwatch(self, *action_names: str) -> None:
        """取消订阅。"""
        for name in action_names:
            self.rc.remove_watch(name)

    def is_idle(self) -> bool:
        """检查角色是否空闲。"""
        return len(self.rc.inbox) == 0 and self.rc.todo is None

    def _get_prefix(self) -> str:
        """生成角色前缀提示词。"""
        if self.desc:
            return self.desc
        prefix = PREFIX_TEMPLATE.format(
            profile=self.profile,
            name=self.name,
            goal=self.goal
        )
        if self.constraints:
            prefix += CONSTRAINT_TEMPLATE.format(constraints=self.constraints)
        return prefix

    def run(self, env: Any) -> None:
        """执行角色的observe-think-act循环。"""
        # 1. Observe
        observed = self._observe()
        if not observed and self.rc.react_mode != RoleReactMode.PLAN_AND_ACT:
            return
        
        # 2. React based on mode
        if self.rc.react_mode == RoleReactMode.REACT:
            self._react_loop(env)
        elif self.rc.react_mode == RoleReactMode.BY_ORDER:
            self._react_by_order(env)
        elif self.rc.react_mode == RoleReactMode.PLAN_AND_ACT:
            self._react_plan_and_act(env)

    def _react_loop(self, env: Any) -> None:
        """ReAct模式：循环执行think->act。"""
        for _ in range(self.rc.max_react_loop):
            action = self._think()
            if action is None:
                break
            result = self._act(action)
            if result:
                env.publish(result)
            # 检查是否应该终止
            if self.rc.state == -1:
                break

    def _react_by_order(self, env: Any) -> None:
        """按顺序执行所有Actions。"""
        for action in self.actions:
            self._set_state(self.actions.index(action))
            result = self._act(action)
            if result:
                env.publish(result)

    def _react_plan_and_act(self, env: Any) -> None:
        """Plan-Act模式：先规划后执行。"""
        if self.rc.plan is None or not self.rc.plan.pending_tasks:
            # 需要创建新计划
            self._create_plan()
        
        while self.rc.plan and self.rc.plan.current_task:
            task = self.rc.plan.current_task
            # 执行任务
            action = self._select_action_for_task(task)
            if action:
                result = self._act(action)
                if result:
                    env.publish(result)
                    from rebot.schema import TaskResult
                    self.rc.plan.finish_current_task(
                        TaskResult(task_id=task.id, success=True, output=result)
                    )
            else:
                break

    def _create_plan(self) -> None:
        """创建执行计划（可被子类覆盖）。"""
        # 默认简单计划：每个action对应一个task
        tasks = []
        for i, action in enumerate(self.actions):
            tasks.append(Task(
                id=f"task_{i}",
                name=_any_to_str(action),
                description=f"Execute {_any_to_str(action)}",
                assigned_to=self.address
            ))
        if tasks:
            self.rc.plan = Plan(
                goal=self.goal,
                tasks=tasks,
                current_task_id=tasks[0].id if tasks else None
            )

    def _select_action_for_task(self, task: Task) -> Action | None:
        """根据任务选择Action。"""
        for action in self.actions:
            if _any_to_str(action) == task.name:
                return action
        return self.actions[0] if self.actions else None

    def _observe(self) -> list[RoutedMessage]:
        """观察阶段：从inbox获取新消息。"""
        messages = list(self.rc.inbox)
        self.rc.inbox.clear()
        
        # 添加到msg_buffer
        self.rc.msg_buffer.extend(messages)
        
        # 根据watch过滤
        if self.rc.watch:
            messages = [
                m for m in messages
                if m.cause_by in self.rc.watch
                or m.sent_from in self.rc.watch
                or not m.send_to  # 广播消息
                or self.address in m.send_to
                or bool(self.addresses & set(m.send_to))
            ]
        
        # 找出新消息并添加到memory
        news = self.rc.memory.find_news(messages)
        self.rc.memory.add_batch(news)
        self.rc.news = news
        
        return news

    def _think(self) -> Action | None:
        """思考阶段：决定下一步执行哪个Action。"""
        if not self.actions:
            return None
        
        # 如果只有一个action，直接执行
        if len(self.actions) == 1:
            self._set_state(0)
            return self.actions[0]
        
        # 如果从恢复状态，继续之前的action
        if self.recovered and self.rc.state >= 0:
            self.recovered = False
            return self.actions[self.rc.state] if self.rc.state < len(self.actions) else None
        
        # BY_ORDER模式：顺序执行
        if self.rc.react_mode == RoleReactMode.BY_ORDER:
            next_state = self.rc.state + 1
            if 0 <= next_state < len(self.actions):
                self._set_state(next_state)
                return self.actions[next_state]
            return None
        
        # REACT模式：使用LLM选择
        if self.llm:
            next_state = self._think_with_llm()
        else:
            # 无LLM时默认执行第一个
            next_state = 0
        
        if next_state == -1:
            return None
        
        self._set_state(next_state)
        return self.actions[next_state] if 0 <= next_state < len(self.actions) else None

    def _think_with_llm(self) -> int:
        """使用LLM决策下一个状态。"""
        if not self.llm:
            return 0
        
        history_text = "\n".join(
            f"{m.sent_from}: {m.message.content[:200]}" 
            for m in self.rc.memory.get(10)
        )
        
        prompt = self._get_prefix() + STATE_TEMPLATE.format(
            history=history_text,
            previous_state=self.rc.state,
            states="\n".join(self.states),
            n_states=len(self.states) - 1
        )
        
        try:
            response = self.llm.invoke([Message(role="user", content=prompt)], tools=[])
            content = response.content.strip()
            # 解析数字
            import re
            match = re.search(r'-?\d+', content)
            if match:
                return int(match.group())
        except Exception as e:
            logger.warning(f"LLM think failed: {e}")
        
        return 0

    def _set_state(self, state: int) -> None:
        """设置当前状态。"""
        self.rc.state = state
        if 0 <= state < len(self.actions):
            self.rc.todo = self.actions[state]
        else:
            self.rc.todo = None

    def _act(self, action: Action) -> RoutedMessage | None:
        """执行阶段：执行指定Action。"""
        logger.info(f"{self.address}: executing {_any_to_str(action)}")
        
        # 获取历史消息作为输入
        history = self.rc.memory.get(10)
        
        # 执行action
        result = action.run(self, history)
        
        # 处理结果
        if result:
            # 确保设置cause_by
            if not result.cause_by:
                result.cause_by = _any_to_str(action)
            if not result.sent_from:
                result.sent_from = self.address
            
            # 添加到记忆
            self.rc.memory.add(result)
        
        return result

    def put_message(self, message: RoutedMessage) -> None:
        """将消息放入inbox。"""
        self.rc.inbox.append(message)

    def publish_message(self, message: RoutedMessage, env: Any) -> None:
        """发布消息到环境。"""
        if not message.sent_from:
            message.sent_from = self.address
        env.publish(message)

    # ========== Language Tag Support ==========
    
    def process_tagged_input(self, tagged_input: Any) -> RoutedMessage:
        """处理带标签的输入。"""
        from rebot.roles.encoding import TaggedInput
        
        if isinstance(tagged_input, str):
            # 尝试解析标签
            parsed = TaggedInput.parse(tagged_input)
            content = parsed.to_prompt()
        elif isinstance(tagged_input, TaggedInput):
            content = tagged_input.to_prompt()
        else:
            content = str(tagged_input)
        
        return RoutedMessage(
            message=Message(role="user", content=content),
            sent_from=self.address,
            send_to=[],
            cause_by="TaggedInput",
        )
    
    def create_tagged_output(
        self,
        content: str,
        target_tag: str = "any"
    ) -> RoutedMessage:
        """创建带目标标签的输出。"""
        from rebot.roles.encoding import TaggedInput
        
        tagged = TaggedInput(
            content=content,
            source_tag=self.profile,
            target_tag=target_tag
        )
        
        return RoutedMessage(
            message=Message(role="assistant", content=tagged.to_prompt()),
            sent_from=self.address,
            send_to=[],
            cause_by=_any_to_str(self.rc.todo) if self.rc.todo else "Unknown",
            metadata={"target_tag": target_tag}
        )
    
    def get_encoding(self) -> Any:
        """获取角色编码。"""
        from rebot.roles.encoding import RoleEncoder
        encoder = RoleEncoder()
        return encoder.encode(self)

    def serialize(self) -> dict:
        """序列化角色状态。"""
        return {
            "name": self.name,
            "profile": self.profile,
            "goal": self.goal,
            "constraints": self.constraints,
            "desc": self.desc,
            "address": self.address,
            "addresses": list(self.addresses),
            "state": self.rc.state,
            "memory_count": self.rc.memory.count(),
            "watch": list(self.rc.watch),
            "react_mode": self.rc.react_mode.value,
            "leader": self.leader,
            "subordinates": self.subordinates,
        }

    @classmethod
    def deserialize(cls, data: dict, actions: list[Action] = None) -> "Role":
        """反序列化恢复角色。"""
        from rebot.roles.context import RoleReactMode
        
        role = cls(
            name=data.get("name", ""),
            profile=data.get("profile", ""),
            goal=data.get("goal", ""),
            constraints=data.get("constraints", ""),
            desc=data.get("desc", ""),
            address=data.get("address", ""),
            actions=actions or [],
            leader=data.get("leader"),
            subordinates=data.get("subordinates", []),
        )
        role.addresses = set(data.get("addresses", []))
        role.rc.state = data.get("state", -1)
        role.rc.watch = set(data.get("watch", []))
        
        react_mode_str = data.get("react_mode", "react")
        try:
            role.rc.react_mode = RoleReactMode(react_mode_str)
        except ValueError:
            role.rc.react_mode = RoleReactMode.REACT
        
        role.recovered = True
        return role

