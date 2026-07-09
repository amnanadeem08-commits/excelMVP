"""Dashboard module: interactive Streamlit + Plotly UI building blocks.

Contains everything visual: page styling, KPI cards, sidebar filters, and
automatic chart generation (line, bar, pie, histogram, scatter, heatmap).

CUSTOMIZE:
- Change the color palette / fonts in ``inject_styles``.
- Add chart types in ``generate_charts``.
- Adjust how many filter widgets render in ``filter_dataframe``.
"""

from __future__ import annotations

import base64
import html as html_lib
import os
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from analytics_engine import categorical_dimensions, numeric_measures
from visualization_engine import ChartRecommendation, ChartSpec, VisualizationEngine

PLOTLY_TEMPLATE = "plotly_white"

# CUSTOMIZE: add more presets or edit hex values for client brands.
COLOR_THEMES: dict[str, dict[str, str | list[str]]] = {
    "Corporate Blue": {
        "accent": "#2563eb",
        "accent_dark": "#1d4ed8",
        "sidebar_from": "#0f172a",
        "sidebar_to": "#111827",
        "gradient_rgb": "37,99,235",
        "ink": "#111827",
        "muted": "#64748b",
        "surface_soft": "#f8fafc",
        "palette": ["#2563eb", "#0891b2", "#059669", "#d97706", "#7c3aed"],
        "success": "#059669",
        "warning": "#d97706",
    },
    "Emerald Finance": {
        "accent": "#059669",
        "accent_dark": "#047857",
        "sidebar_from": "#064e3b",
        "sidebar_to": "#022c22",
        "gradient_rgb": "5,150,105",
        "ink": "#052e16",
        "muted": "#4b5563",
        "surface_soft": "#f0fdf4",
        "palette": ["#059669", "#10b981", "#0891b2", "#14b8a6", "#84cc16"],
        "success": "#16a34a",
        "warning": "#ca8a04",
    },
    "Royal Purple": {
        "accent": "#7c3aed",
        "accent_dark": "#6d28d9",
        "sidebar_from": "#2e1065",
        "sidebar_to": "#1e1b4b",
        "gradient_rgb": "124,58,237",
        "ink": "#1e1b4b",
        "muted": "#6b7280",
        "surface_soft": "#faf5ff",
        "palette": ["#7c3aed", "#a855f7", "#6366f1", "#ec4899", "#8b5cf6"],
        "success": "#059669",
        "warning": "#d97706",
    },
    "Sunset Business": {
        "accent": "#ea580c",
        "accent_dark": "#c2410c",
        "sidebar_from": "#431407",
        "sidebar_to": "#1c1917",
        "gradient_rgb": "234,88,12",
        "ink": "#1c1917",
        "muted": "#78716c",
        "surface_soft": "#fff7ed",
        "palette": ["#ea580c", "#f59e0b", "#ef4444", "#f97316", "#eab308"],
        "success": "#059669",
        "warning": "#dc2626",
    },
    "Ocean Teal": {
        "accent": "#0891b2",
        "accent_dark": "#0e7490",
        "sidebar_from": "#164e63",
        "sidebar_to": "#0f172a",
        "gradient_rgb": "8,145,178",
        "ink": "#0f172a",
        "muted": "#64748b",
        "surface_soft": "#ecfeff",
        "palette": ["#0891b2", "#06b6d4", "#0284c7", "#14b8a6", "#3b82f6"],
        "success": "#059669",
        "warning": "#d97706",
    },
    "Ruby Executive": {
        "accent": "#dc2626",
        "accent_dark": "#b91c1c",
        "sidebar_from": "#450a0a",
        "sidebar_to": "#1f2937",
        "gradient_rgb": "220,38,38",
        "ink": "#111827",
        "muted": "#6b7280",
        "surface_soft": "#fef2f2",
        "palette": ["#dc2626", "#f97316", "#eab308", "#ef4444", "#b91c1c"],
        "success": "#059669",
        "warning": "#ca8a04",
    },
    "Slate Minimal": {
        "accent": "#334155",
        "accent_dark": "#1e293b",
        "sidebar_from": "#0f172a",
        "sidebar_to": "#334155",
        "gradient_rgb": "51,65,85",
        "ink": "#0f172a",
        "muted": "#64748b",
        "surface_soft": "#f8fafc",
        "palette": ["#334155", "#475569", "#64748b", "#0ea5e9", "#94a3b8"],
        "success": "#059669",
        "warning": "#d97706",
    },
    "Rose Modern": {
        "accent": "#db2777",
        "accent_dark": "#be185d",
        "sidebar_from": "#500724",
        "sidebar_to": "#1f2937",
        "gradient_rgb": "219,39,119",
        "ink": "#1f2937",
        "muted": "#6b7280",
        "surface_soft": "#fdf2f8",
        "palette": ["#db2777", "#ec4899", "#a855f7", "#f43f5e", "#8b5cf6"],
        "success": "#059669",
        "warning": "#d97706",
    },
}

