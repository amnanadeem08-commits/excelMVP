"""Data binding resolution without storing dataframes in widgets."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

from widgets.models import DataBinding


class DatasetRegistry:
    """Runtime dataset lookup by id (session-scoped in Streamlit)."""

    def __init__(self) -> None:
        self._datasets: dict[str, pd.DataFrame] = {}

    def register(self, dataset_id: str, frame: pd.DataFrame) -> None:
        self._datasets[dataset_id] = frame

    def get(self, dataset_id: str) -> pd.DataFrame | None:
        return self._datasets.get(dataset_id)

    def clear(self) -> None:
        self._datasets.clear()


def binding_cache_key(binding: DataBinding) -> str:
    payload = json.dumps(binding.to_dict(), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def resolve_dataset(binding: DataBinding, registry: DatasetRegistry) -> pd.DataFrame:
    """Resolve a dataset using binding metadata only."""
    frame = registry.get(binding.dataset_id)
    if frame is None:
        return pd.DataFrame()

    result = frame.copy()
    for column, value in binding.filters.items():
        if column in result.columns:
            if isinstance(value, (list, tuple, set)):
                result = result[result[column].isin(list(value))]
            else:
                result = result[result[column] == value]

    if binding.columns:
        keep = [col for col in binding.columns if col in result.columns]
        if keep:
            result = result[keep]

    if binding.sort:
        sort_cols = [col for col in binding.sort if col in result.columns]
        if sort_cols:
            result = result.sort_values(sort_cols)

    return result.head(1000)


def default_binding(dataset_id: str, *, columns: list[str] | None = None) -> DataBinding:
    return DataBinding(
        dataset_id=dataset_id,
        columns=list(columns or []),
        cache_key=binding_cache_key(DataBinding(dataset_id=dataset_id, columns=list(columns or []))),
    )
