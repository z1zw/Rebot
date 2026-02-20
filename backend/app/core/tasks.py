from __future__ import annotations

from typing import Any

from app.core.settings import settings


class TaskQueue:
    async def enqueue(self, run_id: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


class InMemoryQueue(TaskQueue):
    async def enqueue(self, run_id: str, payload: dict[str, Any]) -> None:
        return None


class RabbitQueue(TaskQueue):
    def __init__(self, url: str) -> None:
        self._url = url

    async def enqueue(self, run_id: str, payload: dict[str, Any]) -> None:
        import aio_pika
        import json

        connection = await aio_pika.connect_robust(self._url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(
                "rebot.tasks",
                durable=True,
                arguments={"x-max-priority": 10},
            )
            body = json.dumps({"run_id": run_id, "payload": payload}).encode("utf-8")
            priority = payload.get("priority", 5)
            try:
                priority = max(0, min(int(priority), 10))
            except Exception:
                priority = 5
            await channel.default_exchange.publish(
                aio_pika.Message(body=body, priority=priority), routing_key=queue.name
            )


def get_task_queue() -> TaskQueue | None:
    if settings.force_local_tasks:
        return None
    if settings.rabbitmq_url:
        return RabbitQueue(settings.rabbitmq_url)
    return None
