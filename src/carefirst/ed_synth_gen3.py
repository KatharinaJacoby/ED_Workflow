
import numpy as np
import pandas as pd
from typing import Dict, Tuple

# -------- Default config --------
def default_config() -> dict:
    return {
        "arrival_per_day": 300,
        # Target case mix
        "enforce_case_mix_exact": True,
        "case_mix": {
            "chest_pain":   0.30,
            "dyspnea":      0.30,
            "neuro_deficit":0.15,
            "abd_pain":     0.10,
            "minor_trauma": 0.05,
            "polytrauma":   0.05,
            "obgyn":        0.03,
            "ent_oph":      0.02
        },
        # Subtype mixture
        "subtype_mix": {
            "chest_pain": {"stemi":0.15, "nstemi":0.20, "afib_rvr":0.25, "atypical":0.40},
            "dyspnea":    {"hf":0.40, "pe":0.15, "copd":0.30, "pna":0.15},
            "neuro_deficit":{"stroke":0.60, "confusion":0.25, "headache":0.15},
            "abd_pain":   {"chole":0.35, "gi_bleed":0.25, "appendicitis":0.40},
            "minor_trauma":{"fracture":0.30, "sprain":0.70},
            "polytrauma": {"blunt":0.70, "penetrating":0.30},
            "obgyn":      {"ectopic":0.10, "bleeding":0.90},
            "ent_oph":    {"fb_eye":0.50, "otitis":0.50}
        },
        # Base risks by subtype
        "base_risk": {
            "chest_pain": {"stemi":0.95, "nstemi":0.40, "afib_rvr":0.70, "atypical":0.05},
            "dyspnea":    {"hf":0.30, "pe":0.60, "copd":0.20, "pna":0.15},
            "neuro_deficit":{"stroke":0.45, "confusion":0.15, "headache":0.05},
            "abd_pain":   {"chole":0.15, "gi_bleed":0.40, "appendicitis":0.20},
            "minor_trauma":{"fracture":0.05, "sprain":0.01},
            "polytrauma": {"blunt":0.30, "penetrating":0.50},
            "obgyn":      {"ectopic":0.30, "bleeding":0.08},
            "ent_oph":    {"fb_eye":0.01, "otitis":0.01}
        },
        # Vitals / triage centroids per subtype
        "vitals": {
            "chest_pain": {
                "stemi":     {"HF": (105,18), "MAP": (65,10), "triage": (1.5, 0.5)},
                "nstemi":    {"HF": (98,15),  "MAP": (72,10), "triage": (2.0, 0.5)},
                "afib_rvr":  {"HF": (135,22), "MAP": (78,12), "triage": (2.5, 0.5)},
                "atypical":  {"HF": (82,12),  "MAP": (85,10), "triage": (3.5, 0.5)},
            },
            "dyspnea": {
                "hf":        {"HF": (110,18), "MAP": (70,12), "triage": (2.0, 0.5)},
                "pe":        {"HF": (118,20), "MAP": (68,12), "triage": (1.8, 0.5)},
                "copd":      {"HF": (100,16), "MAP": (78,10), "triage": (2.5, 0.5)},
                "pna":       {"HF": (95,14),  "MAP": (82,10), "triage": (3.0, 0.5)},
            },
            "neuro_deficit":{
                "stroke":    {"HF": (92,12),  "MAP": (82,10), "triage": (1.8, 0.5)},
                "confusion": {"HF": (85,10),  "MAP": (85,10), "triage": (2.6, 0.5)},
                "headache":  {"HF": (80,10),  "MAP": (88,10), "triage": (3.6, 0.5)},
            },
            "abd_pain": {
                "chole":     {"HF": (94,12),  "MAP": (78,10), "triage": (2.8, 0.5)},
                "gi_bleed":  {"HF": (105,16), "MAP": (70,12), "triage": (2.2, 0.5)},
                "appendicitis":{"HF": (96,14), "MAP": (80,10), "triage": (2.8, 0.5)},
            },
            "minor_trauma":{
                "fracture":  {"HF": (88,12),  "MAP": (86,10), "triage": (3.8, 0.5)},
                "sprain":    {"HF": (80,10),  "MAP": (88,10), "triage": (4.0, 0.5)},
            },
            "polytrauma":{
                "blunt":     {"HF": (110,18), "MAP": (70,12), "triage": (1.2, 0.5)},
                "penetrating":{"HF": (120,22), "MAP": (65,12), "triage": (1.1, 0.5)},
            },
            "obgyn":{
                "ectopic":   {"HF": (105,18), "MAP": (72,12), "triage": (1.8, 0.5)},
                "bleeding":  {"HF": (95,14),  "MAP": (78,10), "triage": (2.6, 0.5)},
            },
            "ent_oph":{
                "fb_eye":    {"HF": (78,10),  "MAP": (90,10), "triage": (4.2, 0.5)},
                "otitis":    {"HF": (78,10),  "MAP": (90,10), "triage": (4.2, 0.5)},
            }
        },
        # Universal triage + timing
        "universal_orders": {"ECG": True, "VBG": True},
        "timing_rules": {"red": 0, "yellow": 10, "green": 60},
        # Resource & staffing
        "ct_in_resus": True,
        "length_of_stay_min": {"mean": 360, "sd": 90},
        "icu_capacity_max": 20,
        "icu_block_prob": 0.10,
        "shift_weights": { "day": 0.5, "evening": 0.35, "night": 0.15 },
        "triage_servers_by_shift": {"day":2, "evening":2, "night":1},
        "attending_boost": {"day":1, "trigger_queue": 1, "window_min":180},
        "triage_service_means": {1:2, 2:6, 3:9, 4:10, 5:10},
        "triage_role_speed": {"nurse":1.0, "attending":0.7},
        "ambulance_bursts_per_day": 2,
        "ambulances_per_burst_min": 3,
        "ambulances_per_burst_max": 4,
        "burst_hours_range": [9, 16],
        "burst_jitter_min": 6,
        # Demographics / history
        "age_dist": {"mean": 58, "sd": 18, "min": 16, "max": 95},
        "sex_prob_male": 0.52,
        "hx_prob": {"copd": 0.18, "hf": 0.12},
        "subtype_bias": {
            "dyspnea": {"hf_given_hx_hf": 0.20, "copd_given_hx_copd": 0.25},
            "chest_pain": {"stemi_age50_male_mult": 1.25, "nstemi_age50_male_mult": 1.15}
        },
        "prevalence_target": 0.1081,
        "seed": 123
    }

