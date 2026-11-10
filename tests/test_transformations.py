"""Tests for transformations.py: individual steps and ordered replay."""

from __future__ import annotations

import pandas as pd
import pytest

from transformations import apply_transforms, describe_op


@pytest.fixture
def base_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Customer": ["Alice", "Bob", "Carol", "Dan"],
            "City": ["Paris", "Berlin", "Madrid", "Paris"],
            "Revenue": [100.0, 250.0, 50.0, 400.0],
            "Units": [1, 3, 2, 5],
        }
    )


def test_select_keeps_only_chosen_columns_in_order(base_df):
    out, applied, errors = apply_transforms(base_df, [{"op": "select", "columns": ["City", "Revenue"]}])
    assert list(out.columns) == ["City", "Revenue"]
    assert applied == ["Kept 2 selected column(s)"]
    assert errors == []


def test_select_missing_column_reports_error_and_applies_nothing(base_df):
    out, applied, errors = apply_transforms(
        base_df, [{"op": "select", "columns": ["Revenue", "Nope"]}]
    )
    assert applied == []
    assert len(errors) == 1
    assert "Nope" in errors[0]
    pd.testing.assert_frame_equal(out, base_df)


def test_select_empty_list_rejected(base_df):
    _, applied, errors = apply_transforms(base_df, [{"op": "select", "columns": []}])
    assert applied == []
    assert "at least one column" in errors[0]


def test_rename_column(base_df):
    out, applied, errors = apply_transforms(
        base_df, [{"op": "rename", "old": "Revenue", "new": "Sales"}]
    )
    assert "Sales" in out.columns and "Revenue" not in out.columns
    assert errors == []
    assert "Renamed 'Revenue' to 'Sales'" in applied[0]


def test_rename_rejects_empty_and_duplicate_names(base_df):
    _, _, errors = apply_transforms(base_df, [{"op": "rename", "old": "Revenue", "new": "  "}])
    assert "empty" in errors[0]
    _, _, errors = apply_transforms(base_df, [{"op": "rename", "old": "Revenue", "new": "Units"}])
    assert "already exists" in errors[0]


def test_split_column_keeps_original_and_adds_parts():
    df = pd.DataFrame({"Name": ["John Smith", "Ada Lovelace"], "Revenue": [1.0, 2.0]})
    out, applied, errors = apply_transforms(df, [{"op": "split", "column": "Name", "sep": " "}])
    assert errors == []
    assert "Name" in out.columns  # original preserved
    assert list(out["Name 1"]) == ["John", "Ada"]
    assert list(out["Name 2"]) == ["Smith", "Lovelace"]


def test_split_without_separator_fails_cleanly():
    df = pd.DataFrame({"Code": ["A1", "B2"], "Revenue": [1.0, 2.0]})
    _, applied, errors = apply_transforms(df, [{"op": "split", "column": "Code", "sep": "|"}])
    assert applied == []
    assert "nothing to split" in errors[0]


def test_merge_columns_with_separator(base_df):
    out, _, errors = apply_transforms(
        base_df, [{"op": "merge", "columns": ["Customer", "City"], "sep": " @ ", "new_name": "Contact"}]
    )
    assert errors == []
    assert list(out["Contact"]) == ["Alice @ Paris", "Bob @ Berlin", "Carol @ Madrid", "Dan @ Paris"]


def test_merge_requires_two_columns(base_df):
    _, _, errors = apply_transforms(
        base_df, [{"op": "merge", "columns": ["Customer"], "sep": " ", "new_name": "X"}]
    )
    assert "at least two columns" in errors[0]


def test_merge_avoids_column_name_collision(base_df):
    out, _, _ = apply_transforms(
        base_df, [{"op": "merge", "columns": ["Customer", "City"], "sep": " ", "new_name": "City"}]
    )
    assert "City" in out.columns  # original untouched
    assert "City (2)" in out.columns  # merged copy got a unique name


