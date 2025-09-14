
# run_service.py — Phase-1 core API (PoC) with QR GET route
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from typing import Optional
import uvicorn, os, json, json, time

from carefirst.core_services_sop_registry import SOPRegistry
from core_sop_bindings import seed_binding, load_binding, save_binding, update_step, list_bindings_for_encounter

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



# --------- SOP Binding (patient-specific) ---------
from fastapi import Body

@app.post("/api/patients/{enc}/sop/bind")
def bind_sop(enc: str, sop_id: str = Body(...), title: str = Body(...), url: str = Body(...), pdf_url: str | None = Body(None), steps: list[dict] = Body([]), source: str = Body("SOP-Notaufnahme")):
    meta = {"id": sop_id, "title": title, "url": url, "pdf_url": pdf_url, "source": source}
    b = seed_binding(enc, meta, steps)
    return {"ok": True, "binding": b}

@app.get("/api/patients/{enc}/sop/list")
def list_enc_bindings(enc: str):
    return {"items": list_bindings_for_encounter(enc)}

@app.get("/api/patients/{enc}/sop/{sop_id}/tasks")
def get_enc_sop_tasks(enc: str, sop_id: str):
    data = load_binding(enc, sop_id) or {"steps": []}
    return data

@app.post("/api/patients/{enc}/sop/{sop_id}/tasks/check")
def post_enc_sop_check(enc: str, sop_id: str, step_id: str = Body(...), status: str = Body("done"), note: str | None = Body(None)):
    ev = {"type":"manual","summary": note or f"Set {status}"}
    data = update_step(enc, sop_id, step_id, status=status, evidence=ev, autocompleted=False)
    return {"ok": True, "binding": data}

@app.post("/api/patients/{enc}/sop/{sop_id}/tasks/snooze")
def post_enc_sop_snooze(enc: str, sop_id: str, step_id: str = Body(...), minutes: int = Body(30)):
    data = update_step(enc, sop_id, step_id, snooze_min=minutes)
    return {"ok": True, "binding": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT","8000")))

# ---- SOP flow endpoints ----
FLOW_PATH = os.environ.get("PRIORITY_FLOWS_PATH","./data/priority_flows.json")

@app.get("/api/sops/flow")
def list_priority_flows():
    if not os.path.exists(FLOW_PATH):
        return JSONResponse({"items":[]})
    return JSONResponse(json.load(open(FLOW_PATH,"r")))

@app.get("/api/sops/pdf")
def sop_pdf(url: str):
    # passthrough reference for UI to embed
    return JSONResponse({"pdf_url": url})

# Movement logging for equipment analytics
MOVES_LOG = os.environ.get("EQUIPMENT_MOVES_LOG","./logs/equipment_moves.log")

def _append_move(entry: dict):
    os.makedirs(os.path.dirname(MOVES_LOG), exist_ok=True)
    with open(MOVES_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

@app.get("/api/metrics")
def metrics():
    if not os.path.exists(MOVES_LOG):
        return JSONResponse({"equipment": {"moves": 0, "mean_time_to_find_min": None}})
    with open(MOVES_LOG, "r") as f:
        lines = [json.loads(x) for x in f if x.strip()]
    moves_count = len(lines)
    by_id = {}
    for m in lines:
        by_id.setdefault(m["id"], []).append(m)
    ttf = []
    for eid, evs in by_id.items():
        evs.sort(key=lambda x: x["ts"])
        last_missing = None
        for e in evs:
            was_missing = (e.get("from") in (None, "Unknown")) or (e.get("status")=="missing")
            if was_missing:
                last_missing = e["ts"]
            became_found = e.get("to") not in (None, "Unknown")
            if last_missing and became_found:
                ttf.append(e["ts"] - last_missing)
                last_missing = None
    mean_ttf_min = round(sum(ttf)/len(ttf)/60000.0, 1) if ttf else None
    return JSONResponse({"equipment": {"moves": moves_count, "mean_time_to_find_min": mean_ttf_min}})
