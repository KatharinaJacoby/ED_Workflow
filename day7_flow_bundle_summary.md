# Day 7 — Flow Bundle v1.1 Summary
**Timestamp (Berlin):** 2025-08-10 19:14

## What changed today
- **Troponin Δ (0/1h) classifier** added with **assay‑specific** cutoffs:
  - **Roche Elecsys hs‑cTnT**: rule‑out 0h \<5 ng/L, or 0h \<12 and Δ1h \<3; rule‑in 0h ≥52 or Δ1h ≥5. (ESC/Manufacturer)  
  - **Abbott ARCHITECT hs‑cTnI**: rule‑in 0h ≥64 ng/L (ESC 2020 update) or Δ1h ≥6; rule‑out 0h \<2 or band 2–5 with Δ1h \<2 (note: imprecision near LoD).  
- ECG path now consumes the troponin class (rule‑in → **RED**; observe → **YELLOW** + automatic repeat).
- Unified loader now also brings in **Neurology**, **Psych**, and **System** packs.
- Synthetic demos updated for **both assays**.

## What you still need to attend to
1) **Confirm local assay & units** with your lab (Roche hs‑cTnT vs Abbott hs‑cTnI; ng/L vs ng/mL). Update `ASSAYS` if different.  
2) **Edge cases**: early presenters (<3 h symptoms), CKD, known CAD — keep clinical override; consider 0/2h path next.  
3) **Role‑targeted alert escalation** (nurse→resident→attending timers) — still off.  
4) **Local antibiotic ladders** (CAP/COPD/sepsis) — wire when you share regimens.  
5) Replace SOP‑Notaufnahme **scaffolds** with exact steps once PDFs are available.

## How to run
- Use the new notebook: `ed_agent_mesh_FLOW_BUNDLE_v1_1.ipynb` (run top‑to‑bottom).  
- Packs auto‑load if the YAMLs are present in `/mnt/data`.  
- Demos at the bottom show: ACS (Roche), ACS (Abbott), PE + CAP + Psych.

## References (for thresholds)
- ESC 0/1h algorithm and performance overview; 0/2h as validated alternative.  
- **Roche hs‑cTnT** rule‑in/out and Δ1h thresholds (manufacturer brochure).  
- **Abbott hs‑cTnI**: ESC 2020 rule‑in at **64 ng/L**; Δ1h **6 ng/L**; rule‑out **2 ng/L** single or **2–5 with Δ\<2**; note analytical imprecision near LoD.

— End of day 7.
