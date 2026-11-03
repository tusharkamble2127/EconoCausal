from __future__ import annotations

import inspect
import io
import json
import logging
import math
import os
import sys
import time
import tokenize
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "artifacts" / "definitive_validation"
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from app.core.logging import configure_logging
from app.models import allocation, balance_metric, customer, dataset, drift_result, feature_importance, ite_score, propensity_diagnostic, propensity_score, recommendation_result, refutation_result, run, password_reset_token, user
from app.models.base import Base
from app.pipeline import causal_graph, cleaning, dml_model, features, propensity_score as propensity_module
from app.repositories import customer_repository, dataset_repository
from app.schemas.run_schema import RunCreateSchema
from app.services import training_service
from app.services.confidence_service import compute as compute_confidence
from data.generators import generate_mock_data

configure_logging(logging.WARNING)
logging.getLogger("dowhy").setLevel(logging.WARNING)
logging.getLogger("econml").setLevel(logging.WARNING)

LEVELS = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
EVAL_LEVEL = 10.0
BUDGET = 30000.0
DATASETS = [
    ("A", 2000, 42),
    ("B", 2000, 7),
    ("C", 2000, 123),
    ("D", 2000, 456),
    ("E", 2000, 789),
    ("F", 1500, 42),
]


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return [jsonable(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value

def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def write_json(name: str, value: Any) -> None:
    (OUTPUT / name).write_text(json.dumps(jsonable(value), indent=2, sort_keys=True), encoding="utf-8")


def true_effect_frame(df: pd.DataFrame, level: float, effect_multiplier: float = 1.0, tenure_shift: float = 0.0, loyalty_shift: float = 0.0) -> pd.DataFrame:
    x = df.copy()
    if tenure_shift:
        x["tenure_months"] = x["tenure_months"] + tenure_shift
    if loyalty_shift:
        x["loyalty_score"] = np.clip(x["loyalty_score"] + loyalty_shift, 0.0, 1.0)
    theta = (0.004 + 0.01 * (1.0 - x["loyalty_score"].to_numpy())) * effect_multiplier
    eta0 = (
        -1.5
        + 0.02 * x["tenure_months"].to_numpy()
        + 0.15 * x["past_purchase_frequency"].to_numpy()
        + 1.2 * x["loyalty_score"].to_numpy()
    )
    p0 = expit(eta0)
    p1 = expit(eta0 + float(level) * theta)
    return pd.DataFrame({
        "true_ite": p1 - p0,
        "true_latent_ite": float(level) * theta,
        "true_p0": p0,
        "true_p1": p1,
    })


def generate_controlled(n: int, seed: int, effect_multiplier: float = 1.0, tenure_shift: float = 0.0, loyalty_shift: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tenure = rng.integers(1, 60, size=n).astype(float)
    frequency = rng.poisson(3, size=n).astype(float)
    loyalty = rng.uniform(0, 1, size=n).astype(float)
    aov = rng.normal(50, 15, size=n).clip(min=5)
    if tenure_shift:
        tenure = tenure + tenure_shift
    if loyalty_shift:
        loyalty = loyalty + loyalty_shift
        loyalty = np.clip(loyalty, 0.0, 1.0)
    propensity_logit = -1.0 + 2.0 * loyalty + 0.05 * frequency
    propensity = 1.0 / (1.0 + np.exp(-propensity_logit))
    treatment = np.array([rng.choice([0.0, 10.0, 20.0], p=generate_mock_data._treatment_probs(p)) for p in propensity])
    theta = (0.004 + 0.01 * (1.0 - loyalty)) * effect_multiplier
    eta = -1.5 + 0.02 * tenure + 0.15 * frequency + 1.2 * loyalty + treatment * theta
    outcome = rng.binomial(1, expit(eta))
    return pd.DataFrame({
        "tenure_months": tenure,
        "past_purchase_frequency": frequency,
        "loyalty_score": loyalty,
        "avg_order_value": aov,
        "treatment": treatment,
        "outcome": outcome,
    })


def pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    if np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def top_overlap(pred: np.ndarray, truth: np.ndarray, fraction: float) -> float:
    k = max(1, int(math.ceil(len(pred) * fraction)))
    pred_idx = set(np.argsort(-pred, kind="stable")[:k])
    truth_idx = set(np.argsort(-truth, kind="stable")[:k])
    return float(len(pred_idx & truth_idx) / k)


def qini_from_predictions(pred: np.ndarray) -> dict[str, Any]:
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


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()



def insert_dataset(db, df: pd.DataFrame, name: str) -> int:
    feature_cols = [c for c in df.columns if c not in {"treatment", "outcome", "customer_id"}]
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "features": {c: float(row[c]) for c in feature_cols},
            "treatment": float(row["treatment"]),
            "outcome": int(row["outcome"]),
        })
    ds = dataset_repository.create(db, name=name, row_count=len(rows), owner_id=1)
    customer_repository.bulk_create(db, ds.dataset_id, rows)
    return ds.dataset_id


def propensity_metrics(db, run_id: int) -> dict[str, float]:
    result = {
        "pct_outside_support": 0.0,
        "pct_extreme": 0.0,
        "n_unmatched_treated": 0,
        "n_matched_pairs": 0,
    }
    for d in db.query(propensity_diagnostic.PropensityDiagnostic).filter_by(run_id=run_id).all():
        if not d.details_json:
            continue
        try:
            values = json.loads(d.details_json)
        except (TypeError, ValueError):
            continue
        if d.metric_name == "overlap_summary":
            result["pct_outside_support"] = float(values.get("pct_outside_support", 0.0))
            result["pct_extreme"] = float(values.get("pct_extreme", 0.0))
        elif d.metric_name == "matching_summary":
            result["n_unmatched_treated"] = int(values.get("n_unmatched_treated", 0))
            result["n_matched_pairs"] = int(values.get("n_matched_pairs", 0))
    return result


def run_production(db, df: pd.DataFrame, label: str, dataset_id: int, effect_multiplier: float = 1.0) -> dict[str, Any]:
    df_clean = cleaning.clean(df.copy())
    feature_set = features.engineer(df_clean)
    customers = sorted(customer_repository.list_by_dataset(db, dataset_id), key=lambda c: c.customer_id)
    id_to_row = {c.customer_id: i for i, c in enumerate(customers)}
    payload = RunCreateSchema(
        dataset_id=dataset_id,
        budget=BUDGET,
        base_estimator="RandomForest",
        campaign_name=f"definitive_{label}",
        discount_levels=LEVELS,
        treatment_column="treatment",
        outcome_column="outcome",
    )
    started = pd.Timestamp.now()
    response = training_service.create_run(db, payload, owner_id=1)
    finished = pd.Timestamp.now()
    ite_rows = db.query(ite_score.IteScore).filter_by(run_id=response.run_id).all()
    refutation_rows = db.query(refutation_result.RefutationResult).filter_by(run_id=response.run_id).all()
    allocation_rows = db.query(allocation.Allocation).filter_by(run_id=response.run_id).all()
    recommendation_rows = db.query(recommendation_result.RecommendationResult).filter_by(run_id=response.run_id).all()
    pred_lookup = {(r.customer_id, float(r.discount_level)): r for r in ite_rows}
    refutations = []
    for r in refutation_rows:
        details = json.loads(r.details_json) if r.details_json else {}
        refutations.append({
            "test_name": r.test_name,
            "passed": bool(r.passed),
            "original_effect": details.get("original_effect"),
            "new_effect": details.get("new_effect"),
            "effect_difference": None if details.get("original_effect") is None or details.get("new_effect") is None else abs(float(details["new_effect"]) - float(details["original_effect"])),
            "elapsed_s": details.get("elapsed_s"),
            "is_statistically_significant": details.get("is_statistically_significant"),
        })
    pred_records = []
    for r in ite_rows:
        idx = id_to_row[r.customer_id]
        truth = true_effect_frame(df_clean, float(r.discount_level), effect_multiplier=effect_multiplier).iloc[idx]
        pred_records.append({
            "label": label,
            "customer_id": int(r.customer_id),
            "discount_level": float(r.discount_level),
            "ite_value": float(r.ite_value),
            "ci_lower": float(r.ci_lower),
            "ci_upper": float(r.ci_upper),
            "true_ite": float(truth["true_ite"]),
            "true_latent_ite": float(truth["true_latent_ite"]),
        })
    pred_all = pd.DataFrame(pred_records)
    pred_eval = pred_all[pred_all["discount_level"] == EVAL_LEVEL].copy().reset_index(drop=True)
    pred = pred_eval["ite_value"].to_numpy()
    truth = pred_eval["true_ite"].to_numpy()
    true_ate = float(np.mean(truth))
    estimated_ate = float(np.mean(pred))
    ate_error = abs(estimated_ate - true_ate)
    ate_pct_error = None if abs(true_ate) < 1e-15 else ate_error / abs(true_ate) * 100.0
    qini = qini_from_predictions(pred)
    rec_by_customer = {r.customer_id: r for r in recommendation_rows}
    confidence_records = []
    for a in allocation_rows:
        rec = rec_by_customer.get(a.customer_id)
        p = pred_lookup.get((a.customer_id, float(a.chosen_discount)))
        if p is None or rec is None:
            continue
        confidence_records.append({
            "customer_id": int(a.customer_id),
            "chosen_discount": float(a.chosen_discount),
            "chosen_ite": float(p.ite_value),
            "confidence_score": float(rec.confidence_score),
            "confidence_level": rec.confidence_level,
            "ci_lower": float(p.ci_lower),
            "ci_upper": float(p.ci_upper),
            "evidence": json.loads(rec.evidence) if rec.evidence else {},
        })
    original_effect = next((r["original_effect"] for r in refutations if r["original_effect"] is not None), None)
    return {
        "label": label,
        "run_id": int(response.run_id),
        "status": response.status,
        "runtime_s": float((finished - started).total_seconds()),
        "n_rows": len(df_clean),
        "n_features": feature_set.X.shape[1],
        "feature_names": feature_set.feature_names,
        "treatment_values": sorted(float(v) for v in df_clean["treatment"].unique()),
        "outcome_mean": float(df_clean["outcome"].mean()),
        "metrics": {
            "ite_mae": float(np.mean(np.abs(pred - truth))),
            "ite_rmse": float(np.sqrt(np.mean((pred - truth) ** 2))),
            "pehe": float(np.sqrt(np.mean((pred - truth) ** 2))),
            "ite_correlation": pearson(pred, truth),
            "true_ate": true_ate,
            "estimated_ate": estimated_ate,
            "ate_absolute_error": ate_error,
            "ate_percentage_error": ate_pct_error,
            "top10_overlap": top_overlap(pred, truth, 0.10),
            "top20_overlap": top_overlap(pred, truth, 0.20),
            "top30_overlap": top_overlap(pred, truth, 0.30),
            **qini,
        },
        "refutations": refutations,
        "original_dowhy_effect": original_effect,
        "dowhy_implied_ate_at_eval_level": None if original_effect is None else float(original_effect) * EVAL_LEVEL,
        "propensity_metrics": propensity_metrics(db, response.run_id),
        "prediction_count": len(pred_all),
        "allocation_count": len(allocation_rows),
        "confidence_count": len(confidence_records),
        "confidence_mean": float(np.mean([r["confidence_score"] for r in confidence_records])) if confidence_records else None,
        "confidence_records": confidence_records,
        "prediction_frame": pred_all,
        "qini_curve": pd.DataFrame({"fraction": qini["qini_fraction"], "qini_gain": qini["qini_curve"]}),
    }


def confidence_math_validation(result: dict[str, Any]) -> dict[str, Any]:
    records = result["confidence_records"]
    intervals = np.array([[r["ci_lower"], r["ci_upper"]] for r in records], dtype=float)
    centers = (intervals[:, 0] + intervals[:, 1]) / 2.0
    chosen = np.array([r["chosen_ite"] for r in records], dtype=float)
    center_errors = centers - chosen
    return {
        "selected_ite_math_valid": bool(np.all(np.isfinite(intervals))),
        "ci_center_max_abs_error": float(np.max(np.abs(center_errors))),
        "ci_center_mean_abs_error": float(np.mean(np.abs(center_errors))),
        "all_centered_within_1e_6": bool(np.all(np.abs(center_errors) < 1e-6)),
        "all_finite_intervals": bool(np.isfinite(intervals).all()),
        "all_valid_bounds": bool(np.all(intervals[:, 1] >= intervals[:, 0])),
    }


def confidence_validation(df: pd.DataFrame) -> dict[str, Any]:
    clean = cleaning.clean(df.copy())
    feature_set = features.engineer(clean)
    est = dml_model.train(feature_set, "RandomForest")
    x = feature_set.X.to_numpy()
    baseline = json.loads((OUTPUT / "validation_baseline_seed42.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(OUTPUT / "predictions_baseline_seed42.csv")
    pred_lookup = {
        (int(r.customer_id), float(r.discount_level)): r
        for r in db_records_from_predictions(predictions)
    }
    persisted = [r for r in baseline["confidence_records"] if float(r["chosen_discount"]) > 0.0][:20]
    refutation_pass_rate = float(np.mean([bool(r["passed"]) for r in baseline["refutations"]]))
    propensity = baseline["propensity_metrics"]
    runtime_rows = []
    recomputed_records = []
    for rec in persisted:
        cid = int(rec["customer_id"])
        idx = cid - 1
        level = float(rec["chosen_discount"])
        point = float(est.effect(x[idx:idx + 1], T0=np.array([0.0]), T1=np.array([level]))[0])
        lower, upper = est.effect_interval(
            x[idx:idx + 1], T0=np.array([0.0]), T1=np.array([level]), alpha=0.10
        )
        lower = float(np.asarray(lower).reshape(-1)[0])
        upper = float(np.asarray(upper).reshape(-1)[0])
        persisted_row = pred_lookup.get((cid, level))
        center_error = ((lower + upper) / 2.0) - point
        runtime_rows.append({
            "customer_id": cid,
            "customer_index": idx,
            "chosen_discount": level,
            "production_ite": point,
            "ci_lower": lower,
            "ci_upper": upper,
            "ci_center_error": float(center_error),
            "persisted_ite": None if persisted_row is None else float(persisted_row.ite_value),
            "persisted_ci_lower": None if persisted_row is None else float(persisted_row.ci_lower),
            "persisted_ci_upper": None if persisted_row is None else float(persisted_row.ci_upper),
            "persisted_ite_max_abs_error": None if persisted_row is None else abs(float(persisted_row.ite_value) - point),
            "persisted_ci_max_abs_error": None if persisted_row is None else max(abs(float(persisted_row.ci_lower) - lower), abs(float(persisted_row.ci_upper) - upper)),
        })
        customer_values = predictions[predictions["customer_id"] == cid].sort_values("discount_level")["ite_value"].tolist()
        common = {
            "customer_ite_values": [float(v) for v in customer_values],
            "chosen_discount": level,
            "refutation_pass_rate": refutation_pass_rate,
            "n_samples": int(baseline["prediction_count"]),
            "n_distinct_treatments": len(LEVELS),
            "ci_level": 0.90,
            "pct_outside_support": float(propensity["pct_outside_support"]),
            "pct_extreme": float(propensity["pct_extreme"]),
            "n_unmatched_treated": int(propensity["n_unmatched_treated"]),
            "n_matched_pairs": int(propensity["n_matched_pairs"]),
        }
        computed = compute_confidence(ci_lower=lower, ci_upper=upper, chosen_ite=point, **common)
        recomputed_records.append({
            "customer_id": cid,
            "chosen_discount": level,
            "chosen_ite": point,
            "computed_score": float(computed.confidence_score),
            "persisted_score": float(rec["confidence_score"]),
            "score_abs_error": abs(float(computed.confidence_score) - float(rec["confidence_score"])),
            "computed_level": computed.confidence_level,
            "persisted_level": rec["confidence_level"],
            "computed_evidence": computed.evidence,
            "persisted_evidence": rec["evidence"],
        })

    common = {
        "customer_ite_values": [0.05, 0.10, 0.15],
        "chosen_discount": 10.0,
        "refutation_pass_rate": 1.0,
        "n_samples": 2000,
        "n_distinct_treatments": 7,
        "ci_level": 0.90,
        "pct_outside_support": 0.0,
        "pct_extreme": 0.0,
        "n_unmatched_treated": 0,
        "n_matched_pairs": 1000,
    }
    base = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_ite=0.10, **common)
    changed = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_ite=0.20, **common)
    wide = compute_confidence(ci_lower=0.00, ci_upper=0.40, chosen_ite=0.10, **common)
    narrow = compute_confidence(ci_lower=0.09, ci_upper=0.11, chosen_ite=0.10, **common)
    zero_common = {k: v for k, v in common.items() if k != "chosen_discount"}
    zero = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_discount=0.0, chosen_ite=0.0, **zero_common)
    failed_refutation = compute_confidence(ci_lower=0.08, ci_upper=0.12, chosen_ite=0.10, refutation_pass_rate=0.0, **{k: v for k, v in common.items() if k != "refutation_pass_rate"})
    invalid_cases = {}
    for name, lower, upper in [("missing_lower", None, 0.12), ("missing_upper", 0.08, None), ("nan", np.nan, np.nan), ("infinite", np.inf, 1.0), ("reversed", 0.20, 0.10)]:
        result = compute_confidence(ci_lower=lower, ci_upper=upper, chosen_ite=0.10, **common)
        invalid_cases[name] = {
            "score": float(result.confidence_score),
            "level": result.confidence_level,
            "ci_available": result.evidence["ci_available"],
            "ci_finite": result.evidence["ci_finite"],
        }
    bounded_scores = [base.confidence_score, changed.confidence_score, wide.confidence_score, narrow.confidence_score, zero.confidence_score, failed_refutation.confidence_score]
    bounded_scores.extend(float(r["confidence_score"]) for r in baseline["confidence_records"])
    evidence_consistent = []
    for r in recomputed_records:
        persisted_evidence = r["persisted_evidence"]
        computed_evidence = r["computed_evidence"]
        expected_width = float(np.clip(r["chosen_discount"] and (r["computed_evidence"]["ci_upper"] - r["computed_evidence"]["ci_lower"]), 0.0, 1.0)) if False else None
        evidence_consistent.append({
            "customer_id": r["customer_id"],
            "chosen_discount": r["chosen_discount"],
            "computed_ci_width": float(computed_evidence["ci_width"]),
            "persisted_ci_width": persisted_evidence.get("ci_width"),
            "computed_ci_relative_width": computed_evidence.get("ci_relative_width"),
            "persisted_ci_relative_width": persisted_evidence.get("ci_relative_width"),
            "computed_ci_excludes_zero": computed_evidence["ci_excludes_zero"],
            "persisted_ci_excludes_zero": persisted_evidence.get("ci_excludes_zero"),
            "computed_ci_finite": computed_evidence["ci_finite"],
            "persisted_ci_finite": persisted_evidence.get("ci_finite"),
        })
    return {
        "actual_confidence_service": "backend.app.services.confidence_service.compute",
        "actual_recommendation_service": "backend.app.services.recommendation_service._compute_recommendations",
        "runtime_model": "EconML LinearDML via app.pipeline.dml_model.train",
        "runtime_n_customers": len(runtime_rows),
        "runtime_interval_center_max_abs_error": float(np.max(np.abs([r["ci_center_error"] for r in runtime_rows]))),
        "runtime_interval_center_mean_abs_error": float(np.mean(np.abs([r["ci_center_error"] for r in runtime_rows]))),
        "runtime_intervals_centered_within_1e_8": bool(np.all(np.abs([r["ci_center_error"] for r in runtime_rows]) < 1e-8)),
        "econml_interval_expected_centered": True,
        "econml_interval_source": "backend/.venv_py312/Lib/site-packages/econml/inference/_inference.py:1054-1076",
        "persisted_vs_runtime_ite_max_abs_error": float(np.max([r["persisted_ite_max_abs_error"] for r in runtime_rows])),
        "persisted_vs_runtime_ci_max_abs_error": float(np.max([r["persisted_ci_max_abs_error"] for r in runtime_rows])),
        "checks": {
            "chosen_ite_selected_customer_and_discount": bool(all(r["persisted_ite_max_abs_error"] < 1e-8 for r in runtime_rows)),
            "ci_same_customer_and_discount": bool(all(r["persisted_ci_max_abs_error"] < 1e-8 for r in runtime_rows)),
            "confidence_receives_correct_chosen_ite": bool(max(r["score_abs_error"] for r in recomputed_records) < 1e-8),
            "zero_discount": zero.confidence_score == 0.0 and zero.confidence_level == "Insufficient Evidence",
            "invalid_or_missing_ci": all(r["score"] == 0.0 and r["level"] == "Insufficient Evidence" for r in invalid_cases.values()),
            "confidence_bounded_0_1": bool(all(0.0 <= score <= 1.0 for score in bounded_scores)),
            "changing_selected_ite_changes_confidence": base.confidence_score != changed.confidence_score,
            "high_uncertainty_lowers_confidence": wide.confidence_score < base.confidence_score,
            "narrower_uncertainty_improves_confidence": narrow.confidence_score > wide.confidence_score,
            "failed_refutation_lowers_confidence": failed_refutation.confidence_score < base.confidence_score,
            "evidence_internally_consistent": bool(all(abs(r["computed_ci_width"] - r["persisted_ci_width"]) < 1e-10 and r["computed_ci_excludes_zero"] == r["persisted_ci_excludes_zero"] and r["computed_ci_finite"] == r["persisted_ci_finite"] for r in evidence_consistent)),
        },
        "sensitivity": {
            "base_score": float(base.confidence_score),
            "changed_ite_score": float(changed.confidence_score),
            "wide_interval_score": float(wide.confidence_score),
            "narrow_interval_score": float(narrow.confidence_score),
            "zero_discount_score": float(zero.confidence_score),
            "failed_refutation_score": float(failed_refutation.confidence_score),
        },
        "invalid_ci_cases": invalid_cases,
        "runtime_records": runtime_rows,
        "recomputed_records": recomputed_records,
        "evidence_consistency": evidence_consistent,
    }


