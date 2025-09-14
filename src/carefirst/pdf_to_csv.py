import re, csv, hashlib, os
from typing import List, Dict, Optional
from pdfminer.high_level import extract_text

# Columns your rule engine expects
COLUMNS = ["icd","title","group","eligibility","requires_second_icd",
           "second_icd_hint","acute_window_months","notes","source_url","source_version"]

ICD_RX = re.compile(r"\b([A-TV-Z]\d{2}(?:\.\d)?)\b")  # e.g., R26.2, G35, I63.9
MONTHS_RX = re.compile(r"längstens\s+(\d+)\s*(?:Monat|Monate)", re.IGNORECASE)

def sha16(path:str)->str:
    h = hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def parse_pdf(pdf_path: str, version_hint: str, default_url: str="") -> List[Dict]:
    text = extract_text(pdf_path) or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows: Dict[str, Dict] = {}

    for ln in lines:
        codes = list(ICD_RX.finditer(ln))
        if not codes:
            continue

        # crude title: remove all ICDs from the same line
        title_guess = ICD_RX.sub("", ln).strip()
        title_guess = re.sub(r"\s{2,}", " ", title_guess)

        # detect “längstens X Monate …” constraints
        months = None
        mm = MONTHS_RX.search(ln)
        if mm:
            try:
                months = int(mm.group(1))
            except:
                months = None

        # lightweight eligibility heuristics (optional; you can leave as NONE and curate later)
        elig = "NONE"
        ln_low = ln.lower()
        if "besonderer verordnungsbedarf" in ln_low:
            elig = "BVB"
        elif "langfrist" in ln_low and "heilmittel" in ln_low:
            elig = "LHB"

        for m in codes:
            icd = m.group(1).upper()
            if icd not in rows:
                rows[icd] = dict(
                    icd=icd,
                    title=title_guess[:160],
                    group="",                          # fill later if needed
                    eligibility=elig,                  # can be curated later
                    requires_second_icd=False,         # set True later if entry requires it
                    second_icd_hint="",
                    acute_window_months=months,        # keep months if we saw them
                    notes="",
                    source_url=default_url,
                    source_version=version_hint,
                )
            else:
                # complement months if previously unknown
                if rows[icd]["acute_window_months"] is None and months is not None:
                    rows[icd]["acute_window_months"] = months
                # prefer BVB/LHB over NONE if detected on another line
                if rows[icd]["eligibility"] == "NONE" and elig in {"BVB","LHB"}:
                    rows[icd]["eligibility"] = elig

    # return as sorted list
    out = [rows[k] for k in sorted(rows.keys())]
    return out

def write_csv(records: List[Dict], csv_path: str):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in records:
            # normalize boolean to True/False
            r["requires_second_icd"] = bool(r.get("requires_second_icd", False))
            w.writerow({k: r.get(k, "") for k in COLUMNS})

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", default="2025-01-01")
    ap.add_argument("--url", default="")
    args = ap.parse_args()

    recs = parse_pdf(args.pdf, version_hint=args.version, default_url=args.url)
    write_csv(recs, args.out)
    print(f"Wrote {len(recs)} rows → {args.out}")
