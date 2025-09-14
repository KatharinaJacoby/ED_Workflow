
# Day 5 ICU Capacity Modeling — Progress Summary

## 1. Project Overview
We aimed to build a hospital capacity prediction model focusing on **ICU and non-ICU bed availability** at UKE (Universitätsklinikum Hamburg-Eppendorf), with realistic department sizes.  
The simulation also covers **EMS arrivals**, suspected conditions, and operational constraints such as ICU bed kept open for resuscitation.

---

## 2. Baseline Setup
- Initial dataset: 500 simulated patient records
- Key features:
  - Patient demographics (`age`, `home_type`)
  - Clinical presentation (`suspected_condition`, `ems_triage_code`)
  - Hospital arrival timing (`day_of_week`, `hour_of_day`)
  - Departmental capacities (`cap_*` features for ICU & non-ICU)
- Initial model: **MLP (Multi-Layer Perceptron)**  
- Metric: MSE & MAE on validation/test

Baseline performance:
```
Validation MSE: ~0.0224
Validation MAE: ~0.1224
```
Training was stable, simple architecture for ease of debugging.

---

## 3. Simplifications and Adjustments
- Removed **sex** feature as not clinically relevant for this routing context.
- Focused on **EMS triage code** instead of raw vitals, since EMS interventions change vitals before ED arrival.
- Fixed hospital target to **UKE** for simplicity.
- Initially proposed simplifying ICU to a single bed count — decided against it.
- Instead:
  - Used **realistic ICU sizes** from UKE's published numbers (minus 1 bed for resuscitation).
  - Simulated non-ICU departments with generic capacity ranges (20–50 beds).
- Label generation updated to reflect **ICU bottleneck risk** and **assignment suitability**.

---

## 4. Failures & Bug Fixes
- **Metadata save issues** on Kaggle → solved by downloading notebook locally.
- `icu_assignment_suitability` KeyError → fixed by patching `generate_patient()` to include new labels.
- Removed references to unused features (`icu_bottleneck_risk`, `pathway_latency_min`, `route_plan`) in certain display calls.
- Encoding errors (`could not convert string to float`) → fixed by reusing fitted `ColumnTransformer` for consistent numeric arrays.
- Drop-feature retraining and target leakage checks successfully implemented after preprocessing fix.

---

## 5. ICU Sensitivity Analysis
### Method:
- Ran **permutation importance** on ICU and non-ICU features.
- Tested model without ICU features.

### Results:
- Removing ICU features slightly worsened performance:
```
No ICU features → Test MSE: 0.0262 | MAE: 0.1386
Baseline          → Test MSE: 0.0256 | MAE: 0.1313
```
- ICU capacities are clinically critical and often hard to transfer into — treating them as **bottlenecks** in planning is justified.

---

## 6. Decision on Complexity
- Considered simplifying to only ICU or only overall capacity.
- Rejected oversimplification:
  - ICU availability alone does not represent full operational reality.
  - Multi-task heads possible with current richer label set.
  - Non-ICU departments still matter for patient flow and bed planning.
- Kept expanded department capacity model.

---

## 7. Current Model Status
- **Inputs**: 39 features (categoricals encoded, capacities normalized)
- **Architecture**: MLP with dropout
- **Performance**:
  - Baseline test MSE: 0.0256
  - Stable convergence
- **Top features** include:
  - `ems_triage_code`
  - `cap_gastroenterology`
  - `cap_neurological_icu`
  - Several ICU and non-ICU departments

---

## 8. Next Steps
1. **Multi-task heads**:
   - Predict both `icu_assignment_suitability` and `ward_assignment_suitability`.
   - Optional: also predict pathway latency.
2. **Scenario testing**:
   - Simulate surge events (e.g., mass casualty, flu season).
3. **Calibration with real data**:
   - If available, fit to historic UKE bed occupancy.
4. **Routing policy optimization**:
   - Use trained model to recommend optimal patient distribution across departments.

---
