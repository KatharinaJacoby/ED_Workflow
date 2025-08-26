
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Callable
import pandas as pd
import numpy as np

def run_ui(tracker, get_state: Callable[[], Any], get_actions: Callable[[Any], List[Dict[str, Any]]], critic: Any) -> None:
    import streamlit as st
    import io

    st.set_page_config(page_title="ED Tracker", layout="wide")
    st.title("ED Tracker — Core Ops")

    # --- Controls / refresh ---
    c0, c1, c2, c3 = st.columns([2,2,2,2])
    with c0:
        thresh = st.number_input("Overdue threshold (min)", min_value=5, max_value=720, value=120, step=5)
    with c1:
        if st.button("Refresh"):
            st.experimental_rerun()
    with c2:
        st.caption(f"Data root: {tracker.CONFIG['DATA_ROOT'] if isinstance(tracker.CONFIG, dict) else 'N/A'}")

    # --- Equipment panel ---
    st.header("Equipment")
    eq_df = tracker.equipment_status()
    s1, s2 = st.columns([2,1])
    with s1:
        q = st.text_input("Find equipment (ID / name / location / status)", "")
        filt = tracker.find_equipment(q) if q else eq_df
        st.dataframe(filt, use_container_width=True, height=260)
    with s2:
        overdue = tracker.overdue_equipment(int(thresh))
        st.subheader("Overdue")
        if overdue.empty:
            st.write("None")
        else:
            st.dataframe(overdue[["equip_id","name","location","last_seen","age_min"]], use_container_width=True, height=200)

    # Move logger
    st.markdown("**Update location / log move**")
    mc1, mc2, mc3, mc4 = st.columns([2,2,2,1])
    with mc1:
        sel_id = st.selectbox("Equipment ID", [""] + sorted(list(eq_df.get("equip_id", []))))
    with mc2:
        loc_from = st.text_input("From", "")
    with mc3:
        loc_to = st.text_input("To", "")
    with mc4:
        if st.button("Log move") and sel_id and loc_to:
            tracker.log_move(sel_id, loc_from, loc_to)
            st.success(f"Move logged: {sel_id} → {loc_to}")

    # --- QR panel (generate + scan-to-update) ---
    st.header("QR")
    qr_col1, qr_col2 = st.columns([2,2])
    with qr_col1:
        qr_txt = st.text_input("QR payload to generate", "")
        if st.button("Generate QR") and qr_txt:
            path = tracker.make_qr(qr_txt)
            st.write("QR saved to:", path)
    with qr_col2:
        st.write("Scan and update location")
        f = st.file_uploader("Upload QR image", type=["png","jpg","jpeg","webp"])
        manual_payload = st.text_input("Manual payload (fallback if decoding fails)", "")
        new_loc = st.text_input("New location (after scan)", "")
        if st.button("Scan & Update"):
            equip_payload = None
            if f is not None:
                equip_payload = tracker.decode_qr_bytes(f.read())
            if not equip_payload and manual_payload:
                equip_payload = manual_payload
            if equip_payload and new_loc:
                equip_id = equip_payload
                if "id=" in equip_payload:
                    try:
                        equip_id = equip_payload.split("id=",1)[1].split("&",1)[0]
                    except Exception:
                        equip_id = equip_payload
                tracker.log_move(str(equip_id), "", new_loc)
                st.success(f"Updated via payload. {equip_id} → {new_loc}")
            elif not new_loc:
                st.error("Provide a new location.")
            else:
                st.error("No QR payload detected (image or manual).")

    # --- SOP registry + search ---
    
