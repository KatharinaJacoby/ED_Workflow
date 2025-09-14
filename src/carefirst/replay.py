
from __future__ import annotations
import argparse, json, numpy as np, torch
from typing import Dict, Any
from .config import load_config
from .actions import ActionSpace
from .heads import make_action_head
from .calibrate import TempScaler
from .gate import GateConfig, gate_predictions
from .policy import apply_policy
from .bridge import BridgeAdapter
from .metrics import SLARecorder, safety_utility
from .xai import shallow_attributions
from .audit import AuditLog, export_anchor
from .policy_tests import detect_duplicate_orders, detect_contradictions, stale_capacity_violation
from .notifier import Notifier

def run_replay(cfg_path: str, events_path: str, model_path: str, out_path: str, audit_path: str=None):
    cfg = load_config(cfg_path)
    actions = ActionSpace(cfg.actions)
    sla = SLARecorder()
    audit = AuditLog(audit_path) if audit_path else None
    notifier = Notifier()
    events = [json.loads(line) for line in open(events_path)]
    X = np.array([e["features"] for e in events], dtype=float)
    X = torch.tensor(X, dtype=torch.float32).unsqueeze(1)
    model = make_action_head(input_dim=X.shape[-1], num_actions=len(actions), cfg=cfg.__dict__)
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    logits = model(X)
    T = cfg.temperature
    logits = logits / max(T, 1e-6)
    probs = torch.softmax(logits, dim=-1).detach().cpu().numpy()
    gcfg = GateConfig(tau=cfg.gate.get("tau",0.5),
                      per_class={int(k):float(v) for k,v in cfg.thresholds.items()},
                      top_k=int(cfg.gate.get("top_k",1)))
    pred, info = gate_predictions(probs, gcfg)
    action_msgs = apply_policy(pred, probs, {"cap_stale": False, "approval": {"ORDER_CT": False}, "uncertainty": None},
                               [s.__dict__ for s in actions.specs])
    bridge = BridgeAdapter(system="json")
    feature_names = cfg.features
    atts = shallow_attributions(model=lambda x: model(x), temp=lambda z: z/ max(cfg.temperature,1e-6), xb=X, feature_names=feature_names, top_k=5)
    out = []
    for i, m in enumerate(action_msgs):
        msg = bridge.to_message(m)
        msg['xai_top_features'] = atts[i]
        out.append(msg)
        if audit:
            audit.append({'event_id': i, 'action': m, 'message': msg})
    sla.add_sample()
    sla.mark_duplicate_blocked(detect_duplicate_orders(out))
    sla.mark_contradiction_blocked(detect_contradictions(out))
out = [bridge.to_message(m) for m in action_msgs]
    with open(out_path, "w") as f:
        for rec in out: f.write(json.dumps(rec) + "\n")
    if audit:
        anchor = export_anchor(audit_path, audit_path+'.anchor.json')
        print('Anchor:', anchor)
    print('SLA summary:', json.dumps(sla.summary()))
    print(f"Wrote {len(out)} messages ->", out_path)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out",    required=True)
    args = ap.parse_args()
    run_replay(args.config, args.events, args.model, args.out)