def test_range_filter_keeps_rows_within_bounds(base_df):
    out, _, errors = apply_transforms(
        base_df, [{"op": "range", "column": "Revenue", "min": 100, "max": 300}]
    )
    assert errors == []
    assert list(out["Customer"]) == ["Alice", "Bob"]


def test_range_filter_rejects_non_numeric(base_df):
    _, _, errors = apply_transforms(
        base_df, [{"op": "range", "column": "City", "min": 0, "max": 10}]
    )
    assert "not numeric" in errors[0]


def test_join_left_adds_columns_from_right_file(base_df):
    right = pd.DataFrame({"City": ["Paris", "Berlin"], "Tax Rate": [0.2, 0.1]})
    out, applied, errors = apply_transforms(
        base_df,
        [{"op": "join", "right": right, "left_key": "City", "right_key": "City", "how": "left"}],
    )
    assert errors == []
    assert "Tax Rate" in out.columns
    assert len(out) == 4  # left join keeps every row
    assert out.loc[out["Customer"] == "Carol", "Tax Rate"].isna().all()  # Madrid unmatched


def test_join_inner_drops_unmatched_rows(base_df):
    right = pd.DataFrame({"City": ["Paris"], "Tax Rate": [0.2]})
    out, _, _ = apply_transforms(
        base_df,
        [{"op": "join", "right": right, "left_key": "City", "right_key": "City", "how": "inner"}],
    )
    assert list(out["Customer"]) == ["Alice", "Dan"]


def test_join_missing_key_column_reports_available_columns(base_df):
    right = pd.DataFrame({"City": ["Paris"], "Tax Rate": [0.2]})
    _, _, errors = apply_transforms(
        base_df,
        [{"op": "join", "right": right, "left_key": "City", "right_key": "Country", "how": "left"}],
    )
    assert "was not found in the second file" in errors[0]
    assert "City" in errors[0]  # lists available columns


def test_join_with_zero_matches_is_an_error(base_df):
    right = pd.DataFrame({"City": ["Tokyo"], "Tax Rate": [0.1]})
    _, _, errors = apply_transforms(
        base_df,
        [{"op": "join", "right": right, "left_key": "City", "right_key": "City", "how": "inner"}],
    )
    assert "0 rows" in errors[0]


def test_steps_apply_in_order(base_df):
    ops = [
        {"op": "rename", "old": "City", "new": "Location"},
        {"op": "select", "columns": ["Location", "Revenue"]},
    ]
    out, applied, errors = apply_transforms(base_df, ops)
    assert errors == []
    assert list(out.columns) == ["Location", "Revenue"]
    assert len(applied) == 2


def test_failure_stops_remaining_steps_but_keeps_earlier_ones(base_df):
    ops = [
        {"op": "rename", "old": "City", "new": "Location"},  # ok
        {"op": "select", "columns": ["Missing"]},  # fails
        {"op": "select", "columns": ["Revenue"]},  # never runs
    ]
    out, applied, errors = apply_transforms(base_df, ops)
    assert len(applied) == 1
    # Rename applied to the full frame; the failing select changed nothing.
    assert list(out.columns) == ["Customer", "Location", "Revenue", "Units"]
    assert len(errors) == 1
    assert errors[0].startswith("Step 2")
    assert "remaining steps skipped" in errors[0]


def test_unknown_operation_is_reported(base_df):
    _, applied, errors = apply_transforms(base_df, [{"op": "teleport"}])
    assert applied == []
    assert "unknown transformation" in errors[0]


def test_describe_op_covers_every_operation():
    assert "Kept" in describe_op({"op": "select", "columns": ["a", "b"]})
    assert "Renamed" in describe_op({"op": "rename", "old": "a", "new": "b"})
    assert "Split" in describe_op({"op": "split", "column": "a", "sep": ","})
    assert "Merged" in describe_op({"op": "merge", "columns": ["a", "b"], "new_name": "c"})
    assert "Kept rows" in describe_op({"op": "range", "column": "a", "min": 1, "max": 2})
    assert "join" in describe_op(
        {"op": "join", "left_key": "a", "right_key": "b", "how": "left"}
    )
