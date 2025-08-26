
# --- Gate Engine integration (drop this in a new cell) ---
import pandas as pd
from ops_rules import compute_gates

# Replace `df_patients` with the DataFrame variable your UI uses
try:
    _df_preview = df_patients.head()
except NameError:
    # Heuristic fallbacks
    candidates = [name for name in globals() if isinstance(globals()[name], pd.DataFrame)]
    if candidates:
        df_patients = globals()[candidates[0]]
    else:
        raise NameError("No patient DataFrame found. Set df_patients to your main table.")

df_with_gates = compute_gates(df_patients)

# If your UI referenced a 'Gate_pos' column, replace UI bindings:
# - Instead of boolean Gate_pos, use:
#   - df_with_gates['priority'] for sorting/severity
#   - df_with_gates['gates'] for badges
#   - df_with_gates['next_action'] for button/tooltip text

display_cols = [c for c in df_with_gates.columns if c not in ('Gate_pos',)]
display(df_with_gates[display_cols].head(20))
# --- end ---
