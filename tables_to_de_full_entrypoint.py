
import pandas as pd
import numpy as np
from datetime import timedelta

REQUIRED_COLUMNS = [
    "Tag","t_min","Triage","Leitsymptom","HF","MAP","ICU_Kap","Kap_veraltet",
    "t_norm","hat_Labor","Labor_ausstehend","hat_Roentgen","Roentgen_ausstehend",
    "hat_CT","CT_ausstehend","naechste_Aktion","Gate_Pos"
]

def tables_to_de_full(
    tables: dict,
    *,
    coding_maps: dict,
    prevalence_target: float,
    tag_strategy: str = "zero",   # "zero" (all 0) or "day_index"
    normalize_t_norm_by: int = 1440,  # minutes in a day
    gate_pos_policy: str = "require", # "require" | "sample_prevalence" | "from_function"
    gate_pos_fn = None,               # if gate_pos_policy == "from_function", callable(row_df)->Series of 0/1
) -> pd.DataFrame:
    """
    Convert synthetic ED generator tables into the 16-feature + Gate_Pos frame used by your model.

    Parameters
    ----------
    tables : dict[str, pd.DataFrame]
        Expected keys: at least {'encounters','events'}; optionally {'orders','results'} for imaging/lab flags.
        'encounters' must include: ['enc_id','arrival_ts','triage_system','triage_level','complaint_group']
        'events' must include: ['enc_id','t','triage','complaint','hr','map','cap_icu','capacity_stale','action']
        'orders'/'results' (optional) include ['enc_id','code','ts_placed'] / ['enc_id','code','ts_result']
    coding_maps : dict
        Required keys (no guessing; this raises if missing):
          - 'complaint_to_code': dict[str,int]  # complaint_group -> Leitsymptom integer code
          - 'action_to_code': dict[str,int]     # action string -> naechste_Aktion integer code
        Optional keys:
          - 'lab_code_prefixes': list[str]      # e.g., ['TROPONIN','LAC','CRP']
          - 'xray_code_prefixes': list[str]     # e.g., ['CXR']
          - 'ct_code_prefixes': list[str]       # e.g., ['CT']
    prevalence_target : float
        Desired Gate_Pos prevalence for the output (Bernoulli sampling if gate_pos_policy == "sample_prevalence").
    tag_strategy : str
        "zero": Tag = 0 for all rows (single-day generation). "day_index": Tag = (arrival date - min date) in days.
    normalize_t_norm_by : int
        Denominator for t_norm; defaults to 1440 (minutes/day).
    gate_pos_policy : str
        "require" (hard fail unless derived elsewhere), "sample_prevalence" (Bernoulli(p=prevalence_target) per row),
        or "from_function" (call gate_pos_fn).
    gate_pos_fn : callable
        If provided and gate_pos_policy == "from_function", should map the assembled DataFrame to a 0/1 Series.

    Returns
    -------
    DataFrame with columns REQUIRED_COLUMNS in this exact order.
    """
    # --- Validate required tables ---
    for key in ["encounters","events"]:
        if key not in tables:
            raise ValueError(f"Missing required table '{key}' in input. Keys present: {list(tables.keys())}")

    enc = tables["encounters"].copy()
    ev  = tables["events"].copy()

    # --- Validate required columns ---
    req_enc = {"enc_id","arrival_ts","triage_level","complaint_group"}
    req_ev  = {"enc_id","t","triage","hr","map","cap_icu","capacity_stale","action"}
    if not req_enc.issubset(enc.columns):
        raise ValueError(f"'encounters' missing columns: {sorted(list(req_enc - set(enc.columns)))}")
    if not req_ev.issubset(ev.columns):
        raise ValueError(f"'events' missing columns: {sorted(list(req_ev - set(ev.columns)))}")

    # Ensure dtypes for times
    if not np.issubdtype(enc["arrival_ts"].dtype, np.datetime64):
        try:
            enc["arrival_ts"] = pd.to_datetime(enc["arrival_ts"])
        except Exception as e:
            raise ValueError(f"Failed to parse encounters.arrival_ts to datetime: {e}")

    # Build event absolute timestamp for flag computations
    ev = ev.merge(enc[["enc_id","arrival_ts","complaint_group"]], on="enc_id", how="left")
    ev["event_ts"] = ev["arrival_ts"] + ev["t"].astype(int).map(lambda m: pd.Timedelta(minutes=int(m)))

    # --- Deterministic fields (unambiguous) ---
    out = pd.DataFrame(index=ev.index)
    # Tag
    if tag_strategy == "zero":
        out["Tag"] = 0
    elif tag_strategy == "day_index":
        d0 = enc["arrival_ts"].dt.normalize().min()
        out["Tag"] = (ev["arrival_ts"].dt.normalize() - d0).dt.days.astype(int)
    else:
        raise ValueError(f"Unknown tag_strategy: {tag_strategy}")

    # Time
    out["t_min"] = ev["t"].astype(int)
    out["Triage"] = ev["triage"].astype(int)
    out["HF"] = ev["hr"].astype(int)
    out["MAP"] = ev["map"].astype(int)
    out["ICU_Kap"] = ev["cap_icu"].astype(int)
    out["Kap_veraltet"] = ev["capacity_stale"].astype(int)
    # Normalized time
    denom = float(normalize_t_norm_by) if normalize_t_norm_by else float(ev["t"].max() or 1)
    out["t_norm"] = (out["t_min"].astype(float) / denom).clip(0.0, 1.0)

    # --- Encodings that require explicit maps (no guessing) ---
    if "complaint_to_code" not in coding_maps:
        raise ValueError("coding_maps['complaint_to_code'] is required to map complaint_group -> Leitsymptom int.")
    if "action_to_code" not in coding_maps:
        raise ValueError("coding_maps['action_to_code'] is required to map action string -> naechste_Aktion int.")

    comp_map = coding_maps["complaint_to_code"]
    act_map  = coding_maps["action_to_code"]

    # Leitsymptom from encounters.complaint_group
    out["Leitsymptom"] = ev["complaint_group"].map(comp_map).astype("Int64")
    if out["Leitsymptom"].isnull().any():
        missing = sorted(ev.loc[out["Leitsymptom"].isnull(),"complaint_group"].unique().tolist())
        raise ValueError(f"Unmapped complaint_group values: {missing}")

    # Next action code
    out["naechste_Aktion"] = ev["action"].map(act_map).astype("Int64")
    if out["naechste_Aktion"].isnull().any():
        missing = sorted(ev.loc[out["naechste_Aktion"].isnull(),"action"].unique().tolist())
        raise ValueError(f"Unmapped action values: {missing}")

    # --- Imaging/Lab flags (optional; require orders/results + code prefixes) ---
    def _flags(prefixes_key, orders, results):
        """Return (has_any, outstanding) Series based on code prefixes and event_ts ordering."""
        px = coding_maps.get(prefixes_key, None)
        if px is None:
            # Hard fail to avoid silent mislabeling
            raise ValueError(f"coding_maps['{prefixes_key}'] is required for flag derivation.")
        # compile boolean masks per event
        # Join orders/results per enc_id to filter by code prefix
        ords = orders.copy()
        ress = results.copy()
        # Filter codes by prefixes
        def code_mask(df, prefixes):
            c = df["code"].astype(str)
            m = False
            for p in prefixes:
                m = m | c.str.startswith(p)
            return df[m]

        ords = code_mask(ords, px) if not ords.empty else ords
        ress = code_mask(ress, px) if not ress.empty else ress

        # For each event, has_any if any order placed before event_ts; outstanding if placed before and result after (or missing)
        # Build helper per enc_id for speed
        ords = ords.sort_values("ts_placed")
        ress = ress.sort_values("ts_result")

        has_any = np.zeros(len(out), dtype=int)
        outstanding = np.zeros(len(out), dtype=int)

        # group by encounter for local lookups
        ord_by_enc = {k: g[["ts_placed"]].values.ravel() for k,g in ords.groupby("enc_id")}
        res_by_enc = {k: g[["ts_result"]].values.ravel() for k,g in ress.groupby("enc_id")}

        enc_ids = ev["enc_id"].values
        ev_ts = ev["event_ts"].values.astype("datetime64[ns]")

        for i in range(len(out)):
            e = enc_ids[i]; ts = ev_ts[i]
            ord_ts = ord_by_enc.get(e, None)
            if ord_ts is None or len(ord_ts)==0:
                continue
            # any order placed before ts?
            any_before = np.any(ord_ts <= ts)
            if any_before:
                has_any[i] = 1
                res_ts = res_by_enc.get(e, None)
                if res_ts is None or len(res_ts)==0:
                    outstanding[i] = 1
                else:
                    outstanding[i] = int(np.any(res_ts > ts))

        return pd.Series(has_any, index=out.index), pd.Series(outstanding, index=out.index)

    if "orders" in tables and "results" in tables:
        orders = tables["orders"].copy()
        results = tables["results"].copy()
        # Ensure time parsing
        for col in ["ts_placed"]:
            if col in orders.columns and not np.issubdtype(orders[col].dtype, np.datetime64):
                orders[col] = pd.to_datetime(orders[col], errors="coerce")
        for col in ["ts_result"]:
            if col in results.columns and not np.issubdtype(results[col].dtype, np.datetime64):
                results[col] = pd.to_datetime(results[col], errors="coerce")

        out["hat_Labor"], out["Labor_ausstehend"] = _flags("lab_code_prefixes", orders, results)
        out["hat_Roentgen"], out["Roentgen_ausstehend"] = _flags("xray_code_prefixes", orders, results)
        out["hat_CT"], out["CT_ausstehend"] = _flags("ct_code_prefixes", orders, results)
    else:
        # Explicit fail: flags required for your feature set
        raise ValueError("orders/results tables required to derive imaging/lab flags. Add them to 'tables'.")

    # --- Gate_Pos ---
    if gate_pos_policy == "require":
        raise ValueError("Gate_Pos derivation not specified. Set gate_pos_policy='sample_prevalence' or provide gate_pos_fn.")
    elif gate_pos_policy == "sample_prevalence":
        rng = np.random.default_rng(42)
        out["Gate_Pos"] = (rng.random(len(out)) < float(prevalence_target)).astype(int)
    elif gate_pos_policy == "from_function":
        if gate_pos_fn is None:
            raise ValueError("gate_pos_fn is None but gate_pos_policy='from_function'.")
        g = gate_pos_fn(out)
        if not set(np.unique(g)).issubset({0,1}):
            raise ValueError("gate_pos_fn must return 0/1 values.")
        out["Gate_Pos"] = g.astype(int)
    else:
        raise ValueError(f"Unknown gate_pos_policy: {gate_pos_policy}")

    # --- Final ordering & dtype enforcement ---
    out = out[REQUIRED_COLUMNS].copy()
    # Cast dtypes to match your real dataset
    int_cols = ["Tag","t_min","Triage","Leitsymptom","HF","MAP","ICU_Kap","Kap_veraltet",
                "hat_Labor","Labor_ausstehend","hat_Roentgen","Roentgen_ausstehend",
                "hat_CT","CT_ausstehend","naechste_Aktion","Gate_Pos"]
    for c in int_cols:
        out[c] = out[c].astype(int)
    out["t_norm"] = out["t_norm"].astype(float)
    return out
