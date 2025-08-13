
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
import yaml, json

@dataclass
class Config:
    actions: List[Dict[str, Any]]
    features: List[str]
    backbone: Dict[str, Any] = field(default_factory=lambda: {"type":"gru","hidden":64,"dropout":0.3})
    head: Dict[str, Any] = field(default_factory=lambda: {"type":"unified"})
    thresholds: Dict[str, float] = field(default_factory=dict)
    gate: Dict[str, Any] = field(default_factory=lambda: {"tau":0.5, "top_k":1})
    temperature: float = 1.0
    seed: int = 1337

def load_config(path: str) -> Config:
    if path.endswith(".json"):
        data = json.load(open(path))
    else:
        data = yaml.safe_load(open(path))
    return Config(**data)
