
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import os
from pathlib import Path
import pandas as pd
import numpy as np

# --------- Config helpers ---------

def cfg_get(CONFIG: Any, key: str, default: Any = None) -> Any:
    try:
        return CONFIG.get(key, default)  # dict-like
    except Exception:
        return getattr(CONFIG, key, default) if hasattr(CONFIG, key) else default

def ensure_parent(path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

# --------- Data models ---------

@dataclass
class EquipmentRecord:
    equip_id: str
    name: str = ""
    location: str = ""
    status: str = ""
    last_seen: Optional[str] = None
    battery: Optional[float] = None
    confidence: Optional[float] = None

    def to_row(self) -> Dict[str, Any]:
        return {
            "equip_id": self.equip_id,
            "name": self.name,
            "location": self.location,
            "status": self.status,
            "last_seen": self.last_seen,
            "battery": self.battery,
            "confidence": self.confidence,
        }

# --------- Repositories ---------

class EquipmentRepository:
    def __init__(self, status_csv: Path):
        self.status_csv = Path(status_csv)
        ensure_parent(self.status_csv)
        if not self.status_csv.exists():
            pd.DataFrame(columns=[
                "equip_id","name","location","status","last_seen","battery","confidence"
            ]).to_csv(self.status_csv, index=False)

    def read(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.status_csv)
            # normalize dtypes
            if "equip_id" in df.columns:
                df["equip_id"] = df["equip_id"].astype(str)
            return df
        except Exception:
            return pd.DataFrame(columns=[
                "equip_id","name","location","status","last_seen","battery","confidence"
            ])

    def upsert(self, rec: EquipmentRecord) -> None:
        df = self.read()
        mask = (df["equip_id"].astype(str) == str(rec.equip_id))
        row = pd.DataFrame([rec.to_row()])
        if mask.any():
            df.loc[mask, :] = row.values
        else:
            df = pd.concat([df, row], ignore_index=True)
        df.to_csv(self.status_csv, index=False)

class MovesLogRepository:
    def __init__(self, moves_csv: Path):
        self.moves_csv = Path(moves_csv)
        ensure_parent(self.moves_csv)
        if not self.moves_csv.exists():
            pd.DataFrame(columns=["equip_id","from","to","ts"]).to_csv(self.moves_csv, index=False)

    def append(self, equip_id: str, loc_from: str, loc_to: str, ts_iso: str) -> None:
        row = pd.DataFrame([{"equip_id": equip_id, "from": loc_from, "to": loc_to, "ts": ts_iso}])
        if self.moves_csv.exists():
            try:
                prev = pd.read_csv(self.moves_csv)
                df = pd.concat([prev, row], ignore_index=True)
            except Exception:
                df = row
        else:
            df = row
        df.to_csv(self.moves_csv, index=False)

class SOPRegistry:
    def __init__(self, sop_csv: Path):
        self.sop_csv = Path(sop_csv)
        ensure_parent(self.sop_csv)
        # do not create file if missing; empty df returned if absent

    def read(self) -> pd.DataFrame:
        if self.sop_csv.exists():
            try:
                return pd.read_csv(self.sop_csv)
            except Exception:
                pass
        return pd.DataFrame(columns=["sop_id","title","pdf_path","version","status"])

# --------- Services ---------

class QRService:
    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def make(self, payload: str) -> str:
        # use qrcode if present; else fallback string
        try:
            import qrcode
            fp = self.out_dir / f"qr_{abs(hash(payload))}.png"
            img = qrcode.make(payload)
            img.save(fp)
            return str(fp)
        except Exception:
            return f"[QR fallback] {payload}"

class TrackerService:
    """Core tracker service: no side effects at import time; UI calls its methods."""
    def __init__(
        self,
        equipment_repo: EquipmentRepository,
        moves_repo: MovesLogRepository,
        sop_registry: SOPRegistry,
        qr: QRService,
        config: Any
    ):
        self.equipment_repo = equipment_repo
        self.moves_repo = moves_repo
        self.sop_registry = sop_registry
        self.qr = qr
        self.CONFIG = config

    @classmethod
    def from_config(cls, CONFIG: Any) -> "TrackerService":
        status_csv = Path(cfg_get(CONFIG, "EQUIPMENT_STATUS_PATH"))
        moves_csv = Path(cfg_get(CONFIG, "EQUIPMENT_MOVES_LOG_PATH"))
        sop_csv = Path(cfg_get(CONFIG, "SOP_REGISTRY_PATH"))
        qr_dir = Path(cfg_get(CONFIG, "QR_OUTPUT_DIR"))
        return cls(EquipmentRepository(status_csv), MovesLogRepository(moves_csv), SOPRegistry(sop_csv), QRService(qr_dir), CONFIG)

    # --- Equipment ---
    def equipment_status(self) -> pd.DataFrame:
        return self.equipment_repo.read()

    def log_move(self, equip_id: str, loc_from: str, loc_to: str) -> None:
        ts_iso = pd.Timestamp.utcnow().isoformat()
        # upsert equipment location
        df = self.equipment_repo.read()
        row = df[df["equip_id"].astype(str) == str(equip_id)]
        name = row["name"].iloc[0] if not row.empty and "name" in row.columns else ""
        rec = EquipmentRecord(equip_id=equip_id, name=name, location=loc_to, status="moved", last_seen=ts_iso)
        self.equipment_repo.upsert(rec)
        # log move
        self.moves_repo.append(equip_id, loc_from, loc_to, ts_iso)

    # --- QR ---
    def make_qr(self, payload: str) -> str:
        return self.qr.make(payload)

    # --- SOP ---
    def sop_table(self) -> pd.DataFrame:
        return self.sop_registry.read()

    # --- Critic scoring ---
    def score_actions(self, state: Any, actions: List[Dict[str, Any]], critic: Any) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # expects state to be a real WorkflowState with .feature_dict()
        return critic.score(state, actions)
