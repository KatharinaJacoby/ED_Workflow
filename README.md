# CARE (Clinical Assessment & Risk Engine)

**A local-first, advice-only system for real-time ED workflow optimization using Gate Engine, CatBoost, and SPC.**

## 🏆 Winner of the Hackathon of Emergency Medicine at ICEM 2026!

> **A big thank you to the Hackathon team for Presentation Design & Clinical Framing** – we had a lot of fun and not much sleep 🚀
>
> **Call for Collaborators:** I am looking for **informaticians** and **EM physicians** to take over maintenance, EHR integration, and further development. If you are interested in stewarding this tool, please contact me via GitHub Issues or my clinic homepage.

---

## 🔧 System Overview

CARE is designed to support—not replace—clinical judgment. It transforms fragmented emergency department data into unified, actionable insights while maintaining strict human oversight.

### Core Components

1.  **Gate Engine**
    *   **Function:** Rule-based system for capacity management, handoff protocols, and equipment tracking.
    *   **Features:** Configurable thresholds (e.g., "page if ICU >90% full") and pilot-stage ICU negotiation rules.
    *   **Philosophy:** Logic is separated from configuration; hospitals can adapt rules to local SOPs without code changes.

2.  **CatBoost Models**
    *   **Predictions:**
        *   Length of Stay >6h
        *   ICU transfer (3h)
        *   Intubation risk (2h)
        *   Sepsis bundle activation (2h)
    *   **Safety:** Trained on MIMIC-IV with cross-validation; outputs include **SHAP explanations** so clinicians understand *why* a risk was flagged.

3.  **SPC Monitoring**
    *   **Function:** Shewhart/EWMA control charts for admissions, respiratory complaints, and lab turnaround times.
    *   **Alerting:** Triggers when metrics breach statistical control limits, providing an early warning system for outbreaks or resource strain.

4.  **Local LLM Integration**
    *   **BioBERT:** For structured note extraction and semantic analysis.
    *   **Meditron-7B:** For generating natural language explanations (deployed locally via `llama.cpp` to ensure data sovereignty).

---

## 🛡️ Clinical Safety & Ethics

> **"The right information, at the right time, to the right people."**

This system operates under a strict **Advice-Only Protocol**. All outputs require explicit clinician approval before any action is taken. No automated orders are generated.

*   **[Read the Full Clinical Safety Manifesto](https://github.com/KatharinaJacoby/ED_Workflow/blob/Main_organized/Clinical_safety.md)**

### Key Safety Principles
*   **Sustained Ambiguity:** The system is designed to hesitate and present uncertainty rather than force a rushed decision.
*   **Explainability:** Every prediction includes SHAP values detailing the contributing factors (e.g., "Flagged due to rising lactate + low SpO₂").
*   **Fail-Safes:**
    *   *False Positives:* Mitigated by requiring CatBoost confidence >0.9 for critical alerts.
    *   *False Negatives:* Fallback to SPC-only alerts if model confidence drops.
    *   *Data Drift:* Automatic weekly retraining triggers and SPC updates.

---

## 📦 Data Pipeline

### Feature Engineering
```python
def create_features(df):
    df["admissions_rolling_6h"] = df["admissions"].rolling(6).mean()
    df["respiratory_pct_change_24h"] = df["respiratory_complaints"].pct_change(24)
    df["cold_snap"] = (df["temp"] < 5).astype(int)
    df["school_holiday"] = df["date"].isin(school_holidays)
    return df
```

### Labeling
```python
df["outbreak_flag"] = 0
df.loc[(df["admissions"] > df["admissions_ucl"]) & (df["vomiting_pct"] > 0.15), "outbreak_flag"] = 1
df.loc[df["date"].between("2023-01-03", "2023-01-05"), "outbreak_type"] = "norovirus"
```

---

## 🤖 Model Training

### CatBoost
```python
from catboost import CatBoostClassifier

model = CatBoostClassifier(
    depth=6,
    learning_rate=0.05,
    iterations=500,
    l2_leaf_reg=3,
    cat_features=["triage_acuity", "chief_complaint", "allergies"]
)
model.fit(X_train, y_train["outbreak_type"])
```

### SPC
```python
from pyculiarity import detect_cusum
cusum_results = detect_cusum(df["respiratory_complaints"], threshold=1.0, drift=0.1)
df["cusum_alert"] = cusum_results["alert"]
```

---

## 📈 Evaluation
| Metric            | Target      |
|-------------------|-------------|
| Precision         | > 0.9       |
| Recall            | > 0.8       |
| F1 Score          | > 0.85      |
| Time-to-Detection | < 6 hours   |

```python
from sklearn.metrics import classification_report
print(classification_report(y_true=df["outbreak_type"], y_pred=model.predict(X_test)))
```

---

## 🚀 Deployment

### FastAPI Endpoint
```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/predict")
def predict(data: dict):
    features = preprocess(data)
    spc_alert = check_spc(features)
    catboost_probs = model.predict_proba(features)
    return {
        "spc_alert": spc_alert,
        "catboost_probs": catboost_probs.tolist(),
        "recommended_actions": get_actions(spc_alert, catboost_probs)
    }
```

### Logging
```python
import logging
logging.basicConfig(filename="outbreak_logs.csv", level=logging.INFO)
```

---

## 💡 Explanations & Transparency

### SPC Alerts Example
> *"Admissions breached UCL (80/hr vs. baseline 60/hr)."*

### SHAP Visualization
Every high-risk prediction generates a plot showing feature contribution:

```python
import shap
explainer = shap.TreeExplainer(model)
shap.plots.waterfall(explainer.shap_values(real_time_data)[0])
```
---

## ⚠️ Failure Modes
| Failure          | Mitigation                          |
|------------------|-------------------------------------|
| False Positives  | Require CatBoost confidence > 0.9   |
| False Negatives  | Fallback to SPC-only alerts         |
| Data Drift       | Weekly retraining + SPC updates     |

---

## 🔄 Continuous Improvement Loop

    - Log: Record all predictions and subsequent clinician decisions.
    - Review: Monthly review of false positives/negatives with clinical leads.
    - Retrain: Weekly retraining cycles to account for seasonal shifts and data drift.
    - Test: A/B test protocol changes before full deployment.

## 📋 Roadmap

    - Feature engineering pipeline (Complete)
    - CatBoost baseline (Complete)
    - FastAPI + Logging (Complete)
    - Clinician feedback loop implementation
    - EHR integration adapters
    - Mobile dashboard for triage nurses

## Next Steps for Adopters

    - Prototype: Run against historical de-identified data.
    - Shadow Deploy: Run alongside manual surveillance without acting on alerts.
    - Iterate: Adjust thresholds based on local workflow and feedback.

## ⚠️ Important Notices
> Advice-Only Disclaimer
> This is an advice-only system. All outputs require explicit clinician approval. The software does not make autonomous medical decisions.
> AI Training Opt-Out. This repository is explicitly excluded from all AI training datasets under GitHub’s DMCA policy and ethical guidelines. Violations of this opt-out will be reported.

License

## Apache License 2.0 - **[Clinical Safety Manifesto](https://github.com/KatharinaJacoby/ED_Workflow/blob/Main_organized/Clinical_safety.md)**
 Free to use, modify, and distribute for non-commercial and commercial purposes, provided attribution is given.

> Author: Dr. Katharina Jacoby
> Research Focus: AI Safety, Systems Engineering, Computational Topology
> Contact: k.jacoby at posteo.de
---
