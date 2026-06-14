"""Smart Dashboard Modes public API."""

from .mode_config import DASHBOARD_MODES, DEFAULT_MODE, MODE_ORDER, get_mode
from .renderers import (
    prepare_mode_artifacts,
    render_analytical_dashboard,
    render_executive_dashboard,
    render_financial_dashboard,
    render_mode_selector,
    render_operational_dashboard,
    render_smart_dashboard,
)

__all__ = [
    "DASHBOARD_MODES",
    "DEFAULT_MODE",
    "MODE_ORDER",
    "get_mode",
    "prepare_mode_artifacts",
    "render_analytical_dashboard",
    "render_executive_dashboard",
    "render_financial_dashboard",
    "render_mode_selector",
    "render_operational_dashboard",
    "render_smart_dashboard",
]
