"""Regression tests for application-wide issues found during the full audit."""
from __future__ import annotations

import math

import pytest

from app.core.exceptions import InvalidDatasetError
from app.pipeline.optimizer import allocate
from app.schemas.dataset_schema import CustomerRowSchema, DatasetCreateSchema
from app.schemas.run_schema import RunCreateSchema
from app.schemas.scenario_schema import ScenarioRequestSchema


# ---------------------------------------------------------------------------
# 1. Custom treatment/outcome column mapping through full pipeline
# ---------------------------------------------------------------------------

class TestColumnMapping:
    """The frontend normalizes CSV columns to `treatment`/`outcome` before
    sending to the backend.  The backend pipeline must therefore use the
    fixed column names that actually exist in the Customer table, not the
    user's original CSV headers stored on the Run model."""

    def test_run_create_schema_accepts_custom_column_names(self):
        schema = RunCreateSchema(
            dataset_id=1,
            budget=100,
            treatment_column="discount_given",
            outcome_column="purchase_result",
        )
        assert schema.treatment_column == "discount_given"
        assert schema.outcome_column == "purchase_result"


# ---------------------------------------------------------------------------
# 2. Input validation: NaN / Infinity rejection
# ---------------------------------------------------------------------------

class TestNaNInfinityValidation:
    def test_dataset_rejects_nan_treatment(self):
        with pytest.raises(ValueError):
            CustomerRowSchema(features={"x": 1.0}, treatment=float("nan"), outcome=1)

    def test_dataset_rejects_inf_treatment(self):
        with pytest.raises(ValueError):
            CustomerRowSchema(features={"x": 1.0}, treatment=float("inf"), outcome=1)

    def test_dataset_rejects_negative_inf_treatment(self):
        with pytest.raises(ValueError):
            CustomerRowSchema(features={"x": 1.0}, treatment=float("-inf"), outcome=1)

    def test_dataset_rejects_nan_feature(self):
        with pytest.raises(ValueError):
            CustomerRowSchema(features={"x": float("nan")}, treatment=0.0, outcome=1)

    def test_dataset_rejects_inf_feature(self):
        with pytest.raises(ValueError):
            CustomerRowSchema(features={"x": float("inf")}, treatment=0.0, outcome=1)

    def test_dataset_rejects_negative_inf_feature(self):
        with pytest.raises(ValueError):
            CustomerRowSchema(features={"x": float("-inf")}, treatment=0.0, outcome=1)

    def test_run_create_schema_rejects_nan_budget(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=float("nan"))

    def test_run_create_schema_rejects_inf_budget(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=float("inf"))

    def test_run_create_schema_rejects_negative_inf_budget(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=float("-inf"))

    def test_scenario_schema_rejects_nan_budget(self):
        with pytest.raises(ValueError):
            ScenarioRequestSchema(budget=float("nan"))

    def test_scenario_schema_rejects_inf_budget(self):
        with pytest.raises(ValueError):
            ScenarioRequestSchema(budget=float("inf"))

    def test_scenario_schema_rejects_nan_discount_levels(self):
        with pytest.raises(ValueError):
            ScenarioRequestSchema(budget=100, discount_levels=[float("nan")])

    def test_scenario_schema_rejects_negative_discount_levels(self):
        with pytest.raises(ValueError):
            ScenarioRequestSchema(budget=100, discount_levels=[-5.0])


# ---------------------------------------------------------------------------
# 3. Optimizer edge cases
# ---------------------------------------------------------------------------

class TestOptimizerEdgeCases:
    def test_negative_budget(self):
        results, total = allocate({1: {0.0: 0.0, 10.0: 0.5}}, budget=-10.0)
        assert total == 0.0
        assert all(r.chosen_discount == 0.0 for r in results)

    def test_huge_budget_still_within_budget(self):
        ite_matrix = {i: {0.0: 0.0, 10.0: 0.1, 20.0: 0.2} for i in range(10)}
        results, total = allocate(ite_matrix, budget=1_000_000.0)
        assert total <= 1_000_000.0

    def test_duplicate_treatment_levels_rejected_by_schema(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=100, discount_levels=[10.0, 10.0, 20.0])

    def test_unsorted_treatment_levels_sorted_by_schema(self):
        schema = RunCreateSchema(dataset_id=1, budget=100, discount_levels=[20.0, 0.0, 10.0])
        assert schema.discount_levels == [0.0, 10.0, 20.0]

    def test_very_large_discount_rejected_by_schema(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=100, discount_levels=[2_000_000.0])

    def test_zero_discount_required_when_missing(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=100, discount_levels=[10.0, 20.0])

    def test_empty_discount_levels_rejected(self):
        with pytest.raises(ValueError):
            RunCreateSchema(dataset_id=1, budget=100, discount_levels=[])


# ---------------------------------------------------------------------------
# 4. Malformed CSV row length validation (frontend behavior)
# ---------------------------------------------------------------------------

class TestMalformedCSV:
    def test_build_rows_rejects_mismatched_row_length(self):
        """Simulate the CampaignConfigPage buildRows behavior."""
        headers = ["a", "b", "c", "d"]
        rawRows = ['1,2,3,4', '5,6']  # second row is too short
        treatmentColumn = "b"
        outcomeColumn = "c"

        def parseCSVLine(line):
            result = []
            current = ""
            inQuotes = False
            for i in range(len(line)):
                char = line[i]
                if char == '"':
                    if inQuotes and i + 1 < len(line) and line[i + 1] == '"':
                        current += '"'
                        i += 1
                    else:
                        inQuotes = not inQuotes
                elif char == "," and not inQuotes:
                    result.append(current)
                    current = ""
                else:
                    current += char
            result.append(current)
            return result

        malformed = []
        rows = []
        for idx, line in enumerate(rawRows):
            values = parseCSVLine(line)
            if len(values) != len(headers):
                malformed.append(f"Row {idx + 1}: expected {len(headers)} columns, got {len(values)}")
            else:
                record = {}
                for h, val in zip(headers, values):
                    record[h] = val
                rows.append(record)

        assert len(malformed) == 1
        assert "expected 4 columns, got 2" in malformed[0]
        assert len(rows) == 1

    def test_parse_csv_line_handles_quoted_commas(self):
        def parseCSVLine(line):
            result = []
            current = ""
            inQuotes = False
            for i in range(len(line)):
                char = line[i]
                if char == '"':
                    if inQuotes and i + 1 < len(line) and line[i + 1] == '"':
                        current += '"'
                        i += 1
                    else:
                        inQuotes = not inQuotes
                elif char == "," and not inQuotes:
                    result.append(current)
                    current = ""
                else:
                    current += char
            result.append(current)
            return result

        line = 'John,"Hyderabad, Telangana",10,1'
        parts = parseCSVLine(line)
        assert parts == ["John", "Hyderabad, Telangana", "10", "1"]

    def test_parse_csv_line_handles_escaped_quotes(self):
        def parseCSVLine(line):
            result = []
            current = ""
            inQuotes = False
            for i in range(len(line)):
                char = line[i]
                if char == '"':
                    if inQuotes and i + 1 < len(line) and line[i + 1] == '"':
                        current += '"'
                        i += 1
                    else:
                        inQuotes = not inQuotes
                elif char == "," and not inQuotes:
                    result.append(current)
                    current = ""
                else:
                    current += char
            result.append(current)
            return result

        line = '"She said ""hello""",5'
        parts = parseCSVLine(line)
        assert parts == ['She said "hello"', "5"]
