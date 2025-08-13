
from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

def safety_utility(y_true, y_pred, fp_cost=1.0, fn_cost=5.0) -> float:
    y_true = np.asarray(y_true); y_pred = np.asarray(y_pred)
    return (- fp_cost * np.sum((y_pred != y_true) & (y_true == 0))
            - fn_cost * np.sum((y_pred != y_true) & (y_true != 0))) / len(y_true)

def compute_confusion(y_true, y_pred, K: int) -> Dict[str,Any]:
    cm = confusion_matrix(y_true, y_pred, labels=list(range(K)))
    prf = precision_recall_fscore_support(y_true, y_pred, labels=list(range(K)), zero_division=0)
    return {"cm": cm.tolist(), "precision": prf[0].tolist(), "recall": prf[1].tolist(), "f1": prf[2].tolist()}
