
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import torch, torch.nn as nn, torch.nn.functional as F

class Backbone(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:  # [B, T, D] -> [B, H]
        raise NotImplementedError

class GRUBackbone(Backbone):
    def __init__(self, input_dim: int, hidden: int=64, dropout: float=0.3):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden, num_layers=1, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.hidden = hidden
    def forward(self, x):
        out, _ = self.gru(x)   # [B,T,H]
        return self.drop(out[:,-1,:])  # [B,H]

class UnifiedHead(nn.Module):
    def __init__(self, emb_dim: int, num_actions: int):
        super().__init__()
        self.fc = nn.Linear(emb_dim, num_actions)
    def forward(self, h):  # [B,H] -> [B,K]
        return self.fc(h)

class MultiHeadActions(nn.Module):
    def __init__(self, emb_dim: int, num_actions: int):
        super().__init__()
        self.heads = nn.ModuleList([nn.Linear(emb_dim, 1) for _ in range(num_actions)])
    def forward(self, h):  # [B,H] -> [B,K]
        logits = [head(h) for head in self.heads]
        return torch.cat(logits, dim=1)  # [B,K]

class ActionHead(nn.Module):
    def __init__(self, backbone: Backbone, head_type: str, num_actions: int):
        super().__init__()
        self.backbone = backbone
        self.num_actions = num_actions
        if head_type == "multi":
            self.classifier = MultiHeadActions(backbone.hidden, num_actions)
        else:
            self.classifier = UnifiedHead(backbone.hidden, num_actions)
    def forward(self, x):  # [B,T,D] -> logits [B,K]
        h = self.backbone(x)
        logits = self.classifier(h)
        return logits

def make_action_head(input_dim: int, num_actions: int, cfg: Dict[str,Any]) -> ActionHead:
    bb = GRUBackbone(input_dim, hidden=cfg.get("backbone",{}).get("hidden",64),
                     dropout=cfg.get("backbone",{}).get("dropout",0.3))
    head_type = cfg.get("head",{}).get("type","unified")
    return ActionHead(bb, head_type=head_type, num_actions=num_actions)
