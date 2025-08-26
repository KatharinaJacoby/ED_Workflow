
import numpy as np
import pandas as pd
from typing import Dict, Tuple

def default_config() -> dict:
    return {
        "arrival_per_day": 300,
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
        "base_risk": {
            "chest_pain": {"stemi":0.95, "nstemi":0.40, "afib_rvr":0.70, "atypical":0.05, "arrest":0.98},
            "dyspnea":    {"hf":0.30, "pe":0.60, "copd":0.20, "pna":0.15},
            "neuro_deficit":{"stroke":0.45, "confusion":0.15, "headache":0.05},
            "abd_pain":   {"chole":0.15, "gi_bleed":0.40, "appendicitis":0.20},
            "minor_trauma":{"fracture":0.05, "sprain":0.01},
            "polytrauma": {"blunt":0.30, "penetrating":0.50},
            "obgyn":      {"ectopic":0.30, "bleeding":0.08},
            "ent_oph":    {"fb_eye":0.01, "otitis":0.01}
        },
        "vitals": {
            "chest_pain": {
                "stemi":     {"HF": (105,18), "MAP": (65,10), "triage": (1.5, 0.5)},
                "nstemi":    {"HF": (98,15),  "MAP": (72,10), "triage": (2.0, 0.5)},
                "afib_rvr":  {"HF": (135,22), "MAP": (78,12), "triage": (2.5, 0.5)},
                "atypical":  {"HF": (82,12),  "MAP": (85,10), "triage": (3.5, 0.5)},
                "arrest":    {"HF": (110,20), "MAP": (60,12), "triage": (1.0, 0.2)}
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
        "universal_orders": {"ECG": True, "VBG": True},
        "timing_rules": {"red": 0, "yellow": 10, "green": 60},
        "ct_in_resus": True,
        "length_of_stay_min": {"mean": 360, "sd": 90},
        "icu_capacity_max": 20,
        "icu_block_prob": 0.10,
        "unit_policy": {
            "cpu_capacity_max": 8,
            "cpu_block_prob": 0.20,
            "cpu_board_delay_min": 60,
            "cpu_board_delay_max": 240,
            "stroke_capacity_max": 12,
            "stroke_block_prob": 0.15,
            "stroke_board_delay_min": 60,
            "stroke_board_delay_max": 240
        },
        "resus_policy": {
            "icu_bed_required": True,
            "arrest_prob_overall": 0.01,
            "rosc_board_delay_min": 120,
            "rosc_board_delay_max": 360,
            "neuro_board_delay_min": 60,
            "neuro_board_delay_max": 240
        },
        "fast_track": {
            "stroke_ct_to_admit_min": 20,
            "stemi_unstable_to_cath_min": 15,
            "polytrauma_resus_to_ct_min": 10,
            "polytrauma_to_admit_min": 30,
            "minor_max_los_min": 180,
            "cpu_admit_min": 30
        },
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
        "age_dist": {"mean": 58, "sd": 18, "min": 16, "max": 95},
        "sex_prob_male": 0.52,
        "hx_prob": {"copd": 0.18, "hf": 0.12},
        "subtype_bias": {
            "dyspnea": {"hf_given_hx_hf": 0.20, "copd_given_hx_copd": 0.25, "pna_given_hx_copd": 0.10},
            "chest_pain": {"stemi_age50_male_mult": 1.25, "nstemi_age50_male_mult": 1.15}
        },
        "enforce_case_mix_exact": True,
        "debias_chest_pain_age_sex": True,
        "prevalence_target": 0.1081,
        "seed": 123
    }

def _rng(seed): return np.random.default_rng(seed)

def _draw_from_mix(rng, mix: Dict[str, float]) -> str:
    keys = list(mix.keys())
    p = np.array([mix[k] for k in keys], float); p = p / p.sum()
    return keys[rng.choice(len(keys), p=p)]

def _triage_color(level:int)->str:
    if level <= 1: return "red"
    if level == 2: return "yellow"
    return "green"

def _capacity_snapshot_generic(rng, max_cap:int, block_p:float)->int:
    if rng.random() < block_p: return 0
    return int(rng.integers(0, max(1, int(max_cap*0.6))+1))

def _capacity_snapshot_icu(rng, max_cap:int, block_p:float)->int:
    return _capacity_snapshot_generic(rng, max_cap, block_p)

def _action_code_for(complaint:str, subtype:str, unstable:bool)->int:
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
        if subtype in ("stemi","arrest"): imgs.append("CT")
    if complaint=="dyspnea":
        if subtype in ("hf","copd","pna"): imgs.append("CXR")
        if subtype=="pe": imgs.append("CT")
    if complaint=="abd_pain":
        labs.append("CRP"); labs.append("CRP")
        imgs.append("CT"); imgs.append("US")
    if complaint=="polytrauma": imgs.append("CT")
    if complaint=="neuro_deficit" and subtype=="stroke": imgs.append("CT")
    return labs, imgs

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
    server_end_times = []
    attend_expiry = -1
    triage_start = np.zeros(n, dtype=int)
    triage_end   = np.zeros(n, dtype=int)

    def ensure_servers(now_min, shift):
        nonlocal server_end_times, attend_expiry
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
        idx_min = min(range(len(server_end_times)), key=lambda j: server_end_times[j][1])
        role, free_min = server_end_times[idx_min]
        start = max(arr, free_min)
        svc = _triage_service_minutes(rng, int(triage_levels[i]), role, cfg)
        end = int(round(start + svc))
        server_end_times[idx_min] = (role, end)
        triage_start[i] = start; triage_end[i] = end

    metrics = {}
    return triage_start, triage_end, metrics

def _validate_vitals(hr:int, mapv:int, temp:float, gcs:int)->bool:
    if hr < 20 and mapv < 50: return False
    if mapv < 50 and hr > 100: return False
    if hr > 170 and mapv > 85: return False
    if temp > 41.5: return False
    return True

def _sample_temp(rng, complaint:str, subtype:str)->float:
    mu = 37.0; sd = 0.6
    if complaint=="dyspnea" and subtype=="pna": mu = 38.5; sd = 0.7
    elif complaint=="abd_pain" and subtype=="gi_bleed": mu = 37.6; sd = 0.7
    return float(np.clip(rng.normal(mu, sd), 34.0, 42.5))

def _sample_gcs(rng, complaint:str, subtype:str)->int:
    if complaint=="neuro_deficit":
        r = rng.random()
        if r < 0.70: return 15
        if r < 0.90: return int(rng.integers(13, 15))
        return int(rng.integers(8, 13))
    if complaint=="polytrauma":
        r = rng.random()
        if r < 0.60: return 15
        if r < 0.85: return int(rng.integers(12, 15))
        return int(rng.integers(6, 12))
    return 15

def generate_day(cfg:dict)->Tuple[dict, dict]:
    seed = int(cfg.get("seed", 123))
    rng = _rng(seed)
    N = int(cfg.get("arrival_per_day", 300))

    weights = cfg.get("shift_weights", {"day":0.5,"evening":0.35,"night":0.15})
    hours = []
    for _ in range(N):
        r = rng.random()
        if r < weights["day"]:    hours.append(int(rng.integers(8, 18)))
        elif r < weights["day"]+weights["evening"]: hours.append(int(rng.integers(18, 24)))
        else: hours.append(int(rng.integers(0, 8)))
    minutes = rng.integers(0, 60, size=N)

    start = np.datetime64("2025-01-01T00:00:00")
    arrival_ts = start + (np.array(hours)*60 + minutes).astype("timedelta64[m]")
    arrivals_min = (np.array(hours)*60 + minutes).astype(int)

    case_mix = cfg["case_mix"]; subtype_mix = cfg["subtype_mix"]; vitals = cfg["vitals"]
    los_mu = cfg["length_of_stay_min"]["mean"]; los_sd = cfg["length_of_stay_min"]["sd"]
    icu_max = int(cfg.get("icu_capacity_max", 20)); icu_block = float(cfg.get("icu_block_prob", 0.10))
    unit = cfg.get("unit_policy", {})
    cpu_max = int(unit.get("cpu_capacity_max", 8)); cpu_block = float(unit.get("cpu_block_prob", 0.20))
    stroke_max = int(unit.get("stroke_capacity_max", 12)); stroke_block = float(unit.get("stroke_block_prob", 0.15))

    tri_levels_for_queue = np.full(N, 3, dtype=int)
    tri_start_min, tri_end_min, _ = _simulate_triage_queue(cfg, arrivals_min, tri_levels_for_queue, np.array(hours), _rng(seed+7))

    # Exact case-mix
    keys = list(case_mix.keys())
    probs = np.array([case_mix[k] for k in keys], dtype=float); probs = probs/probs.sum()
    floors = np.floor(probs * N).astype(int); remain = N - floors.sum()
    remainders = probs * N - floors; order = np.argsort(-remainders); floors[order[:remain]] += 1
    complaints_order = []
    for k,cnt in zip(keys, floors.tolist()): complaints_order.extend([k]*cnt)
    _rng(seed+17).shuffle(complaints_order)

    enc_rows, ev_rows, ord_rows, res_rows = [], [], [], []
    arrest_n = 0; arrest_boarded_n = 0; cpu_boarded_n = 0; stroke_boarded_n = 0

    for i in range(N):
        enc_id = i+1
        complaint = complaints_order[i]

        age = int(np.clip(rng.normal(cfg["age_dist"]["mean"], cfg["age_dist"]["sd"]), cfg["age_dist"]["min"], cfg["age_dist"]["max"]))
        sex_male = int(rng.random() < cfg.get("sex_prob_male", 0.5))
        hx_copd = int(rng.random() < cfg["hx_prob"]["copd"])
        hx_hf   = int(rng.random() < cfg["hx_prob"]["hf"])

        submix = dict(subtype_mix[complaint])
        if complaint == "dyspnea":
            if hx_copd:
                submix["copd"] = submix.get("copd",0.0) + cfg["subtype_bias"]["dyspnea"]["copd_given_hx_copd"]
                submix["pna"]  = submix.get("pna",0.0)  + cfg["subtype_bias"]["dyspnea"]["pna_given_hx_copd"]
            if hx_hf:
                submix["hf"]   = submix.get("hf",0.0)   + cfg["subtype_bias"]["dyspnea"]["hf_given_hx_hf"]
        subtype = _draw_from_mix(rng, submix)

        tri_mu, tri_sd = vitals[complaint][subtype]["triage"]
        triage_level = int(np.clip(round(rng.normal(tri_mu, tri_sd)), 1, 5))

        # Arrest overlay (applies to chest_pain/dyspnea presentations)
        rp = cfg.get("resus_policy", {})
        if bool(rp.get("icu_bed_required", True)) and float(rp.get("arrest_prob_overall", 0.0)) > 0.0:
            if complaint in ("chest_pain","dyspnea") and (rng.random() < float(rp.get("arrest_prob_overall", 0.0))):
                subtype = "arrest"
                complaint = "chest_pain"
                arrest_n += 1

        los = int(np.clip(rng.normal(los_mu, los_sd), 60, 24*60))
        if complaint == "abd_pain":
            los = max(los, 24*60)

        plan_actions = {}
        unstable = (triage_level <= 2) or (complaint=="polytrauma") or (complaint=="dyspnea" and subtype=="pe")
        color = _triage_color(triage_level)
        t0 = int((tri_end_min[i] - arrivals_min[i]) + {"red":0,"yellow":10,"green":60}[_triage_color(triage_level)])

        # Arrest: fast-track; ICU-bed gate else boarding
        if subtype == "arrest" and bool(rp.get("icu_bed_required", True)):
            t0 = 0
            cap0 = _capacity_snapshot_icu(_rng(seed+100+i), icu_max, icu_block)
            if cap0 <= 0:
                dmin = int(rp.get("rosc_board_delay_min",120)); dmax = int(rp.get("rosc_board_delay_max",360))
                los += int(_rng(seed+200+i).integers(dmin, dmax+1)); arrest_boarded_n += 1

        # STEMI: stable -> cath@0; unstable -> resus@0 then cath
        if complaint=="chest_pain" and subtype=="stemi":
            if not unstable:
                t0 = 0; plan_actions[0] = 6; los = min(los, 60)
            else:
                t0 = 0; plan_actions[0] = 1
                plan_actions[int(cfg.get("fast_track",{}).get("stemi_unstable_to_cath_min",15))] = 6

        # Minor fast-track: cap LOS
        if complaint in ("ent_oph","minor_trauma"):
            los = min(los, int(cfg.get("fast_track",{}).get("minor_max_los_min",180)))

        # Stroke: CT@0, then admit to Stroke Unit (or Neuro ICU if severe); boarding if blocked
        if complaint=="neuro_deficit" and subtype=="stroke":
            t0 = 0; plan_actions[0] = 3  # CT
            admit_t = int(cfg.get("fast_track",{}).get("stroke_ct_to_admit_min",20))
            plan_actions[admit_t] = 7
            # Decide destination
            gcs_init = _sample_gcs(_rng(seed+300+i), complaint, subtype)
            severe = (gcs_init <= 12) or (triage_level <= 2)
            if severe:
                capn = _capacity_snapshot_icu(_rng(seed+301+i), icu_max, icu_block)
                if capn <= 0:
                    dmin = int(rp.get("neuro_board_delay_min",60)); dmax = int(rp.get("neuro_board_delay_max",240))
                    los += int(_rng(seed+302+i).integers(dmin, dmax+1)); stroke_boarded_n += 1
            else:
                capn = _capacity_snapshot_generic(_rng(seed+303+i), stroke_max, stroke_block)
                if capn <= 0:
                    dmin = int(cfg["unit_policy"].get("stroke_board_delay_min",60)); dmax = int(cfg["unit_policy"].get("stroke_board_delay_max",240))
                    los += int(_rng(seed+304+i).integers(dmin, dmax+1)); stroke_boarded_n += 1

        # Chest pain non-STEMI: CPU admit; boarding if CPU blocked
        if complaint=="chest_pain" and subtype in ("nstemi","afib_rvr","atypical"):
            admit_t = int(cfg.get("fast_track",{}).get("cpu_admit_min",30))
            plan_actions[admit_t] = 7
            capc = _capacity_snapshot_generic(_rng(seed+400+i), cpu_max, cpu_block)
            if capc <= 0:
                dmin = int(cfg["unit_policy"].get("cpu_board_delay_min",60)); dmax = int(cfg["unit_policy"].get("cpu_board_delay_max",240))
                los += int(_rng(seed+401+i).integers(dmin, dmax+1)); cpu_boarded_n += 1

        # Polytrauma pipeline: resus@0 -> CT -> admit (ICU proxy); boarding if ICU blocked
        if complaint=="polytrauma":
            t0 = 0; plan_actions[0] = 1
            plan_actions[int(cfg.get("fast_track",{}).get("polytrauma_resus_to_ct_min",10))] = 3
            plan_actions[int(cfg.get("fast_track",{}).get("polytrauma_to_admit_min",30))] = 7
            capi = _capacity_snapshot_icu(_rng(seed+500+i), icu_max, icu_block)
            if capi <= 0:
                dmin = int(rp.get("neuro_board_delay_min",60)); dmax = int(rp.get("neuro_board_delay_max",240))
                los += int(_rng(seed+501+i).integers(dmin, dmax+1))

        enc_rows.append((enc_id, arrival_ts[i], complaint, subtype, triage_level, los, age, sex_male, hx_copd, hx_hf))

        # Event timeline
        times = list(range(0, los+1, 15))
        if t0 not in times and 0 <= t0 <= los: times = sorted(set(times + [t0]))
        if len(plan_actions): times = sorted(set(times + [int(tt) for tt in plan_actions.keys() if 0 <= int(tt) <= los]))

        for t in times:
            cap_icu = _capacity_snapshot_icu(_rng(seed+600+i+t), icu_max, icu_block)
            capacity_stale = int(_rng(seed+700+i+t).random() < 0.10)
            HF_mu, HF_sd = vitals[complaint][subtype]["HF"]
            MAP_mu, MAP_sd = vitals[complaint][subtype]["MAP"]
            drift = (t/los) if los>0 else 0.0
            attempts = 0
            while True:
                hf = int(np.clip(_rng(seed+800+i+t).normal(HF_mu + 5*drift, HF_sd), 40, 220))
                mapv = int(np.clip(_rng(seed+900+i+t).normal(MAP_mu - 4*drift, MAP_sd), 40, 120))
                temp = _sample_temp(_rng(seed+1000+i+t), complaint, subtype)
                gcs  = _sample_gcs(_rng(seed+1100+i+t), complaint, subtype)
                if _validate_vitals(hf, mapv, temp, gcs) or attempts >= 6: break
                attempts += 1
            action = plan_actions.get(t, 0)
            if action == 0 and t == t0:
                action = _action_code_for(complaint, subtype, unstable)
            ev_rows.append((enc_id, t, triage_level, hf, mapv, cap_icu, capacity_stale, action))

        labs, imgs = _orders_for(complaint, subtype, cfg.get("universal_orders", {"ECG":True,"VBG":True}))
        dt_place = int(min(max(0, t0), los))
        ts_placed = arrival_ts[i] + np.timedelta64(dt_place, "m")
        for code in labs + imgs:
            if cfg.get("ct_in_resus", True) and code.startswith("CT") and (unstable or subtype=="arrest"):
                dt_res = 15
            else:
                dt_res = int(_rng(seed+1200+i).integers(30, 121))
            ts_result = ts_placed + np.timedelta64(dt_res, "m")
            ord_rows.append((enc_id, code, ts_placed))
            res_rows.append((enc_id, code, ts_result))

    enc = pd.DataFrame(enc_rows, columns=["enc_id","arrival_ts","complaint_group","subtype","triage_level","los_min","age","sex_male","hx_copd","hx_hf"])
    ev  = pd.DataFrame(ev_rows,  columns=["enc_id","t","triage","hr","map","cap_icu","capacity_stale","action"])
    orders = pd.DataFrame(ord_rows, columns=["enc_id","code","ts_placed"]) if len(ord_rows) else pd.DataFrame(columns=["enc_id","code","ts_placed"])
    results= pd.DataFrame(res_rows, columns=["enc_id","code","ts_result"]) if len(res_rows) else pd.DataFrame(columns=["enc_id","code","ts_result"])

    base_risk = cfg["base_risk"]
    base = enc.apply(lambda r: base_risk[r["complaint_group"]][r["subtype"]], axis=1).astype(float).values

    # COPD+HF interplay bump for dyspnea
    both = (enc["complaint_group"].eq("dyspnea") & (enc["hx_copd"]==1) & (enc["hx_hf"]==1)).values
    base = base * (1.15 * both + 1.0 * (~both))

    severe = (enc["triage_level"]<=1) | (enc["complaint_group"].eq("polytrauma")) | ((enc["complaint_group"]=="chest_pain") & (enc["subtype"]=="stemi"))
    base = base * (1.3 * severe.values + 1.0 * (~severe.values))

    # Debias chest pain age/sex multiplier off by default
    # (we do not apply any age/sex boost)

    target = float(cfg.get("prevalence_target", 0.1081))
    s = min(10.0, max(0.01, target / max(1e-9, base.mean())))
    p_adj = np.clip(base * s, 0.001, 0.999)
    y = (_rng(seed+1300).random(len(p_adj)) < p_adj).astype(int)

    enc = enc.assign(Gate_Pos=y, p_gate=p_adj)

    mix = enc.groupby("complaint_group").size().div(len(enc)).to_dict()
    prev = float(enc["Gate_Pos"].mean())
    metrics = {"case_mix_observed": mix, "prevalence_observed": prev, "N_enc": int(len(enc)),
               "arrest_n": int(arrest_n), "arrest_boarded_n": int(arrest_boarded_n),
               "cpu_boarded_n": int(cpu_boarded_n), "stroke_boarded_n": int(stroke_boarded_n)}
    tables = {"encounters": enc, "events": ev, "orders": orders, "results": results}
    return tables, metrics
