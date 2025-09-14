
from __future__ import annotations
from typing import Dict, Any, List
import os, json, hashlib
from datetime import datetime, timezone

def _canon(obj: Dict[str,Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",",":"))

class AuditLog:
    def __init__(self, path: str):
        self.path = path
        self.prev_hash = None
        if os.path.exists(path):
            last = None
            with open(path,"r") as f:
                for line in f: last = line
            if last:
                try:
                    rec = json.loads(last)
                    self.prev_hash = rec.get("chain_hash")
                except Exception:
                    self.prev_hash = None

    def append(self, event: Dict[str,Any]) -> Dict[str,Any]:
        ts = datetime.now(timezone.utc).isoformat()
        rec = {"ts": ts, "event": event}
        base = (self.prev_hash or "") + _canon(rec)
        ch = hashlib.sha256(base.encode("utf-8")).hexdigest()
        out = {"ts": ts, "event": event, "chain_hash": ch}
        with open(self.path, "a") as f:
            f.write(json.dumps(out) + "\n")
        self.prev_hash = ch
        return out

def merkle_root(records: List[str]) -> str:
    if not records: return ""
    layer = [bytes.fromhex(h) for h in records]
    import hashlib
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i+1] if i+1 < len(layer) else a
            nxt.append(hashlib.sha256(a+b).digest())
        layer = nxt
    return layer[0].hex()

def export_anchor(audit_path: str, out_path: str):
    hashes = []
    with open(audit_path, "r") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if "chain_hash" in rec: hashes.append(rec["chain_hash"])
            except Exception:
                pass
    root = merkle_root(hashes)
    anchor = {"anchored_at": datetime.now(timezone.utc).isoformat(), "merkle_root": root, "count": len(hashes)}
    with open(out_path, "w") as f:
        json.dump(anchor, f, indent=2)
    return anchor
