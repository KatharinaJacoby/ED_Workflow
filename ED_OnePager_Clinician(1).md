# ED Workflow Coordination — Clinician One‑Pager (2025-08-16 14:35 UTC)

## What this tool is
A **workflow coordination assistant** to reduce administrative load (paging, reminders, SOP surfacing, resource finding).  
**Not** a diagnostic system. It suggests actions you can **approve**/**dismiss**.

## What it does now (PoC)
- **Equipment tracking (QR):** scan stickers on ultrasound/crash cart → location & status update, quick **reserve** with expiry, **maintenance/cleaning** flags, charging/docking awareness.
- **SOP access:** search by symptom/protocol (e.g., “sepsis bundle”, “HF aFib”); quick‑open the SOP document. Usage is logged locally for quality review.
- **Time‑critical follow‑ups:**
  - **CT pending > 60 min** → *FOLLOW_UP_IMAGING*
  - **Cath/Endoscopy activation > 30 min** → *FOLLOW_UP_* reminder
- **Chest‑pain workflow hygiene (display‑only risk awareness):** serial troponin + **second ECG with second troponin**; delta review prompt (no diagnosis).
- **Patient‑holding safety:** > **2 h** since last assessment → *RECHECK_VITALS*; ≥ **4 h** wait, stable/non‑NPO → *OFFER_SNACKS/HYDRATION*.
- **Language barriers:** offline **phrase‑card hooks** only (no cloud translation; privacy‑safe).

## What it *doesn’t* do
- Doesn’t diagnose or override you.
- Doesn’t use **age/sex** to drive decisions (to avoid bias). Scores like MEWS/qSOFA/HEART are **display‑only**.
- Doesn’t send patient data off the device.

## How to use it in the demo
- **Find equipment:** scan QR → status board updates; reserve if needed; release when done; mark cleaning/maintenance as appropriate.
- **Handle reminders:** when a prompt appears, hit **Approve** if acting now or **Dismiss** if handled/already irrelevant.
- **Open SOPs:** search (“sepsis”, “chest pain”, “HF aFib”) → open the relevant SOP checklist/flow.
- **Chest pain serials:** ensure second troponin triggers a **second ECG** reminder; review delta prompt (display‑only).

## What we measure (to keep it useful)
- **Acceptance rate** (target ≥ 0.65), **alert‑fatigue proxy** (target ≤ 0.30)
- **Clicks/seconds saved** (admin effort avoided)
- **Repeat prompts per encounter** (should trend toward ≤ 1)

## Known gaps (PoC)
- No multi‑patient **status board UI** yet (overdue assessments, vitals deltas).
- SOP **flowchart/checklist viewer** is a placeholder.
- Analytics reports (e.g., time‑to‑find‑equipment) are basic.
- Maintenance notifications to radiology/biomed not wired to real endpoints.

## Near‑term improvements (you’ll see next)
- Patient status board, SOP checklist tracker, richer analytics.
- More operational skills (e.g., expedite labs for deteriorating patients).

**Bottom line:** You approve/decline; the assistant reduces the busywork and keeps track of time‑critical tasks and resources.
