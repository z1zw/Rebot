"""MetaGPT-like role pipeline (Product -> Architect -> Engineer)."""

from __future__ import annotations

from dataclasses import dataclass, field

from rebot.roles.role import Role
from rebot.roles.context import RoleContext
from rebot.core.messages import Message
from rebot.actions.action import ActionNode
from rebot.environment.base import Environment
from rebot.schema import RoutedMessage


@dataclass
class ProductManager(Role):
    address: str = "product_manager"

    def _init_actions(self) -> None:
        self.actions = [
            ActionNode(
                name="write_prd",
                prompt="Write a clear PRD for: {task}. Return markdown.",
                model=self.model,
            )
        ]

    def _init_rc(self) -> None:
        self.rc = RoleContext()


@dataclass
class Architect(Role):
    address: str = "architect"

    def _init_actions(self) -> None:
        self.actions = [
            ActionNode(
                name="write_design",
                prompt="Design the system architecture for: {task}. Return markdown with modules and data flow.",
                model=self.model,
            )
        ]

    def _init_rc(self) -> None:
        self.rc = RoleContext()


@dataclass
class Engineer(Role):
    address: str = "engineer"

    def _init_actions(self) -> None:
        self.actions = [
            ActionNode(
                name="write_tasks",
                prompt="Generate implementation tasks for: {task}. Return markdown checklist.",
                model=self.model,
            )
        ]

    def _init_rc(self) -> None:
        self.rc = RoleContext()


@dataclass
class MetaGPTRolePipeline:
    model: any
    task: str
    messages: list[Message] = field(default_factory=list)

    def run(self) -> list[Message]:
        pm = ProductManager(model=self.model)
        arch = Architect(model=self.model)
        eng = Engineer(model=self.model)
        pm.actions[0].output_to = arch.address
        arch.actions[0].output_to = eng.address
        env = Environment()
        env.register_role(pm)
        env.register_role(arch)
        env.register_role(eng)
        env.publish(
            RoutedMessage(
                message=Message(role="user", content=self.task),
                sent_from="user",
                send_to=[pm.address],
            )
        )
        env.run(max_steps=6)
        self.messages.extend([m.message for m in env.history])
        return self.messages
