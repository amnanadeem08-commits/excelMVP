"""User-controlled data transformations (safe, validated, replayable).

Pure pandas functions with no Streamlit dependency so every step is unit
testable. The UI records a list of operation dicts in session state and
``apply_transforms`` replays them in order on every Streamlit rerun, so the
working dataset is always reproducible from the original file plus the step
list (nothing is mutated in place; the user can clear all steps at any time).

Supported operations:
- ``select``  : keep only the chosen columns
- ``rename``  : rename one column
- ``split``   : split a column into parts on a separator (original kept)
- ``merge``   : concatenate several columns into one new column
- ``range``   : keep rows whose value for a numeric column is within [min, max]
- ``join``    : join a second dataset on a key column (left/inner)

CUSTOMIZE: add a new operation by writing ``_op_<kind>`` and registering it
in ``_OPERATORS`` plus a label branch in ``describe_op``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _unique_name(base: str, existing: set[str]) -> str:
    """Return ``base`` or a non-colliding ``base (2)`` / ``base (3)`` ..."""
    name, counter = base, 2
    while name in existing:
        name = f"{base} ({counter})"
        counter += 1
    return name


def _require_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        available = ", ".join(str(col) for col in df.columns)
        raise ValueError(f"column '{column}' was not found. Available columns: {available}.")


def _op_select(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    columns = list(op.get("columns") or [])
    if not columns:
        raise ValueError("select at least one column to keep.")
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"column(s) not found: {', '.join(str(col) for col in missing)}.")
    return df[columns].copy()


def _op_rename(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    old, new = op.get("old"), str(op.get("new") or "").strip()
    _require_column(df, str(old))
    if not new:
        raise ValueError("the new column name is empty.")
    if new in df.columns and new != old:
        raise ValueError(f"a column named '{new}' already exists.")
    return df.rename(columns={old: new})


def _op_split(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    column = str(op.get("column"))
    sep = str(op.get("sep") or ",")
    _require_column(df, column)
    parts = df[column].astype(str).str.split(sep, expand=True)
    if parts.shape[1] < 2:
        raise ValueError(
            f"'{column}' does not contain the separator '{sep}' anywhere — nothing to split."
        )
    out = df.copy()
    created: set[str] = set(out.columns)
    for idx in range(parts.shape[1]):
        name = _unique_name(f"{column} {idx + 1}", created)
        created.add(name)
        out[name] = parts[idx].str.strip()
    return out


def _op_merge(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    columns = list(op.get("columns") or [])
    if len(columns) < 2:
        raise ValueError("pick at least two columns to merge.")
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"column(s) not found: {', '.join(str(col) for col in missing)}.")
    sep = str(op.get("sep", " "))
    base = str(op.get("new_name") or "Merged").strip() or "Merged"
    name = _unique_name(base, set(df.columns))
    out = df.copy()
    out[name] = out[columns].fillna("").astype(str).agg(sep.join, axis=1)
    return out


def _op_range(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    column = str(op.get("column"))
    _require_column(df, column)
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"'{column}' is not numeric — a range filter needs a measure column.")
    low, high = float(op.get("min", 0)), float(op.get("max", 0))
    if low > high:
        low, high = high, low
    return df[(df[column] >= low) & (df[column] <= high)].copy()


def _op_join(df: pd.DataFrame, op: dict[str, Any]) -> pd.DataFrame:
    right = op.get("right")
    if not isinstance(right, pd.DataFrame):
        raise ValueError("no join file is loaded — upload one in the Join section first.")
    left_key, right_key = str(op.get("left_key")), str(op.get("right_key"))
    _require_column(df, left_key)
    if right_key not in right.columns:
        available = ", ".join(str(col) for col in right.columns)
        raise ValueError(f"key '{right_key}' was not found in the second file. Available: {available}.")
    how = str(op.get("how", "left")).lower()
    if how not in {"left", "inner"}:
        raise ValueError("join type must be 'left' or 'inner'.")
    try:
        merged = df.merge(
            right, left_on=left_key, right_on=right_key, how=how, suffixes=("", "_joined")
        )
    except Exception as exc:  # dtype mismatches and similar merge failures
        raise ValueError(
            f"could not join on '{left_key}' = '{right_key}': {exc}. "
            "Check that both key columns hold matching value types (text vs number vs date)."
        ) from exc
    if merged.empty:
        raise ValueError(
            f"the join produced 0 rows — no values of '{left_key}' matched '{right_key}'."
        )
    return merged


_OPERATORS = {
    "select": _op_select,
    "rename": _op_rename,
    "split": _op_split,
    "merge": _op_merge,
    "range": _op_range,
    "join": _op_join,
}


def describe_op(op: dict[str, Any]) -> str:
    """One-line, human-readable label for an applied step (for the UI log)."""
    kind = op.get("op", "?")
    if kind == "select":
        return f"Kept {len(op.get('columns') or [])} selected column(s)"
    if kind == "rename":
        return f"Renamed '{op.get('old')}' to '{op.get('new')}'"
    if kind == "split":
        return f"Split '{op.get('column')}' on '{op.get('sep')}'"
    if kind == "merge":
        cols = ", ".join(str(c) for c in op.get("columns") or [])
        return f"Merged [{cols}] into '{op.get('new_name', 'Merged')}'"
    if kind == "range":
        return f"Kept rows where {op.get('column')} is {op.get('min')} - {op.get('max')}"
    if kind == "join":
        return (
            f"{str(op.get('how', 'left')).title()} join with external file "
            f"on '{op.get('left_key')}' = '{op.get('right_key')}'"
        )
    return f"Applied step '{kind}'"


def apply_transforms(
    df: pd.DataFrame, ops: list[dict[str, Any]]
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Replay recorded transformation steps in order.

    Returns ``(working_df, applied_labels, error_messages)``. Execution stops
    at the first failing step (later steps may depend on it); steps applied
    before the failure remain applied, and each failure is reported with its
    step number so the user can clear or reorder.
    """
    current = df.copy()
    applied: list[str] = []
    errors: list[str] = []
    for index, op in enumerate(ops, start=1):
        operator = _OPERATORS.get(str(op.get("op")))
        if operator is None:
            errors.append(f"Step {index}: unknown transformation '{op.get('op')}' — remaining steps skipped.")
            break
        try:
            current = operator(current, op)
        except ValueError as exc:
            errors.append(f"Step {index} ({describe_op(op)}): {exc} — remaining steps skipped.")
            break
        applied.append(describe_op(op))
    return current, applied, errors
