
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import torch
import numpy as np

def shallow_attributions(model: torch.nn.Module,
                         temp,
                         xb: torch.Tensor,
                         feature_names: List[str],
                         top_k: int = 5) -> List[List[Tuple[str, float]]]:
    model.eval()
    xb = xb.clone().detach().requires_grad_(True)
    logits = model(xb)
    if isinstance(logits, (tuple, list)):
        logits = logits[0]
    logits = temp(logits)
    pred = logits.argmax(dim=1)
    grads_all = []
    for i in range(xb.size(0)):
        model.zero_grad(set_to_none=True)
        xb.grad = None
        logits[i, pred[i]].backward(retain_graph=True)
        g = xb.grad[i]
        sal = g.abs().sum(dim=0).detach().cpu().numpy()
        grads_all.append(sal)
    out = []
    for sal in grads_all:
        idx = np.argsort(-sal)[:min(top_k, len(sal))]
        out.append([(feature_names[j], float(sal[j])) for j in idx])
    return out