# Backward-compatible named aliases required by the Visualization Engine v2 brief.
COLOR_THEMES.setdefault("Modern", COLOR_THEMES["Ocean Teal"])
COLOR_THEMES.setdefault("Minimal", COLOR_THEMES["Slate Minimal"])
COLOR_THEMES.setdefault("Dark", COLOR_THEMES["Ruby Executive"])
COLOR_THEMES.setdefault("Light", COLOR_THEMES["Corporate Blue"])
COLOR_THEMES.setdefault("Professional", COLOR_THEMES["Emerald Finance"])

DASHBOARD_FOCUS_OPTIONS: dict[str, dict[str, str]] = {
    "AI Recommended": {
        "label": "AI Recommended",
        "caption": "Let the insight engine lead with the strongest story.",
    },
    "Executive Summary": {
        "label": "Executive Summary",
        "caption": "Prioritize KPIs, trend movement, and client-ready recommendations.",
    },
    "Sales / Revenue": {
        "label": "Sales / Revenue",
        "caption": "Emphasize top segments, share charts, and revenue movement.",
    },
    "Operations": {
        "label": "Operations",
        "caption": "Favor distributions, outliers, quality, and process signals.",
    },
    "Finance": {
        "label": "Finance",
        "caption": "Highlight totals, growth, variance, and correlation checks.",
    },
}

DASHBOARD_TEMPLATE_PRESETS: dict[str, dict[str, object]] = {
    "Executive Dashboard": {"two_column": True, "max_charts": 6, "focus": "Executive Summary", "height": 420, "dark": False},
    "Business Dashboard": {"two_column": True, "max_charts": 8, "focus": "AI Recommended", "height": 420, "dark": False},
    "Finance Dashboard": {"two_column": True, "max_charts": 8, "focus": "Finance", "height": 430, "dark": False},
    "HR Dashboard": {"two_column": True, "max_charts": 8, "focus": "Operations", "height": 420, "dark": False},
    "Sales Dashboard": {"two_column": True, "max_charts": 8, "focus": "Sales / Revenue", "height": 430, "dark": False},
    "Marketing Dashboard": {"two_column": True, "max_charts": 10, "focus": "Sales / Revenue", "height": 420, "dark": False},
    "Research Dashboard": {"two_column": False, "max_charts": 10, "focus": "AI Recommended", "height": 460, "dark": False},
    "Minimal Dashboard": {"two_column": False, "max_charts": 5, "focus": "Executive Summary", "height": 400, "dark": False},
    "Dark Dashboard": {"two_column": True, "max_charts": 8, "focus": "AI Recommended", "height": 430, "dark": True},
}


def get_default_theme() -> dict:
    return COLOR_THEMES["Corporate Blue"]


def _normalize_hex(color: str) -> str | None:
    """Return a valid ``#RRGGBB`` string or ``None``."""
    if not color:
        return None
    color = color.strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        return color.lower()
    if re.fullmatch(r"[0-9A-Fa-f]{6}", color):
        return f"#{color.lower()}"
    if re.fullmatch(r"#[0-9A-Fa-f]{3}", color):
        h = color[1:]
        return f"#{h[0] * 2}{h[1] * 2}{h[2] * 2}".lower()
    return None


def _hex_to_rgb_tuple(hex_color: str) -> tuple[int, int, int]:
    h = _normalize_hex(hex_color) or "#2563eb"
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _rgb_string(hex_color: str) -> str:
    r, g, b = _hex_to_rgb_tuple(hex_color)
    return f"{r},{g},{b}"


def _darken_hex(hex_color: str, factor: float = 0.72) -> str:
    r, g, b = _hex_to_rgb_tuple(hex_color)
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def _lighten_hex(hex_color: str, factor: float = 0.28) -> str:
    r, g, b = _hex_to_rgb_tuple(hex_color)
    return f"#{int(r + (255 - r) * factor):02x}{int(g + (255 - g) * factor):02x}{int(b + (255 - b) * factor):02x}"


