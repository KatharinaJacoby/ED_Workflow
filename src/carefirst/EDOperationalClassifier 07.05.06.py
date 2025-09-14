
# EDOperationalClassifier.py — add-only operational state classifier
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
import joblib

ED_STATES = [
    "Normal_Flow",
    "High_Volume",
    "Resource_Constrained",
    "Critical_Surge",
    "Night_Shift",
    "Flu_Season",
]

@dataclass
class OperationalAdjustments:
    triage_urgency_multiplier: float
    handoff_timing_factor: float
    resource_allocation_weights: Dict[str, float]
    communication_urgency_threshold: float
    discharge_readiness_threshold: float

def _default_operational_profiles() -> Dict[str, OperationalAdjustments]:
    return {
        "Normal_Flow": OperationalAdjustments(1.0, 1.0, {"imaging":1.0,"lab":1.0,"bed":1.0}, 0.5, 0.5),
        "High_Volume": OperationalAdjustments(1.1, 1.1, {"imaging":1.0,"lab":1.1,"bed":1.1}, 0.55, 0.48),
        "Resource_Constrained": OperationalAdjustments(1.15, 1.2, {"imaging":0.9,"lab":1.1,"bed":1.2}, 0.6, 0.45),
        "Critical_Surge": OperationalAdjustments(1.3, 1.4, {"imaging":0.8,"lab":1.2,"bed":1.4}, 0.7, 0.4),
        "Night_Shift": OperationalAdjustments(1.05, 1.1, {"imaging":0.9,"lab":1.0,"bed":1.05}, 0.52, 0.5),
        "Flu_Season": OperationalAdjustments(1.1, 1.05, {"imaging":1.0,"lab":1.1,"bed":1.1}, 0.58, 0.47),
    }

class _FeatureSpace:
    def __init__(self, feature_names: Optional[List[str]] = None):
        self.feature_names = feature_names or []
    def fit(self, rows: List[Dict[str, Any]]):
        keys = set()
        for r in rows:
            for k,v in (r or {}).items():
                if isinstance(v, (int,float,bool)) and np.isfinite(float(v)):
                    keys.add(k)
        self.feature_names = sorted(keys); return self
    def transform_one(self, r: Dict[str, Any]):
        out = []
        for k in self.feature_names:
            v = r.get(k, 0.0)
            try: out.append(float(v))
            except Exception: out.append(0.0)
        return np.asarray(out, dtype=float)
    def transform(self, rows: List[Dict[str, Any]]):
        return np.vstack([self.transform_one(r) for r in rows])

class EDOperationalClassifier:
    def __init__(self, hidden_layers: Tuple[int,int]=(64,32), random_state: int = 42):
        self.feature_space = _FeatureSpace()
        self.scaler = StandardScaler()
        self.clf = MLPClassifier(hidden_layer_sizes=hidden_layers, random_state=random_state, max_iter=300)
        self.le = LabelEncoder()
        self.operational_profiles = _default_operational_profiles()
        self.pipeline = Pipeline([("scaler", self.scaler), ("mlp", self.clf)])
        self._fitted = False
    def fit(self, X_dicts: List[Dict[str, Any]], y_labels: List[str]):
        assert len(X_dicts) == len(y_labels) and len(X_dicts) > 0, "Training data is empty/misaligned."
        self.feature_space.fit(X_dicts)
        X = self.feature_space.transform(X_dicts)
        y = self.le.fit_transform([str(y) for y in y_labels])
        self.pipeline.fit(X, y); self._fitted = True; return self
    def predict_proba(self, X_dicts: List[Dict[str, Any]]):
        if not self._fitted:
            n = len(ED_STATES); return np.tile(np.full(n, 1.0/n, dtype=float), (len(X_dicts),1))
        X = self.feature_space.transform(X_dicts)
        proba = self.pipeline.predict_proba(X)
        aligned = np.zeros((proba.shape[0], len(ED_STATES)), dtype=float)
        idx_map = {lbl:i for i,lbl in enumerate(self.le.classes_)}
        for j, state in enumerate(ED_STATES):
            aligned[:, j] = proba[:, idx_map[state]] if state in idx_map else 0.0
        return aligned
    def predict_state(self, X_dict: Dict[str, Any]):
        probs = self.predict_proba([X_dict])[0]; j = int(np.argmax(probs)); label = ED_STATES[j]
        return label, {s: float(p) for s,p in zip(ED_STATES, probs)}
    def get_adjustments(self, X_dict: Dict[str, Any]):
        label, prob_map = self.predict_state(X_dict)
        adj = self.operational_profiles.get(label, _default_operational_profiles()["Normal_Flow"])
        adj_dict = {
            "triage_urgency_multiplier": float(adj.triage_urgency_multiplier),
            "handoff_timing_factor": float(adj.handoff_timing_factor),
            "resource_allocation_weights": dict(adj.resource_allocation_weights),
            "communication_urgency_threshold": float(adj.communication_urgency_threshold),
            "discharge_readiness_threshold": float(adj.discharge_readiness_threshold),
        }
        return label, prob_map, adj_dict
    def save(self, path: str):
        import joblib
        payload = {
            "pipeline": self.pipeline,
            "feature_names": self.feature_space.feature_names,
            "label_encoder": self.le,
            "operational_profiles": self.operational_profiles,
        }
        joblib.dump(payload, path); return path
    @classmethod
    def load(cls, path: str) -> "EDOperationalClassifier":
        import joblib
        payload = joblib.load(path)
        obj = cls()
        obj.pipeline = payload["pipeline"]
        obj.clf = obj.pipeline.named_steps["mlp"]
        obj.scaler = obj.pipeline.named_steps["scaler"]
        obj.feature_space.feature_names = payload["feature_names"]
        obj.le = payload["label_encoder"]
        obj.operational_profiles = payload.get("operational_profiles", _default_operational_profiles())
        obj._fitted = True; return obj
