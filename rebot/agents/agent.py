"""Agent loop for model and tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, TypeVar, Any, Callable
import uuid
import re
from collections import Counter, defaultdict

from pydantic import TypeAdapter
from xml.sax.saxutils import escape

from rebot.agents.middleware import AgentMiddleware, AgentState
from rebot.agents.schema import merge_state_schema
from rebot.agents.structured_output import (
    AutoStrategy,
    ProviderStrategy,
    ResponseFormat,
    ToolStrategy,
    parse_json_message,
    parse_structured,
    schema_name,
    resolve_response_format,
    provider_kwargs,
    structured_tool_from_strategy,
    parse_structured_from_message,
)
from rebot.agents.context_compress import (
    COMPRESS_NONE,
    COMPRESS_RECENT_ONLY,
    COMPRESS_SUMMARY_STUB,
    COMPRESS_SUMMARY_XML,
    COMPRESS_GRAPH_SPARSE,
    normalize_compress_type,
)
from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.core.callbacks import create_event_manager
from rebot.tools.structured import StructuredOutputTool
from rebot.agents.graph_runtime import GraphRuntime
from rebot.tools.base import BaseTool
from rebot.tools.tool_node import ToolNode

ContextT = TypeVar("ContextT")
ResponseT = TypeVar("ResponseT")


@dataclass
class Agent:
    model: ChatModel
    tools: Sequence[BaseTool] = ()
    middleware: Sequence[AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]] = ()
    response_format: ResponseFormat[ResponseT] | None = None
    state_schema: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        schemas: set[type] = {AgentState}
        for m in self.middleware:
            schema = getattr(m, "state_schema", None)
            if schema:
                schemas.add(schema)
        self.state_schema = merge_state_schema(schemas, omit_flag=None)
        self.input_schema = merge_state_schema(schemas, omit_flag="input")
        self.output_schema = merge_state_schema(schemas, omit_flag="output")

    def run(self, state: AgentState[ResponseT], context: ContextT) -> AgentState[ResponseT]:
        _init_run_context(state)
        callbacks = _get_callbacks(state)
        if _fast_path(state):
            return state
        runtime = _build_runtime(
            state,
            context,
            self.middleware,
            self.model,
            self.tools,
            self.response_format,
            callbacks,
        )
        return runtime.run(state, context)

    async def run_async(
        self, state: AgentState[ResponseT], context: ContextT
    ) -> AgentState[ResponseT]:
        _init_run_context(state)
        callbacks = _get_callbacks(state)
        if _fast_path(state):
            return state
        for m in self.middleware:
            update = m.before_agent(state, context)
            if update:
                state.__dict__.update(update)
        if callbacks:
            callbacks.on_run_start(
                self.__class__.__name__,
                {"messages": state.messages},
                state.run_id or "",
            )

        tool_node = ToolNode(self.tools)
        available_tool_names = {t.name for t in self.tools}

        while True:
            for m in self.middleware:
                update = m.before_model(state, context)
                if update:
                    state.__dict__.update(update)

            effective_format = _resolve_response_format(self.response_format, self.model)
            tool_choice = "auto" if isinstance(effective_format, ToolStrategy) else None
            model_tools = list(self.tools)
            structured_tool_name = None
            if isinstance(effective_format, ToolStrategy):
                structured_tool = _structured_tool_from_schema(effective_format)
                structured_tool_name = structured_tool.name
                model_tools.append(structured_tool)

            before_count = len(state.messages)
            if callbacks:
                callbacks.on_model_start(
                    self.model.__class__.__name__,
                    {"messages": state.messages},
                    state.run_id or "",
                    state.span_id or "",
                )
            message = await _ainvoke_model_with_middleware(
                self.middleware,
                self.model,
                state.messages,
                model_tools,
                response_format=_provider_kwargs(effective_format),
                tool_choice=tool_choice,
                configurable=state.configurable,
            )
            if callbacks:
                callbacks.on_model_end(
                    self.model.__class__.__name__,
                    {"message": message},
                    state.run_id or "",
                    state.span_id or "",
                )
            state.messages.append(message)

            for m in self.middleware:
                update = m.after_model(state, context)
                if update:
                    state.__dict__.update(update)

            if _apply_structured_output(state, message, effective_format):
                _record_change_log(state, state.messages[before_count:])
                break

            if self._should_end(state):
                break

            if message.tool_calls:
                _validate_tool_calls(
                    message.tool_calls,
                    available_tool_names,
                    self.middleware,
                    structured_tool_name=structured_tool_name,
                )
                if _handle_structured_tool_calls(state, message, effective_format):
                    _record_change_log(state, state.messages[before_count:])
                    continue
                tool_messages = _execute_tools_with_middleware(
                    self.middleware,
                    tool_node,
                    message.tool_calls,
                    callbacks=callbacks,
                    run_id=state.run_id or "",
                    span_id=state.span_id or "",
                )
                state.messages.extend(tool_messages)
                _record_change_log(state, state.messages[before_count:])
                if _should_end_after_tools(message, tool_node):
                    break
                continue

            break

        for m in self.middleware:
            update = m.after_agent(state, context)
            if update:
                state.__dict__.update(update)
        if callbacks:
            callbacks.on_run_end(
                self.__class__.__name__,
                {"messages": state.messages},
                state.run_id or "",
            )

        return state

    def _should_end(self, state: AgentState[ResponseT]) -> bool:
        if state.structured_response is not None:
            return True
        if not state.messages:
            return True
        last = state.messages[-1]
        return last.role == "assistant" and not last.tool_calls


def _record_change_log(state: AgentState, new_messages: list[Message]) -> None:
    for msg in new_messages:
        if msg.role == "tool":
            state.change_log.append(f"tool:{msg.name} -> {msg.content[:200]}")


def _provider_kwargs(response_format: ResponseFormat | None) -> dict[str, object] | None:
    return provider_kwargs(response_format)


def _resolve_response_format(
    response_format: ResponseFormat | None, model: ChatModel
) -> ResponseFormat | None:
    supports = getattr(model, "supports_response_format", False)
    return resolve_response_format(response_format, supports_provider=supports)


def _fast_path(state: AgentState) -> bool:
    if not state.messages:
        return False
    last = state.messages[-1]
    # Never skip real user requests; only allow a no-op fast path for tiny
    # assistant tails that are already completed and have no tool calls.
    return (
        last.role == "assistant"
        and not last.tool_calls
        and len((last.content or "").strip()) < 20
    )


def _trim_messages(messages: list[Message], configurable: dict[str, Any] | None) -> list[Message]:
    if not configurable:
        return messages
    max_chars = configurable.get("max_context_chars")
    max_tokens = configurable.get("max_context_tokens")
    if not max_chars and max_tokens:
        try:
            max_chars = int(max_tokens) * 4
        except Exception:
            max_chars = None
    if not max_chars:
        return messages
    strategy = normalize_compress_type(configurable.get("context_compress_type"))
    if strategy == COMPRESS_NONE:
        return messages
    if strategy == COMPRESS_RECENT_ONLY:
        total = 0
        trimmed: list[Message] = []
        for msg in reversed(messages):
            total += len(msg.content)
            trimmed.append(msg)
            if total >= max_chars:
                break
        return list(reversed(trimmed))

    keep_head_ratio = configurable.get("context_head_ratio")
    try:
        keep_head_ratio = float(keep_head_ratio) if keep_head_ratio is not None else 0.25
    except Exception:
        keep_head_ratio = 0.25
    keep_head_ratio = min(0.6, max(0.0, keep_head_ratio))
    head_budget = int(max_chars * keep_head_ratio)
    tail_budget = max_chars - head_budget

    head: list[Message] = []
    head_chars = 0
    for msg in messages:
        if msg.role == "system" or head_chars < head_budget:
            head.append(msg)
            head_chars += len(msg.content or "")
            continue
        break

    tail: list[Message] = []
    tail_chars = 0
    for msg in reversed(messages):
        if msg in head:
            continue
        tail_chars += len(msg.content or "")
        tail.append(msg)
        if tail_chars >= tail_budget:
            break
    tail = list(reversed(tail))

    merged: list[Message] = []
    seen = set()
    for msg in head + tail:
        key = (msg.role, msg.name or "", msg.content)
        if key in seen:
            continue
        seen.add(key)
        merged.append(msg)

    if strategy in {COMPRESS_SUMMARY_STUB, COMPRESS_SUMMARY_XML, COMPRESS_GRAPH_SPARSE}:
        dropped = len(messages) - len(merged)
        if dropped > 0:
            dropped_msgs = [m for m in messages if m not in merged]
            matrix_rows = _bounded_int(configurable.get("context_matrix_rows"), default=8, low=2, high=32)
            matrix_cols = _bounded_int(configurable.get("context_matrix_cols"), default=8, low=2, high=32)
            sketch_dim = _bounded_int(configurable.get("context_sketch_dim"), default=64, low=16, high=512)
            digest = _build_context_digest_xml(
                dropped_msgs,
                include_graph=(strategy == COMPRESS_GRAPH_SPARSE),
                include_sparse=(strategy == COMPRESS_GRAPH_SPARSE),
                matrix_rows=matrix_rows,
                matrix_cols=matrix_cols,
                sketch_dim=sketch_dim,
            )
            if digest:
                merged.insert(
                    0,
                    Message(
                        role="system",
                        content=digest,
                    ),
                )
            merged.insert(
                0,
                Message(
                    role="system",
                    content=(
                        f"Context compressed: {dropped} earlier messages omitted. "
                        "Prioritize latest user request and preserved system constraints."
                    ),
                ),
            )
    return merged


def _build_context_digest_xml(
    messages: list[Message],
    max_items: int = 8,
    *,
    include_graph: bool = False,
    include_sparse: bool = False,
    matrix_rows: int = 8,
    matrix_cols: int = 8,
    sketch_dim: int = 64,
) -> str:
    items: list[str] = []
    raw_fragments: list[str] = []
    candidates = messages[-16:]
    for msg in candidates:
        role = escape(msg.role)
        for kind, snippet in _extract_salient_fragments(msg.content):
            if len(items) >= max_items:
                break
            raw_fragments.append(snippet)
            if kind == "code":
                cdata = snippet.replace("]]>", "]]]]><![CDATA[>")
                items.append(
                    f'<item role="{role}" kind="{kind}"><![CDATA[{cdata}]]></item>'
                )
            else:
                items.append(
                    f'<item role="{role}" kind="{kind}">{escape(snippet)}</item>'
                )
        if len(items) >= max_items:
            break
    if not items:
        return ""
    sections = ["<items>", *items, "</items>"]

    if include_graph:
        graph_xml = _build_graph_digest_xml(raw_fragments)
        if graph_xml:
            sections.append(graph_xml)

    if include_sparse:
        sparse_xml = _build_sparse_digest_xml(raw_fragments)
        if sparse_xml:
            sections.append(sparse_xml)
        attn_xml = _build_attention_matrix_xml(
            raw_fragments,
            rows=matrix_rows,
            cols=matrix_cols,
            sketch_dim=sketch_dim,
        )
        if attn_xml:
            sections.append(attn_xml)

    body = "\n".join(sections)
    return f"<context_digest>\n{body}\n</context_digest>"


def _extract_salient_fragments(content: str) -> list[tuple[str, str]]:
    if not content:
        return []
    out: list[tuple[str, str]] = []

    code_blocks = re.findall(r"```(?:[^\n`]*)\n([\s\S]*?)```", content)
    for block in code_blocks[:2]:
        clip = _clip_fragment(block, 320)
        if clip:
            out.append(("code", clip))

    xml_blocks = re.findall(
        r"<([A-Za-z_][\\w\\-:.]*)(?:\\s[^>]*)?>[\\s\\S]{1,500}?</\\1>",
        content,
    )
    if "<" in content and ">" in content:
        # Capture short XML-like snippets even when full block regex is not perfect.
        lines = [ln.strip() for ln in content.splitlines() if "<" in ln and ">" in ln]
        for line in lines[:2]:
            clip = _clip_fragment(line, 260)
            if clip:
                out.append(("xml", clip))
    if xml_blocks:
        # `xml_blocks` regex returns tag names due grouping; keep lines-based snippet above.
        pass

    for line in content.splitlines():
        low = line.lower()
        if any(k in low for k in ("error", "exception", "traceback", "failed", "todo", "fixme")):
            clip = _clip_fragment(line, 220)
            if clip:
                out.append(("signal", clip))
                if len([x for x in out if x[0] == "signal"]) >= 2:
                    break

    if not out:
        text = _clip_fragment(content, 180)
        if text:
            out.append(("summary", text))
    return out


def _build_graph_digest_xml(fragments: list[str], max_nodes: int = 48, max_edges: int = 96) -> str:
    nodes: set[str] = set()
    edge_weights: defaultdict[tuple[str, str], int] = defaultdict(int)

    for frag in fragments:
        symbols = _extract_symbols_for_graph(frag)
        if len(symbols) < 2:
            continue
        for s in symbols:
            if len(nodes) < max_nodes:
                nodes.add(s)
        for i in range(len(symbols) - 1):
            a, b = symbols[i], symbols[i + 1]
            if a == b:
                continue
            if (a in nodes) and (b in nodes):
                edge_weights[(a, b)] += 1

    if not nodes:
        return ""

    node_lines = [f'<node id="{escape(n)}" />' for n in sorted(nodes)]
    edges_sorted = sorted(edge_weights.items(), key=lambda kv: kv[1], reverse=True)[:max_edges]
    edge_lines = [
        f'<edge src="{escape(a)}" dst="{escape(b)}" w="{w}" />'
        for (a, b), w in edges_sorted
    ]
    return (
        f'<graph nodes="{len(node_lines)}" edges="{len(edge_lines)}">\n'
        + "\n".join(node_lines + edge_lines)
        + "\n</graph>"
    )


def _extract_symbols_for_graph(text: str) -> list[str]:
    # Keep language-agnostic symbols and include C/C++ + XML/HTML hints.
    syms: list[str] = []

    for inc in re.findall(r"#include\s*[<\"]([^>\"]+)[>\"]", text):
        part = inc.strip().split("/")[-1]
        if part:
            syms.append(f"include:{part}")

    for fn in re.findall(
        r"\b([A-Za-z_][\w:]*)\s*\([^()]{0,80}\)\s*\{?",
        text,
    ):
        if fn not in {"if", "for", "while", "switch", "return"}:
            syms.append(f"fn:{fn}")

    for tag in re.findall(r"</?([A-Za-z_][\w:\-]*)\b", text):
        syms.append(f"tag:{tag.lower()}")

    for ident in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", text):
        if ident.lower() in {"const", "static", "class", "struct", "public", "private", "void"}:
            continue
        syms.append(ident[:48])

    # De-duplicate while preserving local order.
    ordered: list[str] = []
    seen: set[str] = set()
    for s in syms:
        if s in seen:
            continue
        seen.add(s)
        ordered.append(s)
        if len(ordered) >= 64:
            break
    return ordered


def _build_sparse_digest_xml(fragments: list[str], dim: int = 128, top_k: int = 32) -> str:
    text = "\n".join(fragments)
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_:\-]{1,40}", text.lower())
    if not tokens:
        return ""

    token_counts = Counter(tokens)
    vec: defaultdict[int, float] = defaultdict(float)
    for tok, cnt in token_counts.items():
        idx = (hash(tok) & 0x7FFFFFFF) % dim
        vec[idx] += float(cnt)

    nnz = sorted(vec.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    if not nnz:
        return ""
    payload = " ".join(f"{i}:{v:.1f}" for i, v in nnz)
    return f'<sparse_vector dim="{dim}" nnz="{len(nnz)}">{payload}</sparse_vector>'


def _build_attention_matrix_xml(
    fragments: list[str],
    rows: int = 8,
    cols: int = 8,
    sketch_dim: int = 64,
) -> str:
    # CountSketch + fixed signed projection:
    # - O(1) state size (rows*cols + sketch_dim), independent of prompt length.
    # - Single pass token update, stable output format for downstream prompts.
    if rows <= 0 or cols <= 0:
        return ""
    sketch_dim = max(16, int(sketch_dim))
    text = "\n".join(fragments)
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_:\-]{1,40}", text.lower())
    if not tokens:
        return ""

    sketch = [0.0 for _ in range(sketch_dim)]
    prev_h: int | None = None
    for tok in tokens:
        h = _stable_hash64(tok)
        idx = h % sketch_dim
        sign = 1.0 if ((h >> 7) & 1) == 0 else -1.0
        sketch[idx] += sign
        if prev_h is not None:
            b = _mix64(prev_h, h)
            b_idx = b % sketch_dim
            b_sign = 1.0 if ((b >> 5) & 1) == 0 else -1.0
            sketch[b_idx] += 0.5 * b_sign
        prev_h = h

    matrix = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            rc = r * cols + c
            acc = 0.0
            for j, v in enumerate(sketch):
                if v == 0.0:
                    continue
                acc += v * _proj_sign(j, rc)
            matrix[r][c] = acc

    # L2 normalize for stable magnitude independent of prompt length.
    norm = sum(v * v for row in matrix for v in row) ** 0.5
    if norm <= 1e-9:
        return ""
    for r in range(rows):
        for c in range(cols):
            matrix[r][c] = matrix[r][c] / norm

    packed_rows = [" ".join(f"{matrix[r][c]:.4f}" for c in range(cols)) for r in range(rows)]
    body = ";".join(packed_rows)
    return (
        f'<attention_matrix rows="{rows}" cols="{cols}" sketch_dim="{sketch_dim}" norm="l2">'
        f"{body}</attention_matrix>"
    )


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        n = int(value)
    except Exception:
        return default
    if n < low:
        return low
    if n > high:
        return high
    return n


def _stable_hash64(text: str) -> int:
    # FNV-1a 64-bit for deterministic cross-process hashing.
    h = 1469598103934665603
    for b in text.encode("utf-8", errors="ignore"):
        h ^= b
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def _mix64(a: int, b: int) -> int:
    x = (a ^ (b + 0x9E3779B97F4A7C15 + ((a << 6) & 0xFFFFFFFFFFFFFFFF) + (a >> 2))) & 0xFFFFFFFFFFFFFFFF
    x ^= (x >> 30)
    x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x ^= (x >> 27)
    x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    x ^= (x >> 31)
    return x & 0xFFFFFFFFFFFFFFFF


def _proj_sign(j: int, rc: int) -> float:
    # Fixed signed projection weight in {-1, +1}.
    x = ((j + 1) * 1103515245) ^ ((rc + 7) * 2654435761)
    x &= 0xFFFFFFFF
    return 1.0 if (x & 1) == 0 else -1.0


def _clip_fragment(text: str, max_len: int) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "..."


def _apply_structured_output(
    state: AgentState, message: Message, response_format: ResponseFormat | None
) -> bool:
    ok, data, error = parse_structured_from_message(response_format, message)
    if ok:
        state.structured_response = data
        if isinstance(response_format, ToolStrategy):
            tool_name = response_format.tool_name or schema_name(response_format.schema)
            content = response_format.tool_message_content or "Structured output parsed."
            tool_call_id = None
            for tc in message.tool_calls:
                if tc.name == tool_name and tc.id:
                    tool_call_id = tc.id
                    break
            meta = {"tool_call_id": tool_call_id} if tool_call_id else {}
            state.messages.append(Message(role="tool", content=content, name=tool_name, metadata=meta))
        return True
    if error and isinstance(response_format, ToolStrategy) and response_format.handle_errors:
        tool_name = response_format.tool_name or schema_name(response_format.schema)
        tool_call_id = None
        for tc in message.tool_calls:
            if tc.name == tool_name and tc.id:
                tool_call_id = tc.id
                break
        meta = {"tool_call_id": tool_call_id} if tool_call_id else {}
        state.messages.append(
            Message(role="tool", content=f"Error: {error}", name=tool_name, metadata=meta)
        )
    return False


def _validate_tool_calls(
    tool_calls, available_names: set[str], middleware, structured_tool_name: str | None
) -> None:
    has_wrap_tool = any(hasattr(m, "wrap_tool_call") for m in middleware)
    if has_wrap_tool:
        return
    for call in tool_calls:
        if structured_tool_name and call.name == structured_tool_name:
            continue
        if call.name not in available_names:
            raise ValueError(f"Unknown tool: {call.name}")


def _invoke_model_with_middleware(middleware, model, messages, tools, **kwargs):
    def base(req_messages, req_tools, req_kwargs):
        return model.invoke(req_messages, tools=req_tools, **req_kwargs)

    handler: Callable[[list[Message], list[BaseTool], dict[str, Any]], Message] = base
    for m in reversed(middleware):
        if hasattr(m, "wrap_model_call"):
            wrap = m.wrap_model_call

            def _make(wrap_fn, inner):
                return lambda msgs, tls, kw: wrap_fn(msgs, tls, kw, inner)

            handler = _make(wrap, handler)
    req_kwargs = _merge_configurable(kwargs)
    return handler(messages, tools, req_kwargs)


async def _ainvoke_model_with_middleware(middleware, model, messages, tools, **kwargs):
    async def base(req_messages, req_tools, req_kwargs):
        return await model.ainvoke(req_messages, tools=req_tools, **req_kwargs)

    handler = base
    for m in reversed(middleware):
        if hasattr(m, "awrap_model_call"):
            wrap = m.awrap_model_call

            async def _make(wrap_fn, inner):
                async def _call(msgs, tls, kw):
                    return await wrap_fn(msgs, tls, kw, inner)

                return _call

            handler = await _make(wrap, handler)
    req_kwargs = _merge_configurable(kwargs)
    return await handler(messages, tools, req_kwargs)


def _execute_tools_with_middleware(
    middleware, tool_node, tool_calls, callbacks=None, run_id: str = "", span_id: str = ""
):
    def base(calls):
        if callbacks:
            for call in calls:
                callbacks.on_tool_start(call.name, {"args": call.args}, run_id, span_id)
        return tool_node.execute(calls)

    handler = base
    for m in reversed(middleware):
        if hasattr(m, "wrap_tool_call"):
            wrap = m.wrap_tool_call

            def _make(wrap_fn, inner):
                return lambda calls: wrap_fn(calls, inner)

            handler = _make(wrap, handler)
    result = handler(tool_calls)
    if callbacks:
        for msg in result:
            if msg.role == "tool":
                callbacks.on_tool_end(msg.name or "tool", {"content": msg.content}, run_id, span_id)
    return result


def _get_callbacks(state: AgentState):
    if state.callbacks is not None:
        return state.callbacks
    if state.events:
        state.callbacks = create_event_manager(state.events)
        return state.callbacks
    return None


def _init_run_context(state: AgentState) -> None:
    if state.run_id is None:
        state.run_id = uuid.uuid4().hex
    state.span_id = uuid.uuid4().hex


def _merge_configurable(kwargs: dict[str, Any]) -> dict[str, Any]:
    configurable = kwargs.pop("configurable", None) or {}
    if not isinstance(configurable, dict):
        return kwargs
    merged = {**configurable, **kwargs}
    return merged


def _build_runtime(state, context, middleware, model, tools, response_format, callbacks):
    max_workers = None
    if state.configurable and isinstance(state.configurable, dict):
        max_workers = state.configurable.get("tool_max_workers")
    tool_node = ToolNode(tools, max_workers=max_workers)
    available_tool_names = {t.name for t in tools}

    def before_agent_node(s, ctx):
        for m in middleware:
            if hasattr(m, "before_agent"):
                update = m.before_agent(s, ctx)
                if update:
                    s.__dict__.update(update)
        if callbacks:
            callbacks.on_run_start(model.__class__.__name__, {"messages": s.messages}, s.run_id or "")
        return s

    def before_model_node(s, ctx):
        for m in middleware:
            if hasattr(m, "before_model"):
                update = m.before_model(s, ctx)
                if update:
                    s.__dict__.update(update)
        return s

    def model_node(s, ctx):
        effective_format = _resolve_response_format(response_format, model)
        tool_choice = "auto" if isinstance(effective_format, ToolStrategy) else None
        model_tools = list(tools)
        structured_tool_name = None
        if isinstance(effective_format, ToolStrategy):
            structured_tool = _structured_tool_from_schema(effective_format)
            structured_tool_name = structured_tool.name
            model_tools.append(structured_tool)
        s._structured_tool_name = structured_tool_name  # type: ignore[attr-defined]
        s._effective_format = effective_format  # type: ignore[attr-defined]
        before_count = len(s.messages)
        if callbacks:
            callbacks.on_model_start(
                model.__class__.__name__,
                {"messages": s.messages},
                s.run_id or "",
                s.span_id or "",
            )
        base_messages = _trim_messages(s.messages, state.configurable)
        model_messages = list(base_messages)
        if s.completion_structured:
            model_messages.insert(
                0,
                Message(
                    role="system",
                    content=f"Completion map:\n{s.completion_structured}",
                ),
            )
            if s.completion_structured.get("gap_score", 0.0) > 0.5:
                model_messages.insert(
                    0,
                    Message(
                        role="system",
                        content="High gap score detected. Prefer cautious reasoning and ask clarifying questions.",
                    ),
                )
            tasks = s.completion_structured.get("tasks") if isinstance(s.completion_structured, dict) else None
            if tasks:
                model_messages.insert(
                    0,
                    Message(
                        role="system",
                        content="Follow these completion tasks:\n" + "\n".join(f"- {t}" for t in tasks),
                    ),
                )
            auto_actions = (
                s.completion_structured.get("auto_actions")
                if isinstance(s.completion_structured, dict)
                else None
            )
            if auto_actions:
                model_messages.insert(
                    0,
                    Message(
                        role="system",
                        content="Auto actions suggested:\n" + "\n".join(f"- {a}" for a in auto_actions),
                    ),
                )
            if s.completion_structured.get("gap_score", 0.0) > 0.7:
                model_messages.insert(
                    0,
                    Message(
                        role="system",
                        content="Gap score is high. Request external view or run retrieval before final answer.",
                    ),
                )
        message = _invoke_model_with_middleware(
            middleware,
            model,
            model_messages,
            model_tools,
            response_format=_provider_kwargs(effective_format),
            tool_choice=tool_choice,
            stream_callback=s.rc_stream_callback,
            configurable=s.configurable,
        )
        if callbacks:
            callbacks.on_model_end(
                model.__class__.__name__,
                {"message": message},
                s.run_id or "",
                s.span_id or "",
            )
        s.messages.append(message)
        s._last_model_before = before_count  # type: ignore[attr-defined]
        return s

    def after_model_node(s, ctx):
        for m in middleware:
            if hasattr(m, "after_model"):
                update = m.after_model(s, ctx)
                if update:
                    s.__dict__.update(update)
        return s

    def tools_node(s, ctx):
        msg = _last_ai_message(s)
        if msg is None:
            return s
        structured_tool_name = getattr(s, "_structured_tool_name", None)
        effective_format = getattr(s, "_effective_format", None)
        _validate_tool_calls(msg.tool_calls, available_tool_names, middleware, structured_tool_name)
        if _handle_structured_tool_calls(s, msg, effective_format):
            return s
        tool_messages = _execute_tools_with_middleware(
            middleware,
            tool_node,
            msg.tool_calls,
            callbacks=callbacks,
            run_id=s.run_id or "",
            span_id=s.span_id or "",
        )
        s.messages.extend(tool_messages)
        before_count = getattr(s, "_last_model_before", len(s.messages))
        _record_change_log(s, s.messages[before_count:])
        return s

    def after_agent_node(s, ctx):
        for m in middleware:
            if hasattr(m, "after_agent"):
                update = m.after_agent(s, ctx)
                if update:
                    s.__dict__.update(update)
        if callbacks:
            callbacks.on_run_end(
                model.__class__.__name__,
                {"messages": s.messages},
                s.run_id or "",
            )
        return s

    def entry_name():
        if any(hasattr(m, "before_agent") for m in middleware):
            return "before_agent"
        if any(hasattr(m, "before_model") for m in middleware):
            return "before_model"
        return "model"

    loop_entry = "before_model" if any(hasattr(m, "before_model") for m in middleware) else "model"
    loop_exit = "after_model" if any(hasattr(m, "after_model") for m in middleware) else "model"
    exit_node = "after_agent" if any(hasattr(m, "after_agent") for m in middleware) else "end"

    def route_from_model(s):
        if s.jump_to == "end":
            return exit_node
        if s.jump_to == "tools":
            return "tools"
        if s.jump_to == "model":
            return loop_entry
        msg = _last_ai_message(s)
        if msg is None:
            return exit_node
        effective_format = getattr(s, "_effective_format", None)
        if _apply_structured_output(s, msg, effective_format):
            return exit_node
        if not msg.tool_calls:
            return exit_node
        return "tools"

    def route_after_model(s):
        return route_from_model(s)

    def route_tools(s):
        msg = _last_ai_message(s)
        if msg is None:
            return loop_entry
        if _should_end_after_tools(msg, tool_node):
            return exit_node
        if s.structured_response is not None:
            return exit_node
        return loop_entry

    nodes = {
        "before_agent": before_agent_node,
        "before_model": before_model_node,
        "model": model_node,
        "after_model": after_model_node,
        "tools": tools_node,
        "after_agent": after_agent_node,
        "end": lambda s, ctx: s,
    }
    edges = {
        "before_agent": lambda s: loop_entry,
        "before_model": lambda s: "model",
        "model": route_from_model,
        "after_model": route_after_model,
        "tools": route_tools,
        "after_agent": lambda s: "end",
        "end": lambda s: None,
    }
    return GraphRuntime(graph=None, nodes=nodes, edges=edges, entry=entry_name(), end="end")


def _last_ai_message(state: AgentState) -> Message | None:
    for msg in reversed(state.messages):
        if msg.role == "assistant":
            return msg
    return None


def _structured_tool_from_schema(strategy: ToolStrategy) -> StructuredOutputTool:
    return structured_tool_from_strategy(strategy)


def _handle_structured_tool_calls(
    state: AgentState, message: Message, response_format: ResponseFormat | None
) -> bool:
    if not isinstance(response_format, ToolStrategy):
        return False
    tool_name = response_format.tool_name or schema_name(response_format.schema)
    for tc in message.tool_calls:
        if tc.name == tool_name:
            if _apply_structured_output(state, message, response_format):
                return True
            return True
    return False


def _should_end_after_tools(message: Message, tool_node: ToolNode) -> bool:
    if not message.tool_calls:
        return False
    client_calls = [c for c in message.tool_calls if c.name in tool_node.tools_by_name]
    if client_calls and all(tool_node.tools_by_name[c.name].return_direct for c in client_calls):
        return True
    return False
