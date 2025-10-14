# ED Workflow Coordination System

**A local-first, advice-only system for emergency department workflow optimization**

This project integrates a **Gate Engine**, **CatBoost predictive models**, and **Statistical Process Control (SPC)** to provide real-time, explainable advice for ED capacity management, anomaly detection, and root cause analysis—without automated decision-making.

---

## 🔍 Problem Framing

### Multi-Objective System
1. **Anomaly Detection (SPC)**
   - *Is the ED deviating from expected behavior?*
   - **Metrics:** Admissions/hour, % respiratory complaints, lab turnaround time.
   - **Output:** Binary alert (0/1) + confidence score.

2. **Root Cause Analysis (CatBoost)**
   - *What’s causing the anomaly?*
   - **Metrics:** Correlations between symptoms, labs, external factors (weather, events).
   - **Output:** Probability distribution over causes (e.g., flu: 0.7, norovirus: 0.2).

3. **Decision Automation (Gate Engine)**
   - *What should we do about it?*
   - **Actions:** Adjust capacity thresholds, reassign teams, trigger protocols.

**Formalization:**
- **Input (X):** Time-series + tabular data (EHR, labs, weather).
- **Output (Y):**
  - `Y_spc`: Binary anomaly flag.
  - `Y_catboost`: Probability vector over causes.
  - `Y_actions`: Recommended Gate Engine adjustments.

---

## 🛠 Core Components

### 1. Gate Engine
- **Purpose:** Rule-based system for capacity management, handoff protocols, and equipment tracking.
- **Features:**
  - Configurable thresholds (e.g., "page if ICU >90% full").
  - ICU negotiation rules (pilot stage).
  - **Rules as Code:** Adjust protocols based on model outputs.

### 2. CatBoost Models
- **Purpose:** Predictive models for:
  - Length of Stay > 6h
  - ICU transfer (3h)
  - Intubation (2h)
  - Sepsis bundle (2h)
- **Features:**
  - SHAP explanations for transparency.
  - Trained on MIMIC-IV ED data.
  - Cross-validated with isotonic calibration.
- **Configuration:**
  ```python
  CatBoostClassifier(
      depth=6,
      learning_rate=0.05,
      iterations=500,
      l2_leaf_reg=3,
      cat_features=["triage_acuity", "chief_complaint", "allergies"]
  )


---
⚠️ **AI Training Opt-Out**
This repository is **excluded from all AI training datasets** under [GitHub’s DMCA policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).
Violations will be reported.
---
