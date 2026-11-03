"""Stage 9: leakage check + confidence score sensitivity + ATE consistency."""
from __future__ import annotations
import os, sys, json, inspect
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "validation"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "data" / "generators"))
os.chdir(ROOT / "backend")
import numpy as np, pandas as pd
from app.pipeline import cleaning, features, dml_model
from app.services.confidence_service import compute as compute_confidence
import generate_mock_data as gmd

# ---- LEAKAGE CHECK ----
df = gmd.generate(n=2000, seed=42)
clean = cleaning.clean(df.copy())
fs = features.engineer(clean)
forbidden = {"treatment", "outcome", "customer_id", "dataset_id", "true_ite", "true_effect", "tau", "p0", "p1", "purchasing_prob"}
found = sorted(forbidden & set(fs.X.columns))
print("LEAKAGE - forbidden columns in X:", found)
print("LEAKAGE - treatment/outcome in X:", "treatment" in fs.X.columns or "outcome" in fs.X.columns)
src = (ROOT / "backend" / "app" / "pipeline" / "features.py").read_text(encoding="utf-8")
tau_terms = [t for t in ["true_ite", "true_effect", "tau"] if t in src]
print("LEAKAGE - ground-truth terms in features.py:", tau_terms)
dml_src = (ROOT / "backend" / "app" / "pipeline" / "dml_model.py").read_text(encoding="utf-8")
print("LEAKAGE - train_test_split in dml_model.py:", "train_test_split" in dml_src)
print("LEAKAGE - LinearDML cv default:", inspect.signature(dml_model.LinearDML).parameters["cv"].default)
# Check no true_ite anywhere in pipeline source
pipeline_dir = ROOT / "backend" / "app" / "pipeline"
leak_terms_found = []
for f in pipeline_dir.glob("*.py"):
    txt = f.read_text(encoding="utf-8")
    for t in ["true_ite", "true_effect", "ground_truth", "tau("]:
        if t in txt:
            leak_terms_found.append((f.name, t))
print("LEAKAGE - ground truth terms in pipeline source:", leak_terms_found)

# ---- CONFIDENCE SCORE SENSITIVITY ----
common = {
    "customer_ite_values": [0.05, 0.10, 0.15],
    "refutation_pass_rate": 1.0,
    "n_samples": 2000,
    "n_distinct_treatments": 7,
    "ci_level": 0.90,
    "pct_outside_support": 0.0,
    "pct_extreme": 0.0,
    "n_unmatched_treated": 0,
    "n_matched_pairs": 1000,
}
base = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_ite=0.10, chosen_discount=10.0, **common)
changed = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_ite=0.20, chosen_discount=10.0, **common)
wide = compute_confidence(ci_lower=0.00, ci_upper=0.40, chosen_ite=0.10, chosen_discount=10.0, **common)
narrow = compute_confidence(ci_lower=0.09, ci_upper=0.11, chosen_ite=0.10, chosen_discount=10.0, **common)
zero = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_discount=0.0, chosen_ite=0.0, **common)
print("\nCONFIDENCE SENSITIVITY:")
print("  base (ite=0.10, ci=[0.08,0.12]):", base.confidence_score, base.confidence_level)
print("  changed (ite=0.20, ci=[0.08,0.12]):", changed.confidence_score, changed.confidence_level)
print("  changed_chosen_ite_changes_score:", base.confidence_score != changed.confidence_score)
print("  wide (ci=[0.00,0.40]):", wide.confidence_score)
print("  narrow (ci=[0.09,0.11]):", narrow.confidence_score)
print("  narrower_has_higher_score:", narrow.confidence_score > wide.confidence_score)
print("  zero_discount:", zero.confidence_score, zero.confidence_level)
print("  base evidence ci_relative_width:", base.evidence.get("ci_relative_width"))
# Verify evidence uses chosen_ite
print("  base evidence ci_width:", base.evidence.get("ci_width"), "expected 0.04")
# Verify CI centered on chosen_ite in evidence
print("  base ci interval:", base.confidence_interval)

# ---- ATE CONSISTENCY ----
# Load seed A predictions
pe = pd.read_csv(OUT / "pred_eval_A.csv")
pred = pe["ite_value"].to_numpy(dtype=float)
ate_from_ite = float(np.mean(pred))
print("\nATE CONSISTENCY:")
print("  mean(ITE) =", ate_from_ite)
print("  (application ATE should equal mean(ITE))")
print("  n =", len(pred))

print("\nSTAGE9 DONE")