def db_records_from_predictions(frame: pd.DataFrame) -> list[Any]:
    return [type("PredictionRow", (), row) for row in frame.to_dict(orient="records")]


def manual_ite_validation(df: pd.DataFrame) -> dict[str, Any]:
    clean = cleaning.clean(df.copy())
    feature_set = features.engineer(clean)
    est = dml_model.train(feature_set, "RandomForest")
    x = feature_set.X.to_numpy()
    rng = np.random.default_rng(2026)
    selected = np.sort(rng.choice(len(clean), size=min(20, len(clean)), replace=False))
    rows = []
    for idx in selected:
        truth_10 = float(true_effect_frame(clean, 10.0).iloc[idx]["true_ite"])
        truth_20 = float(true_effect_frame(clean, 20.0).iloc[idx]["true_ite"])
        prod_10 = float(est.effect(x[idx:idx + 1], T0=np.array([0.0]), T1=np.array([10.0]))[0])
        prod_20 = float(est.effect(x[idx:idx + 1], T0=np.array([0.0]), T1=np.array([20.0]))[0])
        rows.append({
            "customer_id": int(idx + 1),
            "customer_index": int(idx),
            "discount_level": 10.0,
            "true_ite": truth_10,
            "production_ite": prod_10,
            "absolute_error": abs(prod_10 - truth_10),
        })
        rows.append({
            "customer_id": int(idx + 1),
            "customer_index": int(idx),
            "discount_level": 20.0,
            "true_ite": truth_20,
            "production_ite": prod_20,
            "absolute_error": abs(prod_20 - truth_20),
        })
    frame = pd.DataFrame(rows)
    by_level = {}
    for level, subset in frame.groupby("discount_level"):
        errors = subset["absolute_error"].to_numpy(dtype=float)
        by_level[str(int(level))] = {
            "n_customers": int(len(subset)),
            "mean_absolute_error": float(np.mean(errors)),
            "max_absolute_error": float(np.max(errors)),
        }
    return {
        "n_customers": int(len(selected)),
        "n_records": int(len(frame)),
        "production_model": "EconML LinearDML via app.pipeline.dml_model.train",
        "ite_code": "est.effect(X, T0=0, T1=level)",
        "levels": by_level,
        "overall": {
            "mean_absolute_error": float(frame["absolute_error"].mean()),
            "max_absolute_error": float(frame["absolute_error"].max()),
        },
        "records": frame.to_dict(orient="records"),
    }


