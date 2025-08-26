# De-dup Patch Report

## mimic-mlp-pipeline-phase1-2-baseline.ipynb
### Removed: `refresh_sop_registry` in cell 10 (lines 5-57); kept version in cell 12

```python
def refresh_sop_registry(CONFIG: Any, base_url: str="https://sop-notaufnahme.de/sop/")->Dict[str,Any]:
    out_csv=Path(CONFIG["SOP_REGISTRY_PATH"]); pdf_dir=Path(CONFIG["DATA_ROOT"])/"sop_pdfs"; pdf_dir.mkdir(parents=True, exist_ok=True)
    try:
        import requests; from bs4 import BeautifulSoup
    except Exception as e:
        return {"found":0,"saved":0,"errors":1,"error":f"missing libs: {e}"}
    found=saved=errors=0; items=[]
    try:
        r=requests.get(base_url, timeout=15); r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser")
        links=sorted({a["href"] for a in soup.find_all("a", href=True) if "/product/" in a["href"] and a["href"].startswith("http")})
        for url in links:
            try:
                pr=requests.get(url, timeout=15); pr.raise_for_status(); ps=BeautifulSoup(pr.text,"html.parser")
                ttag=ps.find(["h1","h2"]); title=ttag.get_text(strip=True) if ttag else (ps.find("title").get_text(strip=True) if ps.find("title") else url)
                pdfs=[a["href"] for a in ps.find_all("a", href=True) if a["href"].lower().endswith(".pdf")]
                pdf_url=pdfs[0] if pdfs else None; sop_id=_slugify(title or url.split("/")[-2]); pdf_path=""
                if pdf_url:
                    try:
                        fn=sop_id+".pdf"; outp=pdf_dir/fn
                        with requests.get(pdf_url, stream=True, timeout=30) as dr:
                            dr.raise_for_status()
                            with open(outp,"wb") as f:
                                for chunk in dr.iter_content(8192):
                                    if chunk: f.write(chunk)
                        pdf_path=str(outp); saved+=1
                    except Exception:
                        errors+=1; pdf_path=pdf_url
                items.append({"sop_id":sop_id,"title":title or sop_id,"pdf_path":pdf_path,"version":"","status":"fetched" if pdf_path else "linked","keywords":"","checklist":"","source_url":url})
                found+=1
            except Exception: errors+=1; continue
    except Exception as e:
        return {"found":0,"saved":0,"errors":1,"error":str(e)}
    import pandas as pd
    try:
        if out_csv.exists(): df=pd.read_csv(out_csv)
        else: df=pd.DataFrame(columns=["sop_id","title","pdf_path","version","status","keywords","checklist","source_url"])
        df=df.copy()
        if df.empty: new_df=pd.DataFrame(items)
        else:
            df["sop_id"]=df["sop_id"].astype(str)
            for i in items:
                mask=(df["sop_id"]==str(i["sop_id"]))
                if mask.any():
                    for k,v in i.items():
                        if k in df.columns and (pd.isna(df.loc[mask,k]).all() or str(df.loc[mask,k].iloc[0]).strip()=="" or k in ["pdf_path","status","source_url"]):
                            df.loc[mask,k]=v
                else:
                    df=pd.concat([df, pd.DataFrame([i])], ignore_index=True)
            new_df=df
        new_df.to_csv(out_csv, index=False)
    except Exception as e:
        errors+=1
    return {"found":found,"saved":saved,"errors":errors,"csv":str(out_csv),"dir":str(pdf_dir)}
```
### Removed: `calc_qsofa` in cell 24 (lines 31-35); kept version in cell 25

