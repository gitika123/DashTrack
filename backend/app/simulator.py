"""Simulates restaurant prep + dasher movement along the delivery path."""
from __future__ import annotations

import asyncio
from typing import Optional

from .geo import eta_minutes, haversine_km, interpolate
from .models import OrderStatus
from .store import store


async def _publish(order_id: str, event_type: str, payload: dict) -> None:
    await store.bus.publish(
        "delivery.events",
        {"order_id": order_id, "type": event_type, **payload},
    )


async def run_delivery(order_id: str) -> None:
    order = store.orders.get(order_id)
    if not order:
        return

    # Restaurant accepts + prepares
    order.status = OrderStatus.ACCEPTED
    store.append_event(order, "Restaurant accepted order")
    await _publish(order_id, "status", {"status": order.status})
    await asyncio.sleep(1.2)

    order.status = OrderStatus.PREPARING
    prep = max(i.prep_minutes for i in order.items)
    store.append_event(order, f"Kitchen preparing (~{prep} min compressed)")
    await _publish(order_id, "status", {"status": order.status})
    await asyncio.sleep(1.5)

    order.status = OrderStatus.READY
    store.append_event(order, "Order ready for pickup")
    await _publish(order_id, "status", {"status": order.status})

    dasher = store.assign_nearest_dasher(order)
    if not dasher:
        store.append_event(order, "No available dashers nearby")
        await _publish(order_id, "status", {"status": order.status, "error": "no_dasher"})
        return

    await _publish(
        order_id,
        "assigned",
        {
            "status": order.status,
            "dasher_id": dasher.id,
            "dasher_name": dasher.name,
            "eta_minutes": order.eta_minutes,
            "lat": dasher.location.lat,
            "lon": dasher.location.lon,
        },
    )

    # Drive to restaurant
    start = (dasher.location.lat, dasher.location.lon)
    pickup = (order.pickup.lat, order.pickup.lon)
    for step in range(1, 9):
        lat, lon = interpolate(start[0], start[1], pickup[0], pickup[1], step / 8)
        dasher.location.lat = lat
        dasher.location.lon = lon
        rem = haversine_km(lat, lon, pickup[0], pickup[1])
        await _publish(
            order_id,
            "location",
            {
                "phase": "to_restaurant",
                "lat": lat,
                "lon": lon,
                "remaining_km": round(rem, 3),
                "eta_minutes": eta_minutes(rem),
            },
        )
        await asyncio.sleep(0.45)

    order.status = OrderStatus.PICKED_UP
    store.append_event(order, "Dasher picked up order")
    await _publish(order_id, "status", {"status": order.status, "lat": pickup[0], "lon": pickup[1]})

    # Drive to customer
    drop = (order.dropoff.lat, order.dropoff.lon)
    order.status = OrderStatus.EN_ROUTE
    store.append_event(order, "En route to customer")
    await _publish(order_id, "status", {"status": order.status})

    for step in range(1, 11):
        lat, lon = interpolate(pickup[0], pickup[1], drop[0], drop[1], step / 10)
        dasher.location.lat = lat
        dasher.location.lon = lon
        rem = haversine_km(lat, lon, drop[0], drop[1])
        await _publish(
            order_id,
            "location",
            {
                "phase": "to_customer",
                "lat": lat,
                "lon": lon,
                "remaining_km": round(rem, 3),
                "eta_minutes": eta_minutes(rem),
            },
        )
        await asyncio.sleep(0.45)

    order.status = OrderStatus.DELIVERED
    order.eta_minutes = 0
    store.append_event(order, "Delivered")
    dasher.active_order_id = None
    await _publish(
        order_id,
        "delivered",
        {"status": order.status, "lat": drop[0], "lon": drop[1]},
    )


_tasks = {}


def start_delivery(order_id: str) -> Optional[asyncio.Task]:
    if order_id in _tasks and not _tasks[order_id].done():
        return _tasks[order_id]
    task = asyncio.create_task(run_delivery(order_id))
    _tasks[order_id] = task
    return task