# -------- Helpers --------
def _rng(seed): return np.random.default_rng(seed)

def _draw_from_mix(rng, mix: Dict[str, float]) -> str:
    keys = list(mix.keys())
    p = np.array([mix[k] for k in keys], float); p = p / p.sum()
    return keys[rng.choice(len(keys), p=p)]

def _triage_color(level:int)->str:
    if level <= 1: return "red"
    if level == 2: return "yellow"
    return "green"

def _capacity_snapshot_icu(rng, max_cap:int, block_p:float)->int:
    if rng.random() < block_p: return 0
    return int(rng.integers(0, max(1, int(max_cap*0.5))+1))

def _action_code_for(complaint:str, subtype:str, unstable:bool)->int:
    # 0=observe,1=resus,2=rate_control,3=CT,4=CXR,5=lab_draw,6=cath_lab,7=admit
    if unstable:
        if complaint=="chest_pain" and subtype=="stemi": return 6
        if complaint=="polytrauma": return 1
        if complaint=="dyspnea" and subtype=="pe": return 3
        return 1
    if complaint=="chest_pain" and subtype=="afib_rvr": return 2
    if complaint=="dyspnea" and subtype in ("hf","copd","pna"): return 4
    if complaint=="abd_pain": return 5
    return 0

def _orders_for(complaint:str, subtype:str, universal:Dict[str,bool]):
    labs, imgs = [], []
    if universal.get("ECG", False): labs.append("ECG")
    if universal.get("VBG", False): labs.append("VBG")
    if complaint=="chest_pain":
        labs.append("TROPONIN")
        if subtype=="stemi": imgs.append("CT")
    if complaint=="dyspnea":
        if subtype in ("hf","copd","pna"): imgs.append("CXR")
        if subtype=="pe": imgs.append("CT")
    if complaint=="abd_pain":
        labs.append("CRP"); imgs.append("CT")
    if complaint=="polytrauma": imgs.append("CT")
    return labs, imgs

# ---- Triage queueing ----
def _shift_of(hour:int)->str:
    if 8 <= hour < 18: return "day"
    if 18 <= hour < 24: return "evening"
    return "night"

