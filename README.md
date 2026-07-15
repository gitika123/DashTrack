# DashTrack

DashTrack is a real-time food delivery platform that coordinates customers, restaurants, and delivery partners with live geospatial order tracking.

## Features

- REST APIs for restaurants, menus, and orders (FastAPI)
- WebSocket live order status and dasher GPS updates
- Event bus for asynchronous delivery location fan-out
- TTL menu cache with hit and miss statistics
- Geospatial ranking with haversine distance, nearby restaurant search, ETA estimates, and nearest-dasher assignment
- Live delivery map using OpenStreetMap and Leaflet

## Quick start

```bash
cd DashTrack
python3 -m pip install -r requirements.txt
PYTHONPATH=backend python3 -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

1. Select a restaurant and menu items
2. Place an order
3. Track status updates and dasher movement from restaurant to customer on the map

## API

| Method | Path | Description |
|--------|------|---------|
| GET | `/api/restaurants` | List or geo-filter restaurants |
| GET | `/api/restaurants/{id}/menu` | Get menu (TTL cached) |
| POST | `/api/orders` | Place an order and start live tracking |
| GET | `/api/orders/{id}` | Get order details |
| GET | `/api/cache/stats` | Menu cache hit rate |
| WS | `/ws/orders/{id}` | Live location and status for one order |
| WS | `/ws/market` | Marketplace delivery event stream |

## Project structure

```
DashTrack/
  backend/app/
    main.py          # FastAPI application and WebSockets
    models.py        # Domain models and seed data
    geo.py           # Distance, ETA, and nearby search
    events.py        # Event bus and TTL cache
    store.py         # Application state
    simulator.py     # Order prep and dasher movement
  frontend/          # Live map UI
  requirements.txt
```

## Author

[Gitika Rath](https://github.com/gitika123)
