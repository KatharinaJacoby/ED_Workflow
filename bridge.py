
from __future__ import annotations
from typing import Dict, Any, List

class BridgeAdapter:
    def __init__(self, system: str = "json"):
        self.system = system
    def to_message(self, action: Dict[str,Any]) -> Dict[str,Any]:
        code = action["action_code"]
        params = action.get("params", {})
        if code.startswith("ORDER_"):
            return {"type":"ORDER", "modality":code.replace("ORDER_",""), "params":params}
        if code in ("REQUEST_BED", "VERIFY_CAPACITY"):
            return {"type":"BED_OP", "op":code, "params":params}
        if code == "REQUEST_CONSULT":
            return {"type":"CONSULT", "service":params.get("service","auto")}
        return {"type":"INFO", "code":code, "params":params}
