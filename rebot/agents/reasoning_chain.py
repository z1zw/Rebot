"""Reasoning-chain extraction and mechanism completion."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from rebot.agents.middleware import AgentState
from rebot.core.messages import Message
from rebot.models.base import ChatModel


def _hash_messages(messages: list[Message]) -> str:
    data = "\n".join(f"{m.role}:{m.content}" for m in messages[-8:])
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass
class ReasoningChainExtractor:
    model: ChatModel

    def extract(
        self,
        messages: list[Message],
        *,
        external_view: str | None = None,
        external_views: list[str] | None = None,
        external_weights: list[float] | None = None,
    ) -> "ReasoningChainSchema":
        prompt = (
            "Extract a concise reasoning chain (steps) from the input. "
            "Use 3-7 steps, each a short phrase. Identify missing steps."
        )
        content = "\n".join(f"{m.role}: {m.content}" for m in messages[-6:])
        views = []
        if external_view:
            views.append(external_view)
        if external_views:
            views.extend([v for v in external_views if v])
        if views:
            if external_weights and len(external_weights) == len(views):
                weighted = [f"[w={w}] {v}" for w, v in zip(external_weights, views, strict=False)]
                content = f"{content}\n\nExternal views:\n" + "\n---\n".join(weighted)
            else:
                content = f"{content}\n\nExternal views:\n" + "\n---\n".join(views)
        schema = ReasoningChainSchema
        response = _invoke_structured(self.model, prompt, content, schema)
        return response


@dataclass
class MechanismCompletion:
    model: ChatModel

    def complete(
        self,
        chain: "ReasoningChainSchema",
        messages: list[Message],
        *,
        external_view: str | None = None,
        external_views: list[str] | None = None,
        external_weights: list[float] | None = None,
    ) -> "CompletionSchema":
        prompt = (
            "Given a reasoning chain and context, infer missing mechanism details. "
            "Provide short completion hints (1-3 bullets) and map them to missing steps."
        )
        content = "\n".join(f"{m.role}: {m.content}" for m in messages[-6:])
        views = []
        if external_view:
            views.append(external_view)
        if external_views:
            views.extend([v for v in external_views if v])
        if views:
            if external_weights and len(external_weights) == len(views):
                weighted = [f"[w={w}] {v}" for w, v in zip(external_weights, views, strict=False)]
                content = f"{content}\n\nExternal views:\n" + "\n---\n".join(weighted)
            else:
                content = f"{content}\n\nExternal views:\n" + "\n---\n".join(views)
        schema = CompletionSchema
        response = _invoke_structured(
            self.model,
            prompt,
            f"Chain:\n{chain}\n\nContext:\n{content}",
            schema,
        )
        return response


@dataclass
class ReasoningChainMiddleware:
    model: ChatModel
    cache: dict[str, tuple[str, str]] = field(default_factory=dict)

    def before_model(self, state: AgentState, context) -> dict[str, Any] | None:
        cfg = state.configurable or {}
        if not cfg.get("enable_reasoning_chain", False):
            return None
        external_view = cfg.get("external_view")
        external_views = cfg.get("external_views")
        external_weights = cfg.get("external_weights")
        key = _hash_messages(state.messages)
        if key in self.cache:
            chain_text, hint_text = self.cache[key]
        else:
            extractor = ReasoningChainExtractor(self.model)
            chain_obj = extractor.extract(
                state.messages,
                external_view=external_view,
                external_views=external_views,
                external_weights=external_weights,
            )
            completer = MechanismCompletion(self.model)
            completion_obj = completer.complete(
                chain_obj,
                state.messages,
                external_view=external_view,
                external_views=external_views,
                external_weights=external_weights,
            )
            completion_obj.gap_score = _compute_gap_score(chain_obj, completion_obj)
            if chain_obj.confidence < 0.35 or completion_obj.confidence < 0.35:
                chain_obj = extractor.extract(
                    state.messages,
                    external_view=external_view,
                    external_views=external_views,
                    external_weights=external_weights,
                )
                completion_obj = completer.complete(
                    chain_obj,
                    state.messages,
                    external_view=external_view,
                    external_views=external_views,
                    external_weights=external_weights,
                )
                completion_obj.gap_score = _compute_gap_score(chain_obj, completion_obj)
            if completion_obj.gap_score > 0.7:
                _auto_retrieve_view(state, cfg)
            chain_text = "\n".join(f"- {s}" for s in chain_obj.steps)
            hint_text = "\n".join(f"- {h}" for h in completion_obj.hints)
            state.reasoning_chain_structured = chain_obj.model_dump()
            state.completion_structured = completion_obj.model_dump()
            self.cache[key] = (chain_text, hint_text)
        state.reasoning_chain = chain_text
        state.completion_hint = hint_text
        state.messages.insert(
            0,
            Message(
                role="system",
                content=f"Reasoning chain:\n{chain_text}\n\nCompletion hint:\n{hint_text}",
            ),
        )
        if completion_obj.tasks:
            if hasattr(state, "rc") and hasattr(state.rc, "state"):
                state.rc.state.setdefault("auto_tasks", []).extend(completion_obj.tasks)
        if completion_obj.auto_actions:
            if hasattr(state, "rc") and hasattr(state.rc, "state"):
                state.rc.state.setdefault("auto_actions", []).extend(completion_obj.auto_actions)
                from rebot.actions.action_factory import build_action_from_text, build_tool_action

                for act in completion_obj.auto_actions:
                    if act.lower().startswith("tool:"):
                        state.rc.todo.append(build_tool_action(act, model=self.model))
                    else:
                        state.rc.todo.append(build_action_from_text(act, model=self.model))
                _execute_auto_actions(state, cfg, completion_obj.auto_actions)
        return None


class ReasoningChainSchema(BaseModel):
    steps: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class CompletionSchema(BaseModel):
    hints: list[str] = Field(default_factory=list)
    fill_map: dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.0
    gap_score: float = 0.0
    tasks: list[str] = Field(default_factory=list)
    auto_actions: list[str] = Field(default_factory=list)


def _invoke_structured(model: ChatModel, prompt: str, content: str, schema: type[BaseModel]):
    if getattr(model, "supports_response_format", False):
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
            },
        }
        msg = model.invoke([Message(role="user", content=f"{prompt}\n\n{content}")], tools=[], response_format=response_format)
        return _parse_schema_with_repair(model, schema, msg.content, prompt, content)
    msg = model.invoke(
        [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{content}")],
        tools=[],
    )
    return _parse_schema_with_repair(model, schema, msg.content, prompt, content)


def _parse_schema_with_repair(
    model: ChatModel,
    schema: type[BaseModel],
    raw: str,
    prompt: str,
    content: str,
    retries: int = 3,
):
    try:
        return schema.model_validate_json(raw)
    except Exception:
        pass
    extracted = _extract_json_object(raw)
    if extracted:
        try:
            return schema.model_validate_json(extracted)
        except Exception:
            pass
    for _ in range(retries):
        repair_prompt = (
            f"{prompt}\n\n"
            "Return valid JSON only. No markdown, no explanation, no trailing text.\n"
            f"Target schema: {schema.model_json_schema()}\n\n"
            "If previous JSON is truncated or has wrong field types, repair it to match schema exactly.\n\n"
            f"Context:\n{content}\n\n"
            f"Previous output:\n{raw}"
        )
        kwargs: dict[str, Any] = {"tools": []}
        if getattr(model, "supports_response_format", False):
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }
        msg = model.invoke([Message(role="user", content=repair_prompt)], **kwargs)
        raw = msg.content
        try:
            return schema.model_validate_json(raw)
        except Exception:
            extracted = _extract_json_object(raw)
            if extracted:
                try:
                    return schema.model_validate_json(extracted)
                except Exception:
                    continue
    raise ValueError(f"{schema.__name__} parse failed after repair retries")


def _compute_gap_score(chain: ReasoningChainSchema, completion: CompletionSchema) -> float:
    if not chain.missing:
        return 0.0
    filled = sum(1 for m in chain.missing if m in completion.fill_map)
    return 1.0 - (filled / max(len(chain.missing), 1))


def _auto_retrieve_view(state: AgentState, cfg: dict[str, Any]) -> None:
    retriever = cfg.get("external_retriever")
    if not retriever:
        return
    user_msg = ""
    for m in reversed(state.messages):
        if m.role == "user":
            user_msg = m.content
            break
    if not user_msg:
        return
    view = retriever(user_msg)
    if not view:
        return
    cfg.setdefault("external_views", []).append(view)
    state.messages.insert(
        0,
        Message(role="system", content=f"External view (auto):\n{view}"),
    )


def _execute_auto_actions(state: AgentState, cfg: dict[str, Any], actions: list[str]) -> None:
    tools = cfg.get("tool_registry") or []
    if not tools:
        return
    from rebot.tools.tool_node import ToolNode
    from rebot.core.messages import ToolCall, Message

    tool_node = ToolNode(tools)
    tool_calls: list[ToolCall] = []
    for act in actions:
        if not act.lower().startswith("tool:"):
            continue
        name, args = _parse_tool_action(act)
        if name:
            tool_calls.append(ToolCall(id=name, name=name, args=args))
    if not tool_calls:
        return
    tool_messages = tool_node.execute(tool_calls)
    state.messages.extend(tool_messages)
    state.change_log.extend([f"tool:{m.name} -> {m.content[:200]}" for m in tool_messages])


def _parse_tool_action(text: str) -> tuple[str | None, dict[str, Any]]:
    raw = text[len("tool:") :].strip()
    if "{" in raw and raw.endswith("}"):
        name, json_part = raw.split("{", 1)
        name = name.strip()
        try:
            args = json.loads("{" + json_part)
        except Exception:
            args = {}
        return name, args
    parts = raw.split()
    if not parts:
        return None, {}
    name = parts[0]
    args: dict[str, Any] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            args[k] = v
    return name, args


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
