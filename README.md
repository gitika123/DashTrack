# DashTrack

Real-time **three-sided food delivery marketplace demo** (customer · restaurant · dasher) with live geospatial tracking.

Inspired by food-delivery platforms like DoorDash / the [FoodFlow](https://github.com/Fouzia-Oreen/FoodFlow_AI-Powered-Food-Delivery-Platform) concept — this repo is an **original implementation**, not a fork. The public FoodFlow tree is largely an empty README scaffold; DashTrack is a working MVP you can run locally.

## What it demonstrates

- REST APIs for restaurants, menus, and orders (FastAPI)
- WebSocket live order status + dasher GPS updates
- In-memory event bus (Kafka-style topic) for async delivery events
- TTL menu cache with hit/miss stats (Redis-style caching pattern)
- Geospatial logic: haversine distance, nearby restaurant ranking, ETA, nearest-dasher assignment
- Simulated kitchen prep + dasher path interpolation on an OpenStreetMap / Leaflet map

## Quick start

```bash
cd DashTrack
python3 -m pip install -r requirements.txt
PYTHONPATH=backend python3 -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

1. Pick a restaurant and menu items  
2. Click **Place order & track live**  
3. Watch status timeline + dasher marker move restaurant → customer  

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/restaurants` | List / geo-filter restaurants |
| GET | `/api/restaurants/{id}/menu` | Menu with TTL cache |
| POST | `/api/orders` | Place order and start live simulation |
| GET | `/api/orders/{id}` | Order snapshot |
| GET | `/api/cache/stats` | Cache hit rate |
| WS | `/ws/orders/{id}` | Live location + status for one order |
| WS | `/ws/market` | All marketplace delivery events |

## Project layout

```
DashTrack/
  backend/app/
    main.py          # FastAPI + WebSockets
    models.py        # Domain models + seed SJ data
    geo.py           # Haversine / ETA / nearby
    events.py        # Event bus + TTL cache
    store.py         # Marketplace state
    simulator.py     # Prep + dasher movement
  frontend/          # Leaflet live map UI
  requirements.txt
```

## Interview talking points

- Why an event bus instead of only request/response for location fan-out  
- How nearest-dasher assignment uses geospatial ranking  
- How menu TTL caching cuts repeat read load (observe hit rate after second menu fetch)  
- Honest demo limits: in-memory store, simulated movement, not production Kafka/Redis clusters  

## Author

Built by [Gitika Rath](https://github.com/gitika123) for DoorDash-oriented product / backend interview prep.
