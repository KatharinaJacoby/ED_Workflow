
from __future__ import annotations
import torch, torch.nn as nn, torch.nn.functional as F

class TempScaler(nn.Module):
    def __init__(self): super().__init__(); self.logT = nn.Parameter(torch.zeros(1))
    def forward(self, logits): return logits / (torch.exp(self.logT) + 1e-6)

@torch.no_grad()
def fit_temperature(model: nn.Module, logits: torch.Tensor, targets: torch.Tensor, max_iter=200):
    model.eval()
    ts = TempScaler()
    nll = nn.CrossEntropyLoss()
    opt = torch.optim.LBFGS(ts.parameters(), lr=0.05, max_iter=max_iter, line_search_fn="strong_wolfe")
    def closure():
        opt.zero_grad()
        loss = nll(ts(logits), targets)
        loss.backward()
        return loss
    opt.step(closure)
    return ts
