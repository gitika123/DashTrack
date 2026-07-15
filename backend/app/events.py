"""In-memory event bus (Kafka-style topics) + TTL menu cache."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


@dataclass
class Event:
    topic: str
    payload: Dict[str, Any]
    ts: float = field(default_factory=time.time)


class EventBus:
    """Lightweight stand-in for a Kafka topic used in local demos."""

    def __init__(self, maxlen: int = 500) -> None:
        self._topics: Dict[str, Deque[Event]] = defaultdict(lambda: deque(maxlen=maxlen))
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: Dict[str, Any]) -> Event:
        event = Event(topic=topic, payload=payload)
        async with self._lock:
            self._topics[topic].append(event)
            for queue in list(self._subscribers[topic]):
                await queue.put(event)
        return event

    async def subscribe(self, topic: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers[topic].append(queue)
        return queue

    async def unsubscribe(self, topic: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subs = self._subscribers.get(topic, [])
            if queue in subs:
                subs.remove(queue)

    def recent(self, topic: str, limit: int = 50) -> List[Event]:
        return list(self._topics.get(topic, []))[-limit:]


class TTLCache:
    """Simple Redis-like in-memory cache with TTL eviction."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple] = {}

    def set(self, key: str, value: Any, ttl_seconds: float = 30.0) -> None:
        self._store[key] = (value, time.time() + ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        value, expires = item
        if time.time() > expires:
            self._store.pop(key, None)
            return None
        return value

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def stats(self) -> Dict[str, int]:
        now = time.time()
        alive = sum(1 for _, exp in self._store.values() if exp > now)
        return {"keys": alive, "tracked": len(self._store)}