# --- SOP auto-pull + flows ---
with st.expander("SOP auto-pull and flows", expanded=False):
    import sop_auto
    if st.button("Refresh SOPs from sop-notaufnahme.de"):
        res = sop_auto.refresh_sop_registry(tracker.CONFIG, base_url="https://sop-notaufnahme.de/sop/")
        st.write(res)
    # Flow display
    flows = sop_auto.load_priority_flows("/mnt/data/priority_flows.json")
    if flows:
        keys = sorted(list(flows.keys()))
        pickf = st.selectbox("Show flow", [""] + keys)
        if pickf:
            flow = flows[pickf]
            st.subheader(flow.get("title", pickf))
            # show nodes and edges
            nodes = flow.get("nodes", []); edges = flow.get("edges", [])
            st.write("Nodes:", ", ".join([n.get("label", n.get("id","")) for n in nodes]))
            # simple matplotlib graph if available
            try:
                import matplotlib.pyplot as plt
                fig = plt.figure()
                pos = {n["id"]:(i, 0) for i,n in enumerate(nodes)}
                for n in nodes:
                    x,y = pos[n["id"]]
                    plt.scatter([x],[y])
                    plt.text(x, y+0.05, n.get("label", n["id"]), ha="center", rotation=45)
                for a,b in edges:
                    xa,ya = pos.get(a,(0,0)); xb,yb = pos.get(b,(0,0))
                    plt.plot([xa,xb],[ya,yb])
                plt.axis("off"); plt.title(flow.get("title", pickf))
                st.pyplot(fig)
            except Exception:
                st.info("Graph display unavailable; showing list instead.")
                st.write(edges)

    st.header("SOPs")
    sop_q = st.text_input("Search SOPs (id/title/keywords)", "")
    sop_hits = tracker.search_sop(sop_q)
    if sop_hits.empty:
        st.info("No SOPs found.")
    else:
        st.dataframe(sop_hits[["sop_id","title","version","status"]], use_container_width=True, height=220)
        pick = st.selectbox("Open SOP", [""] + sop_hits["sop_id"].astype(str).tolist())
        if pick:
            row = sop_hits[sop_hits["sop_id"].astype(str)==pick].iloc[0]
            pdf = row.get("pdf_path","")
            if pdf:
                st.write("PDF path:", pdf)
            # Checklist support if column exists (pipe-separated)
            if "checklist" in sop_hits.columns and isinstance(row.get("checklist", None), str) and row["checklist"].strip():
                st.subheader("Checklist")
                steps = [s.strip() for s in row["checklist"].split("|") if s.strip()]
                completed = []
                for i, step in enumerate(steps, 1):
                    if st.checkbox(f"{i}. {step}", key=f"sop_{pick}_{i}"):
                        completed.append(i)
                st.caption(f"Completed {len(completed)}/{len(steps)} steps")

    # --- Actions & Critic ---
    st.header("Actions & Critic")
    state = get_state()
    # Lingering patient alert (uses WorkflowState fields if present)
    linger_thresh = thresh  # reuse UI input
    if hasattr(state, "feature_dict"):
        feats = state.feature_dict()
        since_v = feats.get("since_vitals_min", None)
        if since_v is not None:
            if since_v > linger_thresh:
                st.error(f"Lingering patient: since_vitals_min={since_v:.0f} > {linger_thresh}")
            else:
                st.success(f"Vitals recently checked: {since_v:.0f} min")
    if st.button("Mark vitals now") and hasattr(state, "touch_now"):
        state.touch_now(pd.Timestamp.utcnow())
        st.success("Vitals timestamp updated.")
    actions = get_actions(state)
    if not actions:
        st.info("No actions available.")
        return
    p, benefit, burden = critic.score(state, actions)
    view = pd.DataFrame({
        "id": [a.get("id") for a in actions],
        "label": [a.get("label") for a in actions],
        "p_accept": np.round(p, 3),
        "benefit": np.round(benefit, 3),
        "burden": np.round(burden, 3),
    }).sort_values(["p_accept","benefit"], ascending=[False, False])
    st.dataframe(view, use_container_width=True, height=240)

    # --- Analytics panel ---
    st.header("Equipment Movement Analytics")
    stats = tracker.movement_stats()
    per_eq = stats["moves_per_equipment"]
    routes = stats["routes"]
    if per_eq.empty:
        st.info("No movement data yet.")
    else:
        st.subheader("Moves per equipment")
        st.dataframe(per_eq, use_container_width=True, height=240)
        try:
            import matplotlib.pyplot as plt
            fig = plt.figure()
            x = per_eq["equip_id"].astype(str).tolist()
            y = per_eq["moves"].tolist()
            plt.bar(x, y)
            plt.xticks(rotation=45, ha="right")
            plt.title("Moves per Equipment")
            st.pyplot(fig)
        except Exception:
            pass
        st.subheader("Top routes")
        st.dataframe(routes, use_container_width=True, height=200)
