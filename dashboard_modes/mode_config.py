"""Definitions for sellable Smart Dashboard Modes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardMode:
    """A dashboard mode shown to the user."""

    key: str
    label: str
    audience: str
    description: str
    chart_limit: int | None
    include_pivots: bool
    icon: str


DEFAULT_MODE = "executive"
MODE_ORDER = ["executive", "analytical", "financial", "operational"]

DASHBOARD_MODES: dict[str, DashboardMode] = {
    "executive": DashboardMode(
        key="executive",
        label="Executive Dashboard",
        audience="Owners, CEOs, managers",
        description="Top KPIs, short business insights, and minimal clutter.",
        chart_limit=2,
        include_pivots=False,
        icon="briefcase",
    ),
    "analytical": DashboardMode(
        key="analytical",
        label="Analytical Dashboard",
        audience="Analysts",
        description="Full charts, filters, pivot tables, and drill-down exploration.",
        chart_limit=None,
        include_pivots=True,
        icon="search",
    ),
    "financial": DashboardMode(
        key="financial",
        label="Financial Dashboard",
        audience="Finance and accounts users",
        description="Revenue, cost, profit, margin, trends, and simple forecasts.",
        chart_limit=6,
        include_pivots=True,
        icon="dollar",
    ),
    "operational": DashboardMode(
        key="operational",
        label="Operational Dashboard",
        audience="Operations managers",
        description="Volume, process, inventory, orders, customer activity, and bottlenecks.",
        chart_limit=6,
        include_pivots=True,
        icon="workflow",
    ),
}


def get_mode(mode_key: str | None) -> DashboardMode:
    """Return a mode config, falling back to the executive dashboard."""
    return DASHBOARD_MODES.get(mode_key or DEFAULT_MODE, DASHBOARD_MODES[DEFAULT_MODE])
