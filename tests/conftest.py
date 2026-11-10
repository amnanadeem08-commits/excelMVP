"""Shared fixtures for the Excel MVP test suite."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
import pytest


class NamedBytesIO(BytesIO):
    """A BytesIO that exposes ``.name`` like Streamlit's UploadedFile."""

    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name


@pytest.fixture
def sales_df() -> pd.DataFrame:
    """Small, deterministic sales dataset with dates, categories and money."""
    rng = np.random.default_rng(42)
    n = 60
    return pd.DataFrame(
        {
            "Order ID": [f"ORD-{i:04d}" for i in range(n)],
            "Order Date": pd.date_range("2024-01-01", periods=n, freq="D"),
            "Region": rng.choice(["North", "South", "East", "West"], n),
            "Product": rng.choice(["Widget A", "Widget B", "Widget C"], n),
            "Revenue": np.round(rng.gamma(4, 250, n), 2),
            "Units": rng.integers(1, 20, n),
        }
    )


@pytest.fixture
def csv_upload(sales_df: pd.DataFrame) -> NamedBytesIO:
    return NamedBytesIO(sales_df.to_csv(index=False).encode("utf-8"), "sales.csv")


@pytest.fixture
def xlsx_upload(sales_df: pd.DataFrame) -> NamedBytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        sales_df.to_excel(writer, index=False, sheet_name="Sales")
        sales_df.head(10).to_excel(writer, index=False, sheet_name="Recent")
    return NamedBytesIO(buffer.getvalue(), "sales.xlsx")
