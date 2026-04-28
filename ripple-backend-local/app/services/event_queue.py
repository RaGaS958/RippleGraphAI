"""
In-memory async event queue — replaces Google Cloud Pub/Sub.
Uses asyncio.Queue under the hood. Handlers registered at startup.

Usage:
  # Publish
  await EventQueue.publish({"id": "...", "supplier_id": "...", ...})

  # Subscribe (register once at startup)
  EventQueue.register_handler(my_async_handler)
"""
from __future__ import annotations
import asyncio, logging
from typing import Awaitable, Callable, List

logger = logging.getLogger(__name__)

Handler = Callable[[dict], Awaitable[None]]


class EventQueue:
    _queue: asyncio.Queue = asyncio.Queue()
    _handlers: List[Handler] = []
    _worker_task: asyncio.Task = None

    @classmethod
    def register_handler(cls, handler: Handler) -> None:
        cls._handlers.append(handler)
        logger.info(f"Registered event handler: {handler.__name__}")

    @classmethod
    async def publish(cls, event: dict) -> None:
        await cls._queue.put(event)
        logger.info("Event queued", extra={"event_id": event.get("id")})

    @classmethod
    async def start_worker(cls) -> None:
        cls._worker_task = asyncio.create_task(cls._run())
        logger.info("Event queue worker started")

    @classmethod
    async def stop_worker(cls) -> None:
        if cls._worker_task:
            cls._worker_task.cancel()
            try:
                await cls._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Event queue worker stopped")

    @classmethod
    async def _run(cls) -> None:
        while True:
            event = await cls._queue.get()
            for handler in cls._handlers:
                try:
                    await handler(event)
                except Exception:
                    logger.error(f"Handler {handler.__name__} failed", exc_info=True)
            cls._queue.task_done()
