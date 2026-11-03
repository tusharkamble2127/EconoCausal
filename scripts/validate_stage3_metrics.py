"""Stage 3: compute all requested metrics from a single run's raw output."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path("artifacts/validation")

def pearson(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return None
    return float(np.corrcoef(a, b)[0, 1])

def top_overlap(pred, truth, fraction):
    pred = np.asarray(pred, dtype=float); truth = np.asarray(truth, dtype=float)
    k = max(1, int(math.ceil(len(pred) * fraction)))
    pred_idx = set(np.argsort(-pred, kind="stable")[:k])
    truth_idx = set(np.argsort(-truth, kind="stable")[:k])
    return float(len(pred_idx & truth_idx) / k)

def qini_from_predictions(pred):
    pred = np.asarray(pred, dtype=float)
    order = np.argsort(-pred, kind="stable")
    sorted_pred = pred[order]
    n = len(sorted_pred)
    running = np.cumsum(sorted_pred)
    random_expectation = sorted_pred.sum() * np.arange(1, n + 1) / n
    curve = running - random_expectation
    fractions = np.arange(1, n + 1) / n
    auc = float(np.trapezoid(np.concatenate(([0.0], curve)), np.concatenate(([0.0], fractions))))
    return {
        "qini_curve": curve.tolist(),
        "qini_fraction": fractions.tolist(),
        "qini_max_gain": float(np.max(curve)),
        "qini_min_gain": float(np.min(curve)),
        "qini_auc_validation_summary": auc,
    }

def compute_metrics(pred_eval):
    pred = pred_eval["ite_value"].to_numpy(dtype=float)
    truth = pred_eval["true_ite"].to_numpy(dtype=float)
    true_ate = float(np.mean(truth))
    estimated_ate = float(np.mean(pred))
    ate_error = abs(estimated_ate - true_ate)
    ate_pct = None if abs(true_ate) < 1e-15 else ate_error / abs(true_ate) * 100.0
    qini = qini_from_predictions(pred)
    return {
        "n": int(len(pred)),
        "ite_mae": float(np.mean(np.abs(pred - truth))),
        "ite_rmse": float(np.sqrt(np.mean((pred - truth) ** 2))),
        "pehe": float(np.sqrt(np.mean((pred - truth) ** 2))),
        "pehe_per_customer": float(np.mean((pred - truth) ** 2)),
        "ite_correlation": pearson(pred, truth),
        "true_ate": true_ate,
        "estimated_ate": estimated_ate,
        "ate_absolute_error": ate_error,
        "ate_percentage_error": ate_pct,
        "top10_overlap": top_overlap(pred, truth, 0.10),
        "top20_overlap": top_overlap(pred, truth, 0.20),
        "top30_overlap": top_overlap(pred, truth, 0.30),
        "qini_max_gain": qini["qini_max_gain"],
        "qini_auc_validation_summary": qini["qini_auc_validation_summary"],
        "qini_curve": qini["qini_curve"],
        "qini_fraction": qini["qini_fraction"],
        "pred_mean": float(np.mean(pred)),
        "pred_std": float(np.std(pred)),
        "truth_mean": float(np.mean(truth)),
        "truth_std": float(np.std(truth)),
    }

def confidence_math_validation(confidence_records):
    if not confidence_records:
        return {"pass": False, "reason": "no records"}
    intervals = np.array([[r["ci_lower"], r["ci_upper"]] for r in confidence_records], dtype=float)
    centers = (intervals[:, 0] + intervals[:, 1]) / 2.0
    chosen = np.array([r["chosen_ite"] for r in confidence_records], dtype=float)
    center_errors = centers - chosen
    return {
        "n": len(confidence_records),
        "ci_center_max_abs_error": float(np.max(np.abs(center_errors))),
        "ci_center_mean_abs_error": float(np.mean(np.abs(center_errors))),
        "all_centered_within_1e_6": bool(np.all(np.abs(center_errors) < 1e-6)),
        "all_finite_intervals": bool(np.isfinite(intervals).all()),
        "all_valid_bounds": bool(np.all(intervals[:, 1] >= intervals[:, 0])),
    }

def confidence_score_sensitivity(confidence_records):
    if not confidence_records:
        return {"pass": False, "reason": "no records"}
    scores = np.array([r["confidence_score"] for r in confidence_records], dtype=float)
    ites = np.array([r["chosen_ite"] for r in confidence_records], dtype=float)
    widths = np.array([r["ci_upper"] - r["ci_lower"] for r in confidence_records], dtype=float)
    return {
        "n": len(confidence_records),
        "unique_scores": int(len(set(scores.tolist()))),
        "score_min": float(np.min(scores)),
        "score_max": float(np.max(scores)),
        "score_std": float(np.std(scores)),
        "corr_score_ite": pearson(scores, ites),
        "corr_score_width": pearson(scores, widths),
    }

if __name__ == "__main__":
    pred_eval = pd.read_csv(OUT / "pred_eval_A.csv")
    m = compute_metrics(pred_eval)
    print(json.dumps({k: v for k, v in m.items() if not isinstance(v, list)}, indent=2))
    conf = pd.read_csv(OUT / "confidence_A.csv")
    cm = confidence_math_validation(conf.to_dict("records"))
    print("CONFIDENCE MATH:", json.dumps(cm, indent=2))
    cs = confidence_score_sensitivity(conf.to_dict("records"))
    print("CONFIDENCE SENSITIVITY:", json.dumps(cs, indent=2))
    print("STAGE3 OK")