
# 🧭 Day 3 — Pivot to a Simplified AI Pathway Coordination Baseline

## 📌 Purpose

This project is part of an open research effort to explore how AI can assist in the coordination of patient pathways across emergency services, emergency departments (ED), hospital wards, and discharge planning.

The goal is not deployment or productization — this is a **community-facing research prototype**, developed in the open, to document what a more **ethically grounded, human-aware AI** system could look like in time-sensitive medical environments.

---

## 🔄 Shift in Scope

After two days of exploratory work, the direction of the project was clarified:  
We shifted from an ambitious, full-behavioral simulation to a **simplified, hard-variable-only coordination pipeline**. This means:

- No speculative modeling of staff psychology, inter-departmental friction, or refusal behavior (yet)
- Only **observable, processable variables** (e.g., triage level, ORBIS/IVENA capacities, timestamps)
- Focus on **routing, timing, and discharge coordination**

This change enables:

- **Faster iteration and clearer debugging**
- More **transparent results** and easier community validation
- A stable foundation for layering in behavioral complexity later

---

## 🚫 Why Mamba Was Not Used

The project initially considered newer structured state space models (SSMs) like **Mamba** for their ability to model long-range dependencies.

After review, the decision was made to **not pursue Mamba** at this stage:

| Reason | Explanation |
|--------|-------------|
| 🧮 Sequence length | Patient journeys are short, bounded sequences (EMS → ED → Ward → Discharge) |
| 🧠 Interpretability | GRUs are easier to debug and explain, especially in healthcare contexts |
| 🔧 Complexity | Mamba adds hyperparameter tuning and potential instability, with no meaningful gain in this setup |

The model will instead use a **hybrid GRU + MLP** structure, which is appropriate for the sequence length, modeling requirements, and training simplicity.

---

## ✅ Current Focus

We are now building a **Minimal Viable AI Assistant** that:

- Simulates patient pathways using synthetic, realistic hospital data
- Assists in coordination decisions (e.g., hospital routing, ward assignment, discharge comms)
- Evaluates outcomes like:
  - **Pathway latency**
  - **Ward suitability**
  - **Discharge coordination completeness**

All assumptions are stated clearly and transparently, and all data is simulated (no real patient data).

---

## 🔍 Contributions Welcome

If you're working on hospital flow, medical AI ethics, synthetic healthcare datasets, or practical coordination tools — contributions, critique, and validation ideas are all welcome.

This project will remain open-source, community-aligned, and accountable to clinical realism.
