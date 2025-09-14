
# Day 1+2
**Hamburg Safety Mamba Hybrid Prototype Project
**
This document chronicles the development of the Hamburg Safety Mamba hybrid prototype through iterative testing, debugging, and methodology refinements. The project is inspired by the APONA framework but is driven by a safety-first, clinician-informed approach that prioritizes patient and staff wellbeing.

## 1. Project Overview

- **Idea**: Build a hybrid clinical–temporal model to predict system breakdown, staff wellbeing deterioration (burnout, retention risk), and patient safety degradation in Hamburg EMS/ED workflows.
- **Architecture**:
  - **Clinical encoder**: `HamburgClinicalEncoder` transforms vitals, demographics, system, and environmental features into a unified representation.
  - **Backbone**: GRU (proof‑of‑concept) with a future plan to swap in a Mamba temporal backbone for long‑range reasoning.
  - **Output heads**:
    - **Crisis classification** (multi‑class)
    - **Burnout risk** (regression 0‑1)
    - **Retention probability** (regression 0‑1)
    - **Response delay** (regression in minutes)
    - **Safety metrics** (handoff quality, documentation completeness, adverse event risk)

## 2. Initial Unit Test with Synthetic Data

> **Date:** 2025‑08‑04  
> **Milestone:** End‑to‑end test of hybrid model with synthetic input  
> **Author:** Katharina (Physician‑led AI Safety Researcher)

We verified that the hybrid model processes synthetic clinical/system tensors correctly:

| Key              | Shape        | Sample Value                          |
|------------------|--------------|---------------------------------------|
| `crisis_logits`  | (2, 5)       | `[0.06, 0.01, -0.02, 0.09, -0.06]`    |
| `burnout`        | (2,)         | `0.51`                                |
| `fatigue`        | (2,)         | `0.96`                                |
| `retention`      | (2,)         | `0.51`                                |
| `response_delay` | (2,)         | `0.04`                                |
| `quality`        | (2,)         | `0.52`                                |
| `adverse_risk`   | (2,)         | `0.50`                                |

- Encoder outputs match expected dimensions (`d_model`).
- GRU backbone runs without tensor shape mismatches.
- Output heads produce interpretable baseline predictions.

## 3. Session Progress and Major Fixes

The following log captures key iterations, challenges, and resolutions during model development:

### 3.1 Tensor Shape and Batch Mismatch

- **Issue**: GRU expected 3D input, but feature stacking produced 4D tensors.
- **Fix**: Consolidated feature stacking into a single tensor of shape `(batch_size, sequence_length, feature_dim)` before feeding into the GRU.

### 3.2 Syntax and DataLoader Construction

- **Issue**: SyntaxErrors and NameErrors arose from emojis, missing imports, and undefined variables (`config`, `model`, `train_loader`).
- **Fixes**:
  - Removed all emojis and non-ASCII characters from code artifacts.
  - Consolidated import statements (`train_test_split`, `nn`, `optim`, etc.) at the top of each notebook.
  - Clearly defined `config = SmallConfig()` or `HamburgMambaConfig()` in Cell 1.
  - Structured DataFrame splitting on `patient_id` to preserve full sequences in train/validation sets.
  - Ensured `HamburgGroundTruthDataset` and `HybridSafetyModel` classes are declared before DataLoader usage.

### 3.3 Real‑Data Generator Integration

- **Issue**: Early training runs used placeholder synthetic targets; real crisis labels were not wired in.
- **Plan**:
  - Integrated `HamburgGroundTruthGenerator.generate_complete_ground_truth(...)` in `make_real_hamburg_df`.
  - The real DataFrame now contains coherent sequences of ground‑truth labels for crisis_level, burnout_risk, retention_probability, response_delay, and safety metrics.

### 3.4 Multi‑Task Loss and Uncertainty Weighting

- **Implementation**: Adopted a multi-task loss wrapper with learnable log‑variance (`log_vars`) to balance classification and regression signals:
  ```
  total_loss = Σ [exp(-log_var_i) * loss_i + log_var_i]
  ```
- **Benefit**: Allows the model to dynamically adjust focus on tasks whose signals are more or less noisy during training.

### 3.5 Scheduler and Early Stopping

- Introduced `ReduceLROnPlateau` scheduler to reduce learning rate on validation stagnation.
- Implemented early stopping with patience (e.g. 10 epochs) and checkpointing of best model state.

### 3.6 Recurring Implementation of Fixes

Across multiple notebook restarts, the following pattern recurred:
1. Define `config`, `model`, and `dataset` classes in Cell 1–2.
2. Build `hamburg_df` and DataLoaders in Cell 3.
3. Execute forward pass in Cell 4 to confirm tensor shapes.
4. Initialize optimizer, loss wrapper, and scheduler in Cell 5.
5. Run full training loop in Cell 6 with run_epoch helper functions defined in Cell 2.

Each cycle revealed missing imports or mismatches that were promptly fixed following this template.

## 4. Next Steps

1. **Finalize Real‑Data Training**: Execute training on the fully generated real Hamburg dataset and verify metrics:
   - Crisis classification accuracy and confusion matrices.
   - Calibration of burnout/retention regressions.
2. **Swap Backbone**: Replace GRU with the Mamba SSM backbone and compare performance on long sequences.
3. **Hyperparameter Tuning**: Adjust learning rates, weight initializations, and scheduling strategies.
4. **Visualization and Reporting**: Plot training curves, auxiliary output distributions, and issue transparent session logs.
5. **Documentation**: Archive this merged development log for reproducibility.

**Contribution Goals**

This is a research-only, non-deployment project shared publicly to:

    Offer clinically aligned alternatives to exploitative hospital coordination AI

    Share open notebooks, simulation code, and modeling steps

    Invite feedback and collaboration from both technical and medical communities

**Collaboration Acknowledgment:**  
This document was assembled interactively by Katharina (physician-led AI researcher) and ChatGPT, summarizing the session’s bugs, fixes, and methodological steps.