```python
def calc_qsofa(v: Dict[str,Any]):
    rr=_pick(v,["rr","resp_rate"]); sbp=_pick(v,["sbp","systolic"]); gcs=_pick(v,["gcs"],float)
    avpu = (v.get("avpu") or "").upper()[:1]
    altered = (gcs is not None and gcs<15) or avpu in {"V","P","U"}
    return {"name":"qSOFA","score": int((rr is not None and rr>=22)) + int((sbp is not None and sbp<=100)) + int(altered)}
```
### Removed: `calc_mews` in cell 24 (lines 37-43); kept version in cell 25

```python
def calc_mews(v: Dict[str,Any]):
    def rr_s(x):  return 3 if x is not None and x<=8 else (0 if x and 9<=x<=14 else (1 if x and 15<=x<=20 else (2 if x and 21<=x<=29 else (3 if x and x>=30 else 0))))
    def hr_s(x):  return 2 if x is not None and x<=40 else (1 if x and 41<=x<=50 else (0 if x and 51<=x<=100 else (1 if x and 101<=x<=110 else (2 if x and 111<=x<=129 else (3 if x and x>=130 else 0)))))
    def sbp_s(x): return 3 if x is not None and x<=70 else (2 if x and 71<=x<=80 else (1 if x and 81<=x<=100 else (0 if x and 101<=x<=199 else (2 if x and x>=200 else 0))))
    def t_s(x):   return 2 if x is not None and x<=35.0 else (1 if x and 35.1<=x<=36.0 else (0 if x and 36.1<=x<=38.0 else (1 if x and 38.1<=x<=38.5 else (2 if x and x>=38.6 else 0))))
    def avpu_s(x): return {"A":0,"V":1,"P":2,"U":3}.get((x or "A").upper()[:1],0)
    return {"name":"MEWS","score": int(rr_s(_pick(v,["rr"]))+hr_s(_pick(v,["hr","pulse"]))+sbp_s(_pick(v,["sbp"]))+t_s(_pick(v,["temp"]))+avpu_s(v.get("avpu")))}
```
### Removed: `calc_heart` in cell 24 (lines 45-52); kept version in cell 25

```python
def calc_heart(p: Dict[str,Any]):
    age=_pick(p,["age"],int); hist=_pick(p,["heart_history"],int); ecg=_pick(p,["heart_ecg"],int); risk=_pick(p,["heart_risk"],int)
    trop=_pick(p,["troponin","hs_troponin","trop"]); uln=_pick(p,["troponin_uln"],float)
    age_s = 2 if (age is not None and age>=65) else (1 if (age is not None and 45<=age<=64) else 0)
    ratio = (trop/uln) if (trop is not None and uln) else None
    trop_s = 2 if (ratio is not None and ratio>3) else (1 if (ratio is not None and 1<ratio<=3) else 0)
    total = (hist or 0)+(ecg or 0)+age_s+(risk or 0)+trop_s
    return {"name":"HEART","score": int(total)}
```
### Removed: `calc_grace_coarse` in cell 24 (lines 54-61); kept version in cell 25

```python
def calc_grace_coarse(p: Dict[str,Any]):
    age=_pick(p,["age"],int); hr=_pick(p,["hr","pulse"]); sbp=_pick(p,["sbp"]); crea=_pick(p,["creatinine"])
    sc=0
    if age is not None: sc += (0 if age<40 else 20 if age<60 else 40 if age<80 else 60)
    if hr  is not None: sc += (0 if hr<70  else 10 if hr<90  else 20 if hr<110 else 30 if hr<150 else 40)
    if sbp is not None: sc += (40 if sbp<80 else 30 if sbp<100 else 10 if sbp<120 else 0)
    if crea is not None: sc += (0 if crea<1.2 else 10 if crea<2.0 else 20 if crea<3.0 else 30)
    return {"name":"GRACE_coarse","score": int(sc)}
```
### Removed: `calc_sofa_min` in cell 24 (lines 63-76); kept version in cell 25

