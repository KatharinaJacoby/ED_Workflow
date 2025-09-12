from fastapi import APIRouter
from .schemas import ChatRequest, ChatResponse
from .model_client import run_chat

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    context_line = ""
    if req.patient_context:
        items = ", ".join(f"{k}: {v}" for k, v in req.patient_context.items())
        context_line = f"(Kontext: {items})"
    reply = await run_chat(req.message, context_line)
    return ChatResponse(reply=reply)