def leakage_validation(df: pd.DataFrame) -> dict[str, Any]:
    clean = cleaning.clean(df.copy())
    feature_set = features.engineer(clean)
    pipeline_dir = ROOT / "backend" / "app" / "pipeline"
    pipeline_files = sorted(pipeline_dir.glob("*.py"))
    pipeline_code_tokens = []
    for path in pipeline_files:
        with path.open(encoding="utf-8") as handle:
            pipeline_code_tokens.extend(
                token.string for token in tokenize.generate_tokens(handle.readline) if token.type == tokenize.NAME
            )
    pipeline_code_text = "\n".join(pipeline_code_tokens)
    generator_text = (ROOT / "data" / "generators" / "generate_mock_data.py").read_text(encoding="utf-8")
    forbidden = ["treatment", "outcome", "customer_id", "dataset_id", "true_ite", "true_effect", "tau", "theta"]
    found_in_X = sorted(set(forbidden) & set(feature_set.X.columns))
    truth_terms_in_pipeline = sorted({
        term: [path.name for path in pipeline_files if term in path.read_text(encoding="utf-8")]
        for term in ["true_ite", "true_effect", "ground_truth", "true_effect_per_dollar", "theta"]
        if any(term in path.read_text(encoding="utf-8") for path in pipeline_files)
    }.keys())
    generator_imports_pipeline = "generate_mock_data" in pipeline_code_text
    feature_source = (ROOT / "backend" / "app" / "pipeline" / "features.py").read_text(encoding="utf-8").splitlines()
    dml_source = (ROOT / "backend" / "app" / "pipeline" / "dml_model.py").read_text(encoding="utf-8").splitlines()
    checks = [
        {
            "check": "treatment_not_in_X",
            "status": "PASS" if "treatment" not in feature_set.X.columns else "FAIL",
            "source_file": "backend/app/pipeline/features.py",
            "source_function": "engineer",
            "evidence": f"X columns={list(feature_set.X.columns)}",
        },
        {
            "check": "outcome_not_in_X",
            "status": "PASS" if "outcome" not in feature_set.X.columns else "FAIL",
            "source_file": "backend/app/pipeline/features.py",
            "source_function": "engineer",
            "evidence": f"X columns={list(feature_set.X.columns)}",
        },
        {
            "check": "customer_id_not_predictive",
            "status": "PASS" if "customer_id" not in feature_set.X.columns else "FAIL",
            "source_file": "backend/app/pipeline/features.py",
            "source_function": "engineer",
            "evidence": "NON_FEATURE_COLUMNS excludes customer_id before get_dummies",
        },
        {
            "check": "dataset_id_not_predictive",
            "status": "PASS" if "dataset_id" not in feature_set.X.columns else "FAIL",
            "source_file": "backend/app/pipeline/features.py",
            "source_function": "engineer",
            "evidence": "NON_FEATURE_COLUMNS excludes dataset_id before get_dummies",
        },
        {
            "check": "true_ite_not_passed_to_training",
            "status": "PASS" if not any(term in pipeline_code_text for term in ["true_ite", "true_effect", "ground_truth", "true_effect_per_dollar"]) else "FAIL",
            "source_file": "backend/app/pipeline",
            "source_function": "features.engineer and dml_model.train",
            "evidence": f"pipeline truth terms={truth_terms_in_pipeline}",
        },
        {
            "check": "true_theta_not_passed_to_training",
            "status": "PASS" if "theta" not in pipeline_code_text else "FAIL",
            "source_file": "backend/app/pipeline",
            "source_function": "features.engineer and dml_model.train",
            "evidence": f"theta occurrences in pipeline={pipeline_code_text.count('theta')}",
        },
        {
            "check": "preprocessing_has_no_target_derived_features",
            "status": "PASS" if "outcome" not in feature_set.X.columns and "treatment" not in feature_set.X.columns else "FAIL",
            "source_file": "backend/app/pipeline/features.py",
            "source_function": "engineer",
            "evidence": "only confounder columns are one-hot encoded; treatment/outcome are split separately",
        },
        {
            "check": "no_test_set_target_enters_training",
            "status": "PASS" if "train_test_split" not in pipeline_code_text else "FAIL",
            "source_file": "backend/app/pipeline/dml_model.py",
            "source_function": "train",
            "evidence": "no explicit train/test split; LinearDML performs internal cross-fitting over Y and T",
        },
        {
            "check": "synthetic_ground_truth_validation_only",
            "status": "PASS" if generator_imports_pipeline is False and not any(term in pipeline_code_text for term in ["true_ite", "true_effect_per_dollar", "theta"]) else "FAIL",
            "source_file": "data/generators/generate_mock_data.py and backend/app/pipeline",
            "source_function": "generate and pipeline training",
            "evidence": f"generator contains true effect; pipeline imports generator={generator_imports_pipeline}",
        },
    ]
    return {
        "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
        "runtime_X_columns": list(feature_set.X.columns),
        "forbidden_columns_found_in_X": found_in_X,
        "pipeline_files_scanned": [str(path.relative_to(ROOT)) for path in pipeline_files],
        "generator_contains_ground_truth": any(term in generator_text for term in ["true_effect_per_dollar", "theta"]),
        "checks": checks,
    }


