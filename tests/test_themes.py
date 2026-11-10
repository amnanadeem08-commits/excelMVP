"""Tests for dashboard themes (DESIGN.md §5): presets, surfaces, dark mode."""

from __future__ import annotations

import pandas as pd

from data_cleaning import clean_data, detect_column_types
from dashboard import (
    COLOR_THEMES,
    build_custom_theme,
    generate_charts,
    get_default_theme,
)

REQUIRED_KEYS = {
    "accent", "accent_dark", "sidebar_from", "sidebar_to", "gradient_rgb",
    "ink", "muted", "surface_soft", "palette", "success", "warning",
}


def test_every_preset_has_required_keys():
    """All presets must define the full base theme (surfaces may use defaults)."""
    for name, theme in COLOR_THEMES.items():
        missing = REQUIRED_KEYS - set(theme)
        assert not missing, f"theme '{name}' is missing keys: {missing}"
        assert len(theme["palette"]) >= 4, f"theme '{name}' needs a usable palette"
        assert all(c.startswith("#") for c in theme["palette"]), f"theme '{name}' palette must be hex"


def test_required_theme_set_exists():
    """DESIGN.md §5: Light Professional, Executive Blue-like, Minimal-like, Dark."""
    names = set(COLOR_THEMES)
    assert {"Light Professional", "Dark"} <= names
    # Executive Blue ≈ Corporate Blue; Minimal ≈ Slate Minimal (kept for saved sessions)
    assert {"Corporate Blue", "Slate Minimal"} <= names


def test_dark_theme_defines_dark_surfaces():
    dark = COLOR_THEMES["Dark"]
    assert dark.get("is_dark") is True
    assert dark.get("surface", "").startswith("#0")
    assert "card_bg" in dark and "plot_bg" in dark and "paper_bg" in dark
    # Dark ink must be a light color for contrast
    assert dark["ink"].startswith("#e") or dark["ink"].startswith("#f")


def test_custom_theme_gets_light_surface_defaults():
    theme = build_custom_theme("#ff0000")
    # No dark keys -> renderer falls back to light defaults
    assert "card_bg" not in theme and "is_dark" not in theme
    assert theme["accent"] == "#ff0000"


def test_charts_follow_dark_theme_surfaces():
    """Plotly chart backgrounds must come from the theme, not hard-coded white."""
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "Revenue": [10.0, 20.0, 30.0],
            "Units": [1.0, 2.0, 3.0],
            "Margin": [0.1, 0.2, 0.3],
        }
    )
    types = detect_column_types(df)
    charts = generate_charts(df, types, COLOR_THEMES["Dark"])
    assert charts
    for chart in charts:
        layout = chart.figure.layout
        assert layout.paper_bgcolor == COLOR_THEMES["Dark"]["paper_bg"]
        assert layout.plot_bgcolor == COLOR_THEMES["Dark"]["plot_bg"]
        assert layout.font.color == COLOR_THEMES["Dark"]["ink"]


def test_charts_keep_light_defaults_without_dark_keys():
    df = pd.DataFrame({"Revenue": [1.0, 2.0], "Region": ["a", "b"]})
    types = detect_column_types(df)
    charts = generate_charts(df, types, get_default_theme())
    assert charts
    assert charts[0].figure.layout.plot_bgcolor == "#ffffff"
