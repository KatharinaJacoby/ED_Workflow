

## Walk-ins & Social Discharge (added)
- **Walk-in triage:** triage within 10 min (`SLA_WALKIN_TRIAGE_MIN`). Gate `WALKIN_UNTRIAGED` if exceeded.
- **Re-triage:** if walk-in triaged Green/Yellow but high-risk symptoms or abnormal vitals → `RETRIAGE_NOW`.
- **Social placement:** `SOCIAL_PLACEMENT_REQUIRED` when `needs_social_placement` and not confirmed; `SOCIAL_PLACEMENT_BLOCKED` if ETA≥120 min, ETA unknown, or after-hours (no social worker).
- **Discharge blocked by social:** `DISCHARGE_BLOCK_SOCIAL` when clinically ready yet placement missing.
- **Primary-care follow-up:** `FOLLOWUP_GP_REQUIRED` when no GP or follow-up not scheduled (book community clinic/GP before discharge).


---
## Domain Summary (v1) — 2025-08-22T20:58:42Z

### Bias hygiene / safety
- Chest pain pathways **must not** use age/sex for gating (ECG/ACS workup).
- Younger patients can have stroke/ACS/myo-/peri-/endocarditis post-COVID; avoid “too young” heuristics.
- Pregnancy testing is **organ/exposure-based**: `pregnancy_possible` → test required; not tied to gender labels.

### Core fast-tracks & pathways
- **STEMI**: direct cathlab when stable; unstable → resus stabilize → cathlab; ECMO if criteria (even during CPR).
- **Stroke**: resus room handoff → **CT immediately** → neuro + ED attending + radiologist review → neuro ICU if stroke confirmed; otherwise ED.
- **Polytrauma**: resus → CT/OR as indicated.
- **Minor fast-track**: attendings may discharge; residents must present before transfer/discharge.

### Abdominal pain guardrails (treat as “brittle code”)
- No discharge **< 24h**; keep in Observation (<-> ED).
- **Labs ≥ 2 cycles** before disposition.
- **Ultrasound and/or CT** required; plain X-ray de-prioritized except constipation pathway.
- Pregnancy test when `pregnancy_possible=True`.

### Troponin / serial protocol
- Many transfers blocked until **troponin #2** drawn/resulted.
- Default intervals: draw #2 at **≥ 180 min** after #1; **overdue at ≥ 210 min** → escalate.
- Gate names: `TROP2_DUE`, `TROP2_OVERDUE` (block transfer readiness until cleared).

### Endoscopy orchestration
- If GI can scope “in a couple of hours”, patient waits in ED; track `endoscopy_eta_min`.
- Escalate if ETA **≥ 180 min** (`ENDO_WAIT`).

### Walk-ins (no GP / GP on vacation)
- Walk-in does **not** imply low severity; guard for undertreatment.
- **Triage within 10 min** (`WALKIN_UNTRIAGED` if exceeded).
- If triaged Green/Yellow **but** high-risk symptoms or abnormal vitals (SpO₂<92, RR>24, MAP<65, HF>120, GCS<15) → `RETRIAGE_NOW`.

### Social discharge & community linkage
- Some elderly cannot be sent home safely; require **nursing-home/social placement** before discharge.
- Gates: `SOCIAL_PLACEMENT_REQUIRED` (start search), `SOCIAL_PLACEMENT_BLOCKED` (ETA unknown/≥120 min or after-hours), `DISCHARGE_BLOCK_SOCIAL` (clinically ready but blocked), `FOLLOWUP_GP_REQUIRED` (no GP or no follow-up booked).
- Book **GP/community clinic** before discharge when `has_gp=False` or `gp_followup_scheduled=False`.

### Capacity, boarding & exit-block
- **Exit block is structural**: wards preserve elective bed flow; night shift deflects to protect safety/staff.
- Daytime **bed managers** coordinate placement; typically off-duty after ~16:00 → more deflection/friction.
- ICU frequently “too stable to admit” → ROSC/critical linger in ED: gates `ROSC_BED_ESCALATE`, `BED_ESCALATE`.
- Distinguish **transfer readiness** from **blocked**:
  - `TRANSFER_NOT_READY`: therapy plan or med rec or next steps missing (policy: leave ED with a treatment concept + orders).
  - `WARD_TRANSFER_BLOCKED`: beds reported free but ward not accepting **and** bed manager off-duty.
  - `EXIT_BLOCK`: admit decision made, waiting **≥ 60 min**.

