from fastapi import FastAPI
from .router import router

app = FastAPI(title="ED-Assistant PoC (minimal)")
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
