"""Simple local date-based numeric forecasting.

This module intentionally avoids paid integrations and heavy model assumptions.
It uses a transparent linear trend over monthly totals when the dataset has
enough valid date and numeric observations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ForecastResult:
    """Forecast output used by financial dashboards."""

    ok: bool
    message: str
    history: pd.DataFrame
    forecast: pd.DataFrame
    date_column: str | None = None
    value_column: str | None = None


def simple_date_forecast(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
    periods: int = 3,
) -> ForecastResult:
    """Forecast the next N monthly values for a numeric column.

    Returns a clear ``ok=False`` fallback if the columns are missing, invalid,
    or too sparse. Forecast values are clipped at zero when the historical
    series is non-negative.
    """
    if date_column not in df.columns or value_column not in df.columns:
        return ForecastResult(False, "Required date or numeric column is missing.", pd.DataFrame(), pd.DataFrame())

    work = pd.DataFrame(
        {
            "_date": pd.to_datetime(df[date_column], errors="coerce"),
            "_value": pd.to_numeric(df[value_column], errors="coerce"),
        }
    ).dropna()
    if work.empty:
        return ForecastResult(False, "No valid date and numeric values were found for forecasting.", pd.DataFrame(), pd.DataFrame())

    monthly = (
        work.assign(period=work["_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("period", as_index=False)["_value"]
        .sum()
        .sort_values("period")
        .rename(columns={"period": "date", "_value": "actual"})
    )
    if len(monthly) < 3:
        return ForecastResult(False, "Forecasting needs at least three valid monthly periods.", monthly, pd.DataFrame())

    x = np.arange(len(monthly), dtype=float)
    y = monthly["actual"].astype(float).to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    future_x = np.arange(len(monthly), len(monthly) + periods, dtype=float)
    future_dates = pd.date_range(monthly["date"].max() + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    predicted = intercept + slope * future_x
    if (y >= 0).all():
        predicted = np.clip(predicted, 0, None)

    forecast = pd.DataFrame({"date": future_dates, "forecast": predicted.round(2)})
    direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    return ForecastResult(
        True,
        f"Simple {periods}-month linear forecast based on a {direction} monthly trend.",
        monthly,
        forecast,
        date_column=date_column,
        value_column=value_column,
    )
