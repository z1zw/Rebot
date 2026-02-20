"""Runnable execution primitives."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
import json

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class RunnableConfig:
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    max_concurrency: int | None = None
    callbacks: Any | None = None
    configurable: dict[str, Any] | None = None
    configurable_schema: dict[str, Any] | None = None
    run_id: str | None = None


@dataclass
class RunnableContext:
    config: RunnableConfig

    def on_start(self, name: str, payload: dict[str, Any]) -> None:
        cb = self.config.callbacks
        if cb and hasattr(cb, "on_start"):
            cb.on_start(
                name,
                {
                    **payload,
                    "tags": self.config.tags,
                    "metadata": self.config.metadata,
                    "run_id": self.config.run_id,
                },
            )
        if cb and isinstance(cb, RunnableTrace):
            cb.events.append({"type": "start", "name": name, "payload": payload})

    def on_end(self, name: str, payload: dict[str, Any]) -> None:
        cb = self.config.callbacks
        if cb and hasattr(cb, "on_end"):
            cb.on_end(
                name,
                {
                    **payload,
                    "tags": self.config.tags,
                    "metadata": self.config.metadata,
                    "run_id": self.config.run_id,
                },
            )
        if cb and isinstance(cb, RunnableTrace):
            cb.events.append({"type": "end", "name": name, "payload": payload})

    def on_error(self, name: str, payload: dict[str, Any]) -> None:
        cb = self.config.callbacks
        if cb and hasattr(cb, "on_error"):
            cb.on_error(
                name,
                {
                    **payload,
                    "tags": self.config.tags,
                    "metadata": self.config.metadata,
                    "run_id": self.config.run_id,
                },
            )
        if cb and isinstance(cb, RunnableTrace):
            cb.events.append({"type": "error", "name": name, "payload": payload})


@dataclass
class SimpleRunnableCallbacks:
    events: list[dict[str, Any]] = field(default_factory=list)

    def on_start(self, name: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": "start", "name": name, "payload": payload})

    def on_end(self, name: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": "end", "name": name, "payload": payload})

    def on_error(self, name: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": "error", "name": name, "payload": payload})


@dataclass
class RunnableTrace:
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.events, indent=2)


class Runnable(Generic[InputT, OutputT]):
    def __or__(self, other: "Runnable") -> "Runnable":
        return RunnableSequence([self, coerce_runnable(other)])

    def with_configurable(self, **kwargs: Any) -> "Runnable":
        return RunnableConfigurable(self, overrides=kwargs)

    def with_configurable_schema(self, schema: dict[str, Any]) -> "Runnable":
        return RunnableConfigurable(self, overrides={}, schema_overrides=schema)

    def invoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        raise NotImplementedError

    async def ainvoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.invoke, input, config)

    def batch(
        self,
        inputs: Sequence[InputT],
        config: RunnableConfig | None = None,
        *,
        return_exceptions: bool = False,
    ) -> list[OutputT | Exception]:
        if not inputs:
            return []
        max_concurrency = config.max_concurrency if config else None
        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            futures = [executor.submit(self.invoke, i, config) for i in inputs]
        results: list[OutputT | Exception] = []
        for f in futures:
            if return_exceptions:
                try:
                    results.append(f.result())
                except Exception as exc:  # noqa: BLE001
                    results.append(exc)
            else:
                results.append(f.result())
        return results

    def stream(
        self, input: InputT, config: RunnableConfig | None = None
    ) -> Iterator[OutputT]:
        yield self.invoke(input, config)

    async def astream(
        self, input: InputT, config: RunnableConfig | None = None
    ) -> AsyncIterator[OutputT]:
        yield await self.ainvoke(input, config)

    def transform(
        self, input: Iterator[InputT], config: RunnableConfig | None = None
    ) -> Iterator[OutputT]:
        final: InputT | None = None
        for chunk in input:
            final = chunk if final is None else chunk
        if final is not None:
            yield from self.stream(final, config)

    async def atransform(
        self, input: AsyncIterator[InputT], config: RunnableConfig | None = None
    ) -> AsyncIterator[OutputT]:
        final: InputT | None = None
        async for chunk in input:
            final = chunk if final is None else chunk
        if final is not None:
            async for out in self.astream(final, config):
                yield out


def _merge_config(base: RunnableConfig | None, overrides: dict[str, Any]) -> RunnableConfig:
    if base is None:
        return RunnableConfig(configurable=overrides)
    merged = dict(base.configurable or {})
    merged.update(overrides)
    return RunnableConfig(
        tags=base.tags,
        metadata=base.metadata,
        max_concurrency=base.max_concurrency,
        callbacks=base.callbacks,
        configurable=merged,
        configurable_schema=base.configurable_schema,
        run_id=base.run_id,
    )


def _merge_schema(base: dict[str, Any] | None, extra: dict[str, Any]) -> dict[str, Any]:
    if base is None:
        return extra
    merged = dict(base)
    merged.update(extra)
    return merged


def coerce_runnable(obj: Any) -> "Runnable":
    if isinstance(obj, Runnable):
        return obj
    if callable(obj):
        return RunnableLambda(obj)
    raise TypeError(f"Cannot coerce to Runnable: {type(obj)}")


@dataclass
class RunnableLambda(Runnable[InputT, OutputT]):
    func: Any

    def invoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        ctx = RunnableContext(config or RunnableConfig())
        ctx.on_start(self.__class__.__name__, {"input": input})
        try:
            result = self.func(input)
            ctx.on_end(self.__class__.__name__, {"output": result})
            return result
        except Exception as exc:  # noqa: BLE001
            ctx.on_error(self.__class__.__name__, {"error": str(exc)})
            raise


@dataclass
class RunnablePassthrough(Runnable[InputT, InputT]):
    def invoke(self, input: InputT, config: RunnableConfig | None = None) -> InputT:
        return input


@dataclass
class RunnableSequence(Runnable[InputT, OutputT]):
    steps: list[Runnable]

    def invoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        ctx = RunnableContext(config or RunnableConfig())
        ctx.on_start(self.__class__.__name__, {"steps": len(self.steps)})
        value: Any = input
        try:
            for step in self.steps:
                value = step.invoke(value, config)
            ctx.on_end(self.__class__.__name__, {"output": value})
            return value
        except Exception as exc:  # noqa: BLE001
            ctx.on_error(self.__class__.__name__, {"error": str(exc)})
            raise

    async def ainvoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        value: Any = input
        for step in self.steps:
            value = await step.ainvoke(value, config)
        return value


@dataclass
class RunnableParallel(Runnable[InputT, dict[str, Any]]):
    branches: dict[str, Runnable]

    def invoke(self, input: InputT, config: RunnableConfig | None = None) -> dict[str, Any]:
        ctx = RunnableContext(config or RunnableConfig())
        ctx.on_start(self.__class__.__name__, {"branches": list(self.branches.keys())})
        max_concurrency = config.max_concurrency if config else None
        try:
            with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
                futures = {k: executor.submit(v.invoke, input, config) for k, v in self.branches.items()}
            result = {k: f.result() for k, f in futures.items()}
            ctx.on_end(self.__class__.__name__, {"output": result})
            return result
        except Exception as exc:  # noqa: BLE001
            ctx.on_error(self.__class__.__name__, {"error": str(exc)})
            raise

    async def ainvoke(self, input: InputT, config: RunnableConfig | None = None) -> dict[str, Any]:
        tasks = {k: v.ainvoke(input, config) for k, v in self.branches.items()}
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))


@dataclass
class RunnableConfigurable(Runnable[InputT, OutputT]):
    runnable: Runnable
    overrides: dict[str, Any]
    schema_overrides: dict[str, Any] | None = None

    def invoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        merged = _merge_config(config, self.overrides)
        if self.schema_overrides:
            merged.configurable_schema = _merge_schema(
                merged.configurable_schema, self.schema_overrides
            )
        return self.runnable.invoke(input, merged)

    async def ainvoke(self, input: InputT, config: RunnableConfig | None = None) -> OutputT:
        merged = _merge_config(config, self.overrides)
        if self.schema_overrides:
            merged.configurable_schema = _merge_schema(
                merged.configurable_schema, self.schema_overrides
            )
        return await self.runnable.ainvoke(input, merged)
