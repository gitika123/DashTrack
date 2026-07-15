"""Mutable in-memory store for the demo marketplace."""
from __future__ import annotations

import copy
import time
from typing import Dict, List, Optional

from .events import EventBus, TTLCache
from .geo import eta_minutes, haversine_km, nearby
from .models import (
    SEED_CUSTOMERS,
    SEED_DASHERS,
    SEED_RESTAURANTS,
    Customer,
    Dasher,
    MenuItem,
    Order,
    OrderCreate,
    OrderStatus,
    Restaurant,
    new_id,
)


class Store:
    def __init__(self) -> None:
        self.restaurants: Dict[str, Restaurant] = copy.deepcopy(SEED_RESTAURANTS)
        self.dashers: Dict[str, Dasher] = copy.deepcopy(SEED_DASHERS)
        self.customers: Dict[str, Customer] = copy.deepcopy(SEED_CUSTOMERS)
        self.orders: Dict[str, Order] = {}
        self.bus = EventBus()
        self.menu_cache = TTLCache()
        self.cache_hits = 0
        self.cache_misses = 0

    def list_restaurants(self, lat: Optional[float] = None, lon: Optional[float] = None, radius_km: float = 5.0):
        if lat is None or lon is None:
            return list(self.restaurants.values())
        points = [(r.id, r.location.lat, r.location.lon) for r in self.restaurants.values()]
        ranked = nearby(lat, lon, points, radius_km)
        return [self.restaurants[rid] for rid, _ in ranked]

    def get_menu(self, restaurant_id: str) -> Optional[List[MenuItem]]:
        cache_key = f"menu:{restaurant_id}"
        cached = self.menu_cache.get(cache_key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        self.cache_misses += 1
        restaurant = self.restaurants.get(restaurant_id)
        if not restaurant:
            return None
        # Simulate a slightly expensive DB/menu read path
        self.menu_cache.set(cache_key, restaurant.menu, ttl_seconds=20.0)
        return restaurant.menu

    def create_order(self, body: OrderCreate) -> Order:
        restaurant = self.restaurants[body.restaurant_id]
        customer = self.customers[body.customer_id]
        menu_by_id = {m.id: m for m in restaurant.menu}
        items = [menu_by_id[i] for i in body.item_ids if i in menu_by_id]
        if not items:
            raise ValueError("No valid menu items selected")
        dropoff = body.dropoff or customer.location
        order = Order(
            id=new_id("ord"),
            customer_id=customer.id,
            restaurant_id=restaurant.id,
            items=items,
            pickup=restaurant.location,
            dropoff=dropoff,
            total=round(sum(i.price for i in items), 2),
            created_at=time.time(),
            events=["Order placed"],
        )
        self.orders[order.id] = order
        return order

    def append_event(self, order: Order, message: str) -> None:
        order.events.append(message)

    def assign_nearest_dasher(self, order: Order) -> Optional[Dasher]:
        free = [
            (d.id, d.location.lat, d.location.lon)
            for d in self.dashers.values()
            if d.online and not d.active_order_id
        ]
        if not free:
            return None
        ranked = nearby(order.pickup.lat, order.pickup.lon, free, radius_km=15.0)
        if not ranked:
            return None
        dasher = self.dashers[ranked[0][0]]
        dasher.active_order_id = order.id
        order.dasher_id = dasher.id
        order.status = OrderStatus.ASSIGNED
        dist = haversine_km(
            dasher.location.lat, dasher.location.lon, order.pickup.lat, order.pickup.lon
        )
        order.eta_minutes = eta_minutes(dist) + max(i.prep_minutes for i in order.items)
        self.append_event(order, f"Assigned dasher {dasher.name}")
        return dasher

    def cache_stats(self) -> dict:
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total) if total else 0.0
        return {
            **self.menu_cache.stats(),
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": round(hit_rate, 3),
        }


store = Store()
