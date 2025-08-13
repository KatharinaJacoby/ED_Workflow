
from __future__ import annotations
from typing import Dict, Any, List
import time

class Notifier:
    def __init__(self):
        self.queue: List[Dict[str,Any]] = []
    def send(self, msg: Dict[str,Any]) -> bool:
        self.queue.append({"ts": time.time(), "msg": msg, "status": "queued"})
        return True
