"""Action abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any

from rebot.schema import RoutedMessage
from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.agents.structured_output import (
    ToolStrategy,
    ProviderStrategy,
    AutoStrategy,
    schema_name,
    parse_structured,
)
from rebot.tools.structured import StructuredOutputTool


class Action(Protocol):
    name: str

    def run(self, context: Any, inbox: list[RoutedMessage]) -> RoutedMessage | None:
        ...


@dataclass
class SimpleAction:
    name: str
    handler: callable

    def run(self, context: Any, inbox: list[RoutedMessage]) -> RoutedMessage | None:
        return self.handler(context, inbox)


@dataclass
class CompositeAction:
    name: str
    actions: list[Action]

    def run(self, context: Any, inbox: list[RoutedMessage]) -> RoutedMessage | None:
        result: RoutedMessage | None = None
        for action in self.actions:
            result = action.run(context, inbox)
            if result is None:
                break
            inbox.append(result)
        return result


@dataclass
class ActionNode:
    name: str
    prompt: str
    output_to: str | None = None
    model: ChatModel | None = None
    response_format: ToolStrategy | ProviderStrategy | AutoStrategy | None = None
    max_retries: int = 1

    def run(self, context: Any, inbox: list[RoutedMessage]) -> RoutedMessage | None:
        if not inbox:
            return None
        latest = inbox[-1]
        context_text = "\n".join(m.message.content for m in inbox[-5:])
        content = f"{self.prompt}\n\n{context_text}"
        if self.model is None:
            msg = Message(role="assistant", content=content)
        else:
            kwargs: dict[str, Any] = {}
            tools = []
            if isinstance(self.response_format, ProviderStrategy):
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name(self.response_format.schema),
                        "schema": (
                            self.response_format.schema
                            if isinstance(self.response_format.schema, dict)
                            else {}
                        ),
                    },
                }
            if isinstance(self.response_format, ToolStrategy):
                tool = StructuredOutputTool(
                    name=self.response_format.tool_name
                    or schema_name(self.response_format.schema),
                    description="ActionNode structured output",
                    input_schema=(
                        self.response_format.schema
                        if isinstance(self.response_format.schema, dict)
                        else {}
                    ),
                )
                tools = [tool]
                kwargs["tool_choice"] = "auto"
            attempts = 0
            while True:
                msg = self.model.invoke([Message(role="user", content=content)], tools=tools, **kwargs)
                if isinstance(self.response_format, ToolStrategy) and msg.tool_calls:
                    tool_name = self.response_format.tool_name or schema_name(self.response_format.schema)
                    parsed = False
                    for tc in msg.tool_calls:
                        if tc.name == tool_name:
                            try:
                                structured = parse_structured(self.response_format.schema, tc.args)
                                msg = Message(role="assistant", content=str(structured))
                                if hasattr(context, "rc"):
                                    context.rc.state["structured_output"] = structured
                                parsed = True
                                break
                            except Exception:
                                parsed = False
                    if parsed or not self.response_format.handle_errors:
                        break
                else:
                    break
                attempts += 1
                if attempts > self.max_retries:
                    break
        return RoutedMessage(
            message=msg,
            sent_from=getattr(context, "address", None),
            send_to=[self.output_to] if self.output_to else [],
        )
