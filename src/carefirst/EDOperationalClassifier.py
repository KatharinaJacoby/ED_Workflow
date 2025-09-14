
"""
EDOperationalClassifier (add-on)
- No import-time side effects
- SafeDictVectorizer avoids sklearn.feature_extraction to survive version pinning
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# --- Public API ---
__all__ = [
    "ED_STATES",
    "OperationalAdjustments",
    "default_operational_profiles",
    "SafeDictVectorizer",
    "EDOperationalClassifier",
]

# --- State labels ---
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

def default_operational_profiles() -> Dict[str, OperationalAdjustments]:
    return {
        "Normal_Flow": OperationalAdjustments(1.0,1.0,{"imaging":0.33,"lab":0.33,"bed":0.34},1.0,1.0),
        "High_Volume": OperationalAdjustments(1.1,1.1,{"imaging":0.28,"lab":0.27,"bed":0.45},0.95,1.05),
        "Resource_Constrained": OperationalAdjustments(1.15,1.05,{"imaging":0.25,"lab":0.25,"bed":0.50},0.9,1.1),
        "Critical_Surge": OperationalAdjustments(1.3,1.25,{"imaging":0.2,"lab":0.2,"bed":0.6},0.85,1.15),
        "Night_Shift": OperationalAdjustments(1.05,0.95,{"imaging":0.3,"lab":0.25,"bed":0.45},1.05,1.0),
        "Flu_Season": OperationalAdjustments(1.1,1.0,{"imaging":0.25,"lab":0.35,"bed":0.40},0.95,1.1),
    }

class SafeDictVectorizer:
    """Minimal DictVectorizer: numeric-only, missing keys -> 0.0; stable key order."""
    def __init__(self):
        self.feature_names_ = None

    def fit(self, X: List[Dict[str, Any]], y=None):
        keys = set()
        for d in X:
            keys.update(d.keys())
        self.feature_names_ = sorted(keys)
        return self

    def transform(self, X: List[Dict[str, Any]]):
        if self.feature_names_ is None:
            raise RuntimeError("SafeDictVectorizer used before fit")
        out = np.zeros((len(X), len(self.feature_names_)), dtype=float)
        for i, d in enumerate(X):
            for j, k in enumerate(self.feature_names_):
                out[i, j] = float(d.get(k, 0.0) or 0.0)
        return out

    def fit_transform(self, X, y=None):
        return self.fit(X, y).transform(X)

    # sklearn API nicety
    def get_feature_names_out(self):
        return np.array(self.feature_names_, dtype=object)

class EDOperationalClassifier:
    """
    MLP-based classifier for ED operational state -> adjustment factors.
    Cold-start safe: if unfitted, predict_* returns Normal_Flow with uniform probabilities.
    """
    def __init__(self):
        self.operational_profiles = default_operational_profiles()
        self.pipeline = Pipeline([
            ("vect", SafeDictVectorizer()),
            ("scaler", StandardScaler()),
            ("mlp", MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                random_state=42,
                max_iter=500,
                early_stopping=True
            ))
        ])
        self._is_fitted = False

    # --- Supervised API ---
    def fit(self, feature_dicts: List[Dict[str, Any]], labels: List[str]):
        self.pipeline.fit(feature_dicts, labels)
        self._is_fitted = True
        return self

    # --- Inference ---
    def predict_proba(self, feature_dicts: List[Dict[str, Any]]):
        if not self._is_fitted:
            return np.tile(np.array([1.0/len(ED_STATES)]*len(ED_STATES)), (len(feature_dicts),1))
        return self.pipeline.predict_proba(feature_dicts)

    def predict_state(self, feature_dicts: List[Dict[str, Any]]):
        if not self._is_fitted:
            return ["Normal_Flow"] * len(feature_dicts)
        return self.pipeline.predict(feature_dicts)

    def get_adjustments(self, feature_dict: Dict[str, Any]):
        probs = self.predict_proba([feature_dict])[0]
        if not self._is_fitted:
            return "Normal_Flow", probs, self.operational_profiles["Normal_Flow"]
        classes = list(self.pipeline.named_steps["mlp"].classes_)
        max_idx = int(np.argmax(probs))
        state = classes[max_idx] if classes else "Normal_Flow"
        return state, probs, self.operational_profiles[state]

    # --- Persistence ---
    def save(self, path: str):
        joblib.dump({
            "pipeline": self.pipeline,
            "profiles": self.operational_profiles,
            "states": ED_STATES
        }, path)

    @staticmethod
    def load(path: str) -> "EDOperationalClassifier":
        blob = joblib.load(path)
        clf = EDOperationalClassifier()
        clf.pipeline = blob["pipeline"]
        clf.operational_profiles = blob["profiles"]
        clf._is_fitted = True
        return clf
