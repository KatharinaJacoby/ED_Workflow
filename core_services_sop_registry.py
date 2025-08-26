
"""
core_services_sop_registry.py
Core SOP registry service for PoC. Source: https://sop-notaufnahme.de/sop/
This file is safe to import from tests and run_service.py (no scraping by default).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional
import json, os, time

SOURCE_ATTR = "SOP-Notaufnahme — Medizinische Leitfäden (Quelle: https://sop-notaufnahme.de/sop/)"
LICENSE_NOTE = ("Einbindung nach Impressum: Nutzung für medizinisches Fachpersonal kostenfrei; "
                "Weitergabe mit Quellenangabe; Modifikation untersagt; "
                "hausinterne Nutzung (kommerziell) → Lizenz erforderlich.")

@dataclass(frozen=True)
class SOPItem:
    id: str
    title: str
    category: Optional[str]
    url: str
    pdf_url: Optional[str]
    source: str = SOURCE_ATTR
    license: str = LICENSE_NOTE

class SOPRegistry:
    def __init__(self, path:str = "./data/sop_registry.json"):
        self.path = path
        self.items: List[SOPItem] = []

    def load(self) -> int:
        if not os.path.exists(self.path):
            self.items = []
            return 0
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.items = [SOPItem(**it) for it in data.get("items", [])]
        return len(self.items)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({
                "source": SOURCE_ATTR,
                "license_note": LICENSE_NOTE,
                "count": len(self.items),
                "generated_at": int(time.time()),
                "items": [asdict(x) for x in self.items],
            }, f, ensure_ascii=False, indent=2)

    def refresh_offline_demo(self):
        demo = [
            SOPItem(id="cpain", title="Brustschmerz — Chest Pain Evaluation", category="Kardiologie",
                    url="https://sop-notaufnahme.de/product/brustschmerz/", pdf_url=None),
            SOPItem(id="sepsis", title="Sepsis — Recognition & Treatment Bundle", category="Infektiologie",
                    url="https://sop-notaufnahme.de/product/sepsis/", pdf_url=None),
            SOPItem(id="erys", title="Erysipel", category="Infektiologie",
                    url="https://sop-notaufnahme.de/product/erysipel/", pdf_url="https://sop-notaufnahme.de/wp-content/.../sop-erysipel.pdf"),
        ]
        self.items = demo
        self.save()
        return len(self.items)
