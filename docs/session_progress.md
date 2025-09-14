# Session Progress Log

This document captures the development journey during the recent session, illustrating iterations, challenges, and decisions made while building the Hamburg Healthcare Safety Mamba and exploring hybrid alternatives.

---

## 1. Initial Mamba Architecture

- **Goal**: Build an SSM-based Mamba model to process complete patient pathways (EMS → ED → Ward → Discharge).
- **Key Components**:
  - `HamburgMambaConfig` with parameters: `d_model=512`, `n_layers=12`, `d_state=64`, etc.
  - `SelectiveSSMLayer` implementing state-space mechanism with convolution for local patterns.
  - `selective_scan_fn` doing a time-step loop for SSM dynamics.
  - Complete model integrating clinical encoding, Mamba blocks, and prediction heads.

**Outcome**: Model initialized successfully, but inference crashed with error `RuntimeError: a Tensor with 4 elements cannot be converted to Scalar` due to improper use of `.item()` on batch tensors.

---

## 2. Batch-Size Fixes

- **Issue**: Calling `.item()` on tensors of shape `[batch_size]` caused errors.
- **Fix**: Changed to aggregate via `.mean().item()` and adjusted `predict_system_breakdown` to compute warnings based on aggregate risk scores.

---

## 3. Tensor Shape and Math Mismatches

- **Observation**: For larger batch sizes, the model crashed or math didn’t align.
- **Investigation**:
  - Verified conv1d shapes and causal slicing.
  - Explored helper functions `einsum` and `rearrange` for correctness.
- **Simplification**: Created a minimal `SelectiveSSMLayer` and `selective_scan_fn` with explicit shape comments, tested on CPU with small dims.

**Minimal test code**:
```python
layer = SelectiveSSMLayer(d_model=8, d_inner=8, d_state=4, dt_rank=2, d_conv=3)
x = torch.randn(1, 16, 8)
out = layer(x)
print(out.shape)  # (1,16,8)
```

---

## 4. Fresh Implementation

- **Action**: Provided full standalone code for `SelectiveSSMLayer` and `selective_scan_fn`.
- **Result**: Verified output shapes for batch sizes >1 without errors:
  - `torch.Size([2, 16, 8])`

---

## 5. Broader Model Integration

- **Reviewed**: Full HamburgHealthcareSafetyMamba model including:
  - `HamburgClinicalEncoder` for structured clinical features.
  - `HamburgMambaBlock` with residual + norm.
  - Prediction heads (`CrisisEarlyWarningSystem`, `StaffWellbeingPredictor`, `SafetyOutcomePredictor`).
  - Data connector `connect_hamburg_data` for batching DataFrame inputs.

- **Confirmations**:
  - Input dimensions and concatenation (416 → 512) correct.
  - Categorical embeddings encodings valid.
  - Decoder modules consistent.

---

## 6. Decision Point: Mamba vs Hybrid

- **Pros of Mamba**:
  - Strong long-range modeling, novel research.
- **Cons of Mamba**:
  - Hard to debug, less interpretable.

- **Pros of Hybrid**:
  - Simpler to configure, debug, and explain.
  - Leverages familiar modules (GRU, Transformer).
- **Cons of Hybrid**:
  - Potentially less efficient on very long contexts.

**Decision**: Recommend starting with a hybrid prototype for PoC, then evaluate Mamba in Phase 2.

---

## 7. Next Steps

1. **Implement Hybrid Prototype**:
   - Categorical embeddings + numerical normalization
   - GRU/Transformer backbone
   - Safety & wellbeing prediction heads
2. **Validation**:
   - Run on synthetic and real Hamburg crisis generator data
   - Compare baseline (CatBoost) vs hybrid vs Mamba
3. **Documentation**:
   - Publish architecture decisions and experiments in repository README.

---

*Generated during interactive development session.*

