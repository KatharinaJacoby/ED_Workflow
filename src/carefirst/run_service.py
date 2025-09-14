
# run_service.py
# Minimal API server exposing SOP endpoints for the PoC core.
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from core_services_sop_registry import SOPRegistry
import uvicorn, os

app = FastAPI(title="ED Ops Core (PoC)", version="v5")

REG = SOPRegistry(os.environ.get("SOP_REGISTRY_PATH","./data/sop_registry.json"))
REG.load() or REG.refresh_offline_demo()

@app.get("/api/sops")
def list_sops():
    REG.load()
    return JSONResponse({"items": [x.__dict__ for x in REG.items]})

@app.post("/api/sops/refresh")
def refresh_demo():
    n = REG.refresh_offline_demo()
    return JSONResponse({"refreshed": n})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT","8000")))
