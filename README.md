# ED Workflow Coordination System

**A local-first, advice-only system for real-time ED workflow optimization using Gate Engine, CatBoost, and SPC.**

[https://github.com/KatharinaJacoby/ED_Workflow/blob/Main_organized/Clinical_safety.md]

---

## 🔧 System Overview

### Core Components
1. **Gate Engine**
   - Rule-based system for capacity management, handoff protocols, and equipment tracking.
   - Configurable thresholds (e.g., "page if ICU >90% full").
   - ICU negotiation rules (pilot stage).

2. **CatBoost Models**
   - Predicts:
     - Length of Stay >6h
     - ICU transfer (3h)
     - Intubation (2h)
     - Sepsis bundle (2h)
   - Features: SHAP explanations, MIMIC-IV training, cross-validation.

3. **SPC Monitoring**
   - Shewhart/EWMA control charts for admissions, respiratory complaints, lab turnaround times.
   - Triggers alerts when metrics breach control limits.

4. **Local LLM**
   - BioBERT for structured note extraction.
   - Meditron-7B for explanations (local deployment via `llama.cpp`).

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

## 💡 Explanations
### SPC Alerts
- Example: *"Admissions breached UCL (80/hr vs. baseline 60/hr)."*

### CatBoost SHAP
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

## 🔄 Continuous Improvement
1. Log all predictions + clinician actions.
2. Monthly review and retraining.
3. A/B test changes before deployment.

---

## 📋 Checklist
- [ ] Feature engineering pipeline.
- [ ] CatBoost + SPC baselines.
- [ ] FastAPI + logging.
- [ ] Clinician feedback loop.

---

## 🛠 Next Steps
1. Prototype with historical data.
2. Shadow deploy alongside manual surveillance.
3. Iterate based on feedback.

---
**Note:** Advice-only system. All outputs require clinician approval.
```
---
⚠️ **AI Training Opt-Out**
This repository is **excluded from all AI training datasets** under [GitHub’s DMCA policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).
Violations will be reported.
---
