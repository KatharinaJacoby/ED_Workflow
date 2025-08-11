# Day 7 Summary — ED Pathway + Embedded Mesh

**Run status:** agents ran clean; trainer + mesh integration OK.

## Data + Split
- patients: (300, 10) | ems: (300, 9) | labs: (600, 4) | transfers: (300, 6)
- unique final units: ['ED-BOARD', 'EDObs', 'ICU', 'StepDown', 'Ward']
- split: train/val/test = 210/45/45
- pos_rate_train: 0.148 | pos_weight: 5.77

## Model
- parameters: 26817

### Validation by epoch
| epoch | train_loss | val_auc | val_bce |
|---:|---:|---:|---:|
| 1 | 1.2860 | 0.695 | 0.709 |
| 2 | 1.1857 | 0.741 | 0.709 |
| 3 | 1.2141 | 0.748 | 0.704 |
| 4 | 1.2094 | 0.774 | 0.705 |
| 5 | 1.1792 | 0.786 | 0.697 |
| 6 | 1.2484 | 0.797 | 0.687 |
| 7 | 1.1340 | 0.805 | 0.678 |
| 8 | 1.1272 | 0.816 | 0.668 |

### Test set
- n: 45 | AUC: 0.564 | BCE: 0.697

**Interpretation (blunt):**
- Validation AUC climbed to ~0.82 by epoch 8, but **test AUC is ~0.56 on n=45**. That gap suggests high variance and/or distribution mismatch.
- With n=45, uncertainty is large. Do **not** trust a single split. Move to repeated stratified CV or bootstrap CIs.
- Current class balance: pos_rate_train ~0.15 with pos_weight ~5.8. Keep, but verify label noise in positives.

## Disposition / Flow snapshot (test)
- summary: {'n': 45, 'icu_req_rate': 0.0, 'admit_rate': 1.0, 'board_rate': 0.4444444444444444, 'regional_rate': 0.26666666666666666, 'final_units': {'EDObs': 24, 'ED-BOARD': 20, 'StepDown': 1}}
- head (illustrative): [{'pid': 'S00100', 'prob': 0.480972, 'unit_req': 'EDObs', 'approved': True, 'final_unit': 'EDObs', 'to_hospital': 'Campus A', 'transferred': False, 'board_in_ed': False, 'joker_used': False}, {'pid': 'S00053', 'prob': 0.491624, 'unit_req': 'EDObs', 'approved': True, 'final_unit': 'EDObs', 'to_hospital': 'Campus A', 'transferred': False, 'board_in_ed': False, 'joker_used': False}, {'pid': 'S00182', 'prob': 0.48994, 'unit_req': 'EDObs', 'approved': True, 'final_unit': 'EDObs', 'to_hospital': 'Campus A', 'transferred': False, 'board_in_ed': False, 'joker_used': False}]

**Signals:**
- **icu_req_rate = 0.0** (in test) while **board_rate ~44%**. Either: (a) test cohort is low-acuity, (b) ICU request policy never triggers, or (c) capacity model pushes ED-BOARD too aggressively.
- Action: instrument the **decision to request ICU** (preconditions) and the **capacity state** at each decision point; print 5 example traces.

## What to fix next (short list)
1. **Evaluation hygiene**: 5x repeated *stratified* CV (or bootstrap) → report mean AUC ± CI; keep the current test set as a final holdout (n>100 if possible).
2. **Thresholding**: add calibration (Platt or isotonic) + decision curve; save `prob_at_fixed_sens/spec` so clinicians can pick an operating point.
3. **Regularization**: small dropout / L2; early stop on **val AUC**; checkpoint the best epoch.
4. **Flow realism**: ensure **ICU request** logic can actually fire when criteria met; add the 30-min retry loop you specified.
5. **Troponin**: switch to **Roche hs-cTnT 0/1-h** rules (GREEN/RED/YELLOW) with CKD guard; auto-schedule 1h ECG+troponin together.
6. **Audit**: write `jsonl` line per action (who/when/why) for reproducibility of flow decisions.

## Artifact
- /mnt/data/ed_trainer_v13_3_run_20250811-150810

