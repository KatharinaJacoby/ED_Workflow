
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
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
            if "equip_id" in df.columns:
                df["equip_id"] = df["equip_id"].astype(str)
            return df
        except Exception:
            return pd.DataFrame(columns=[
                "equip_id","name","location","status","last_seen","battery","confidence"
            ])

    def upsert(self, rec: EquipmentRecord) -> None:
        df = self.read()
        if df.empty:
            df = pd.DataFrame([rec.to_row()])
        else:
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
        try:
            prev = pd.read_csv(self.moves_csv) if self.moves_csv.exists() else None
            df = pd.concat([prev, row], ignore_index=True) if prev is not None else row
        except Exception:
            df = row
        df.to_csv(self.moves_csv, index=False)

    def read(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.moves_csv)
        except Exception:
            return pd.DataFrame(columns=["equip_id","from","to","ts"])

class SOPRegistry:
    def __init__(self, sop_csv: Path):
        self.sop_csv = Path(sop_csv)
        ensure_parent(self.sop_csv)

    def read(self) -> pd.DataFrame:
        if self.sop_csv.exists():
            try:
                df = pd.read_csv(self.sop_csv)
                # expected columns: sop_id,title,pdf_path,version,status,(optional)keywords,checklist
                for col in ["sop_id","title","pdf_path"]:
                    if col not in df.columns:
                        df[col] = ""
                return df
            except Exception:
                pass
        return pd.DataFrame(columns=["sop_id","title","pdf_path","version","status","keywords","checklist"])

# --------- Services ---------

class QRService:
    """QR encode/decode with graceful fallbacks."""
    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def make(self, payload: str) -> str:
        """Generate a QR (PNG) if possible; else return a fallback string."""
        try:
            import qrcode
            fp = self.out_dir / f"qr_{abs(hash(payload))}.png"
            img = qrcode.make(payload)
            img.save(fp)
            return str(fp)
        except Exception:
            return f"[QR fallback] {payload}"

    def decode_file(self, image_bytes: bytes) -> Optional[str]:
        """Try to decode a QR from image bytes. Returns payload or None."""
        # Try pyzbar (if available)
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            try:
                from pyzbar.pyzbar import decode as zbar_decode
                results = zbar_decode(img)
                if results:
                    return results[0].data.decode("utf-8", errors="ignore")
            except Exception:
                pass
        except Exception:
            pass
        return None

# --------- Core tracker service ---------

class TrackerService:
    """Core tracker service: repositories + utilities. No side effects at import."""
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
        """Current equipment table."""
        return self.equipment_repo.read()

    def log_move(self, equip_id: str, loc_from: str, loc_to: str) -> None:
        """Update equipment location and append to moves log."""
        ts_iso = pd.Timestamp.utcnow().isoformat()
        df = self.equipment_repo.read()
        row = df[df["equip_id"].astype(str) == str(equip_id)]
        name = row["name"].iloc[0] if not row.empty and "name" in row.columns else ""
        rec = EquipmentRecord(equip_id=equip_id, name=name, location=loc_to, status="moved", last_seen=ts_iso)
        self.equipment_repo.upsert(rec)
        self.moves_repo.append(equip_id, loc_from or "", loc_to, ts_iso)

    def find_equipment(self, query: str) -> pd.DataFrame:
        """Simple case-insensitive search over id/name/location/status."""
        q = (query or "").strip().lower()
        df = self.equipment_repo.read()
        if not q:
            return df
        def hit(row):
            return any(q in str(row.get(k,"")).lower() for k in ["equip_id","name","location","status"])
        return df[df.apply(hit, axis=1)]

    def overdue_equipment(self, threshold_minutes: int = 120) -> pd.DataFrame:
        """Equipment not seen within threshold minutes."""
        df = self.equipment_repo.read().copy()
        if df.empty or "last_seen" not in df.columns:
            return df.iloc[0:0]
        ts = pd.to_datetime(df["last_seen"], errors="coerce", utc=True)
        age_min = (pd.Timestamp.utcnow().tz_localize("UTC") - ts).dt.total_seconds() / 60.0
        df["age_min"] = age_min
        return df[age_min > float(threshold_minutes)].sort_values("age_min", ascending=False)

    # --- Analytics ---
    def movement_stats(self) -> Dict[str, pd.DataFrame]:
        """Basic analytics: moves per equipment and routes frequency."""
        log = self.moves_repo.read()
        if log.empty:
            return {"moves_per_equipment": log, "routes": log}
        per_eq = log.groupby("equip_id").size().reset_index(name="moves").sort_values("moves", ascending=False)
        routes = log.groupby(["from","to"]).size().reset_index(name="count").sort_values("count", ascending=False)
        return {"moves_per_equipment": per_eq, "routes": routes}

    # --- SOPs ---
    def sop_table(self) -> pd.DataFrame:
        return self.sop_registry.read()

    def search_sop(self, query: str) -> pd.DataFrame:
        df = self.sop_registry.read().copy()
        if df.empty:
            return df
        q = (query or "").strip().lower()
        if not q:
            return df
        cols = [c for c in ["sop_id","title","keywords","version","status"] if c in df.columns]
        mask = df[cols].astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        return df[mask]

    # --- QR encode/decode helpers for UI ---
    def make_qr(self, payload: str) -> str:
        return self.qr.make(payload)

    def decode_qr_bytes(self, image_bytes: bytes) -> Optional[str]:
        return self.qr.decode_file(image_bytes)