def _triage_service_minutes(rng, triage_level:int, role:str, cfg:dict)->float:
    base = cfg.get("triage_service_means", {}).get(int(triage_level), 10)
    mult = cfg.get("triage_role_speed", {}).get(role, 1.0)
    mean = max(1.0, base * mult)
    return float(max(0.5, rng.normal(mean, max(0.1, mean*0.25))))

def _simulate_triage_queue(cfg:dict, arrivals_min, triage_levels, arrival_hours, rng):
    n = len(arrivals_min)
    base_servers = cfg.get("triage_servers_by_shift", {"day":2, "evening":2, "night":1})
    attend_cfg   = cfg.get("attending_boost", {"day":1, "trigger_queue":1, "window_min":180})
    server_end_times = []  # list of (role, next_free_min)
    attend_expiry = -1
    triage_start = np.zeros(n, dtype=int)
    triage_end   = np.zeros(n, dtype=int)
    max_queue = 0; boosts = 0

    def ensure_servers(now_min, shift):
        nonlocal server_end_times, attend_expiry
        # keep busy servers; rebuild list with base nurses + attending if active
        nurse_busy = [t for role,t in server_end_times if role=="nurse" and t>now_min]
        attend_busy= [t for role,t in server_end_times if role=="attending" and t>now_min]
        server_end_times = [("nurse",t) for t in nurse_busy] + [("attending",t) for t in attend_busy]
        while sum(1 for r,_ in server_end_times if r=="nurse") < int(base_servers.get(shift,1)):
            server_end_times.append(("nurse", now_min))
        if now_min < attend_expiry:
            while sum(1 for r,_ in server_end_times if r=="attending") < int(attend_cfg.get("day",0)):
                server_end_times.append(("attending", now_min))
        else:
            server_end_times = [it for it in server_end_times if not (it[0]=="attending" and it[1]<=now_min and now_min>=attend_expiry)]

    for i in range(n):
        arr = int(arrivals_min[i])
        hour = int(arrival_hours[i])
        shift = _shift_of(hour)
        ensure_servers(arr, shift)
        # Does patient wait?
        min_free = min([t for _,t in server_end_times]) if server_end_times else arr
        waits = arr < min_free
        if waits and shift=="day" and int(attend_cfg.get("day",0))>0 and arr >= attend_expiry:
            attend_expiry = arr + int(attend_cfg.get("window_min",180))
            boosts += 1
            ensure_servers(arr, shift)

        # Assign to earliest server
        idx_min = min(range(len(server_end_times)), key=lambda j: server_end_times[j][1])
        role, free_min = server_end_times[idx_min]
        start = max(arr, free_min)
        svc = _triage_service_minutes(rng, int(triage_levels[i]), role, cfg)
        end = int(round(start + svc))
        server_end_times[idx_min] = (role, end)
        triage_start[i] = start; triage_end[i] = end
        if waits: max_queue = max(max_queue, 1)

    metrics = {"triage_max_queue": int(max_queue), "triage_boost_activations": int(boosts)}
    return triage_start, triage_end, metrics

