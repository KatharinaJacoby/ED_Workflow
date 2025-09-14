
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass(frozen=True)
class ActionSpec:
    code: str
    label: str
    critical: bool = False
    params: Dict[str, Any] = None

class ActionSpace:
    def __init__(self, specs: List[Dict[str, Any]]):
        self.specs: List[ActionSpec] = [ActionSpec(**s) for s in specs]
        self.idx: Dict[str,int] = {s.code:i for i,s in enumerate(self.specs)}
        self.codes: List[str] = [s.code for s in self.specs]
        self.labels: List[str] = [s.label for s in self.specs]
        self.critical_mask = [int(s.critical) for s in self.specs]
    def __len__(self): return len(self.specs)
    def id(self, code: str) -> int: return self.idx[code]
    def spec(self, i: int) -> ActionSpec: return self.specs[i]
