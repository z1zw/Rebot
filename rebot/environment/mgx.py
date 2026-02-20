"""MGX-like environment routing rules."""

from __future__ import annotations

from dataclasses import dataclass

from rebot.environment.base import Environment
from rebot.schema import RoutedMessage


@dataclass
class MGXEnvironment(Environment):
    leader_address: str | None = None
    direct_chat: bool = True

    def publish(self, routed: RoutedMessage) -> None:
        if self.leader_address and routed.sent_from != self.leader_address:
            if self.leader_address not in routed.send_to:
                routed.send_to.append(self.leader_address)
        if self.direct_chat and routed.send_to:
            routed.send_to = [addr for addr in routed.send_to if addr in self.roles]
        super().publish(routed)
