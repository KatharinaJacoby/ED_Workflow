from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Dict

@dataclass
class RuleRow:
    icd: str
    title: str
    group: str
    eligibility: str                 # "BVB" | "LHB" | "NONE"
    requires_second_icd: bool
    second_icd_hint: str
    acute_window_months: Optional[int]
    notes: str
    source_url: str
    source_version: str

@dataclass
class PatientContext:
    icds: List[str]
    acute_event_date: Optional[date] = None

@dataclass
class EligibilityResult:
    icd: str
    eligible: bool
    kind: Optional[str]              # "BVB" | "LHB" | None
    conditions_met: Dict[str, bool]
    missing: List[str]
    explain: str
    source_version: str

def months_between(d1: date, d2: date) -> int:
    return (d1.year - d2.year)*12 + (d1.month - d2.month) - (1 if d1.day < d2.day else 0)

f.loc[df["icd"]=="I63.9", ["title","group","eligibility"]] = [
    "Hirninfarkt, nicht näher bezeichnet", "", "NONE"
]
df.to_csv("/kaggle/working/diagnoseliste_curated.csv", index=False)


    if rule.acute_window_months is not None:
        if ctx.acute_event_date:
            conds["acute_window_ok"] = months_between(today, ctx.acute_event_date) <= rule.acute_window_months
            if not conds["acute_window_ok"]:
                missing.append(f"Frist nach Akutereignis ≤ {rule.acute_window_months} Monate")
        else:
            conds["acute_window_ok"] = False
            missing.append("Datum des Akutereignisses erforderlich")

    eligible = all(conds.values()) and rule.eligibility in {"BVB", "LHB"}
    explain = f"{rule.icd} – {rule.title or 'Diagnose'}: "
    explain += ("qualifiziert" if eligible else "qualifiziert nicht")
    if rule.eligibility in {"BVB","LHB"}:
        explain += f" für {rule.eligibility}"
    if rule.group:
        explain += f" (Diagnosegruppe {rule.group})"
    if rule.notes:
        explain += f". {rule.notes}"

    return EligibilityResult(
        icd=rule.icd,
        eligible=eligible,
        kind=rule.eligibility if eligible else None,
        conditions_met=conds,
        missing=missing,
        explain=explain.strip(),
        source_version=rule.source_version,
    )

def evaluate_patient(ctx: PatientContext, rules_by_icd: Dict[str, RuleRow], today: date):
    results = []
    for icd in ctx.icds:
        rule = rules_by_icd.get(icd)
        if rule:
            results.append(check_rule(rule, ctx, today))
    return results

def normalize_icds(s: str) -> List[str]:
    import re
    toks = re.split(r"[,\s;]+", (s or "").strip())
    return [t.upper() for t in toks if t]

def icd_neighbors(icd: str, all_icds: List[str], k: int = 20) -> List[str]:
    # simple “family” by stem (R26.* etc.)
    if len(icd) >= 4 and icd[3] == ".":
        stem = icd[:4]
    else:
        stem = icd[:3] + "."
    return [x for x in sorted(all_icds) if x.startswith(stem)][:k]
