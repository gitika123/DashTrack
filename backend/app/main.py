"""
DashTrack API — real-time three-sided food delivery event tracker.

Inspired by marketplace concepts (customers, restaurants, dashers) with:
- REST APIs for orders and menus
- WebSocket live location + status
- In-memory event bus (Kafka-style topics for local demos)
- TTL menu cache (Redis-style hit/miss stats)
- Geospatial ranking / ETA via haversine
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import OrderCreate, OrderStatus
from .simulator import start_delivery
from .store import store

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title="DashTrack",
    description="Real-time geospatial food delivery tracker for a three-sided marketplace demo",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "dashtrack"}


@app.get("/api/restaurants")
async def restaurants(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: float = Query(5.0, ge=0.5, le=30.0),
):
    return store.list_restaurants(lat, lon, radius_km)


@app.get("/api/restaurants/{restaurant_id}/menu")
async def menu(restaurant_id: str):
    items = store.get_menu(restaurant_id)
    if items is None:
        raise HTTPException(404, "Restaurant not found")
    return {"restaurant_id": restaurant_id, "items": items, "cache": store.cache_stats()}


@app.get("/api/dashers")
async def dashers():
    return list(store.dashers.values())


@app.get("/api/customers")
async def customers():
    return list(store.customers.values())


@app.post("/api/orders")
async def create_order(body: OrderCreate):
    if body.customer_id not in store.customers:
        raise HTTPException(404, "Customer not found")
    if body.restaurant_id not in store.restaurants:
        raise HTTPException(404, "Restaurant not found")
    try:
        order = store.create_order(body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await store.bus.publish(
        "delivery.events",
        {"order_id": order.id, "type": "placed", "status": order.status},
    )
    start_delivery(order.id)
    return order


@app.get("/api/orders")
async def list_orders():
    return sorted(store.orders.values(), key=lambda o: o.created_at, reverse=True)


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    order = store.orders.get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@app.get("/api/cache/stats")
async def cache_stats():
    return store.cache_stats()


@app.get("/api/events/recent")
async def recent_events(limit: int = Query(40, ge=1, le=200)):
    events = store.bus.recent("delivery.events", limit=limit)
    return [{"topic": e.topic, "ts": e.ts, "payload": e.payload} for e in events]


@app.websocket("/ws/orders/{order_id}")
async def order_ws(websocket: WebSocket, order_id: str):
    await websocket.accept()
    order = store.orders.get(order_id)
    if order:
        await websocket.send_json({"type": "snapshot", "order": json.loads(order.model_dump_json())})
    queue = await store.bus.subscribe("delivery.events")
    try:
        while True:
            event = await queue.get()
            if event.payload.get("order_id") != order_id:
                continue
            live = store.orders.get(order_id)
            await websocket.send_json(
                {
                    "type": event.payload.get("type", "event"),
                    "payload": event.payload,
                    "order": json.loads(live.model_dump_json()) if live else None,
                }
            )
            if live and live.status == OrderStatus.DELIVERED:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await store.bus.unsubscribe("delivery.events", queue)


@app.websocket("/ws/market")
async def market_ws(websocket: WebSocket):
    """Broadcast all marketplace delivery events (ops-style live board)."""
    await websocket.accept()
    queue = await store.bus.subscribe("delivery.events")
    try:
        while True:
            event = await queue.get()
            await websocket.send_json({"type": "market_event", "payload": event.payload, "ts": event.ts})
    except WebSocketDisconnect:
        pass
    finally:
        await store.bus.unsubscribe("delivery.events", queue)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def index():
        return FileResponse(FRONTEND_DIR / "index.html")
