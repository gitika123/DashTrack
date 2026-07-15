const state = {
  restaurants: [],
  customer: null,
  orderId: null,
  ws: null,
  markers: {},
  selectedItems: new Set(),
};

const map = L.map("map").setView([37.3382, -121.8863], 14);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap",
}).addTo(map);

function markerIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.35)"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function setMarker(key, lat, lon, color, label) {
  if (state.markers[key]) {
    state.markers[key].setLatLng([lat, lon]);
    return;
  }
  state.markers[key] = L.marker([lat, lon], { icon: markerIcon(color) })
    .addTo(map)
    .bindPopup(label);
}

async function refreshCacheStats() {
  const stats = await api("/api/cache/stats");
  document.getElementById("cacheStats").textContent =
    `Menu cache hits ${stats.hits} / misses ${stats.misses} (${Math.round(stats.hit_rate * 100)}%)`;
}

async function loadMenu(restaurantId) {
  const data = await api(`/api/restaurants/${restaurantId}/menu`);
  const menu = document.getElementById("menuList");
  menu.innerHTML = "";
  state.selectedItems = new Set();
  data.items.forEach((item) => {
    const row = document.createElement("label");
    row.className = "item";
    row.innerHTML = `<input type="checkbox" value="${item.id}" /> <span>${item.name} · $${item.price.toFixed(2)}</span>`;
    row.querySelector("input").addEventListener("change", (e) => {
      if (e.target.checked) state.selectedItems.add(item.id);
      else state.selectedItems.delete(item.id);
    });
    menu.appendChild(row);
  });
  await refreshCacheStats();
}

function renderTimeline(events) {
  const ol = document.getElementById("timeline");
  ol.innerHTML = "";
  (events || []).forEach((e) => {
    const li = document.createElement("li");
    li.textContent = e;
    ol.appendChild(li);
  });
}

function connectWs(orderId) {
  if (state.ws) state.ws.close();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/orders/${orderId}`);
  state.ws = ws;

  ws.onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    const order = data.order;
    if (order) {
      document.getElementById("orderMeta").textContent =
        `Order ${order.id}\nStatus: ${order.status}\nTotal: $${order.total}\nETA: ${order.eta_minutes ?? "—"} min\nDasher: ${order.dasher_id || "pending"}`;
      renderTimeline(order.events);
      setMarker("rest", order.pickup.lat, order.pickup.lon, "#c2410c", "Restaurant");
      setMarker("cust", order.dropoff.lat, order.dropoff.lon, "#0f766e", "Customer");
    }
    const p = data.payload || {};
    if (typeof p.lat === "number" && typeof p.lon === "number") {
      setMarker("dash", p.lat, p.lon, "#1d4ed8", "Dasher");
      map.panTo([p.lat, p.lon]);
    }
  };
}

async function init() {
  const [restaurants, customers] = await Promise.all([
    api("/api/restaurants"),
    api("/api/customers"),
  ]);
  state.restaurants = restaurants;
  state.customer = customers[0];

  setMarker("cust-home", state.customer.location.lat, state.customer.location.lon, "#0f766e", state.customer.name);

  const select = document.getElementById("restaurantSelect");
  restaurants.forEach((r) => {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = `${r.name} (${r.cuisine})`;
    select.appendChild(opt);
    setMarker(`rest-${r.id}`, r.location.lat, r.location.lon, "#c2410c", r.name);
  });
  select.addEventListener("change", () => loadMenu(select.value));
  await loadMenu(select.value);

  document.getElementById("orderBtn").addEventListener("click", async () => {
    if (!state.selectedItems.size) {
      alert("Select at least one menu item");
      return;
    }
    const btn = document.getElementById("orderBtn");
    btn.disabled = true;
    try {
      const order = await api("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_id: state.customer.id,
          restaurant_id: select.value,
          item_ids: [...state.selectedItems],
        }),
      });
      state.orderId = order.id;
      document.getElementById("orderMeta").textContent = `Order ${order.id}\nStatus: ${order.status}`;
      renderTimeline(order.events);
      connectWs(order.id);
      await loadMenu(select.value); // second fetch should show cache hits
    } catch (err) {
      alert(err.message || String(err));
    } finally {
      btn.disabled = false;
    }
  });
}

init().catch((err) => {
  document.getElementById("orderMeta").textContent = `Failed to load: ${err}`;
});