# ---- Main generation ----
def generate_day(cfg:dict)->Tuple[dict, dict]:
    seed = int(cfg.get("seed", 123))
    rng = _rng(seed)
    N = int(cfg.get("arrival_per_day", 300))

    # Arrival timestamps by shift + bursts
    weights = cfg.get("shift_weights", {"day":0.5,"evening":0.35,"night":0.15})
    hours = []
    for _ in range(N):
        r = rng.random()
        if r < weights["day"]:    hours.append(int(rng.integers(8, 18)))
        elif r < weights["day"]+weights["evening"]: hours.append(int(rng.integers(18, 24)))
        else: hours.append(int(rng.integers(0, 8)))
    minutes = rng.integers(0, 60, size=N)
    # Ambulance bursts (overwrite some arrivals)
    bursts = int(cfg.get("ambulance_bursts_per_day", 0))
    if bursts > 0 and N >= 10:
        bmin = int(cfg.get("ambulances_per_burst_min", 3))
        bmax = int(cfg.get("ambulances_per_burst_max", 4))
        h_lo, h_hi = cfg.get("burst_hours_range", [9,16])
        jitter = int(cfg.get("burst_jitter_min", 6))
        idx_pool = np.arange(N); rng.shuffle(idx_pool); ptr = 0
        hours_arr = np.array(hours); minutes_arr = np.array(minutes)
        for _ in range(bursts):
            sz = int(rng.integers(bmin, bmax+1))
            if ptr+sz > len(idx_pool): break
            sel = idx_pool[ptr:ptr+sz]; ptr += sz
            burst_hour = int(rng.integers(h_lo, h_hi+1))
            burst_min  = int(rng.integers(0, 60))
            hours_arr[sel] = burst_hour
            minutes_arr[sel] = np.clip(burst_min + rng.integers(0, max(1,jitter), size=sz), 0, 59)
        hours = hours_arr.tolist(); minutes = minutes_arr.tolist()

    start = np.datetime64("2025-01-01T00:00:00")
    arrival_ts = start + (np.array(hours)*60 + minutes).astype("timedelta64[m]")
    arrivals_min = (np.array(hours)*60 + minutes).astype(int)

    case_mix = cfg["case_mix"]; subtype_mix = cfg["subtype_mix"]; vitals = cfg["vitals"]
    # Build exact complaint list if requested
    if cfg.get("enforce_case_mix_exact", False):
        keys = list(case_mix.keys())
        probs = np.array([case_mix[k] for k in keys], dtype=float)
        probs = probs / probs.sum()
        floors = np.floor(probs * N).astype(int)
        remain = N - floors.sum()
        remainders = probs * N - floors
        order = np.argsort(-remainders)
        floors[order[:remain]] += 1
        # Expand into a list of complaints with exact counts
        complaints_order = []
        for k, cnt in zip(keys, floors.tolist()):
            complaints_order.extend([k] * cnt)
        rng.shuffle(complaints_order)
    else:
        complaints_order = None
    
    los_mu = cfg["length_of_stay_min"]["mean"]; los_sd = cfg["length_of_stay_min"]["sd"]
    icu_max = int(cfg.get("icu_capacity_max", 20)); block_p = float(cfg.get("icu_block_prob", 0.10))
    universal = cfg.get("universal_orders", {"ECG":True,"VBG":True})
    timing = cfg.get("timing_rules", {"red":0,"yellow":10,"green":60})

    # Pre-triage: assume triage level 3 for queue calc; accurate level reconciled in events via SLA offset
    tri_levels_for_queue = np.full(N, 3, dtype=int)
    tri_start_min, tri_end_min, tri_metrics = _simulate_triage_queue(cfg, arrivals_min, tri_levels_for_queue, np.array(hours), _rng(seed+7))

    enc_rows, ev_rows, ord_rows, res_rows = [], [], [], []

    for i in range(N):
        enc_id = i+1
        complaint = complaints_order[i] if complaints_order is not None else _draw_from_mix(rng, case_mix)
        # demographics & history
        age = int(np.clip(rng.normal(cfg["age_dist"]["mean"], cfg["age_dist"]["sd"]), cfg["age_dist"]["min"], cfg["age_dist"]["max"]))
        sex_male = int(rng.random() < cfg.get("sex_prob_male", 0.5))
        hx_copd = int(rng.random() < cfg["hx_prob"]["copd"])
        hx_hf   = int(rng.random() < cfg["hx_prob"]["hf"])
        # subtype with hx bias for dyspnea
        submix = dict(subtype_mix[complaint])
        if complaint == "dyspnea":
            if hx_copd: submix["copd"] = submix.get("copd",0.0) + cfg["subtype_bias"]["dyspnea"]["copd_given_hx_copd"]
            if hx_hf:   submix["hf"]   = submix.get("hf",0.0)   + cfg["subtype_bias"]["dyspnea"]["hf_given_hx_hf"]
        subtype = _draw_from_mix(rng, submix)

        tri_mu, tri_sd = vitals[complaint][subtype]["triage"]
        triage_level = int(np.clip(round(rng.normal(tri_mu, tri_sd)), 1, 5))

        los = int(np.clip(rng.normal(los_mu, los_sd), 60, 24*60))
        enc_rows.append((enc_id, arrival_ts[i], complaint, subtype, triage_level, los, age, sex_male, hx_copd, hx_hf))

        # Stable/unstable and first action time (after triage end + SLA)
        unstable = triage_level <= 2 or (complaint=="chest_pain" and subtype in ("stemi","afib_rvr")) or (complaint=="polytrauma") or (complaint=="dyspnea" and subtype=="pe")
        color = _triage_color(triage_level)
        t0 = int((tri_end_min[i] - arrivals_min[i]) + int(timing[color]))

        # Event timeline every 15 min + t0
        times = list(range(0, los+1, 15))
        if t0 not in times and 0 <= t0 <= los: times = sorted(set(times + [t0]))

        for t in times:
            cap_icu = _capacity_snapshot_icu(rng, icu_max, block_p)
            capacity_stale = int(rng.random() < 0.10)
            HF_mu, HF_sd = vitals[complaint][subtype]["HF"]
            MAP_mu, MAP_sd = vitals[complaint][subtype]["MAP"]
            drift = (t/los) if los>0 else 0.0
            hf = int(np.clip(rng.normal(HF_mu + 5*drift, HF_sd), 40, 220))
            mapv = int(np.clip(rng.normal(MAP_mu - 4*drift, MAP_sd), 40, 120))
            action = _action_code_for(complaint, subtype, unstable) if t == t0 else 0
            ev_rows.append((enc_id, t, triage_level, hf, mapv, cap_icu, capacity_stale, action))

        labs, imgs = _orders_for(complaint, subtype, universal)
        if 0 <= t0 <= los:
            dt_place = int(t0)
        else:
            dt_place = int(min(max(0, t0), los))
        ts_placed = arrival_ts[i] + np.timedelta64(dt_place, "m")
        for code in labs + imgs:
            if cfg.get("ct_in_resus", True) and code.startswith("CT") and unstable:
                dt_res = 15
            else:
                dt_res = int(rng.integers(30, 121))
            ts_result = ts_placed + np.timedelta64(dt_res, "m")
            ord_rows.append((enc_id, code, ts_placed))
            res_rows.append((enc_id, code, ts_result))

    enc = pd.DataFrame(enc_rows, columns=["enc_id","arrival_ts","complaint_group","subtype","triage_level","los_min","age","sex_male","hx_copd","hx_hf"])
    ev  = pd.DataFrame(ev_rows,  columns=["enc_id","t","triage","hr","map","cap_icu","capacity_stale","action"])
    orders = pd.DataFrame(ord_rows, columns=["enc_id","code","ts_placed"]) if len(ord_rows) else pd.DataFrame(columns=["enc_id","code","ts_placed"])
    results= pd.DataFrame(res_rows, columns=["enc_id","code","ts_result"]) if len(res_rows) else pd.DataFrame(columns=["enc_id","code","ts_result"])

    # Labels
    base_risk = cfg["base_risk"]
    base = enc.apply(lambda r: base_risk[r["complaint_group"]][r["subtype"]], axis=1).astype(float).values
    # Chest-pain age/sex multiplier
    mask_cp = (enc["complaint_group"]=="chest_pain")
    age50_m = ((enc["age"]>=50) & (enc["sex_male"]==1))
    mult = np.ones(len(enc))
    mult[(mask_cp & age50_m & (enc["subtype"]=="stemi"))] *= cfg["subtype_bias"]["chest_pain"]["stemi_age50_male_mult"]
    mult[(mask_cp & age50_m & (enc["subtype"]=="nstemi"))] *= cfg["subtype_bias"]["chest_pain"]["nstemi_age50_male_mult"]
    base = base * mult
    # severity bump
    severe = (enc["triage_level"]<=1) | (enc["complaint_group"].eq("polytrauma")) | ((enc["complaint_group"]=="chest_pain") & (enc["subtype"]=="stemi"))
    base = base * (1.3 * severe.values + 1.0 * (~severe.values))
    # scale to prevalence
    target = float(cfg.get("prevalence_target", 0.1081))
    s = min(10.0, max(0.01, target / max(1e-9, base.mean())))
    p_adj = np.clip(base * s, 0.001, 0.999)
    y = (_rng(seed+99).random(len(p_adj)) < p_adj).astype(int)

    enc = enc.assign(Gate_Pos=y, p_gate=p_adj)

    # Metrics
    mix = enc.groupby("complaint_group").size().div(len(enc)).to_dict()
    prev = float(enc["Gate_Pos"].mean())
    waits = np.maximum(0, (np.array(tri_start_min) - arrivals_min))
    tri_metrics.update({"triage_wait_p50": float(np.percentile(waits,50)),
                        "triage_wait_p90": float(np.percentile(waits,90)),
                        "triage_wait_p99": float(np.percentile(waits,99))})
    metrics = {"case_mix_observed": mix, "prevalence_observed": prev, "N_enc": int(len(enc)), **tri_metrics}
    tables = {"encounters": enc, "events": ev, "orders": orders, "results": results}
    return tables, metrics
