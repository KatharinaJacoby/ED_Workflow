import sys
import requests
import json

API_URL = "http://127.0.0.1:8000/chat"

def send_message(message: str, session_id="demo", patient_context=None):
    payload = {
        "session_id": session_id,
        "message": message,
        "patient_context": patient_context or {"Alter": "68"}
    }
    resp = requests.post(API_URL, json=payload)
    try:
        return resp.json()
    except Exception:
        return {"error": resp.text}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_chat.py 'Your message here'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    reply = send_message(message)
    print(json.dumps(reply, indent=2, ensure_ascii=False))