def build_custom_theme(primary: str, secondary: str | None = None, tertiary: str | None = None) -> dict:
    """Build a full theme dict from 1-3 client hex colors."""
    primary = _normalize_hex(primary) or "#2563eb"
    secondary = _normalize_hex(secondary) or _lighten_hex(primary, 0.35)
    tertiary = _normalize_hex(tertiary) or _darken_hex(primary, 0.85)
    accent_dark = _darken_hex(primary, 0.78)
    return {
        "accent": primary,
        "accent_dark": accent_dark,
        "sidebar_from": _darken_hex(primary, 0.32),
        "sidebar_to": _darken_hex(primary, 0.48),
        "gradient_rgb": _rgb_string(primary),
        "ink": "#111827",
        "muted": "#64748b",
        "surface_soft": _lighten_hex(primary, 0.92),
        "palette": [primary, secondary, tertiary, accent_dark, _lighten_hex(secondary, 0.4)],
        "success": "#059669",
        "warning": "#d97706",
    }


def _theme_swatches(theme: dict) -> str:
    palette = theme["palette"]
    return "".join(
        f'<span title="{c}" style="display:inline-block;width:30px;height:30px;border-radius:8px;'
        f'background:{c};margin-right:6px;border:2px solid rgba(255,255,255,.9);'
        f'box-shadow:0 2px 6px rgba(0,0,0,.15);"></span>'
        for c in palette[:5]
    )


def select_client_branding() -> tuple[dict, str, dict]:
    """Ask client for company name, logo, and color scheme (preset or custom hex)."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Client Branding")
    st.sidebar.caption("Add the client's name, logo, and brand colors for a white-label dashboard.")

    company_name = st.sidebar.text_input("Company / client name", placeholder="e.g. Acme Retail Ltd", key="client_company")
    logo_file = st.sidebar.file_uploader("Company logo", type=["png", "jpg", "jpeg", "webp"], key="client_logo")
    if logo_file is not None:
        st.sidebar.image(logo_file, width=110, caption="Logo preview")

    st.sidebar.markdown("**Color scheme**")
    names = list(COLOR_THEMES.keys()) + ["Custom Brand Colors"]
    choice = st.sidebar.selectbox("Color theme", names, key="client_color_theme")

    if choice == "Custom Brand Colors":
        pick_primary = st.sidebar.color_picker("Primary brand color", "#2563eb", key="pick_primary")
        pick_secondary = st.sidebar.color_picker("Secondary color", "#0891b2", key="pick_secondary")
        pick_tertiary = st.sidebar.color_picker("Third accent", "#059669", key="pick_tertiary")
        with st.sidebar.expander("Or type hex codes manually"):
            hex_primary = st.text_input("Primary hex", pick_primary, placeholder="#2563eb", key="hex_primary")
            hex_secondary = st.text_input("Secondary hex", pick_secondary, placeholder="#0891b2", key="hex_secondary")
            hex_tertiary = st.text_input("Third hex", pick_tertiary, placeholder="#059669", key="hex_tertiary")
        theme = build_custom_theme(
            _normalize_hex(hex_primary) or pick_primary,
            _normalize_hex(hex_secondary) or pick_secondary,
            _normalize_hex(hex_tertiary) or pick_tertiary,
        )
        theme_label = f"Custom ({theme['accent']})"
    else:
        theme = COLOR_THEMES[choice]
        theme_label = choice

    st.sidebar.markdown(
        f'<div style="margin:.35rem 0 .85rem;">{_theme_swatches(theme)}</div>'
        f'<div style="font-size:.78rem;color:#94a3b8;">Primary: {theme["accent"]}</div>',
        unsafe_allow_html=True,
    )

    branding = {
        "company_name": company_name.strip() or "Client Dashboard",
        "logo_bytes": logo_file.getvalue() if logo_file is not None else None,
        "logo_name": logo_file.name if logo_file is not None else "",
    }
    display_name = company_name.strip() or theme_label
    return theme, display_name, branding


def select_dashboard_controls() -> dict:
    """Render left-sidebar dashboard builder controls."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Dashboard Builder")

    focus = st.sidebar.selectbox(
        "AI dashboard focus",
        list(DASHBOARD_FOCUS_OPTIONS.keys()),
        key="dashboard_focus",
        help="Controls which insight story and chart mix should be emphasized.",
    )
    st.sidebar.caption(DASHBOARD_FOCUS_OPTIONS[focus]["caption"])

    dashboard_template = st.sidebar.selectbox(
        "Dashboard template",
        list(DASHBOARD_TEMPLATE_PRESETS.keys()),
        index=0,
        key="dashboard_template",
        help="Applies a professional layout preset for KPI cards, chart density, and visuals.",
    )

    density = st.sidebar.radio(
        "Chart density",
        ["Compact", "Balanced", "Deep Dive"],
        index=1,
        horizontal=False,
        key="dashboard_density",
    )
    max_charts = {"Compact": 4, "Balanced": 8, "Deep Dive": 12}[density]

    layout = st.sidebar.radio(
        "Chart layout",
        ["Two columns", "Single column"],
        index=0,
        key="dashboard_layout",
    )

    chart_sort = st.sidebar.selectbox(
        "Chart sorting",
        ["Relevance", "Title (A-Z)", "Title (Z-A)"],
        index=0,
        key="chart_sorting",
    )

    chart_height = st.sidebar.slider(
        "Chart height",
        min_value=320,
        max_value=680,
        value=430,
        step=10,
        key="chart_height",
        help="Resize charts for compact or presentation-focused layouts.",
    )

    show_chart_downloads = st.sidebar.toggle(
        "Enable chart downloads (PNG/SVG)",
        value=True,
        key="show_chart_downloads",
    )

    show_ai_brief = st.sidebar.toggle("Show AI dashboard brief", value=True, key="show_ai_brief")

    template_defaults = DASHBOARD_TEMPLATE_PRESETS.get(dashboard_template, DASHBOARD_TEMPLATE_PRESETS["Executive Dashboard"])
    return {
        "focus": focus,
        "dashboard_template": dashboard_template,
        "density": density,
        "max_charts": min(max_charts, int(template_defaults["max_charts"])),
        "two_column": (layout == "Two columns") if dashboard_template != "Minimal Dashboard" else False,
        "chart_sort": chart_sort,
        "chart_height": chart_height,
        "show_chart_downloads": show_chart_downloads,
        "template_dark": bool(template_defaults["dark"]),
        "show_ai_brief": show_ai_brief,
    }


