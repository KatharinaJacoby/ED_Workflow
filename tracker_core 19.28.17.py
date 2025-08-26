"""
edtracker.core.tracker_core
---------------------------
Core repository/services layer for the ED Tracker project.

Contents:
- EquipmentRecord (dataclass)
- EquipmentRepository (CSV-backed store with robust schema handling)
- MovesLogRepository (append-only movement log)
- SOPRegistry (CSV index of SOPs)
- QRService (generate/scan QR payloads; deterministic filenames)
- TrackerService (facade that wires the above together)

Design notes:
- No heavy I/O at import time; repositories only touch disk when methods are called.
- All CSV reads ALWAYS return a DataFrame with a fixed schema/order.
- Functions/classes are safe to import inside notebooks, CLIs, or services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
import hashlib

import pandas as pd
import numpy as np


__all__ = [
    "EquipmentRecord",
    "EquipmentRepository",
    "MovesLogRepository",
    "SOPRegistry",
    "QRService",
    "TrackerService",
]


# -----------------------------
# Helpers
# -----------------------------

def _cfg(CONFIG: Any, key: str, default: Any = None) -> Any:
    """Read a value from a mapping-like or object-like CONFIG without raising."""
    try:
        return CONFIG.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return getattr(CONFIG, key, default) if hasattr(CONFIG, key) else default


def _ensure_parent(p: Path) -> None:
    """Create parent directory of a path (for file or directory), idempotently."""
    p = Path(p)
    (p.parent if p.suffix else p).mkdir(parents=True, exist_ok=True)


# Fixed schemas (stable column order)
_EQUIP_COLS = ["equip_id", "name", "location", "status", "last_seen", "battery", "confidence"]
_MOVES_COLS = ["equip_id", "from", "to", "ts"]
_SOP_COLS   = ["sop_id", "title", "pdf_path", "version", "status", "keywords", "checklist", "source_url"]


# -----------------------------
# Data objects
# -----------------------------

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


# -----------------------------
# Repositories
# -----------------------------

class EquipmentRepository:
    """CSV-backed store of equipment status with robust read/upsert semantics."""

    def __init__(self, status_csv: Path):
        self.status_csv = Path(status_csv)
        _ensure_parent(self.status_csv)
        if not self.status_csv.exists():
            pd.DataFrame(columns=_EQUIP_COLS).to_csv(self.status_csv, index=False)

    def read(self) -> pd.DataFrame:
        """Always return a DataFrame with _EQUIP_COLS in this exact order."""
        try:
            df = pd.read_csv(self.status_csv)
        except Exception:
            return pd.DataFrame(columns=_EQUIP_COLS)

        # Ensure required columns exist
        for col in _EQUIP_COLS:
            if col not in df.columns:
                df[col] = np.nan

        # Normalize types/order
        df["equip_id"] = df["equip_id"].astype(str)
        return df[_EQUIP_COLS]

    def upsert(self, rec: EquipmentRecord) -> None:
        """Insert or replace a row by equip_id, preserving schema/order."""
        df = self.read()
        row = pd.DataFrame([rec.to_row()])
        # align to schema (reindex also tolerates extra keys gracefully)
        row = row.reindex(columns=_EQUIP_COLS)
        mask = (df["equip_id"].astype(str) == str(rec.equip_id))
        if mask.any():
            df.loc[mask, _EQUIP_COLS] = row.values
        else:
            df = pd.concat([df, row], ignore_index=True)
        df.to_csv(self.status_csv, index=False)


class MovesLogRepository:
    """Append-only movement log for equipment moves."""

    def __init__(self, moves_csv: Path):
        self.moves_csv = Path(moves_csv)
        _ensure_parent(self.moves_csv)
        if not self.moves_csv.exists():
            pd.DataFrame(columns=_MOVES_COLS).to_csv(self.moves_csv, index=False)

    def append(self, equip_id: str, loc_from: str, loc_to: str, ts_iso: str) -> None:
        row = pd.DataFrame([{"equip_id": equip_id, "from": loc_from, "to": loc_to, "ts": ts_iso}])
        try:
            prev = pd.read_csv(self.moves_csv) if self.moves_csv.exists() else None
            df = pd.concat([prev, row], ignore_index=True) if prev is not None else row
        except Exception:
            df = row
        # ensure schema/order
        for c in _MOVES_COLS:
            if c not in df.columns:
                df[c] = np.nan
        df[_MOVES_COLS].to_csv(self.moves_csv, index=False)

    def read(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.moves_csv)
        except Exception:
            return pd.DataFrame(columns=_MOVES_COLS)
        for c in _MOVES_COLS:
            if c not in df.columns:
                df[c] = np.nan
        return df[_MOVES_COLS]


class SOPRegistry:
    """Lightweight CSV registry of SOPs; tolerant of missing/extra columns."""

    def __init__(self, sop_csv: Path):
        self.sop_csv = Path(sop_csv)
        _ensure_parent(self.sop_csv)
        if not self.sop_csv.exists():
            pd.DataFrame(columns=_SOP_COLS).to_csv(self.sop_csv, index=False)

    def read(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.sop_csv)
        except Exception:
            return pd.DataFrame(columns=_SOP_COLS)
        for c in _SOP_COLS:
            if c not in df.columns:
                df[c] = "" if c in {"sop_id", "title", "pdf_path"} else np.nan
        return df[_SOP_COLS]


# -----------------------------
# QR Service
# -----------------------------

class QRService:
    """Generate & decode QR codes with deterministic filenames."""

    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def make(self, payload: str) -> str:
        """Create a QR image; filename is a stable hash of the payload."""
        try:
            import qrcode  # type: ignore
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
            fp = self.out_dir / f"qr_{digest}.png"
            img = qrcode.make(payload)
            img.save(fp)
            return str(fp)
        except Exception:
            # No qrcode or error — return a readable fallback
            return f"[QR fallback] {payload}"

    def decode_file(self, image_bytes: bytes) -> Optional[str]:
        """Attempt to decode a QR image from bytes; return payload or None."""
        try:
            from PIL import Image  # type: ignore
            import io
            img = Image.open(io.BytesIO(image_bytes))
            try:
                from pyzbar.pyzbar import decode as zbar_decode  # type: ignore
                res = zbar_decode(img)
                if res:
                    return res[0].data.decode("utf-8", "ignore")
            except Exception:
                # pyzbar missing or failed
                pass
        except Exception:
            pass
        return None


# -----------------------------
# Facade Service
# -----------------------------

class TrackerService:
    """
    High-level facade composing repositories + QR service.
    All methods are pure in-memory except where they touch the repositories.
    """

    def __init__(
        self,
        equipment_repo: EquipmentRepository,
        moves_repo: MovesLogRepository,
        sop_registry: SOPRegistry,
        qr: QRService,
        config: Any,
    ):
        self.equipment_repo = equipment_repo
        self.moves_repo = moves_repo
        self.sop_registry = sop_registry
        self.qr = qr
        self.CONFIG = config

    @classmethod
    def from_config(cls, CONFIG: Any) -> "TrackerService":
        return cls(
            EquipmentRepository(Path(_cfg(CONFIG, "EQUIPMENT_STATUS_PATH"))),
            MovesLogRepository(Path(_cfg(CONFIG, "EQUIPMENT_MOVES_LOG_PATH"))),
            SOPRegistry(Path(_cfg(CONFIG, "SOP_REGISTRY_PATH"))),
            QRService(Path(_cfg(CONFIG, "QR_OUTPUT_DIR"))),
            CONFIG,
        )

    # ---- Equipment ----

    def equipment_status(self) -> pd.DataFrame:
        return self.equipment_repo.read()

    def log_move(self, equip_id: str, loc_from: str, loc_to: str) -> None:
        ts_iso = pd.Timestamp.utcnow().isoformat()
        df = self.equipment_repo.read()
        name = ""
        if not df.empty and "name" in df.columns:
            row = df[df["equip_id"].astype(str) == str(equip_id)]
            if not row.empty:
                # use existing name if present
                try:
                    name = str(row["name"].iloc[0])
                except Exception:
                    name = ""
        rec = EquipmentRecord(
            equip_id=str(equip_id),
            name=name,
            location=str(loc_to),
            status="moved",
            last_seen=ts_iso,
        )
        self.equipment_repo.upsert(rec)
        self.moves_repo.append(str(equip_id), str(loc_from or ""), str(loc_to), ts_iso)

    def find_equipment(self, query: str) -> pd.DataFrame:
        q = (query or "").strip().lower()
        df = self.equipment_repo.read()
        if not q:
            return df
        def _hit(row: Dict[str, Any]) -> bool:
            return any(q in str(row.get(k, "")).lower() for k in ["equip_id", "name", "location", "status"])
        return df[df.apply(_hit, axis=1)]

    def overdue_equipment(self, threshold_minutes: int = 120) -> pd.DataFrame:
        df = self.equipment_repo.read().copy()
        if df.empty or "last_seen" not in df.columns:
            return df.iloc[0:0]
        ts = pd.to_datetime(df["last_seen"], errors="coerce", utc=True)
        age_min = (pd.Timestamp.utcnow().tz_localize("UTC") - ts).dt.total_seconds() / 60.0
        df["age_min"] = age_min
        out = df[age_min > float(threshold_minutes)].sort_values("age_min", ascending=False)
        return out

    def movement_stats(self) -> Dict[str, pd.DataFrame]:
        log = self.moves_repo.read()
        if log.empty:
            empty = pd.DataFrame(columns=["equip_id", "moves"])
            return {"moves_per_equipment": empty, "routes": pd.DataFrame(columns=["from", "to", "count"])}
        per_eq = (
            log.groupby("equip_id")
            .size()
            .reset_index(name="moves")
            .sort_values("moves", ascending=False)
        )
        routes = (
            log.groupby(["from", "to"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        return {"moves_per_equipment": per_eq, "routes": routes}

    # ---- SOPs ----

    def sop_table(self) -> pd.DataFrame:
        return self.sop_registry.read()

    def search_sop(self, query: str) -> pd.DataFrame:
        q = (query or "").strip().lower()
        df = self.sop_registry.read().copy()
        if df.empty or not q:
            return df
        cols = [c for c in ["sop_id", "title", "keywords", "version", "status"] if c in df.columns]
        mask = df[cols].astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        return df[mask]

    # ---- QR passthrough ----

    def make_qr(self, payload: str) -> str:
        return self.qr.make(payload)

    def decode_qr_bytes(self, image_bytes: bytes) -> Optional[str]:
        return self.qr.decode_file(image_bytes)


# End of module
