"""Unit tests for request schema validation."""
import pytest

from app.pipeline.dml_model import _make_base_estimator
from app.schemas.run_schema import RunCreateSchema
from app.schemas.scenario_schema import ScenarioRequestSchema


def test_run_create_schema_requires_positive_dataset_id():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=0, budget=100)


def test_run_create_schema_rejects_negative_budget():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=-1)


def test_run_create_schema_rejects_unsupported_estimator():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, base_estimator="GradientBoosting")


def test_run_create_schema_rejects_empty_discount_levels():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, discount_levels=[])


def test_run_create_schema_rejects_negative_discount_levels():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, discount_levels=[-5.0, 10.0])


def test_run_create_schema_rejects_duplicate_discount_levels():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, discount_levels=[10.0, 10.0, 20.0])


def test_run_create_schema_rejects_missing_zero_discount_level():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, discount_levels=[10.0, 20.0])


def test_run_create_schema_rejects_discount_above_100():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, discount_levels=[0.0, 10.0, 150.0])


def test_run_create_schema_default_levels():
    schema = RunCreateSchema(dataset_id=1, budget=100)
    assert schema.discount_levels == [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]


def test_run_create_schema_accepts_decimal_levels():
    schema = RunCreateSchema(dataset_id=1, budget=100, discount_levels=[0.0, 7.5, 12.5, 33.3])
    assert schema.discount_levels == [0.0, 7.5, 12.5, 33.3]


def test_run_create_schema_sorts_levels():
    schema = RunCreateSchema(dataset_id=1, budget=100, discount_levels=[20.0, 0.0, 10.0])
    assert schema.discount_levels == [0.0, 10.0, 20.0]


def test_run_create_schema_requires_at_least_two_levels():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, discount_levels=[0.0])


def test_run_create_schema_rejects_empty_treatment_column():
    with pytest.raises(ValueError):
        RunCreateSchema(dataset_id=1, budget=100, treatment_column="   ")


def test_dml_model_rejects_unsupported_estimator():
    with pytest.raises(ValueError):
        _make_base_estimator("GradientBoosting")


def test_dml_model_accepts_random_forest():
    est = _make_base_estimator("RandomForest")
    assert est.__class__.__name__ == "RandomForestRegressor"


def test_scenario_schema_rejects_negative_discount_levels():
    with pytest.raises(ValueError):
        ScenarioRequestSchema(budget=100, discount_levels=[-5.0])


def test_scenario_schema_rejects_missing_zero():
    with pytest.raises(ValueError):
        ScenarioRequestSchema(budget=100, discount_levels=[10.0, 20.0])


def test_scenario_schema_accepts_valid_levels():
    schema = ScenarioRequestSchema(budget=100, discount_levels=[0.0, 15.0, 30.0])
    assert schema.discount_levels == [0.0, 15.0, 30.0]
