import json, re, httpx
from .config import settings
from .prompt import SYSTEM_PROMPT
from .tools import TOOLS

CALL_RE = re.compile(r"<\|call:(?P<tool>\w+)\|>(?P<body>\{.*\})<\|end\|>", re.S)

async def _ollama_chat(messages):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": settings.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": settings.temperature,
                    "top_p": settings.top_p,
                    "num_predict": settings.max_tokens,
                },
            },
        )
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]

def _mock_reply(user_message: str, context: str) -> str:
    # Deterministic, short, empathetic template
    lines = []
    lines.append("Guten Tag, ich bin Ihre Unterstützung in der Notaufnahme.")
    lines.append("Ich höre, dass Sie belastet sind — danke, dass Sie es ansprechen.")
    lines.append("Ich prüfe, was wir sofort tun können. Gibt es Alarmzeichen wie stärkere Schmerzen, Atemnot oder Benommenheit?")
    return " ".join(lines)

async def run_chat(user_message: str, context: str = "") -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n{user_message}".strip()},
    ]

    if settings.model_backend == "ollama":
        reply = await _ollama_chat(messages)
        # if the model emits a tool call, handle it (optional demo)
        m = CALL_RE.search(reply)
        if m:
            tool = m.group("tool")
            body = json.loads(m.group("body"))
            if tool in TOOLS:
                result = TOOLS[tool](**body)
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "system", "content": f"[TOOL:{tool}_RESULT]{json.dumps(result)}"})
                reply = await _ollama_chat(messages)
        return reply
    else:
        # mock backend
        return _mock_reply(user_message, context)

# Pure-Python guard (no external deps): ensure no fabricated numeric labs unless present in a tool result string
LAB_VALUE_RE = re.compile(r"(CRP|CRP-Wert)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)", re.I)

def guard_no_fake_labs(text: str, last_tool_result: str | None) -> bool:
    """Return True if 'text' is safe (does not mention numeric lab values unless present in last_tool_result)."""
    m = LAB_VALUE_RE.search(text or "")
    if not m:
        return True
    if not last_tool_result:
        return False
    val = m.group(2).replace(",", ".")
    return val in last_tool_result
