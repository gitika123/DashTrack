"""Domain models and seed data for the three-sided marketplace."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    EN_ROUTE = "en_route"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Role(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT = "restaurant"
    DASHER = "dasher"


class Location(BaseModel):
    lat: float
    lon: float


class MenuItem(BaseModel):
    id: str
    name: str
    price: float
    prep_minutes: int = 12


class Restaurant(BaseModel):
    id: str
    name: str
    cuisine: str
    location: Location
    menu: List[MenuItem]


class Dasher(BaseModel):
    id: str
    name: str
    location: Location
    online: bool = True
    active_order_id: Optional[str] = None


class Customer(BaseModel):
    id: str
    name: str
    location: Location


class OrderCreate(BaseModel):
    customer_id: str
    restaurant_id: str
    item_ids: List[str] = Field(min_length=1)
    dropoff: Optional[Location] = None


class Order(BaseModel):
    id: str
    customer_id: str
    restaurant_id: str
    dasher_id: Optional[str] = None
    items: List[MenuItem]
    status: OrderStatus = OrderStatus.PLACED
    pickup: Location
    dropoff: Location
    total: float
    eta_minutes: Optional[int] = None
    created_at: float
    events: List[str] = Field(default_factory=list)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


# Seed: San Jose downtown-ish coordinates
SEED_RESTAURANTS: Dict[str, Restaurant] = {
    "rest_spice": Restaurant(
        id="rest_spice",
        name="Spice Route Kitchen",
        cuisine="Indian",
        location=Location(lat=37.3382, lon=-121.8863),
        menu=[
            MenuItem(id="m1", name="Butter Chicken Bowl", price=14.5, prep_minutes=15),
            MenuItem(id="m2", name="Paneer Wrap", price=11.0, prep_minutes=10),
            MenuItem(id="m3", name="Mango Lassi", price=4.5, prep_minutes=3),
        ],
    ),
    "rest_norte": Restaurant(
        id="rest_norte",
        name="Norte Taqueria",
        cuisine="Mexican",
        location=Location(lat=37.3350, lon=-121.8810),
        menu=[
            MenuItem(id="m4", name="Al Pastor Burrito", price=12.0, prep_minutes=12),
            MenuItem(id="m5", name="Street Tacos (3)", price=9.5, prep_minutes=8),
            MenuItem(id="m6", name="Horchata", price=3.5, prep_minutes=2),
        ],
    ),
    "rest_bay": Restaurant(
        id="rest_bay",
        name="Bay Bites Burger",
        cuisine="American",
        location=Location(lat=37.3420, lon=-121.8920),
        menu=[
            MenuItem(id="m7", name="Classic Cheeseburger", price=13.0, prep_minutes=14),
            MenuItem(id="m8", name="Sweet Potato Fries", price=5.5, prep_minutes=8),
            MenuItem(id="m9", name="Shake", price=6.0, prep_minutes=5),
        ],
    ),
}

SEED_DASHERS: Dict[str, Dasher] = {
    "dash_maya": Dasher(
        id="dash_maya",
        name="Maya Chen",
        location=Location(lat=37.3365, lon=-121.8840),
    ),
    "dash_leo": Dasher(
        id="dash_leo",
        name="Leo Okonkwo",
        location=Location(lat=37.3400, lon=-121.8900),
    ),
    "dash_sam": Dasher(
        id="dash_sam",
        name="Sam Rivera",
        location=Location(lat=37.3330, lon=-121.8780),
    ),
}

SEED_CUSTOMERS: Dict[str, Customer] = {
    "cust_gitika": Customer(
        id="cust_gitika",
        name="Gitika",
        location=Location(lat=37.3370, lon=-121.8905),
    ),
}
