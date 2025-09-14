
"""
phase2_bridge.py
Optional integration hooks for ICU constraints, agent mesh, and trainer loops.
All imports are lazy and only attempted when RUN_PIPELINE=True.
No side effects on import.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
import importlib

def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None

def icu_constraints_available() -> bool:
    # expected names you might promote to proper modules later
    return any(_try_import(n) for n in [
        "icu_constraints",
        "modeling_icu_constraints",  # pythonized name of your notebook
    ])

def agent_mesh_available() -> bool:
    return any(_try_import(n) for n in [
        "agent_mesh",
        "ed_agent_mesh",
    ])

def trainer_available() -> bool:
    return any(_try_import(n) for n in [
        "trainer",
        "ed_trainer",
    ])

def run_icu_constraints(state: Any) -> Dict[str, Any]:
    """
    Returns a dict of ICU-related signals to merge into WorkflowState.feature_dict().
    If no ICU module is found, returns {}.
    """
    mod = _try_import("icu_constraints") or _try_import("modeling_icu_constraints")
    if not mod:
        return {}
    # Expected contract (customize when you promote the notebook code to a module):
    # mod.compute_icu_flags(state) -> dict
    if hasattr(mod, "compute_icu_flags"):
        try:
            return dict(mod.compute_icu_flags(state))
        except Exception:
            return {}
    return {}

def mesh_route_actions(state: Any, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Optionally route/annotate actions via agent mesh. Returns possibly reordered/annotated list.
    """
    mod = _try_import("agent_mesh") or _try_import("ed_agent_mesh")
    if not mod:
        return actions
    if hasattr(mod, "route"):
        try:
            return list(mod.route(state, actions))
        except Exception:
            return actions
    return actions

def trainer_fit_critic(critic: Any, samples: List[Dict[str, Any]], y) -> Any:
    """
    Optionally fit critic with trainer pipeline. If unavailable, returns critic unchanged.
    """
    mod = _try_import("trainer") or _try_import("ed_trainer")
    if not mod:
        return critic
    if hasattr(mod, "fit_critic"):
        try:
            return mod.fit_critic(critic, samples, y)
        except Exception:
            return critic
    return critic
