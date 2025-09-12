from pydantic import BaseModel, Field
from typing import Dict, Optional

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID per conversation")
    message: str
    patient_context: Optional[Dict[str, str]] = None

class ChatResponse(BaseModel):
    reply: str