def run_validation_case(db, label: str, n: int, seed: int) -> dict[str, Any]:
    df = generate_mock_data.generate(n=n, seed=seed)
    dataset_id = insert_dataset(db, df, f"definitive_{label}_{n}_{seed}")
    result = run_production(db, df, label, dataset_id)
    payload = add_baseline_fields(result, df, result["feature_names"])
    payload["n"] = n
    payload["seed"] = seed
    return payload


def write_case_artifacts(label: str, payload: dict[str, Any], result: dict[str, Any]) -> None:
    write_json(f"validation_{label}.json", payload)
    result["prediction_frame"].to_csv(OUTPUT / f"predictions_{label}.csv", index=False)
    pd.DataFrame(result["refutations"]).to_csv(OUTPUT / f"refutations_{label}.csv", index=False)
    pd.DataFrame(result["confidence_records"]).to_csv(OUTPUT / f"confidence_{label}.csv", index=False)


def cross_seed_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [
        "ite_mae",
        "ite_rmse",
        "pehe",
        "ite_correlation",
        "true_ate",
        "estimated_ate",
        "ate_absolute_error",
        "qini_auc_validation_summary",
    ]
    summary = {}
    for name in metric_names:
        values = [r["metrics"][name] for r in results if r["metrics"].get(name) is not None]
        summary[name] = {
            "mean": float(np.mean(values)),
            "std_sample": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "values": values,
        }
    relative_errors = [r["ate_relative_error"] for r in results if r.get("ate_relative_error") is not None]
    summary["ate_relative_error"] = {
        "mean": float(np.mean(relative_errors)),
        "std_sample": float(np.std(relative_errors, ddof=1)) if len(relative_errors) > 1 else 0.0,
        "min": float(np.min(relative_errors)),
        "max": float(np.max(relative_errors)),
        "values": relative_errors,
    }
    summary["run_count"] = len(results)
    summary["all_runs_complete"] = bool(all(r["status"] == "complete" for r in results))
    return summary