### Lingering / reassessment
- Reassess vitals by triage: Red 0 (continuous), Orange 15, Yellow 30, Green 60 → `LINGERING_REASSESS`.
- `OBS_24H_ESCALATE`: total ED/Obs time ≥ 24h → force disposition.
- `SELF_DISCHARGE_RISK`: long ED stay (≥4h) **and** pending critical step (troponin #2 or endoscopy) → proactive communication to prevent AMA/self-discharge.

### Equipment & capacity telemetry
- `EQUIP_OVERDUE`: device last_seen ≥ 60 min (locate/refresh).
- `REFRESH_CAPACITY`: capacity telemetry stale (e.g., >10 min).

### Gate priorities (high-level)
- 5: Immediate harm / fast-tracks (RESUS_NOW, STEMI/STROKE/POLYTRAUMA, ROSC_BED_ESCALATE).
- 4: Time-critical steps (ECG_DUE, BED_ESCALATE, ABDOMEN_GUARDRAILS, TROP2_DUE/OVERDUE, WARD_TRANSFER_BLOCKED, EXIT_BLOCK, RETRIAGE_NOW).
- 3: Safety/completeness (LABS_OVERDUE in abdomen, CT_OVERDUE in abdomen, TRANSFER_NOT_READY, ENDO_WAIT, LINGERING_REASSESS).
- 2: Comfort/comms load (SELF_DISCHARGE_RISK, FOLLOWUP_GP_REQUIRED, EQUIP_OVERDUE).
- 1: Hygiene (REFRESH_CAPACITY, CONSTIPATION_PATHWAY).

### Field signals expected in `WorkflowState.feature_dict()` (additive, optional)
- Admission & discharge: `admit_decision` (bool), `admit_wait_min` (num), `discharge_ready` (bool).
- Transfer readiness: `therapy_plan_ready`, `med_rec_done`, `next_steps_ordered` (bools).
- Ward interface: `ward_beds_free` (num), `ward_acceptance` (bool), `bed_manager_on_duty` (bool).
- Troponin: `troponin_protocol_active` (bool), `since_trop1_min` (num), `trop2_done` (bool).
- Endoscopy: `endoscopy_eta_min` (num).
- Walk-ins: `walk_in` (bool), `triage_done` (bool).
- Social: `needs_social_placement`, `placement_confirmed` (bools), `placement_eta_min` (num), `social_worker_on_duty` (bool), `has_gp` (bool), `gp_followup_scheduled` (bool).
- Existing reused: `Triage`, `Leitsymptom`, `MAP`, `HF`, `SpO2`, `RR`, `GCS`, `Kap_veraltet`, `ICU_Kap`, `time_in_ed_min`, `since_arrival_min`, `since_vitals_min`.

### Config knobs (minutes unless stated)
- ECG 10; CT stroke 30; CT polytrauma 30; Obs limit 1440; Reassess (0/15/30/60); Equip overdue 60; Capacity stale 10.
- Troponin: interval 180; overdue 210.
- Admission escalate 60; Endoscopy escalate 180; Walk-in triage 10.
- Social placement escalate 120; hard 360.
All are in `CONFIG` and read by the gate engine; UI can expose sliders.

---

## Re-entry hook (single source of truth)
Treat this file as the **canonical policy**. Next time we resume:
1) Open `ops_policy.md` and skim **Domain Summary**.
2) Ensure `/mnt/data/ops_intel.py` is in the path; call:
   ```python
   from ops_intel import compute_gates_from_features
   res = compute_gates_from_features(state.feature_dict(), CONFIG)
   ```
3) If you add new policy, append it here **first**, then I’ll mirror into code in `ops_intel.py` (gate name + rule + TTL).

### Minimal resume checklist
- [ ] Reconfirm SLAs in CONFIG (UI sliders or static).
- [ ] Confirm bed manager duty window (either emit `bed_manager_on_duty` or let us derive by clock).
- [ ] Emit any new fields needed for gates you want to activate.
- [ ] Run the Sanity Pack (test cases for troponin, walk-in, social placement, exit-block).

### Optional: “one-line re-entry” cell (paste into your notebook)
```python
import sys; sys.path.append("/mnt/data")
from ops_intel import compute_gates_from_features
print("POLICY_VERSION: Domain Summary (v1) — 2025-08-22T20:58:42Z")
```

### Open questions to tighten later
- Do you run 0/1h or 0/2h troponin protocols for subsets? If yes, expose `trop_protocol` so rules switch per patient.
- Exact bed-manager hours per department; weekends/holidays different?
- Any endoscopy priority flags (bleeding/severe anemia) to bump `ENDO_WAIT` priority?
- Preferred escalation chain text for `WARD_TRANSFER_BLOCKED` and `EXIT_BLOCK` in your site.

---