# Backward-compatible alias
def select_color_theme() -> tuple[dict, str]:
    theme, name, _ = select_client_branding()
    return theme, name


def apply_chart_theme(charts: list[ChartSpec], theme: dict) -> list[ChartSpec]:
    """Re-style already-generated charts when the client changes the color theme."""
    return VisualizationEngine(theme).apply_theme(charts)


def generate_charts(df: pd.DataFrame, column_types: dict[str, list[str]], theme: dict | None = None) -> list[ChartSpec]:
    """Build a smart set of charts based on the detected column types."""
    theme = theme or get_default_theme()
    template_name = st.session_state.get("dashboard_template", "Executive Dashboard")
    return VisualizationEngine(theme, template_name=template_name).build_auto_charts(df, column_types, max_charts=18)


def recommend_charts(df: pd.DataFrame, column_types: dict[str, list[str]], theme: dict | None = None) -> list[ChartRecommendation]:
    """Return ranked chart recommendations for the current dataset."""
    theme = theme or get_default_theme()
    template_name = st.session_state.get("dashboard_template", "Executive Dashboard")
    return VisualizationEngine(theme, template_name=template_name).recommend(df, column_types)


# ---------------------------------------------------------------------------
# Streamlit UI helpers
# ---------------------------------------------------------------------------
def inject_styles(theme: dict | None = None) -> None:
    """Inject CSS using the client's selected color theme."""
    theme = theme or get_default_theme()
    accent = theme["accent"]
    accent_dark = theme["accent_dark"]
    gradient_rgb = theme["gradient_rgb"]
    sidebar_from = theme["sidebar_from"]
    sidebar_to = theme["sidebar_to"]
    surface_soft = theme["surface_soft"]
    st.markdown(
        f"""
        <style>
        :root {{
            --surface: #ffffff;
            --surface-soft: {surface_soft};
            --card-bg: rgba(255,255,255,.94);
            --card-border: rgba(148, 163, 184, .28);
            --ink: {theme["ink"]};
            --muted: {theme["muted"]};
            --accent: {accent};
            --accent-dark: {accent_dark};
            --success: {theme["success"]};
            --warning: {theme["warning"]};
        }}
        .stApp {{
            background:
                linear-gradient(135deg, rgba({gradient_rgb},.12), transparent 28rem),
                linear-gradient(180deg, {surface_soft} 0%, #eef2f7 100%);
            color: var(--ink);
            font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
        }}
        .block-container {{ padding-top: 1.3rem; padding-bottom: 2.4rem; max-width: 1480px; }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {sidebar_from} 0%, {sidebar_to} 100%);
            color: #fff;
            border-right: 1px solid rgba(255,255,255,.08);
        }}
        [data-testid="stSidebar"] * {{ color: inherit; }}
        [data-testid="stSidebar"] [data-testid="stFileUploader"] {{
            border: 1px solid rgba(255,255,255,.16);
            background: rgba(255,255,255,.06);
            border-radius: 8px;
            padding: .55rem;
        }}
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section {{
            background: #ffffff;
            border-color: rgba({gradient_rgb},.25);
        }}
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section *,
        [data-testid="stFileUploader"] section * {{
            color: #0f172a;
        }}
        [data-testid="stSidebar"] [data-testid="stFileUploader"] small,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {{
            color: rgba(255,255,255,.78);
        }}
        .hero {{ padding: 1.3rem 0 1.05rem; border-bottom: 1px solid rgba(148,163,184,.22); margin-bottom: .4rem; }}
        .hero h1 {{ font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; margin: 0; color: var(--ink); }}
        .hero p {{ color: var(--muted); font-size: 1.05rem; margin-top: .65rem; max-width: 58rem; }}
        .dashboard-banner {{
            background: linear-gradient(135deg, {accent} 0%, {accent_dark} 100%);
            color: #fff;
            border-radius: 12px;
            padding: 1.1rem 1.35rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 14px 36px rgba({gradient_rgb},.28);
        }}
        .dashboard-banner h3 {{ margin: 0; font-size: 1.35rem; font-weight: 750; color: #fff; }}
        .dashboard-banner p {{ margin: .35rem 0 0; font-size: .92rem; color: rgba(255,255,255,.88); }}
        .metric-card {{
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            box-shadow: 0 12px 32px rgba(15,23,42,.08);
            min-height: 112px;
            transition: transform .15s ease, box-shadow .15s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 16px 40px rgba(15,23,42,.12);
        }}
        .metric-card .label {{ color: var(--muted); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }}
        .metric-card .value {{ color: var(--ink); font-size: 1.85rem; font-weight: 750; margin-top: .3rem; overflow-wrap: anywhere; }}
        .metric-card .note {{ color: var(--muted); font-size: .9rem; margin-top: .2rem; }}
        .chart-accent-bar {{
            height: 5px;
            border-radius: 10px 10px 0 0;
            margin-top: .65rem;
        }}
        div[data-testid="stPlotlyChart"] {{
            border: 1px solid rgba(148,163,184,.22);
            border-radius: 0 0 12px 12px;
            background: rgba(255,255,255,.95);
            padding: .25rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 10px 28px rgba(15,23,42,.06);
        }}
        .section-title {{ font-size: 1.35rem; font-weight: 760; margin: 1.55rem 0 .7rem; color: var(--ink); }}
        .insight {{
            border-left: 4px solid {accent};
            background: rgba(255,255,255,.88);
            border-radius: 8px;
            padding: .8rem 1rem;
            margin-bottom: .65rem;
            color: #1d2939;
            box-shadow: 0 8px 24px rgba(15,23,42,.05);
        }}
        .warning {{ border-left-color: {theme["warning"]}; }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid rgba(148,163,184,.28);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 10px 26px rgba(15,23,42,.05);
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: .35rem;
            background: rgba(255,255,255,.78);
            border: 1px solid rgba(148,163,184,.24);
            border-radius: 8px;
            padding: .35rem;
        }}
        .stTabs [data-baseweb="tab"] {{ border-radius: 7px; color: #475569; font-weight: 650; padding: .6rem .85rem; }}
        .stTabs [aria-selected="true"] {{ background: {sidebar_from}; color: #ffffff; }}
        div[data-testid="stFileUploader"] {{
            background: rgba(255,255,255,.92);
            border: 1px dashed rgba({gradient_rgb},.45);
            border-radius: 8px;
            padding: .65rem;
        }}
        div[data-testid="stFileUploader"] label,
        div[data-testid="stFileUploader"] p {{
            color: #0f172a;
        }}
        div[data-testid="stFileUploader"] button {{
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            box-shadow: none;
        }}
        div[data-testid="stFileUploader"] button:hover,
        div[data-testid="stFileUploader"] button:focus {{
            background: {surface_soft};
            color: #0f172a;
            border: 1px solid {accent};
            box-shadow: 0 0 0 2px rgba({gradient_rgb},.16);
        }}
        .stButton > button, .stDownloadButton > button {{
            background: linear-gradient(180deg, var(--accent), var(--accent-dark));
            color: #ffffff;
            border: 0;
            border-radius: 8px;
            padding: .62rem 1rem;
            font-weight: 700;
            box-shadow: 0 8px 18px rgba({gradient_rgb},.28);
            transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            color: #ffffff;
            background: linear-gradient(180deg, {accent_dark}, {sidebar_from});
            border: 0;
            transform: translateY(-1px);
            box-shadow: 0 12px 24px rgba({gradient_rgb},.35);
        }}
        .stButton > button:active, .stDownloadButton > button:active,
        .stButton > button:focus, .stDownloadButton > button:focus {{
            color: #ffffff; border: 0; outline: 2px solid rgba({gradient_rgb},.28);
        }}
        div[role="radiogroup"] {{
            background: rgba(255,255,255,.86);
            border: 1px solid rgba(148,163,184,.28);
            border-radius: 8px;
            padding: .45rem .65rem;
        }}
        div[role="radiogroup"] label {{ color: #334155; font-weight: 650; }}
        .stAlert {{ border-radius: 8px; }}
        h1, h2, h3, p, label {{ letter-spacing: 0; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _html_block(html: str, height: int) -> None:
    """Render HTML via iframe — works when st.markdown escapes or code-blocks markup."""
    components.html(html, height=height, scrolling=False)


def render_card(label: str, value: str, note: str = "", accent: str = "#2563eb") -> None:
    """Render a single KPI metric card with a themed accent stripe."""
    _html_block(
        f'<div style="border:1px solid #e2e8f0;border-top:4px solid {accent};border-radius:12px;'
        f'padding:14px 16px;background:#fff;box-shadow:0 8px 22px rgba(15,23,42,.07);'
        f'font-family:Inter,Segoe UI,system-ui,sans-serif;">'
        f'<div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.08em;">'
        f'{html_lib.escape(label)}</div>'
        f'<div style="color:#111827;font-size:26px;font-weight:700;margin-top:6px;">'
        f'{html_lib.escape(value)}</div>'
        f'<div style="color:#64748b;font-size:12px;margin-top:4px;">{html_lib.escape(note)}</div></div>',
        height=118,
    )


def render_metric_cards(kpis: dict[str, dict[str, str]], theme: dict | None = None) -> None:
    """Render a responsive grid of KPI cards using the client color palette."""
    theme = theme or get_default_theme()
    palette = theme["palette"]
    cols = st.columns(min(4, max(1, len(kpis))))
    for idx, (label, metric) in enumerate(kpis.items()):
        with cols[idx % len(cols)]:
            render_card(label, metric["value"], metric.get("note", ""), palette[idx % len(palette)])


def render_dashboard_banner(theme: dict, theme_name: str, branding: dict | None = None) -> None:
    """Dashboard header with client logo, name, and active color theme."""
    branding = branding or {}
    company = branding.get("company_name") or "Client Dashboard"
    accent, accent_dark = theme["accent"], theme["accent_dark"]

    logo_tag = ""
    logo_bytes = branding.get("logo_bytes")
    if logo_bytes:
        ext = (branding.get("logo_name") or "logo.png").split(".")[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        b64 = base64.b64encode(logo_bytes).decode()
        logo_tag = (
            f'<img src="data:{mime};base64,{b64}" alt="logo" '
            f'style="height:54px;max-width:120px;object-fit:contain;'
            f'background:rgba(255,255,255,.18);border-radius:8px;padding:6px;" />'
        )

    _html_block(
        f'<div style="display:flex;align-items:center;gap:14px;'
        f'background:linear-gradient(135deg,{accent} 0%,{accent_dark} 100%);'
        f'border-radius:12px;padding:16px 20px;'
        f'box-shadow:0 12px 30px rgba(0,0,0,.15);font-family:Inter,Segoe UI,system-ui,sans-serif;">'
        f'{logo_tag}'
        f'<div>'
        f'<h3 style="margin:0;color:#fff;font-size:20px;font-weight:700;">{html_lib.escape(company)}</h3>'
        f'<p style="margin:8px 0 0;color:rgba(255,255,255,.92);font-size:14px;line-height:1.45;">'
        f'Theme: <strong>{html_lib.escape(theme_name)}</strong> &nbsp;|&nbsp; '
        f'Branded dashboard - change colors or logo anytime from the sidebar.</p>'
        f'</div></div>',
        height=108 if logo_bytes else 96,
    )


def render_ai_dashboard_brief(ai: dict, dashboard_config: dict, theme: dict) -> None:
    """Render the current AI narrative as a compact dashboard brief."""
    focus = dashboard_config.get("focus", "AI Recommended")
    insights = ai.get("key_insights", []) or []
    recommendations = ai.get("recommendations", []) or []
    anomalies = ai.get("anomalies", []) or []

    lead = ai.get("dataset_summary") or "The dashboard is ready for analysis."
    insight = insights[0] if insights else "No dominant insight has been detected yet."
    action = recommendations[0] if recommendations else "Use the generated pivots and charts to choose the next action."
    watch = anomalies[0] if anomalies else "No major anomaly was detected."

    html = f"""
    <div style="border:1px solid rgba(148,163,184,.26);border-left:5px solid {theme["accent"]};
        background:rgba(255,255,255,.92);border-radius:8px;padding:16px 18px;margin:.4rem 0 1rem;
        box-shadow:0 10px 26px rgba(15,23,42,.06);font-family:Inter,Segoe UI,system-ui,sans-serif;">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
                <div style="color:{theme["muted"]};font-size:11px;text-transform:uppercase;letter-spacing:.08em;">
                    AI dashboard focus
                </div>
                <h3 style="margin:5px 0 8px;color:{theme["ink"]};font-size:19px;">{html_lib.escape(focus)}</h3>
            </div>
            <span style="background:{theme["surface_soft"]};color:{theme["accent_dark"]};border-radius:999px;
                padding:5px 10px;font-size:12px;font-weight:700;">{html_lib.escape(ai.get("dataset_type", "general")).title()}</span>
        </div>
        <p style="margin:0 0 10px;color:{theme["ink"]};line-height:1.45;">{html_lib.escape(lead)}</p>
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;">
            <div><strong>Insight</strong><br><span style="color:{theme["muted"]};">{html_lib.escape(insight)}</span></div>
            <div><strong>Watch</strong><br><span style="color:{theme["muted"]};">{html_lib.escape(watch)}</span></div>
            <div><strong>Action</strong><br><span style="color:{theme["muted"]};">{html_lib.escape(action)}</span></div>
        </div>
    </div>
    """
    _html_block(html, height=320)


def _chart_key(chart: ChartSpec, index: int) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in chart.title).strip("_") or "chart"
    return f"plotly_{index}_{slug}"[:120]


def _prioritize_charts(charts: list[ChartSpec], focus: str | None) -> list[ChartSpec]:
    """Sort generated charts so the selected dashboard story appears first."""
    if not focus or focus == "AI Recommended":
        return charts

    focus_keywords = {
        "Executive Summary": ["trend", "top", "share"],
        "Sales / Revenue": ["top", "share", "monthly", "trend"],
        "Operations": ["distribution", "heatmap", "vs", "record count"],
        "Finance": ["monthly", "trend", "correlation", "distribution"],
    }
    keywords = focus_keywords.get(focus, [])
    if not keywords:
        return charts

    def score(item: tuple[int, ChartSpec]) -> tuple[int, int]:
        index, chart = item
        title = chart.title.lower()
        matches = sum(1 for word in keywords if word in title)
        return (-matches, index)

    return [chart for _, chart in sorted(enumerate(charts), key=score)]


def _apply_chart_sorting(charts: list[ChartSpec], chart_sort: str | None) -> list[ChartSpec]:
    if chart_sort == "Title (A-Z)":
        return sorted(charts, key=lambda c: c.title.lower())
    if chart_sort == "Title (Z-A)":
        return sorted(charts, key=lambda c: c.title.lower(), reverse=True)
    return charts


def _chart_download_buttons(chart: ChartSpec, index: int, enabled: bool = True) -> None:
    if not enabled or os.environ.get("EXCELMVP_SKIP_HEAVY_EXPORTS") == "1":
        return
    col_png, col_svg = st.columns(2)
    try:
        png_bytes = chart.figure.to_image(format="png", width=1600, height=920, scale=2)
        with col_png:
            st.download_button(
                "PNG",
                png_bytes,
                file_name=f"chart_{index + 1}.png",
                mime="image/png",
                key=f"download-png-{index}",
            )
    except Exception:
        with col_png:
            st.caption("PNG export unavailable")

    try:
        svg_bytes = chart.figure.to_image(format="svg", width=1600, height=920, scale=1)
        with col_svg:
            st.download_button(
                "SVG",
                svg_bytes,
                file_name=f"chart_{index + 1}.svg",
                mime="image/svg+xml",
                key=f"download-svg-{index}",
            )
    except Exception:
        with col_svg:
            st.caption("SVG export unavailable")


def render_charts(
    charts: list[ChartSpec],
    theme: dict | None = None,
    two_column: bool = True,
    max_charts: int | None = None,
    focus: str | None = None,
    dashboard_config: dict | None = None,
) -> None:
    """Render charts with themed accent bars; optional two-column layout."""
    if not charts:
        st.warning("No valid chart combinations were detected for this dataset.")
        return
    theme = theme or get_default_theme()
    dashboard_config = dashboard_config or {}
    palette = theme["palette"]
    template_name = dashboard_config.get("dashboard_template", st.session_state.get("dashboard_template", "Executive Dashboard"))
    template_defaults = DASHBOARD_TEMPLATE_PRESETS.get(template_name, DASHBOARD_TEMPLATE_PRESETS["Executive Dashboard"])
    effective_focus = focus or dashboard_config.get("focus") or str(template_defaults["focus"])
    effective_two_column = two_column if dashboard_config.get("dashboard_template") is None else bool(dashboard_config.get("two_column", template_defaults["two_column"]))
    effective_max = max_charts or int(dashboard_config.get("max_charts", template_defaults["max_charts"]))
    chart_height = int(dashboard_config.get("chart_height", template_defaults["height"]))
    show_downloads = bool(dashboard_config.get("show_chart_downloads", False))
    chart_sort = dashboard_config.get("chart_sort", "Relevance")

    charts = _prioritize_charts(charts, effective_focus)
    charts = _apply_chart_sorting(charts, chart_sort)
    charts = charts[:effective_max] if effective_max else charts

    def _draw(chart: ChartSpec, accent: str, index: int) -> None:
        _html_block(f'<div style="height:5px;background:{accent};border-radius:6px 6px 0 0;"></div>', height=12)
        chart.figure.update_layout(height=chart_height)
        st.plotly_chart(chart.figure, use_container_width=True, key=_chart_key(chart, index))
        _chart_download_buttons(chart, index, enabled=show_downloads)

    if not effective_two_column:
        for idx, chart in enumerate(charts):
            _draw(chart, palette[idx % len(palette)], idx)
        return

    for i in range(0, len(charts), 2):
        pair = charts[i : i + 2]
        cols = st.columns(2 if len(pair) == 2 else 1)
        for j, chart in enumerate(pair):
            idx = i + j
            with cols[j]:
                _draw(chart, palette[idx % len(palette)], idx)


def filter_dataframe(df: pd.DataFrame, column_types: dict[str, list[str]]) -> pd.DataFrame:
    """Render sidebar filters (category + date) and return the filtered data."""
    filtered = df.copy()
    st.sidebar.header("Filters")

    categorical = column_types.get("categorical", []) + column_types.get("boolean", [])
    for column in categorical[:8]:
        values = sorted([str(v) for v in filtered[column].dropna().unique()])[:250]
        if not values:
            continue
        selected = st.sidebar.multiselect(column, values, default=values)
        if selected:
            filtered = filtered[filtered[column].astype(str).isin(selected)]

    for column in column_types.get("datetime", [])[:3]:
        series = pd.to_datetime(filtered[column], errors="coerce").dropna()
        if series.empty:
            continue
        start, end = series.min().date(), series.max().date()
        picked = st.sidebar.date_input(column, value=(start, end), min_value=start, max_value=end)
        if isinstance(picked, tuple) and len(picked) == 2:
            filtered = filtered[
                (pd.to_datetime(filtered[column], errors="coerce").dt.date >= picked[0])
                & (pd.to_datetime(filtered[column], errors="coerce").dt.date <= picked[1])
            ]

    return filtered