def summarize_existing_cases() -> dict[str, Any]:
    results = []
    for label, _n, _seed in DATASETS:
        path = OUTPUT / f"validation_{label}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        results.append(json.loads(path.read_text(encoding="utf-8")))
    summary = cross_seed_summary(results)
    payload = {
        "datasets": DATASETS,
        "summary": summary,
        "runs": [{
            "label": r["label"],
            "n": r["n"],
            "seed": r["seed"],
            "status": r["status"],
            "run_id": r["run_id"],
        } for r in results],
    }
    write_json("validation_multi_seed_summary.json", payload)
    return payload


def dowhy_validation(df: pd.DataFrame) -> dict[str, Any]:
    clean = cleaning.clean(df.copy())
    feature_set = features.engineer(clean)
    model_df = feature_set.X.copy()
    model_df["treatment"] = feature_set.T
    model_df["outcome"] = feature_set.Y
    started = time.perf_counter()
    model = causal_graph.build_model(model_df, feature_set.feature_names)
    identified, estimate = causal_graph.identify_and_estimate(model)
    refutations = causal_graph.run_refutation_tests(model, identified, estimate)
    elapsed = time.perf_counter() - started
    refutation_records = [
        {
            "method": r.test_name,
            "passed": bool(r.passed),
            "details": r.details,
        }
        for r in refutations
    ]
    return {
        "identification_success": identified is not None,
        "estimator_success": estimate is not None and math.isfinite(float(estimate.value)),
        "estimator": "backdoor.linear_regression",
        "estimated_effect_per_unit_treatment": float(estimate.value),
        "implied_ate_at_10": float(estimate.value) * 10.0,
        "refutation_method": "production causal_graph.run_refutation_tests",
        "refutations": refutation_records,
        "refutation_pass": bool(refutations) and all(r.passed for r in refutations),
        "runtime_s": float(elapsed),
        "feature_count": feature_set.X.shape[1],
        "sample_count": len(clean),
    }

