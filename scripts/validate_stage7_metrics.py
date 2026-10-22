"""Stage 7: compute all requested metrics across all seeds."""
from __future__ import annotations
import json, math, glob
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path("artifacts/validation")

def pearson(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if len(a) < 2 or np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return None
    return float(np.corrcoef(a, b)[0, 1])

def top_overlap(pred, truth, fraction):
    pred = np.asarray(pred, dtype=float); truth = np.asarray(truth, dtype=float)
    k = max(1, int(math.ceil(len(pred) * fraction)))
    pi = set(np.argsort(-pred, kind="stable")[:k])
    ti = set(np.argsort(-truth, kind="stable")[:k])
    return float(len(pi & ti) / k)

def qini_from_predictions(pred):
    pred = np.asarray(pred, dtype=float)
    order = np.argsort(-pred, kind="stable")
    sp = pred[order]
    n = len(sp)
    running = np.cumsum(sp)
    rand = sp.sum() * np.arange(1, n + 1) / n
    curve = running - rand
    fr = np.arange(1, n + 1) / n
    auc = float(np.trapezoid(np.concatenate(([0.0], curve)), np.concatenate(([0.0], fr))))
    return {"qini_max_gain": float(np.max(curve)), "qini_auc_validation_summary": auc, "qini_curve": curve.tolist(), "qini_fraction": fr.tolist()}

def compute_metrics(label):
    pe = pd.read_csv(OUT / f"pred_eval_{label}.csv")
    pred = pe["ite_value"].to_numpy(dtype=float)
    truth = pe["true_ite"].to_numpy(dtype=float)
    true_ate = float(np.mean(truth))
    est_ate = float(np.mean(pred))
    ate_err = abs(est_ate - true_ate)
    ate_pct = None if abs(true_ate) < 1e-15 else ate_err / abs(true_ate) * 100.0
    q = qini_from_predictions(pred)
    return {
        "label": label, "n": int(len(pred)),
        "ite_mae": float(np.mean(np.abs(pred - truth))),
        "ite_rmse": float(np.sqrt(np.mean((pred - truth) ** 2))),
        "pehe": float(np.sqrt(np.mean((pred - truth) ** 2))),
        "pehe_per_customer": float(np.mean((pred - truth) ** 2)),
        "ite_correlation": pearson(pred, truth),
        "true_ate": true_ate, "estimated_ate": est_ate,
        "ate_absolute_error": ate_err, "ate_percentage_error": ate_pct,
        "top10_overlap": top_overlap(pred, truth, 0.10),
        "top20_overlap": top_overlap(pred, truth, 0.20),
        "top30_overlap": top_overlap(pred, truth, 0.30),
        "qini_max_gain": q["qini_max_gain"], "qini_auc_validation_summary": q["qini_auc_validation_summary"],
        "pred_mean": float(np.mean(pred)), "pred_std": float(np.std(pred)),
        "truth_mean": float(np.mean(truth)), "truth_std": float(np.std(truth)),
    }

def confidence_math(conf):
    if conf is None or len(conf) == 0:
        return {"pass": False, "reason": "no records"}
    intervals = np.array([[r["ci_lower"], r["ci_upper"]] for r in conf], dtype=float)
    centers = (intervals[:, 0] + intervals[:, 1]) / 2.0
    chosen = np.array([r["chosen_ite"] for r in conf], dtype=float)
    err = centers - chosen
    return {"n": len(conf), "ci_center_max_abs_error": float(np.max(np.abs(err))), "ci_center_mean_abs_error": float(np.mean(np.abs(err))), "all_centered_within_1e_6": bool(np.all(np.abs(err) < 1e-6)), "all_finite_intervals": bool(np.isfinite(intervals).all()), "all_valid_bounds": bool(np.all(intervals[:, 1] >= intervals[:, 0]))}

def confidence_sensitivity(conf):
    if conf is None or len(conf) == 0:
        return {"pass": False, "reason": "no records"}
    scores = np.array([r["confidence_score"] for r in conf], dtype=float)
    ites = np.array([r["chosen_ite"] for r in conf], dtype=float)
    widths = np.array([r["ci_upper"] - r["ci_lower"] for r in conf], dtype=float)
    return {"n": len(conf), "unique_scores": int(len(set(scores.tolist()))), "score_min": float(np.min(scores)), "score_max": float(np.max(scores)), "score_std": float(np.std(scores)), "corr_score_ite": pearson(scores, ites), "corr_score_width": pearson(scores, widths)}

if __name__ == "__main__":
    labels = ["A", "B", "C", "D", "E", "F"]
    all_metrics = {}
    for label in labels:
        m = compute_metrics(label)
        all_metrics[label] = m
        conf = pd.read_csv(OUT / f"confidence_{label}.csv").to_dict("records") if (OUT / f"confidence_{label}.csv").exists() else []
        cm = confidence_math(conf)
        cs = confidence_sensitivity(conf)
        m["confidence_math"] = cm
        m["confidence_sensitivity"] = cs
        print(f"{label}: MAE={m['ite_mae']:.5f} RMSE={m['ite_rmse']:.5f} PEHE={m['pehe']:.5f} corr={m['ite_correlation']:.4f} trueATE={m['true_ate']:.5f} estATE={m['estimated_ate']:.5f} ATEerr={m['ate_absolute_error']:.5f} ({m['ate_percentage_error']:.1f}%) Qini={m['qini_auc_validation_summary']:.4f} top10={m['top10_overlap']:.3f} top20={m['top20_overlap']:.3f} top30={m['top30_overlap']:.3f}")
        print(f"   conf math: {json.dumps(cm)}")
        print(f"   conf sens: {json.dumps(cs)}")
    # Cross-seed summary
    metric_names = ["ite_mae", "ite_rmse", "pehe", "ite_correlation", "ate_percentage_error", "qini_auc_validation_summary"]
    summary = {}
    for name in metric_names:
        vals = [all_metrics[l][name] for l in labels if all_metrics[l].get(name) is not None]
        summary[name] = {"mean": float(np.mean(vals)), "std_sample": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, "values": vals}
    print("\nCROSS-SEED SUMMARY:")
    for name in metric_names:
        s = summary[name]
        print(f"  {name:25s} mean={s['mean']:.6f}  sd={s['std_sample']:.6f}  values={[round(v,6) for v in s['values']]}")
    with open(OUT / "all_metrics.json", "w") as f:
        json.dump({"per_seed": all_metrics, "cross_seed": summary}, f, indent=2, default=str)
    print("STAGE7 DONE")