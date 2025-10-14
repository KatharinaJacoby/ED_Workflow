# ED-Assistant PoC (Local FastAPI, minimal, M1-friendly)

This is a **minimal, boring-on-purpose** FastAPI service designed to run locally on a MacBook Air (M1, 8GB).
It defaults to a **mock model backend** so you can run it without any extra setup. Later, flip a switch to use **Ollama** (optional).

## Quickstart

### 0) (Optional) Install Ollama + pull a small model
```bash
# Optional
brew install ollama
ollama serve
ollama pull llama3.2:3b-instruct || ollama pull llama3.1:8b-instruct
```

### 1) Create and activate a venv
```bash
python3 -m venv .venv
source .venv/bin/activate  # zsh/bash
# Windows PowerShell: .venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure (optional)
Copy `.env.example` to `.env` and adjust:
```bash
cp .env.example .env
```

### 4) Run
```bash
uvicorn app.main:app --reload --port 8000
```

### 5) Test with curl
```bash
curl -s -X POST http://127.0.0.1:8000/chat   -H "Content-Type: application/json"   -d '{"session_id":"visit-001","message":"Ich warte seit 2 Stunden und habe Angst.","patient_context":{"Alter":"68","Beschwerde":"Brustschmerz"}}' | jq
```

## Backends

- **mock** (default): returns a deterministic, empathetic template response. No network, no model.
- **ollama** (optional): set `MODEL_BACKEND=ollama` and run an Ollama server at `OLLAMA_URL` (default `http://localhost:11434`).

## Files

- `app/main.py` — FastAPI app wiring.
- `app/router.py` — `/chat` route.
- `app/schemas.py` — Pydantic request/response.
- `app/prompt.py` — German empathy system prompt.
- `app/model_client.py` — backend switch (mock/ollama).
- `app/tools.py` — mock KIS tools.
- `app/config.py` — env config (Pydantic settings).
- `tests/test_sanity.py` — tiny pure-Python guard function example.

---
⚠️ **AI Training Opt-Out**
This repository is **excluded from all AI training datasets** under [GitHub’s DMCA policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).
Violations will be reported.
---