def treatment_dose_validation(frame: pd.DataFrame, df: pd.DataFrame) -> dict[str, Any]:
    observed = {float(v) for v in df["treatment"].unique()}
    rows = []
    for level in [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]:
        subset = frame[frame["discount_level"] == level]
        if level in observed:
            classification = "observed"
        elif min(observed) < level < max(observed):
            classification = "interpolated"
        else:
            classification = "extrapolated"
        rows.append({
            "discount_level": level,
            "classification": classification,
            "sample_count": int(len(subset)),
            "true_ate_at_level": float(subset["true_ite"].mean()),
            "estimated_ate_at_level": float(subset["ite_value"].mean()),
            "ite_mae_at_level": float(np.mean(np.abs(subset["ite_value"] - subset["true_ite"]))),
            "ite_rmse_at_level": float(np.sqrt(np.mean((subset["ite_value"] - subset["true_ite"]) ** 2))),
            "true_ite_statistics": prediction_statistics(subset["true_ite"].to_numpy()),
            "estimated_ite_statistics": prediction_statistics(subset["ite_value"].to_numpy()),
        })
    return {
        "observed_training_treatment_levels": sorted(observed),
        "requested_levels": rows,
        "observed_levels": [r for r in rows if r["classification"] == "observed"],
        "interpolated_levels": [r for r in rows if r["classification"] == "interpolated"],
        "extrapolated_levels": [r for r in rows if r["classification"] == "extrapolated"],
    }


