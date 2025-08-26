
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import re, os

def _cfg(CONFIG: Any, key: str, default: Any=None) -> Any:
    try:
        return CONFIG.get(key, default)
    except Exception:
        return getattr(CONFIG, key, default) if hasattr(CONFIG, key) else default

def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "sop"

def refresh_sop_registry(CONFIG: Any, base_url: str = "https://sop-notaufnahme.de/sop/") -> Dict[str, Any]:
    """
    Fetch the SOP index page and product pages, extract titles and PDF links,
    and update the local SOP_REGISTRY CSV and sop_pdfs directory.

    Returns summary dict: {"found": int, "saved": int, "errors": int}
    """
    out_csv = Path(_cfg(CONFIG, "SOP_REGISTRY_PATH"))
    pdf_dir = Path(_cfg(CONFIG, "DATA_ROOT", "/mnt/data")) / "sop_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception as e:
        # No network libs available; do nothing
        return {"found": 0, "saved": 0, "errors": 1, "error": f"missing libs: {e}"}

    found = 0
    saved = 0
    errors = 0
    items: List[Dict[str, str]] = []

    try:
        r = requests.get(base_url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # product links
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # heuristic: product pages under /product/ or page contains sop- in URL
            if "/product/" in href and href.startswith("http"):
                links.append(href)
        links = sorted(set(links))
        for url in links:
            try:
                pr = requests.get(url, timeout=15)
                pr.raise_for_status()
                ps = BeautifulSoup(pr.text, "html.parser")
                # title
                title = None
                ttag = ps.find(["h1","h2"])
                if ttag:
                    title = ttag.get_text(strip=True)
                if not title:
                    # fallback from meta title
                    mt = ps.find("title")
                    title = mt.get_text(strip=True) if mt else url
                # pdf link(s)
                pdfs = []
                for a2 in ps.find_all("a", href=True):
                    h2 = a2["href"]
                    if h2.lower().endswith(".pdf"):
                        pdfs.append(h2)
                pdf_url = pdfs[0] if pdfs else None
                sop_id = _slugify(title or url.split("/")[-2])
                pdf_path = ""
                if pdf_url:
                    try:
                        fn = sop_id + ".pdf"
                        outp = pdf_dir / fn
                        # stream download
                        with requests.get(pdf_url, stream=True, timeout=30) as dr:
                            dr.raise_for_status()
                            with open(outp, "wb") as f:
                                for chunk in dr.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                        pdf_path = str(outp)
                        saved += 1
                    except Exception:
                        errors += 1
                        pdf_path = pdf_url  # keep remote link
                items.append({
                    "sop_id": sop_id,
                    "title": title or sop_id,
                    "pdf_path": pdf_path,
                    "version": "",
                    "status": "fetched" if pdf_path else "linked",
                    "keywords": "",
                    "checklist": "",
                    "source_url": url,
                })
                found += 1
            except Exception:
                errors += 1
                continue
    except Exception as e:
        return {"found": 0, "saved": 0, "errors": 1, "error": str(e)}

    # Merge into CSV (idempotent by sop_id)
    import pandas as pd
    try:
        if out_csv.exists():
            df = pd.read_csv(out_csv)
        else:
            df = pd.DataFrame(columns=["sop_id","title","pdf_path","version","status","keywords","checklist","source_url"])
        df = df.copy()
        by_id = {str(r["sop_id"]): r for r in items}
        if df.empty:
            new_df = pd.DataFrame(items)
        else:
            df["sop_id"] = df["sop_id"].astype(str)
            # update or append
            for i in items:
                mask = df["sop_id"] == str(i["sop_id"])
                if mask.any():
                    for k,v in i.items():
                        if k in df.columns and (pd.isna(df.loc[mask, k]).all() or str(df.loc[mask, k].iloc[0]).strip()=="" or k in ["pdf_path","status","source_url"]):
                            df.loc[mask, k] = v
                else:
                    df = pd.concat([df, pd.DataFrame([i])], ignore_index=True)
            new_df = df
        new_df.to_csv(out_csv, index=False)
    except Exception as e:
        errors += 1

    return {"found": found, "saved": saved, "errors": errors, "csv": str(out_csv), "dir": str(pdf_dir)}

def load_priority_flows(json_path: str) -> Dict[str, Any]:
    """Load flow definitions (nodes/edges) from priority_flows.json"""
    import json
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

