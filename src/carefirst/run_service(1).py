
# run_service.py — Phase-1 core API (PoC) with QR GET route
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from typing import Optional
import uvicorn, os, json, time

from carefirst.core_services_sop_registry import SOPRegistry

app = FastAPI(title="ED Ops Core (PoC)", version="v5.3")

REG = SOPRegistry(os.environ.get("SOP_REGISTRY_PATH","./data/sop_registry.json"))
REG.load() or REG.refresh_offline_demo()

# --------- SOP endpoints ---------
@app.get("/api/sops")
def list_sops():
    REG.load()
    return JSONResponse({"items": [x.__dict__ for x in REG.items]})

@app.post("/api/sops/refresh")
def refresh_demo():
    n = REG.refresh_offline_demo()
    return JSONResponse({"refreshed": n})

@app.get("/api/sops/search")
def search_sops(q: Optional[str] = ""):
    REG.load()
    ql = (q or "").lower()
    items = [x.__dict__ for x in REG.items if (ql in (x.title or "").lower()) or (ql in (x.category or "").lower())]
    return JSONResponse({"items": items})

# --------- Equipment endpoints ---------
EQUIP_PATH = os.environ.get("EQUIPMENT_STATUS_PATH","./data/equipment_status.json")
def _load_equipment():
    if not os.path.exists(EQUIP_PATH):
        return {"items":[]}
    return json.load(open(EQUIP_PATH,"r"))
def _save_equipment(payload):
    os.makedirs(os.path.dirname(EQUIP_PATH), exist_ok=True)
    json.dump(payload, open(EQUIP_PATH,"w"), indent=2)

def _update_equipment_record(id:str, location:str, status: Optional[str], battery: Optional[int]):
    payload = _load_equipment()
    items = payload.get("items", [])
    found = None
    for it in items:
        if it.get("id")==id:
            found = it; break
    if found is None:
        found = {"id":id, "label": id, "location": location, "status": status or "available"}
        items.append(found)
    found["location"] = location
    if status:
        found["status"] = status
    if battery is not None:
        found["battery"] = battery
    found["seen_at"] = int(time.time()*1000)
    payload["items"] = items
    _save_equipment(payload)
    return found

@app.get("/api/equipment")
def get_equipment():
    return JSONResponse(_load_equipment())

@app.put("/api/equipment/scan")
def scan_equipment(id:str, location:str, status:str="available", battery: Optional[int] = None):
    item = _update_equipment_record(id, location, status, battery)
    return JSONResponse({"ok": True, "item": item})

# --------- QR route guard (GET) for hardware scanners ---------
# Many QR scanners perform a simple HTTP GET without rich headers. This endpoint
# accepts the same params as /api/equipment/scan and returns a minimal HTML page
# that displays a confirmation ("Updated ✅") for human verification.
QR_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Updated ✅</title>
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:#f8fafc; color:#0f172a; }
  .card { max-width: 520px; margin: 8vh auto; background: #fff; padding: 20px 24px; border-radius: 14px;
          box-shadow: 0 8px 24px rgba(15,23,42,0.08); }
  .ok { font-size: 18px; font-weight: 700; }
  .kv { margin-top: 10px; font-size: 14px; color:#334155;}
  .kv div { margin: 4px 0; }
  .pill { display:inline-block; padding: 2px 8px; border-radius: 999px; background:#e2e8f0; margin-left: 6px; }
  .muted { color:#64748b; font-size:12px; margin-top: 10px; }
</style>
</head><body>
  <div class="card">
    <div class="ok">Updated ✅</div>
    <div class="kv">
      <div><b>ID</b> <span class="pill">{id}</span></div>
      <div><b>Location</b> <span class="pill">{location}</span></div>
      <div><b>Status</b> <span class="pill">{status}</span></div>
      <div><b>Battery</b> <span class="pill">{battery}</span></div>
      <div><b>Timestamp</b> <span class="pill">{ts}</span></div>
    </div>
    <div class="muted">You can close this window, or scan another label.</div>
  </div>
</body></html>"""

@app.get("/qr/scan")
def qr_scan(request: Request, id: str, location: str, status: Optional[str] = "available", battery: Optional[int] = None):
    try:
        # Update the store
        item = _update_equipment_record(id, location, status, battery)
        # Heuristic: if the client does not prefer HTML, still return HTML (simple scanners ignore content-type)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.get("seen_at", int(time.time()*1000)) / 1000))
        html = QR_PAGE.format(
            id=item.get("id","?"),
            location=item.get("location","?"),
            status=item.get("status","?"),
            battery=item.get("battery","—"),
            ts=ts,
        )
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        # Fall back to plain text for very limited clients
        return PlainTextResponse(f"ERROR: {e}", status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT","8000")))
