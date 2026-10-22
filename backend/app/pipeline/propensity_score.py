"""
Propensity score / matching and covariate balance module (Volume II Chapter 12, Day 12).

STATISTICAL DESIGN NOTE
-----------------------
The EconoCausal application models discount as a CONTINUOUS treatment
(e.g. 0, 5, 10, 15, 20, 25, 30, plus custom values such as 7.5, 12.5).
EconML's LinearDML is configured with discrete_treatment=False.

Classical Propensity Score Matching (PSM) is defined for a BINARY treatment
T in {0, 1}. Applying binary PSM to a continuous treatment would be
statistically inappropriate: it would discard dose information and could
introduce bias by collapsing multi-level treatment into a single treated/untreated
 dichotomy.

This module therefore implements TWO complementary analyses:

1. BINARY PROPENSITY DIAGNOSTICS (T > 0 vs T == 0)
   - Used as a baseline overlap and covariate balance diagnostic for the
     treated-vs-control comparison.
   - NOT used to alter the continuous DML estimates unless explicitly validated.
   - Supports nearest-neighbor matching for this binary split.

2. CONTINUOUS TREATMENT BALANCE DIAGNOSTICS
   - A regression model predicts the continuous treatment level T from X.
   - Predicted treatment is stratified into deciles.
   - Standardized mean differences (SMD) are computed within each stratum
     to assess whether confounders are balanced across the treatment distribution.
   - This is the closest defensible generalized approach for continuous
     treatment balance diagnostics without discarding dose information.

The module is integrated as a PARALLEL DIAGNOSTIC STAGE in the pipeline:
  cleaning -> features -> propensity/balance -> DoWhy -> DML -> ITE -> optimizer

It must NOT crash the pipeline. Failures produce structured warnings.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger
from app.pipeline.features import FeatureSet

logger = get_logger(__name__)

SMD_BALANCED_THRESHOLD = 0.1
PROPENSITY_EXTREME_LOW = 0.05
PROPENSITY_EXTREME_HIGH = 0.95
PROPENSITY_COMMON_SUPPORT_MIN = 0.1
PROPENSITY_COMMON_SUPPORT_MAX = 0.9
CALIPER_DEFAULT = 0.2


@dataclass
class OverlapDiagnostic:
    """Overlap / common support diagnostics for binary propensity."""
    min_propensity: float
    max_propensity: float
    common_support_min: float
    common_support_max: float
    n_total: int
    n_outside_support: int
    pct_outside_support: float
    n_extreme_low: int
    n_extreme_high: int
    pct_extreme: float


@dataclass
class BalanceMetric:
    """Standardized mean difference for one confounder."""
    feature: str
    smd_before: float
    smd_after: Optional[float]
    improvement: Optional[float]
    balanced_before: bool
    balanced_after: bool
    match_type: str


@dataclass
class MatchingResult:
    """Results of nearest-neighbor matching."""
    method: str
    n_treated: int
    n_control: int
    n_matched_pairs: int
    n_unmatched_treated: int
    n_unmatched_control: int
    caliper: Optional[float]
    replacement: bool
    matched_treated_indices: List[int] = field(default_factory=list)
    matched_control_indices: List[int] = field(default_factory=list)


@dataclass
class BinaryPropensityResult:
    """Results for the binary treated-vs-control propensity analysis."""
    method: str = "logistic_regression"
    treatment_type: str = "binary_diagnostic"
    sample_size: int = 0
    propensity_scores: List[float] = field(default_factory=list)
    overlap: Optional[OverlapDiagnostic] = None
    balance: List[BalanceMetric] = field(default_factory=list)
    matching: Optional[MatchingResult] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "treatment_type": self.treatment_type,
            "sample_size": self.sample_size,
            "propensity_scores": self.propensity_scores,
            "overlap": _overlap_to_dict(self.overlap) if self.overlap else None,
            "balance": [_balance_to_dict(b) for b in self.balance],
            "matching": _matching_to_dict(self.matching) if self.matching else None,
            "warnings": self.warnings,
        }


@dataclass
class ContinuousPropensityResult:
    """Results for the continuous treatment balance diagnostics."""
    method: str = "continuous_stratification"
    treatment_type: str = "continuous"
    sample_size: int = 0
    predicted_treatment: List[float] = field(default_factory=list)
    n_strata: int = 0
    balance: List[BalanceMetric] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "treatment_type": self.treatment_type,
            "sample_size": self.sample_size,
            "predicted_treatment": self.predicted_treatment,
            "n_strata": self.n_strata,
            "balance": [_balance_to_dict(b) for b in self.balance],
            "warnings": self.warnings,
        }


@dataclass
class PropensityResult:
    """Combined propensity analysis result."""
    binary: Optional[BinaryPropensityResult] = None
    continuous: Optional[ContinuousPropensityResult] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binary": self.binary.to_dict() if self.binary else None,
            "continuous": self.continuous.to_dict() if self.continuous else None,
            "warnings": self.warnings,
        }


def _overlap_to_dict(o: OverlapDiagnostic) -> Dict[str, Any]:
    return {
        "min_propensity": round(o.min_propensity, 6),
        "max_propensity": round(o.max_propensity, 6),
        "common_support_min": round(o.common_support_min, 6),
        "common_support_max": round(o.common_support_max, 6),
        "n_total": o.n_total,
        "n_outside_support": o.n_outside_support,
        "pct_outside_support": round(o.pct_outside_support, 2),
        "n_extreme_low": o.n_extreme_low,
        "n_extreme_high": o.n_extreme_high,
        "pct_extreme": round(o.pct_extreme, 2),
    }


def _balance_to_dict(b: BalanceMetric) -> Dict[str, Any]:
    return {
        "feature": b.feature,
        "smd_before": round(b.smd_before, 4),
        "smd_after": round(b.smd_after, 4) if b.smd_after is not None else None,
        "improvement": round(b.improvement, 4) if b.improvement is not None else None,
        "balanced_before": b.balanced_before,
        "balanced_after": b.balanced_after,
        "match_type": b.match_type,
    }


def _matching_to_dict(m: MatchingResult) -> Dict[str, Any]:
    return {
        "method": m.method,
        "n_treated": m.n_treated,
        "n_control": m.n_control,
        "n_matched_pairs": m.n_matched_pairs,
        "n_unmatched_treated": m.n_unmatched_treated,
        "n_unmatched_control": m.n_unmatched_control,
        "caliper": m.caliper,
        "replacement": m.replacement,
        "matched_treated_indices": m.matched_treated_indices,
        "matched_control_indices": m.matched_control_indices,
    }


def _compute_smd(x_treated: np.ndarray, x_control: np.ndarray) -> float:
    """Compute standardized mean difference (SMD) between two groups.

    SMD = (mean_treated - mean_control) / pooled_std
    where pooled_std = sqrt((var_treated + var_control) / 2)

    Convention: |SMD| < 0.1 indicates good balance.
    """
    if len(x_treated) == 0 or len(x_control) == 0:
        return float("inf")

    mean_t = np.mean(x_treated)
    mean_c = np.mean(x_control)
    var_t = np.var(x_treated, ddof=1)
    var_c = np.var(x_control, ddof=1)

    pooled_std = np.sqrt((var_t + var_c) / 2.0)
    if pooled_std < 1e-12:
        return 0.0 if abs(mean_t - mean_c) < 1e-12 else float("inf")

    return float((mean_t - mean_c) / pooled_std)


def _compute_overlap(
    propensity_treated: np.ndarray,
    propensity_control: np.ndarray,
    common_support_min: float = PROPENSITY_COMMON_SUPPORT_MIN,
    common_support_max: float = PROPENSITY_COMMON_SUPPORT_MAX,
) -> OverlapDiagnostic:
    """Compute overlap diagnostics from propensity scores."""
    all_scores = np.concatenate([propensity_treated, propensity_control])
    n_total = len(all_scores)

    min_p = float(np.min(all_scores))
    max_p = float(np.max(all_scores))

    n_extreme_low = int(np.sum(all_scores < PROPENSITY_EXTREME_LOW))
    n_extreme_high = int(np.sum(all_scores > PROPENSITY_EXTREME_HIGH))
    pct_extreme = (n_extreme_low + n_extreme_high) / n_total * 100.0 if n_total > 0 else 0.0

    # Common support: [common_support_min, common_support_max]
    # Observations outside this range are flagged.
    n_outside = int(np.sum((all_scores < common_support_min) | (all_scores > common_support_max)))
    pct_outside = n_outside / n_total * 100.0 if n_total > 0 else 0.0

    return OverlapDiagnostic(
        min_propensity=min_p,
        max_propensity=max_p,
        common_support_min=common_support_min,
        common_support_max=common_support_max,
        n_total=n_total,
        n_outside_support=n_outside,
        pct_outside_support=pct_outside,
        n_extreme_low=n_extreme_low,
        n_extreme_high=n_extreme_high,
        pct_extreme=pct_extreme,
    )


def _match_nearest_neighbor(
    X: np.ndarray,
    treated_indices: np.ndarray,
    control_indices: np.ndarray,
    caliper: Optional[float] = None,
    replacement: bool = False,
) -> Tuple[MatchingResult, np.ndarray, np.ndarray]:
    """Perform 1:1 nearest-neighbor matching on propensity scores.

    Args:
        X: array of shape (n_samples, 1) containing propensity scores.
        treated_indices: indices of treated units.
        control_indices: indices of control units.
        caliper: maximum allowed propensity distance. If None, no caliper.
        replacement: if False, each control unit can be matched only once.

    Returns:
        (MatchingResult, matched_treated_indices, matched_control_indices)
    """
    treated_scores = X[treated_indices, 0]
    control_scores = X[control_indices, 0]

    n_treated = len(treated_indices)
    n_control = len(control_indices)

    if n_treated == 0 or n_control == 0:
        return (
            MatchingResult(
                method="nearest_neighbor",
                n_treated=n_treated,
                n_control=n_control,
                n_matched_pairs=0,
                n_unmatched_treated=n_treated,
                n_unmatched_control=n_control,
                caliper=caliper,
                replacement=replacement,
            ),
            np.array([], dtype=int),
            np.array([], dtype=int),
        )

    # Build nearest neighbors model on control scores with all neighbors
    # so we can iterate through them in distance order.
    nn = NearestNeighbors(n_neighbors=n_control)
    nn.fit(control_scores.reshape(-1, 1))

    # Batch query all treated scores at once for performance.
    all_distances, all_indices = nn.kneighbors(treated_scores.reshape(-1, 1))

    matched_treated = []
    matched_control = []
    used_control = set()
    n_unmatched_treated = 0
    n_unmatched_control = n_control

    for i, t_idx in enumerate(treated_indices):
        distances = all_distances[i]
        indices = all_indices[i]

        candidate_control_local_idx = None
        for dist, c_local_idx in zip(distances, indices):
            if caliper is not None and dist > caliper:
                continue
            c_global_idx = control_indices[c_local_idx]
            if replacement or c_global_idx not in used_control:
                candidate_control_local_idx = c_local_idx
                break

        if candidate_control_local_idx is not None:
            c_global_idx = control_indices[candidate_control_local_idx]
            matched_treated.append(t_idx)
            matched_control.append(c_global_idx)
            used_control.add(c_global_idx)
            n_unmatched_control -= 1
        else:
            n_unmatched_treated += 1

    n_matched = len(matched_treated)

    result = MatchingResult(
        method="nearest_neighbor",
        n_treated=n_treated,
        n_control=n_control,
        n_matched_pairs=n_matched,
        n_unmatched_treated=n_unmatched_treated,
        n_unmatched_control=n_unmatched_control,
        caliper=caliper,
        replacement=replacement,
        matched_treated_indices=[int(x) for x in matched_treated],
        matched_control_indices=[int(x) for x in matched_control],
    )

    return result, np.array(matched_treated, dtype=int), np.array(matched_control, dtype=int)


def _calculate_balance(
    X: pd.DataFrame,
    treated_indices: np.ndarray,
    control_indices: np.ndarray,
    matched_treated_indices: Optional[np.ndarray] = None,
    matched_control_indices: Optional[np.ndarray] = None,
    match_type: str = "binary_propensity",
) -> List[BalanceMetric]:
    """Compute SMD balance metrics for all confounders."""
    metrics = []

    t_before = treated_indices
    c_before = control_indices

    t_after = matched_treated_indices if matched_treated_indices is not None else treated_indices
    c_after = matched_control_indices if matched_control_indices is not None else control_indices

    for col in X.columns:
        smd_before = _compute_smd(X.iloc[t_before][col].values, X.iloc[c_before][col].values)
        smd_after = _compute_smd(X.iloc[t_after][col].values, X.iloc[c_after][col].values)
        improvement = None
        balanced_after = False

        if matched_control_indices is not None and matched_treated_indices is not None:
            if np.isfinite(smd_before) and np.isfinite(smd_after):
                improvement = abs(smd_before) - abs(smd_after)
            balanced_after = abs(smd_after) < SMD_BALANCED_THRESHOLD if np.isfinite(smd_after) else False

        metrics.append(BalanceMetric(
            feature=col,
            smd_before=smd_before,
            smd_after=smd_after if matched_control_indices is not None else None,
            improvement=improvement,
            balanced_before=abs(smd_before) < SMD_BALANCED_THRESHOLD if np.isfinite(smd_before) else False,
            balanced_after=balanced_after,
            match_type=match_type,
        ))

    return metrics


def estimate_binary_propensity(
    features: FeatureSet,
    caliper: Optional[float] = CALIPER_DEFAULT,
    replacement: bool = False,
    common_support_min: float = PROPENSITY_COMMON_SUPPORT_MIN,
    common_support_max: float = PROPENSITY_COMMON_SUPPORT_MAX,
) -> BinaryPropensityResult:
    """Estimate binary propensity (T > 0 vs T == 0) and perform matching.

    This is a DIAGNOSTIC stage for the treated-vs-control comparison.
    It does NOT replace the continuous DML treatment mechanism.

    Args:
        features: FeatureSet with continuous treatment T.
        caliper: maximum allowed propensity score distance for matching.
        replacement: whether control units can be reused in matching.
        common_support_min/max: bounds for common support region.

    Returns:
        BinaryPropensityResult with scores, overlap, balance, and matching info.
    """
    warnings: List[str] = []
    T = features.T
    X = features.X

    # Create binary treatment indicator: treated if discount > 0
    binary_t = (T > 0).astype(int)

    n_treated = int(np.sum(binary_t == 1))
    n_control = int(np.sum(binary_t == 0))

    if n_treated < 2 or n_control < 2:
        warnings.append(
            f"Insufficient variation for binary propensity: {n_treated} treated, {n_control} control. "
            "Need at least 2 in each group."
        )
        return BinaryPropensityResult(
            sample_size=len(T),
            warnings=warnings,
        )

    # Fit logistic regression for propensity score
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=1000, solver="lbfgs", C=1.0, random_state=42)
    model.fit(X_scaled, binary_t)

    propensity_scores = model.predict_proba(X_scaled)[:, 1].tolist()

    treated_indices = np.where(binary_t == 1)[0]
    control_indices = np.where(binary_t == 0)[0]

    propensity_treated = np.array([propensity_scores[i] for i in treated_indices])
    propensity_control = np.array([propensity_scores[i] for i in control_indices])

    overlap = _compute_overlap(
        propensity_treated, propensity_control,
        common_support_min=common_support_min,
        common_support_max=common_support_max,
    )

    # Compute balance BEFORE matching
    balance_before = _calculate_balance(
        X, treated_indices, control_indices,
        match_type="binary_propensity_before",
    )

    # Perform matching
    matching, matched_t, matched_c = _match_nearest_neighbor(
        np.array(propensity_scores).reshape(-1, 1),
        treated_indices,
        control_indices,
        caliper=caliper,
        replacement=replacement,
    )

    # Compute balance AFTER matching
    balance_after = _calculate_balance(
        X, treated_indices, control_indices,
        matched_treated_indices=matched_t,
        matched_control_indices=matched_c,
        match_type="binary_propensity_after",
    )

    # Combine before and after balance
    combined_balance = []
    for b_before, b_after in zip(balance_before, balance_after):
        combined_balance.append(BalanceMetric(
            feature=b_before.feature,
            smd_before=b_before.smd_before,
            smd_after=b_after.smd_after,
            improvement=abs(b_before.smd_before) - abs(b_after.smd_after) if np.isfinite(b_before.smd_before) and np.isfinite(b_after.smd_after) else None,
            balanced_before=b_before.balanced_before,
            balanced_after=b_after.balanced_after,
            match_type="binary_propensity",
        ))

    if overlap.pct_outside_support > 20:
        warnings.append(
            f"{overlap.pct_outside_support:.1f}% of observations fall outside common support. "
            "Matching and causal estimates may be unreliable."
        )

    if overlap.pct_extreme > 10:
        warnings.append(
            f"{overlap.pct_extreme:.1f}% of observations have extreme propensity scores. "
            "Consider reviewing model specification or covariate set."
        )

    if matching.n_unmatched_treated > 0:
        warnings.append(
            f"{matching.n_unmatched_treated} treated units could not be matched. "
            "Causal estimates for these units should be interpreted with caution."
        )

    return BinaryPropensityResult(
        method="logistic_regression",
        treatment_type="binary_diagnostic",
        sample_size=len(T),
        propensity_scores=propensity_scores,
        overlap=overlap,
        balance=combined_balance,
        matching=matching,
        warnings=warnings,
    )


def estimate_continuous_treatment_balance(
    features: FeatureSet,
    n_strata: int = 10,
) -> ContinuousPropensityResult:
    """Estimate continuous treatment balance using stratification on predicted treatment.

    This is a generalized approach for continuous treatment diagnostics.
    A regression model predicts the continuous treatment level T from X.
    Predicted values are divided into strata (deciles by default).
    SMD is computed within each stratum to assess covariate balance
    across the treatment distribution.

    This approach preserves dose information and does NOT collapse
    treatment into a binary indicator.

    Args:
        features: FeatureSet with continuous treatment T.
        n_strata: number of strata for predicted treatment.

    Returns:
        ContinuousPropensityResult with predicted treatment and balance metrics.
    """
    warnings: List[str] = []
    T = features.T
    X = features.X

    n_unique = len(np.unique(T))
    if n_unique < 3:
        warnings.append(
            f"Treatment has only {n_unique} distinct value(s). "
            "Continuous treatment balance diagnostics require more variation."
        )
        return ContinuousPropensityResult(
            sample_size=len(T),
            warnings=warnings,
        )

    # Fit regression model to predict continuous treatment
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
    model.fit(X_scaled, T)

    predicted_t = model.predict(X_scaled).tolist()

    # Stratify by predicted treatment into deciles (or fewer if small sample)
    predicted_arr = np.array(predicted_t)
    actual_strata = min(n_strata, len(np.unique(predicted_arr)))
    if actual_strata < 2:
        warnings.append("Could not form multiple strata from predicted treatment.")
        return ContinuousPropensityResult(
            sample_size=len(T),
            predicted_treatment=predicted_t,
            warnings=warnings,
        )

    try:
        strata = pd.qcut(predicted_arr, q=actual_strata, labels=False, duplicates="drop")
    except ValueError:
        warnings.append("Could not form strata from predicted treatment; too few unique values.")
        return ContinuousPropensityResult(
            sample_size=len(T),
            predicted_treatment=predicted_t,
            warnings=warnings,
        )

    # Compute SMD between highest and lowest stratum for each feature
    # This gives a summary balance metric across the treatment spectrum
    lowest_stratum = strata == 0
    highest_stratum = strata == (actual_strata - 1)

    if np.sum(lowest_stratum) < 2 or np.sum(highest_stratum) < 2:
        warnings.append("Insufficient observations in extreme strata for balance computation.")
        return ContinuousPropensityResult(
            sample_size=len(T),
            predicted_treatment=predicted_t,
            n_strata=actual_strata,
            warnings=warnings,
        )

    balance = []
    for col in X.columns:
        smd = _compute_smd(
            X.loc[highest_stratum, col].values,
            X.loc[lowest_stratum, col].values,
        )
        balance.append(BalanceMetric(
            feature=col,
            smd_before=smd,
            smd_after=None,
            improvement=None,
            balanced_before=abs(smd) < SMD_BALANCED_THRESHOLD if np.isfinite(smd) else False,
            balanced_after=False,
            match_type="continuous_stratification",
        ))

    return ContinuousPropensityResult(
        method="continuous_stratification",
        treatment_type="continuous",
        sample_size=len(T),
        predicted_treatment=predicted_t,
        n_strata=actual_strata,
        balance=balance,
        warnings=warnings,
    )


def run_propensity_analysis(
    features: FeatureSet,
    binary_caliper: Optional[float] = CALIPER_DEFAULT,
    binary_replacement: bool = False,
    n_continuous_strata: int = 10,
) -> PropensityResult:
    """Run the full propensity analysis pipeline.

    Computes both binary diagnostic propensity and continuous treatment
    balance diagnostics. Failures in either stage produce warnings
    rather than crashing the pipeline.

    Args:
        features: FeatureSet from the feature engineering stage.
        binary_caliper: caliper for binary nearest-neighbor matching.
        binary_replacement: whether to use replacement in binary matching.
        n_continuous_strata: number of strata for continuous treatment.

    Returns:
        PropensityResult with binary and/or continuous results.
    """
    warnings: List[str] = []
    binary_result: Optional[BinaryPropensityResult] = None
    continuous_result: Optional[ContinuousPropensityResult] = None

    T = features.T
    n_total = len(T)
    n_treated = int(np.sum(T > 0))
    n_control = int(np.sum(T == 0))

    # Run binary propensity diagnostics if we have both treated and control
    if n_treated >= 2 and n_control >= 2:
        try:
            binary_result = estimate_binary_propensity(
                features,
                caliper=binary_caliper,
                replacement=binary_replacement,
            )
            warnings.extend(binary_result.warnings)
        except Exception as exc:
            logger.exception("Binary propensity analysis failed")
            warnings.append(f"Binary propensity analysis failed: {exc}")
    else:
        warnings.append(
            f"Skipping binary propensity: {n_treated} treated, {n_control} control "
            f"(need >= 2 each)."
        )

    # Run continuous treatment balance diagnostics
    try:
        continuous_result = estimate_continuous_treatment_balance(
            features,
            n_strata=n_continuous_strata,
        )
        warnings.extend(continuous_result.warnings)
    except Exception as exc:
        logger.exception("Continuous treatment balance analysis failed")
        warnings.append(f"Continuous treatment balance analysis failed: {exc}")

    if not binary_result and not continuous_result:
        warnings.append(
            "Propensity analysis produced no results. "
            "This may indicate insufficient treatment variation or missing confounders."
        )

    return PropensityResult(
        binary=binary_result,
        continuous=continuous_result,
        warnings=warnings,
    )
