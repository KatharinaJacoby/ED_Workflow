
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Callable
import pandas as pd
import numpy as np

def run_ui(tracker, get_state: Callable[[], Any], get_actions: Callable[[Any], List[Dict[str, Any]]], critic: Any) -> None:
    import streamlit as st

    st.set_page_config(page_title="ED Core Tracker", layout="wide")
    st.title("ED Core Tracker (Equipment • QR • SOP • Actions)")

    # --- Equipment ---
    st.header("Equipment")
    eq_df = tracker.equipment_status()
    q = st.text_input("Search (ID / name / location)", "")
    if q:
        ql = q.lower()
        def _hit(row):
            return any(ql in str(row.get(k,"")).lower() for k in ["equip_id","name","location","status"])
        eq_df = eq_df[eq_df.apply(_hit, axis=1)]
    st.dataframe(eq_df, use_container_width=True, height=260)

    c1, c2, c3, c4 = st.columns([2,2,2,1])
    with c1:
        equip_id = st.text_input("Equip ID", "")
    with c2:
        loc_from = st.text_input("From", "")
    with c3:
        loc_to = st.text_input("To", "")
    with c4:
        if st.button("Log move"):
            if equip_id and loc_to:
                tracker.log_move(equip_id, loc_from, loc_to)
                st.success(f"Move logged: {equip_id} → {loc_to}")

    # --- QR ---
    st.header("QR generator")
    payload = st.text_input("QR payload", "")
    if st.button("Generate QR") and payload:
        path = tracker.make_qr(payload)
        st.write("QR output:", path)

    # --- SOP ---
    st.header("SOP Registry")
    sop_df = tracker.sop_table()
    if not sop_df.empty:
        st.dataframe(sop_df, use_container_width=True, height=240)
    else:
        st.info("No SOP entries found.")

    # --- Actions + Critic ---
    st.header("Actions & Critic")
    state = get_state()
    actions = get_actions(state)
    if not actions:
        st.info("No actions available.")
        return

    p, b, u = tracker.score_actions(state, actions, critic)
    view = pd.DataFrame({
        "id": [a.get("id") for a in actions],
        "label": [a.get("label") for a in actions],
        "p_accept": np.round(p, 3),
        "benefit": np.round(b, 3),
        "burden": np.round(u, 3),
    }).sort_values(["p_accept","benefit"], ascending=[False, False])
    st.dataframe(view, use_container_width=True, height=240)