def model_specification_validation(frame: pd.DataFrame) -> dict[str, Any]:
    true = frame["true_ite"].to_numpy(dtype=float)
    linear = frame["true_latent_ite"].to_numpy(dtype=float)
    discrepancy = linear - true
    return {
        "ground_truth_formula": "true_ITE(L) = expit(eta0 + L*theta) - expit(eta0)",
        "production_linear_dml_formula": "estimated_ITE(L) = estimated_marginal_effect(X) * L",
        "finding": "model-specification mismatch; not automatically a software implementation bug",
        "nonlinearity_discrepancy": {
            "mean_signed_linear_minus_true": float(np.mean(discrepancy)),
            "mean_absolute_error": float(np.mean(np.abs(discrepancy))),
            "rmse": float(np.sqrt(np.mean(discrepancy ** 2))),
            "max_absolute_error": float(np.max(np.abs(discrepancy))),
            "pearson_correlation": float(np.corrcoef(true, linear)[0, 1]),
        },
        "true_ite_statistics": prediction_statistics(true),
        "linear_approximation_statistics": prediction_statistics(linear),
    }


def controlled_experiment(db, name: str, df: pd.DataFrame, effect_multiplier: float = 1.0) -> dict[str, Any]:
    dataset_id = insert_dataset(db, df, f"controlled_{name}")
    return run_production(db, df, name, dataset_id, effect_multiplier=effect_multiplier)


def controlled_effect_validation() -> dict[str, Any]:
    specs = [
        ("baseline", 1.0),
        ("increased_effect_2x", 2.0),
        ("decreased_effect_0_5x", 0.5),
    ]
    experiments = []
    for name, multiplier in specs:
        df = generate_controlled(n=2000, seed=42, effect_multiplier=multiplier)
        db = make_db()
        result = controlled_experiment(db, name, df, effect_multiplier=multiplier)
        frame = result["prediction_frame"]
        eval_frame = frame[frame["discount_level"] == EVAL_LEVEL]
        confidence_scores = [r["confidence_score"] for r in result["confidence_records"]]
        chosen_discounts = [r["chosen_discount"] for r in result["confidence_records"]]
        experiments.append({
            "name": name,
            "effect_multiplier": multiplier,
            "status": result["status"],
            "run_id": result["run_id"],
            "n": len(df),
            "true_ate_at_10": result["metrics"]["true_ate"],
            "estimated_ate_at_10": result["metrics"]["estimated_ate"],
            "ate_absolute_error": result["metrics"]["ate_absolute_error"],
            "true_ite_statistics": prediction_statistics(eval_frame["true_ite"].to_numpy()),
            "estimated_ite_statistics": prediction_statistics(eval_frame["ite_value"].to_numpy()),
            "recommendation_behavior": {
                "allocation_count": result["allocation_count"],
                "confidence_record_count": result["confidence_count"],
                "chosen_discount_distribution": {
                    str(float(level)): int(sum(abs(float(v) - level) < 1e-9 for v in chosen_discounts))
                    for level in LEVELS
                },
                "mean_chosen_discount": float(np.mean(chosen_discounts)) if chosen_discounts else None,
                "mean_confidence_score": float(np.mean(confidence_scores)) if confidence_scores else None,
            },
            "confidence_behavior": {
                "mean_score": float(np.mean(confidence_scores)) if confidence_scores else None,
                "min_score": float(np.min(confidence_scores)) if confidence_scores else None,
                "max_score": float(np.max(confidence_scores)) if confidence_scores else None,
            },
            "qini_auc_validation_summary": result["metrics"]["qini_auc_validation_summary"],
        })
        write_json(f"controlled_effect_{name}.json", experiments[-1])
        result["prediction_frame"].to_csv(OUTPUT / f"controlled_predictions_{name}.csv", index=False)
        pd.DataFrame(result["confidence_records"]).to_csv(OUTPUT / f"controlled_confidence_{name}.csv", index=False)
    baseline = experiments[0]
    baseline["direction_checks"] = {
        "true_ate_direction_matches_baseline": True,
        "estimated_ate_direction_matches_baseline": True,
        "ite_mean_direction_matches_baseline": True,
    }
    for row in experiments[1:]:
        row["direction_checks"] = {
            "true_ate_direction_matches_baseline": bool(np.sign(row["true_ate_at_10"] - baseline["true_ate_at_10"]) == np.sign(row["effect_multiplier"] - 1.0)),
            "estimated_ate_direction_matches_baseline": bool(np.sign(row["estimated_ate_at_10"] - baseline["estimated_ate_at_10"]) == np.sign(row["effect_multiplier"] - 1.0)),
            "ite_mean_direction_matches_baseline": bool(np.sign(row["estimated_ite_statistics"]["mean"] - baseline["estimated_ite_statistics"]["mean"]) == np.sign(row["effect_multiplier"] - 1.0)),
        }
    payload = {
        "rule": "Only the synthetic generator's true treatment-effect multiplier changes; production model code is unchanged.",
        "experiments": experiments,
    }
    write_json("controlled_effect_validation.json", payload)
    return payload