```python
def calc_sofa_min(v: Dict[str,Any], labs: Dict[str,Any]):
    pf=None; pao2=_pick(labs,["pao2"]); fio2=_pick(labs,["fio2"])
    if pao2 is not None and fio2:
        try: pf=float(pao2)/float(fio2)
        except Exception: pf=None
    plate=_pick(labs,["platelets","plt"]); bili=_pick(labs,["bilirubin"]); mapv=_pick(v,["map"]); gcs=_pick(v,["gcs"]); crea=_pick(labs,["creatinine"])
    sc=0
    if pf is not None:    sc += (4 if pf<100 else 3 if pf<200 else 2 if pf<300 else 1 if pf<400 else 0)
    if plate is not None: sc += (4 if plate<20 else 3 if plate<50 else 2 if plate<100 else 1 if plate<150 else 0)
    if bili  is not None: sc += (4 if bili>=12 else 3 if bili>=6 else 2 if bili>=2 else 1 if bili>=1.2 else 0)
    if mapv  is not None: sc += (1 if mapv<70 else 0)  # presence-guarded (MAP not required)
    if gcs   is not None: sc += (4 if gcs<6 else 3 if gcs<10 else 2 if gcs<13 else 1 if gcs<15 else 0)
    if crea  is not None: sc += (4 if crea>=5 else 3 if crea>=3.5 else 2 if crea>=2 else 1 if crea>=1.2 else 0)
    return {"name":"SOFA_min","score": int(sc)}
```
### Removed: `calc_sirs` in cell 24 (lines 78-85); kept version in cell 25

```python
def calc_sirs(p: Dict[str,Any]):
    crit = {
        "temp>38/<36": int(((_pick(p,["temp"],float) or 37)>38) or ((_pick(p,["temp"],float) or 37)<36)),
        "hr>90": int((_pick(p,["hr","pulse"],float) or 0) > 90),
        "rr>20/paco2<32": int(((_pick(p,["rr"],float) or 0) > 20) or ((_pick(p,["paco2"],float) or 100) < 32)),
        "wbc>12/<4/bands>10%": int(((_pick(p,["wbc"],float) or 7) > 12) or ((_pick(p,["wbc"],float) or 7) < 4) or ((_pick(p,["bands_pct"],float) or 0) > 10)),
    }
    return {"name":"SIRS","score": int(sum(crit.values()))}
```
### Removed: `sepsis3_screen` in cell 24 (lines 87-91); kept version in cell 25

```python
def sepsis3_screen(v: Dict[str,Any], labs: Dict[str,Any], ctx: Dict[str,Any], sofa_min: Dict[str,Any], qsofa: Dict[str,Any]):
    sus = _bool(ctx.get("suspected_infection")); on_pressors=_bool(ctx.get("vasopressors"))
    mapv=_pick(v,["map"]); lact=_pick(labs,["lactate"])
    septic_shock = bool((mapv is not None and mapv<65) and (lact is not None and lact>2) and on_pressors)
    return {"name":"SEPSIS3","sepsis_flag": bool(sus and sofa_min["score"]>=2), "septic_shock": septic_shock}
```

## mimic-mlp-pipeline-phase1-2-baseline-patched.ipynb
### Removed: `assess_troponin_delta` in cell 22 (lines 1-7); kept version in cell 26

```python
def assess_troponin_delta(series):
    from datetime import datetime
    if not series or len(series)<2: return {'available':False}
    to_ng_l=lambda v,u: float(v)*(1000.0 if ('µg' in str(u).lower() or 'ug' in str(u).lower()) else 1.0)
    (t0,v0,u0),(t1,v1,u1)=sorted(series,key=lambda x:x[0] or datetime.min)[-2:]
    p,c=to_ng_l(v0,u0),to_ng_l(v1,u1); d=c-p; pct=(abs(d)/p*100.0) if p else None
    return {'available':True,'prev':p,'curr':c,'delta_abs':d,'delta_pct':pct,'flag':(abs(d)>=51.0) or (pct is not None and pct>=20.0)}
```
