# demo_generate_and_emit.py — generate a synthetic day and emit HL7 to ed_demo_data/orbis_sim
import pandas as pd
from carefirst.synthetic_generator import load_config, default_config, generate_day, emit_hl7
from pathlib import Path

try:
    cfg = load_config('/mnt/data/synthetic_config.yaml')
except Exception:
    cfg = default_config()

tables, metrics = generate_day(cfg, seed=123)
print('Metrics:', metrics)
for k,v in tables.items():
    out = Path('/mnt/data')/f'synth_{k}.parquet'
    v.to_parquet(out); print('wrote', out)

# Emit HL7 into working ed_demo_data folder
base_dir = './ed_demo_data'
paths = emit_hl7(tables, base_dir=base_dir, write_orders=True, write_results=True)
print('HL7 messages written:', len(paths), '→', base_dir + '/orbis_sim/{outbox,inbox}')