def prediction_statistics(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    return {
        "count": int(values.size),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "median": float(np.median(values)),
    }


def serialize_run_result(result: dict[str, Any]) -> dict[str, Any]:
    serializable = dict(result)
    serializable.pop("prediction_frame", None)
    serializable.pop("qini_curve", None)
    return jsonable(serializable)


def add_baseline_fields(result: dict[str, Any], df: pd.DataFrame, feature_names: list[str]) -> dict[str, Any]:
    frame = result["prediction_frame"]
    eval_frame = frame[frame["discount_level"] == EVAL_LEVEL].reset_index(drop=True)
    estimated = eval_frame["ite_value"].to_numpy(dtype=float)
    truth = eval_frame["true_ite"].to_numpy(dtype=float)
    metrics = result["metrics"]
    level_results = []
    for level in [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]:
        subset = frame[frame["discount_level"] == level]
        level_results.append({
            "discount_level": level,
            "sample_count": int(len(subset)),
            "true_ate_at_level": float(subset["true_ite"].mean()),
            "estimated_ate_at_level": float(subset["ite_value"].mean()),
            "ite_mae_at_level": float(np.mean(np.abs(subset["ite_value"] - subset["true_ite"]))),
        })
    treatment_counts = df["treatment"].value_counts().sort_index()
    payload = dict(result)
    payload.pop("prediction_frame", None)
    payload.pop("qini_curve", None)
    payload.update({
        "sample_count": int(len(df)),
        "treatment_distribution": {str(float(k)): int(v) for k, v in treatment_counts.items()},
        "feature_names": feature_names,
        "estimated_ite_statistics": prediction_statistics(estimated),
        "true_ite_statistics": prediction_statistics(truth),
        "ite_mae": metrics["ite_mae"],
        "ite_rmse": metrics["ite_rmse"],
        "pehe": metrics["pehe"],
        "pearson_correlation": metrics["ite_correlation"],
        "true_ate": metrics["true_ate"],
        "estimated_ate": metrics["estimated_ate"],
        "ate_absolute_error": metrics["ate_absolute_error"],
        "ate_relative_error": metrics["ate_percentage_error"] / 100.0 if metrics["ate_percentage_error"] is not None else None,
        "discount_level_results": level_results,
        "production_model": {
            "estimator": "EconML LinearDML",
            "nuisance_models": "RandomForestRegressor",
            "discrete_treatment": False,
            "random_state": 42,
            "feature_builder": "app.pipeline.features.engineer",
            "ite_estimator": "app.pipeline.dml_model.estimate_ite",
        },
    })
    return jsonable(payload)


def main() -> None:
    db = make_db()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_results = []

    for label, n, seed in DATASETS:
        df = generate_mock_data.generate(n=n, seed=seed)
        dataset_id = insert_dataset(db, df, f"definitive_{label}_{n}_{seed}")
        result = run_production(db, df, label, dataset_id)
        payload = add_baseline_fields(result, df, result["feature_names"])
        payload["n"] = n
        payload["seed"] = seed
        write_json(f"validation_{label}.json", payload)
        result["prediction_frame"].to_csv(OUTPUT / f"predictions_{label}.csv", index=False)
        pd.DataFrame(result["refutations"]).to_csv(OUTPUT / f"refutations_{label}.csv", index=False)
        pd.DataFrame(result["confidence_records"]).to_csv(OUTPUT / f"confidence_{label}.csv", index=False)
        all_results.append(payload)
        print(f"CASE {label} COMPLETE", json.dumps({
            "n": n,
            "seed": seed,
            "status": payload["status"],
            "ite_mae": payload["metrics"]["ite_mae"],
            "true_ate": payload["metrics"]["true_ate"],
            "estimated_ate": payload["metrics"]["estimated_ate"],
        }))

    summary = cross_seed_summary(all_results)
    write_json("validation_multi_seed_summary.json", {
        "datasets": DATASETS,
        "summary": summary,
        "runs": [{
            "label": r["label"],
            "n": r["n"],
            "seed": r["seed"],
            "status": r["status"],
            "run_id": r["run_id"],
        } for r in all_results],
    })
    print("MULTI-SEED EXECUTION COMPLETE")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
