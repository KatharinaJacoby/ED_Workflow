
from __future__ import annotations
from typing import Callable, Dict, List, Any
import threading, queue

class InMemoryBus:
    def __init__(self):
        self.subs: Dict[str, List[Callable[[Any],None]]] = {}
        self.q = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def publish(self, topic: str, msg: Any):
        self.q.put((topic, msg))

    def subscribe(self, topic: str, fn: Callable[[Any],None]):
        self.subs.setdefault(topic, []).append(fn)

    def _run(self):
        while self.running:
            try:
                topic, msg = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            for fn in self.subs.get(topic, []):
                try: fn(msg)
                except Exception: pass

    def stop(self):
        self.running = False
        self.thread.join(timeout=1.0)
