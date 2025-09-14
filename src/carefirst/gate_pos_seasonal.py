
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from gate_pos import GatePos, WorkflowState

@dataclass
class SeasonalityManager:
    """Map timestamps to season labels via week-of-year windows.
    windows example: {"winter": (48, 8)}  # wraps year-end
    """
    windows: Dict[str, Tuple[int,int]] = field(default_factory=dict)

    @staticmethod
    def _wk(ts: pd.Timestamp) -> int:
        wk = int(pd.Timestamp(ts).isocalendar().week)
        return 52 if wk == 53 else wk

    @staticmethod
    def _in_window(week: int, start: int, end: int) -> bool:
        if start <= end:
            return start <= week <= end
        return (week >= start) or (week <= end)

    def season_label(self, ts: pd.Timestamp) -> str:
        wk = self._wk(ts)
        for name, (start, end) in self.windows.items():
            if self._in_window(wk, int(start), int(end)):
                return name
        return "base"

class SeasonAwareGatePos(GatePos):
    """GatePos variant with season-aware calibrators.
    Key format: "<daypart>_<weekday>@season:<label>", fallback to non-seasonal then defaults.
    """
    def __init__(self, *args, seasonality: Optional[SeasonalityManager] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.seasonality = seasonality or SeasonalityManager({})

    def _day_key(self, ts: pd.Timestamp) -> str:
        ts = pd.Timestamp(ts)
        weekday = "weekday" if ts.dayofweek < 5 else "weekend"
        daynight = "day" if 7 <= ts.hour < 19 else "night"
        season = self.seasonality.season_label(ts)
        return f"{daynight}_{weekday}@season:{season}"

    def _get_cuts(self, ts: pd.Timestamp, kind: str, default_cuts: List[float]) -> List[float]:
        key_season = self._day_key(ts)
        base_key = key_season.split("@season:")[0]
        cuts = self.calibrators.get(key_season, {}).get(kind)
        if cuts is not None and len(cuts) == 3:
            return list(cuts)
        cuts = self.calibrators.get(base_key, {}).get(kind)
        if cuts is not None and len(cuts) == 3:
            return list(cuts)
        return list(default_cuts)

    def _ordinal_T2_readiness(self, ts: pd.Timestamp, f: Dict[str,Any]):
        default_cuts = [30, 60, 120]
        cuts = self._get_cuts(ts, "T2", default_cuts)
        x = 0.5 + 0.5*min(1.0, f.get("timer__since_vitals_min",0)/120.0) - 0.1*f.get("n_alerts",0)
        logits = [x - 0.2, x, x + 0.2]
        cp = [1/(1+np.exp(-z)) for z in logits]
        p = [max(0.0, min(1.0, cp[0])),
             max(0.0, min(1.0, cp[1]-cp[0])),
             max(0.0, min(1.0, cp[2]-cp[1])),
             1.0 - max(0.0, min(1.0, cp[2]))]
        s = sum(p); p = [float(pi/s) for pi in p]
        labels = [f"<= {cuts[0]}m", f"{cuts[0]}-{cuts[1]}m", f"{cuts[1]}-{cuts[2]}m", f">{cuts[2]}m"]
        return labels, p

    def _ordinal_T4_ready_time(self, ts: pd.Timestamp, f: Dict[str,Any]):
        default_cuts = [60, 120, 240]
        cuts = self._get_cuts(ts, "T4", default_cuts)
        x = 0.4 + 0.6*min(1.0, f.get("timer__since_vitals_min",0)/240.0) - 0.1*f.get("n_alerts",0)
        logits = [x - 0.2, x, x + 0.2]
        cp = [1/(1+np.exp(-z)) for z in logits]
        p = [max(0.0, min(1.0, cp[0])),
             max(0.0, min(1.0, cp[1]-cp[0])),
             max(0.0, min(1.0, cp[2]-cp[1])),
             1.0 - max(0.0, min(1.0, cp[2]))]
        s = sum(p); p = [float(pi/s) for pi in p]
        labels = [f"<= {cuts[0]}m", f"{cuts[0]}-{cuts[1]}m", f"{cuts[1]}-{cuts[2]}m", f">{cuts[2]}m"]
        return labels, p
