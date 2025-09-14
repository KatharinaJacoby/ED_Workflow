\
"""
synthetic_generator.py — realistic synthetic ED pathways with queues & consult behavior.

Provides:
- load_config(path) -> dict
- generate_day(config, seed=42) -> tables(dict of DataFrames), metrics(dict)
- emit_hl7(tables, base_dir="./ed_demo_data", write_orders=True, write_results=True) -> list of file paths

Tables:
  patients, encounters, capacity_snapshots, orders, results, events

Notes:
- No external deps beyond pandas/numpy. YAML optional (PyYAML). If unavailable, pass a dict to generate_day.
- HL7 files are written to a file-based ORBIS layout: {base_dir}/orbis_sim/{inbox|outbox}
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List
import numpy as np, pandas as pd, math, random, json
from datetime import datetime, timedelta
from pathlib import Path

# ------------------ utilities ------------------

def _ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")

def _normal_pos(mean, sd):
    return max(0.1, random.gauss(mean, sd))

def _gamma(shape, scale):
    return np.random.gamma(shape, scale)

def _choice(pairs):
    # pairs = [(value, prob), ...]
    vals, probs = zip(*pairs); return np.random.choice(vals, p=np.array(probs)/sum(probs))

def _piecewise_poisson(hour_means: List[int]) -> List[datetime]:
    # Draw Poisson arrivals per hour, then spread uniformly within each hour.
    start = datetime.fromisoformat("2025-08-12 00:00:00")
    arrivals = []
    for h, lam in enumerate(hour_means):
        n = np.random.poisson(lam)
        for _ in range(n):
            sec = np.random.randint(0, 3600)
            arrivals.append(start + timedelta(hours=h, seconds=int(sec)))
    arrivals.sort()
    return arrivals

# ------------------ resource queues ------------------

class ResourceQueue:
    def __init__(self, n_servers: int, service_gen, name="srv"):
        self.n = n_servers
        self.name = name
        self.next_free = [datetime.min] * n_servers
        self.service_gen = service_gen  # () -> timedelta

    def schedule(self, ready_at: datetime) -> Tuple[datetime, datetime, int]:
        i = min(range(self.n), key=lambda k: self.next_free[k])
        start = max(ready_at, self.next_free[i])
        dur = self.service_gen()
        finish = start + dur
        self.next_free[i] = finish
        return start, finish, i

# ------------------ config loader ------------------

def load_config(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(path.read_text())
        except Exception as e:
            raise RuntimeError("PyYAML required to load YAML; install or use JSON. " + str(e))
    else:
        return json.loads(path.read_text())

# ------------------ main generator ------------------

def generate_day(config: Dict[str, Any], seed: int = 42) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    random.seed(seed); np.random.seed(seed)

    # arrival schedule
    hour_means = config["arrival_process"]["base_per_hour"]
    arrivals = _piecewise_poisson(hour_means)
    ems_frac = config["arrival_process"]["ems_frac"]
    chest_frac = config["arrival_process"].get("chest_pain_frac", 0.5)

    # queues
    svc = config["resources"]["service_times_min"]
    ctQ   = ResourceQueue(config["resources"]["ct_scanners"],   lambda: timedelta(minutes=float(_gamma(svc["ct"]["shape"],   svc["ct"]["scale"]))),   "CT")
    xrayQ = ResourceQueue(config["resources"]["xray_rooms"],    lambda: timedelta(minutes=float(_gamma(svc["xray"]["shape"], svc["xray"]["scale"]))), "CXR")
    labQ  = ResourceQueue(config["resources"]["lab_analyzers"], lambda: timedelta(minutes=float(_gamma(svc["lab"]["shape"],  svc["lab"]["scale"]))),  "LAB")

    # capacity snapshots
    cap = config["capacity"]
    cap_rows = []
    icu_free = cap["icu_free_init"]; ward_free = cap["ward_free_init"]
    t0 = datetime.fromisoformat(config["sampling"]["day_start"])
    tend = t0 + timedelta(days=1)
    snap_dt = timedelta(minutes=cap["update_every_min"])
    t = t0
    while t <= tend:
        stale = 1 if np.random.rand() < cap["stale_prob"] else 0
        cap_rows.append({"ts":t, "icu_total":cap["icu_beds_total"], "icu_free":icu_free,
                         "ward_total":cap["ward_beds_total"], "ward_free":ward_free,
                         "ct_busy":0, "xray_busy":0, "data_stale":stale})
        t += snap_dt
    cap_df = pd.DataFrame(cap_rows)

    # tables we fill
    pat_rows=[]; enc_rows=[]; order_rows=[]; result_rows=[]; event_rows=[]
    pid_counter = 1; enc_counter = 1

    tri_probs = config["triage"]["level_probs"]
    tri_levels = list(map(int, tri_probs.keys()))
    tri_p = np.array(list(tri_probs.values())); tri_p = tri_p/tri_p.sum()

    # syndrome configs
    syn = config["syndromes"]

    for arr in arrivals:
        pid = f"P-{pid_counter:05d}"; enc = f"E-{enc_counter:05d}"
        pid_counter+=1; enc_counter+=1
        # demographics (simplified)
        age = int(np.clip(np.random.normal(62, 18), 18, 95))
        sex = np.random.choice(["F","M"], p=[0.52,0.48])

        pat_rows.append({"patient_id":pid, "age":age, "sex":sex, "allergies_hash":"A0", "insurance_hash":"I0"})

        # complaint sampling
        complaint_group = np.random.choice(["chest_pain","neuro_deficit","abd_pain","dyspnea","polytrauma","minor_trauma","obgyn","ent_oph"],
                                           p=[chest_frac,0.12,0.12,0.11,0.06,0.25,0.02,0.02])
        triage_level = np.random.choice(tri_levels, p=tri_p)
        arrival_mode = np.random.choice(["ems","walk-in"], p=[ems_frac, 1-ems_frac])
        trauma_flag = 1 if complaint_group in ("polytrauma","minor_trauma") else 0

        enc_rows.append({"enc_id":enc, "patient_id":pid, "arrival_ts":arr, "arrival_mode":arrival_mode,
                         "triage_system":config["triage"]["system"], "triage_level":int(triage_level),
                         "complaint_group":complaint_group, "trauma_flag":trauma_flag})

        # per-encounter timeline
        bin_min = config["sampling"]["bin_size_min"]
        # vitals baseline
        hr_base = int(np.clip(np.random.normal(85,12), 45, 160))
        map_base = int(np.clip(np.random.normal(85,10), 50, 120))

        # intentions & orders
        orders=[]; results=[]; pages=[]

        def place_order(ts, target, code, priority="ROUTINE"):
            nonlocal order_rows
            placer = f"PLC{int(ts.timestamp())}{np.random.randint(100,999)}"
            accession = f"ACC{int(ts.timestamp())}{np.random.randint(100,999)}"
            orders.append({"enc_id":enc,"ts_placed":ts,"placer_id":placer,"target":target,"code":code,"priority":priority,"status":"new","accession":accession})
            return placer, accession

        def add_result(accession, code, ts_result, value=None, units="", text=None, status="F", critical=0):
            nonlocal result_rows
            results.append({"enc_id":enc,"accession":accession,"code":code,"ts_result":ts_result,
                            "value":value,"units":units,"report_text":text,"status":status,"critical":critical})

        # syndrome-driven plan
        decision_time = arr + timedelta(hours=6)  # fallback
        need_ct=False; need_cxr=False; need_labs=True
        consult_svc=None; consult_accept_time=None

        if complaint_group=="chest_pain":
            mix = syn["chest_pain"]["mix"]
            typ = np.random.choice(["stemi","nstemi","noncardiac"], p=[mix["stemi"], mix["nstemi"], mix["noncardiac"]])
            need_labs=True; need_cxr = (typ!="stemi")
            if typ=="stemi":
                consult_svc="cardiology"
                consult_accept_time = arr + timedelta(minutes=_normal_pos(10,4))  # fast track
                decision_time = consult_accept_time + timedelta(minutes=5)
            elif typ=="nstemi":
                consult_svc="cardiology"
                # reluctance: add extra wait with some probability
                base_delay = _normal_pos(45, 15)
                if np.random.rand() < 0.35:
                    base_delay += _normal_pos(30, 10)
                consult_accept_time = arr + timedelta(minutes=base_delay)
                decision_time = consult_accept_time + timedelta(minutes=15)
            else:
                decision_time = arr + timedelta(hours=4)

            # orders and queues
            # labs
            plc, acc = place_order(arr + timedelta(minutes=_normal_pos(8,4)), "lab", "TROPONIN^Troponin I")
            start, fin, _ = labQ.schedule(arr + timedelta(minutes=_normal_pos(15,8)))
            add_result(acc, "TROPONIN^Troponin I", fin, value=round(float(np.random.uniform(5, 120)),1), units="ng/L")
            # CXR optional
            if need_cxr:
                plc2, acc2 = place_order(arr + timedelta(minutes=_normal_pos(20,6)), "imaging", "CXR^Chest X-ray")
                s2,f2,_ = xrayQ.schedule(arr + timedelta(minutes=_normal_pos(25,8)))
                add_result(acc2, "CXR^Chest X-ray", f2, text="No acute cardiopulmonary disease.")
            # consult page time
            if consult_svc:
                pages.append({"svc":consult_svc, "ts_page": arr + timedelta(minutes=_normal_pos(12,6)), "ts_accept": consult_accept_time})

        elif complaint_group=="neuro_deficit":
            need_ct=True; consult_svc="neurology"
            # CT head
            plc3, acc3 = place_order(arr + timedelta(minutes=_normal_pos(10,5)), "imaging", "CT_HEAD^CT Head")
            s3,f3,_ = ctQ.schedule(arr + timedelta(minutes=_normal_pos(15,6)))
            add_result(acc3, "CT_HEAD^CT Head", f3, text="CT complete. No acute bleed.")
            delay_ack = _normal_pos(30, 10) + max(0, np.random.normal(15,10))  # overload
            consult_accept_time = arr + timedelta(minutes=delay_ack)
            decision_time = consult_accept_time + timedelta(minutes=20)
            pages.append({"svc":consult_svc, "ts_page": arr + timedelta(minutes=_normal_pos(8,4)), "ts_accept": consult_accept_time})

        elif complaint_group=="polytrauma":
            need_ct=True
            plc4, acc4 = place_order(arr + timedelta(minutes=_normal_pos(5,3)), "imaging", "CT_POLYTRAUMA^CT Polytrauma")
            s4,f4,_ = ctQ.schedule(arr + timedelta(minutes=_normal_pos(8,4)))
            add_result(acc4, "CT_POLYTRAUMA^CT Polytrauma", f4, text="Whole-body CT complete.")
            decision_time = f4 + timedelta(minutes=15)

        else:
            # minor defaults: sometimes xray or labs
            if np.random.rand()<0.4:
                plc5, acc5 = place_order(arr + timedelta(minutes=_normal_pos(25,10)), "imaging", "CXR^Chest X-ray")
                s5,f5,_ = xrayQ.schedule(arr + timedelta(minutes=_normal_pos(30,10)))
                add_result(acc5, "CXR^Chest X-ray", f5, text="No acute findings.")
            if np.random.rand()<0.5:
                plc6, acc6 = place_order(arr + timedelta(minutes=_normal_pos(15,6)), "lab", "CRP^C-Reactive Protein")
                s6,f6,_ = labQ.schedule(arr + timedelta(minutes=_normal_pos(20,8)))
                add_result(acc6, "CRP^C-Reactive Protein", f6, value=round(float(np.random.uniform(0.1, 10.0)),1), units="mg/dL")
            decision_time = arr + timedelta(hours=_normal_pos(3.0, 1.0))

        # Build events timeline at fixed bins
        def _eta_first_result(now):
            fut = [r["ts_result"] for r in results if r["ts_result"]>=now]
            if not fut: return 0.0
            return max(0.0, (min(fut)-now).total_seconds()/60.0)
        def _eta_decision(now):
            return max(0.0, (decision_time - now).total_seconds()/60.0)

        # rules for "next best action" at time now (simple; non-diagnostic)
        def _next_action(now):
            # order labs within 15 min for high acuity
            if (now - arr).total_seconds()/60.0 < 15 and triage_level<=2:
                if not any(o["target"]=="lab" and o["ts_placed"]<=now for o in orders):
                    return "place_labs"
            # imaging when indicated and not yet ordered
            if need_ct and not any("CT" in o["code"] and o["ts_placed"]<=now for o in orders):
                return "place_ct"
            if need_cxr and not any("CXR" in o["code"] and o["ts_placed"]<=now for o in orders):
                return "place_xray"
            # consults
            if consult_svc and any(p["ts_page"]<=now for p in pages) and all(p["ts_accept"]>now for p in pages):
                return f"page_{consult_svc}"
            # finalization
            if now >= decision_time - timedelta(minutes=5):
                # ICU if triage high and consult happened
                if triage_level<=2 and (consult_svc in ("cardiology","neurology","icu")):
                    return "prepare_admit_icu"
                return "prepare_admit_ward"
            return "none"

        # sample bins until decision or 6h cap
        cur = arr
        while cur <= min(arr+timedelta(hours=6), decision_time+timedelta(minutes=30)):
            event_rows.append({
                "enc_id":enc, "t": int((cur-arr).total_seconds()/60.0),
                "triage": triage_level,
                "complaint": 0 if complaint_group=="chest_pain" else 1,
                "hr": int(np.clip(np.random.normal(hr_base,6), 45, 160)),
                "map": int(np.clip(np.random.normal(map_base,6), 50, 120)),
                "cap_icu": 1 if icu_free>0 else 0,
                "capacity_stale": int(np.random.rand()<cap["stale_prob"]),
                "action": _action_id(_next_action(cur)),
                "eta_first_result": _eta_first_result(cur),
                "eta_decision": _eta_decision(cur),
                "patient_id": pid
            })
            cur += timedelta(minutes=bin_min)

        # update capacity at disposition (very rough)
        if triage_level<=2 and (consult_svc in ("cardiology","neurology") or complaint_group=="polytrauma"):
            if icu_free>0: icu_free -= 1
        else:
            if ward_free>0: ward_free -= 1

        # finalize: push collected orders/results to global tables
        order_rows.extend(orders); result_rows.extend(results)

    # build DataFrames
    patients   = pd.DataFrame(pat_rows)
    encounters = pd.DataFrame(enc_rows)
    orders     = pd.DataFrame(order_rows)
    results    = pd.DataFrame(result_rows)
    events     = pd.DataFrame(event_rows)

    # metrics
    def qtl(x, q): 
        arr = np.array(x); 
        return float(np.quantile(arr, q)) if len(arr)>0 else float('nan')
    tat_lab = [(r["ts_result"] - next((o["ts_placed"] for o in order_rows if o["accession"]==r["accession"]), r["ts_result"])).total_seconds()/60.0
               for r in result_rows if "TROPONIN" in r["code"] or "CRP" in r["code"]]
    tat_cxr = [(r["ts_result"] - next((o["ts_placed"] for o in order_rows if o["accession"]==r["accession"]), r["ts_result"])).total_seconds()/60.0
               for r in result_rows if "CXR" in r["code"]]
    tat_ct  = [(r["ts_result"] - next((o["ts_placed"] for o in order_rows if o["accession"]==r["accession"]), r["ts_result"])).total_seconds()/60.0
               for r in result_rows if "CT_" in r["code"]]

    metrics = {
        "n_encounters": int(len(encounters)),
        "labs_tat_p50": qtl(tat_lab, 0.5), "labs_tat_p90": qtl(tat_lab, 0.9),
        "cxr_tat_p50":  qtl(tat_cxr, 0.5), "cxr_tat_p90":  qtl(tat_cxr, 0.9),
        "ct_tat_p50":   qtl(tat_ct, 0.5),  "ct_tat_p90":   qtl(tat_ct, 0.9)
    }

    tables = {
        "patients": patients,
        "encounters": encounters,
        "capacity_snapshots": cap_df,
        "orders": orders,
        "results": results,
        "events": events
    }
    return tables, metrics

# ------------------ helpers for actions ------------------

ACTIONS = ["none","place_labs","place_xray","place_ct","page_cardiology","page_neurology","prepare_admit_ward","prepare_admit_icu"]
ACTION2ID = {a:i for i,a in enumerate(ACTIONS)}
def _action_id(name: str) -> int:
    return ACTION2ID.get(name, 0)

# ------------------ HL7 emission ------------------

def _msh(msg_type, msg_id, ts):
    return f"MSH|^~\\&|SYNTH|SIM|ED|SIM|{_ts(ts)}||{msg_type}|{msg_id}|P|2.5"

def _pid(patient_id, last="DOE", first="JANE", dob="19800101", sex="U"):
    return f"PID|||{patient_id}||{last}^{first}||{dob}|{sex}"

def _join(segs):
    return "\\r".join(segs) + "\\r"

def emit_hl7(tables: Dict[str,pd.DataFrame], base_dir="./ed_demo_data", write_orders=True, write_results=True) -> List[str]:
    base = Path(base_dir); outbox = base/"orbis_sim"/"outbox"; inbox = base/"orbis_sim"/"inbox"; processed = base/"orbis_sim"/"processed"
    for p in (outbox, inbox, processed): p.mkdir(parents=True, exist_ok=True)
    written = []

    # ADT A04 per encounter
    for _, row in tables["encounters"].iterrows():
        ts = pd.to_datetime(row["arrival_ts"]).to_pydatetime()
        pid = row["patient_id"]; mid = f"ADT{int(ts.timestamp())}"
        adt = _join([_msh("ADT^A04", mid, ts), _pid(pid), "PV1||E||||||||||||||||||"])
        f = outbox / f"{_ts(ts)}_ADT_A04_{pid}.hl7"
        f.write_text(adt); written.append(f.as_posix())

    if write_orders and "orders" in tables:
        for _, row in tables["orders"].iterrows():
            ts = pd.to_datetime(row["ts_placed"]).to_pydatetime()
            pid = tables["encounters"][tables["encounters"]["enc_id"]==row["enc_id"]]["patient_id"].values[0]
            code = row["code"]; placer = row["placer_id"]; filler = row["accession"]
            orm = _join([_msh("ORM^O01", f"ORM{int(ts.timestamp())}", ts),
                         _pid(pid),
                         f"ORC|NW|{placer}|{filler}|||||{_ts(ts)}",
                         f"OBR|1|{placer}|{filler}|{code}|||{_ts(ts)}"])
            f = inbox / f"{_ts(ts)}_ORM_O01_{pid}_{placer}.hl7"
            f.write_text(orm); written.append(f.as_posix())

    if write_results and "results" in tables:
        for _, row in tables["results"].iterrows():
            ts = pd.to_datetime(row["ts_result"]).to_pydatetime()
            pid = tables["encounters"][tables["encounters"]["enc_id"]==row["enc_id"]]["patient_id"].values[0]
            acc = row["accession"]; code = row["code"]
            if pd.isna(row.get("report_text", None)) and not pd.isna(row.get("value", np.nan)):
                # numeric ORU
                value = row["value"]; units = row.get("units","")
                oru = _join([_msh("ORU^R01", f"ORU{int(ts.timestamp())}", ts),
                             _pid(pid),
                             f"OBR|1|{acc}|{acc}|{code}|||{_ts(ts)}",
                             f"OBX|1|NM|{code}||{value}|{units}|||N||F|||{_ts(ts)}"])
            else:
                # text report
                text = (row.get("report_text") or "Final report").replace("\n","\\n")
                oru = _join([_msh("ORU^R01", f"ORU{int(ts.timestamp())}", ts),
                             _pid(pid),
                             f"OBR|1|{acc}|{acc}|{code}|||{_ts(ts)}",
                             f"OBX|1|TX|{code}||{text}||||||F|||{_ts(ts)}"])
            f = outbox / f"{_ts(ts)}_ORU_R01_{pid}_{acc}.hl7"
            f.write_text(oru); written.append(f.as_posix())

    return written

# ------------------ default config helper ------------------

def default_config() -> Dict[str, Any]:
    # A Python dict mirror of the YAML config (for environments without PyYAML).
    return {
        "arrival_process": {"base_per_hour":[6,5,5,5,6,8,10,12,14,16,18,20,20,18,16,14,14,16,18,16,12,10,8,6],
                            "ems_frac":0.35, "chest_pain_frac":0.50},
        "triage": {"system":"MTS", "level_probs": {1:0.08, 2:0.30, 3:0.42, 4:0.18, 5:0.02}},
        "syndromes": {
            "chest_pain":{"mix":{"stemi":0.06, "nstemi":0.24, "noncardiac":0.70}},
            "neuro_deficit":{},
            "polytrauma":{}
        },
        "resources": {"ct_scanners":1,"xray_rooms":2,"lab_analyzers":2,
                      "service_times_min":{"ct":{"shape":2.0,"scale":12},"xray":{"shape":2.0,"scale":6},"lab":{"shape":2.0,"scale":18}}},
        "capacity": {"icu_beds_total":12,"ward_beds_total":120,"icu_free_init":3,"ward_free_init":25,"update_every_min":15,"stale_prob":0.10},
        "behavior": {"repage_after_min":15,"escalate_after_min":25,"cardiology_reluctance_nstemi":0.35},
        "noise": {"missing_ts_prob":0.02,"duplicate_order_prob":0.01,"cancel_prob":0.03,"code_flip_prob":0.01},
        "sampling": {"bin_size_min":5, "day_start":"2025-08-12 00:00:00"}
    }
