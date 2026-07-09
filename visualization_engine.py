"""Reusable visualization engine for chart recommendation and rendering.

This module centralizes chart selection, chart construction, and figure theming.
It is designed as a backward-compatible upgrade for existing dashboard flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from analytics_engine import categorical_dimensions, numeric_measures

PLOTLY_TEMPLATE = "plotly_white"
VISUALIZATION_ENGINE_VERSION = "1.0.0"


@dataclass
class ChartSpec:
    """A titled Plotly figure ready to render or export."""

    title: str
    figure: Any
    chart_type: str = "unknown"


@dataclass(frozen=True)
class ChartRecommendation:
    """Recommendation returned by auto chart-selection logic."""

    chart_type: str
    reason: str
    priority: int


class VisualizationEngine:
    """Centralized chart engine for auto recommendations and chart generation."""

    def __init__(self, theme: dict, template_name: str | None = None):
        self.theme = theme
        self.template_name = template_name or "Executive Dashboard"

    def recommend(self, df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[ChartRecommendation]:
        """Recommend chart types based on dataset structure."""
        numeric_cols = numeric_measures(df, column_types)
        categorical_cols = categorical_dimensions(df, column_types)
        date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

        recommendations: list[ChartRecommendation] = []

        if categorical_cols and numeric_cols:
            many_categories = df[categorical_cols[0]].nunique(dropna=True) >= 9
            if many_categories:
                recommendations.append(ChartRecommendation("horizontal_bar", "Many categories are easier to read horizontally.", 100))
            else:
                recommendations.append(ChartRecommendation("bar", "Categorical vs numeric comparison suits a bar chart.", 100))

        if date_cols and numeric_cols:
            recommendations.append(ChartRecommendation("line", "Time vs numeric trend is best shown as a line chart.", 98))
            recommendations.append(ChartRecommendation("area", "Area chart highlights cumulative trend over time.", 90))

        if categorical_cols and numeric_cols and 2 <= df[categorical_cols[0]].nunique(dropna=True) <= 8:
            recommendations.append(ChartRecommendation("donut", "Part-to-whole composition is readable as a donut chart.", 92))
            recommendations.append(ChartRecommendation("pie", "Part-to-whole composition can also be shown as pie.", 88))

        if numeric_cols:
            recommendations.append(ChartRecommendation("histogram", "Numeric distribution is best shown in a histogram.", 95))
            recommendations.append(ChartRecommendation("box", "Box plot summarizes spread and outliers.", 89))
            recommendations.append(ChartRecommendation("gauge", "Gauge is useful for KPI progress visuals.", 72))

        if len(numeric_cols) >= 2:
            recommendations.append(ChartRecommendation("scatter", "Correlation between two numeric measures fits a scatter plot.", 94))
            recommendations.append(ChartRecommendation("correlation_matrix", "High-dimensional numeric data benefits from correlation matrix.", 91))
            recommendations.append(ChartRecommendation("heatmap", "Heatmap captures high-dimensional relationships.", 86))

        if categorical_cols and numeric_cols:
            recommendations.append(ChartRecommendation("treemap", "Hierarchical share view works well as treemap.", 83))
            recommendations.append(ChartRecommendation("funnel", "Stage-like descending values can be shown in a funnel.", 74))
            recommendations.append(ChartRecommendation("waterfall", "Waterfall helps explain contributions to total change.", 73))

        recommendations.append(ChartRecommendation("kpi_cards", "KPI cards provide executive snapshot metrics.", 80))
        recommendations.append(ChartRecommendation("table_view", "Table view supports exact value inspection.", 78))

        deduped: dict[str, ChartRecommendation] = {}
        for rec in sorted(recommendations, key=lambda item: item.priority, reverse=True):
            deduped.setdefault(rec.chart_type, rec)
        return list(deduped.values())

    def request_decision_for_recommendation(
        self,
        df: pd.DataFrame,
        recommendation: ChartRecommendation,
        *,
        widget_id: str = "",
        summary: dict | None = None,
    ) -> dict:
        """Request decision intelligence for a chart recommendation (no embedded business logic)."""
        from decision_intelligence.engine import get_default_engine
        from decision_intelligence.integration import build_source_from_chart

        source = build_source_from_chart(
            widget_id=widget_id or f"chart-{recommendation.chart_type}",
            title=f"{recommendation.chart_type.replace('_', ' ').title()} Chart",
            chart_type=recommendation.chart_type,
            reason=recommendation.reason,
            dataframe=df,
            summary=summary,
        )
        decision = get_default_engine().evaluate(source)
        return decision.to_dict()

    def build_auto_charts(
        self,
        df: pd.DataFrame,
        column_types: dict[str, list[str]],
        max_charts: int = 18,
    ) -> list[ChartSpec]:
        """Generate a diverse chart set using recommendation logic."""
        charts: list[ChartSpec] = []
        numeric_cols = numeric_measures(df, column_types)
        categorical_cols = categorical_dimensions(df, column_types)
        date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

        for date_col in date_cols[:2]:
            for measure in numeric_cols[:2]:
                monthly = (
                    df.assign(_month=pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp())
                    .dropna(subset=["_month"])
                    .groupby("_month", as_index=False)[measure]
                    .sum()
                    .sort_values("_month")
                )
                if len(monthly) < 2:
                    continue
                line = self._build_line(monthly, "_month", measure, f"Monthly {measure} Trend")
                area = self._build_area(monthly, "_month", measure, f"Monthly {measure} Area Trend")
                charts.extend([line, area])

        for cat in categorical_cols[:4]:
            for measure in numeric_cols[:2]:
                aggregated = df.groupby(cat, as_index=False)[measure].sum().sort_values(measure, ascending=False).head(12)
                if aggregated.empty:
                    continue

                if aggregated[cat].astype(str).str.len().median() > 14 or aggregated[cat].nunique(dropna=True) >= 9:
                    charts.append(self._build_horizontal_bar(aggregated, cat, measure, f"Top {cat} by {measure}"))
                else:
                    charts.append(self._build_bar(aggregated, cat, measure, f"Top {cat} by {measure}"))

                if 2 <= aggregated[cat].nunique(dropna=True) <= 8:
                    charts.append(self._build_donut(aggregated, cat, measure, f"{measure} Share by {cat}"))

                charts.append(self._build_treemap(aggregated, cat, measure, f"Treemap: {measure} by {cat}"))
                charts.append(self._build_funnel(aggregated, cat, measure, f"Funnel: {measure} by {cat}"))
                charts.append(self._build_waterfall(aggregated, cat, measure, f"Waterfall: {measure} by {cat}"))

        for measure in numeric_cols[:3]:
            if df[measure].nunique(dropna=True) > 5:
                charts.append(self._build_histogram(df, measure, f"{measure} Distribution"))
                charts.append(self._build_box(df, measure, f"{measure} Box Plot"))

        if len(numeric_cols) >= 2:
            x_col, y_col = numeric_cols[:2]
            sample = df[[x_col, y_col]].dropna()
            if len(sample) > 3000:
                sample = sample.sample(3000, random_state=42)
            if not sample.empty:
                charts.append(self._build_scatter(sample, x_col, y_col, f"{x_col} vs {y_col}"))

            corr = df[numeric_cols[:12]].corr(numeric_only=True)
            if not corr.empty:
                charts.append(self._build_heatmap(corr, "Heatmap"))
                charts.append(self._build_correlation_matrix(corr, "Correlation Matrix"))

        if numeric_cols:
            kpi_col = numeric_cols[0]
            charts.append(self._build_gauge(df, kpi_col, f"Gauge: {kpi_col}"))

        if numeric_cols:
            charts.append(self._build_kpi_cards(df, numeric_cols[:4], "KPI Cards"))

        charts.append(self._build_table_view(df.head(20), "Table View"))

        unique: dict[str, ChartSpec] = {}
        for chart in charts:
            if chart is None:
                continue
            unique.setdefault(f"{chart.chart_type}:{chart.title}", chart)
        return list(unique.values())[:max_charts]

    def apply_theme(self, charts: list[ChartSpec]) -> list[ChartSpec]:
        """Re-apply the current theme to a list of chart specs."""
        themed: list[ChartSpec] = []
        for chart in charts:
            chart.figure = self._format(chart.figure, chart.title)
            chart.figure = self._color_traces(chart.figure, chart.chart_type)
            themed.append(chart)
        return themed

    def _plotly_template(self) -> str:
        return "plotly_dark" if self.template_name == "Dark Dashboard" else PLOTLY_TEMPLATE

    def _format(self, fig: Any, title: str) -> Any:
        fig.update_layout(
            title=dict(text=title, font=dict(size=17, color=self.theme["ink"])),
            template=self._plotly_template(),
            height=430,
            margin=dict(l=20, r=20, t=60, b=30),
            hovermode="x unified",
            legend_title_text="",
            colorway=self.theme["palette"],
            paper_bgcolor="rgba(255,255,255,0.85)",
            plot_bgcolor="#ffffff",
            font=dict(color=self.theme["ink"], family="Inter, Segoe UI, system-ui, sans-serif"),
        )
        fig.update_xaxes(gridcolor="rgba(148,163,184,0.2)", linecolor="rgba(148,163,184,0.35)")
        fig.update_yaxes(gridcolor="rgba(148,163,184,0.2)", linecolor="rgba(148,163,184,0.35)")
        return fig

    def _color_traces(self, fig: Any, chart_type: str = "default") -> Any:
        palette = self.theme["palette"]
        accent = self.theme["accent"]
        for i, trace in enumerate(fig.data):
            color = palette[i % len(palette)]
            if trace.type in {"bar", "histogram", "waterfall", "funnel"}:
                if hasattr(trace, "marker") and trace.marker:
                    trace.marker.color = color if chart_type != "line" else accent
            elif trace.type in {"scatter", "scattergl"}:
                if getattr(trace, "mode", "") and "lines" in str(trace.mode):
                    trace.line.color = accent
                    if hasattr(trace, "marker") and trace.marker:
                        trace.marker.color = accent
                elif hasattr(trace, "marker") and trace.marker:
                    trace.marker.color = color
            elif trace.type in {"pie", "treemap"}:
                if hasattr(trace, "marker") and trace.marker:
                    trace.marker.colors = palette
            elif trace.type == "heatmap":
                fig.update_traces(colorscale=[[0, "#f8fafc"], [0.5, self.theme["accent"]], [1, self.theme["accent_dark"]]], selector=i)
        return fig

    def _build_line(self, df: pd.DataFrame, x: str, y: str, title: str) -> ChartSpec:
        fig = px.line(df, x=x, y=y, markers=True, labels={x: "Time"}, title=title, color_discrete_sequence=[self.theme["accent"]])
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "line"), chart_type="line")

    def _build_area(self, df: pd.DataFrame, x: str, y: str, title: str) -> ChartSpec:
        fig = px.area(df, x=x, y=y, title=title, color_discrete_sequence=[self.theme["accent"]])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "area"), chart_type="area")

    def _build_bar(self, df: pd.DataFrame, x: str, y: str, title: str) -> ChartSpec:
        fig = px.bar(df, x=x, y=y, title=title, text_auto=".2s", color=x, color_discrete_sequence=self.theme["palette"])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "bar"), chart_type="bar")

    def _build_horizontal_bar(self, df: pd.DataFrame, category: str, value: str, title: str) -> ChartSpec:
        ordered = df.sort_values(value, ascending=True)
        fig = px.bar(ordered, x=value, y=category, orientation="h", title=title, text_auto=".2s", color=category, color_discrete_sequence=self.theme["palette"])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "horizontal_bar"), chart_type="horizontal_bar")

    def _build_pie(self, df: pd.DataFrame, names: str, values: str, title: str) -> ChartSpec:
        fig = px.pie(df, names=names, values=values, title=title, color_discrete_sequence=self.theme["palette"])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "pie"), chart_type="pie")

    def _build_donut(self, df: pd.DataFrame, names: str, values: str, title: str) -> ChartSpec:
        fig = px.pie(df, names=names, values=values, hole=0.42, title=title, color_discrete_sequence=self.theme["palette"])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "donut"), chart_type="donut")

    def _build_scatter(self, df: pd.DataFrame, x: str, y: str, title: str) -> ChartSpec:
        fig = px.scatter(df, x=x, y=y, title=title, color_discrete_sequence=[self.theme["accent"]])
        fig.update_traces(marker=dict(color=self.theme["accent"], opacity=0.65, size=7))
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "scatter"), chart_type="scatter")

    def _build_histogram(self, df: pd.DataFrame, x: str, title: str) -> ChartSpec:
        fig = px.histogram(df, x=x, nbins=35, marginal="box", title=title, color_discrete_sequence=[self.theme["accent"]])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "histogram"), chart_type="histogram")

    def _build_box(self, df: pd.DataFrame, y: str, title: str) -> ChartSpec:
        fig = px.box(df, y=y, title=title, color_discrete_sequence=[self.theme["accent"]])
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "box"), chart_type="box")

    def _build_heatmap(self, matrix: pd.DataFrame, title: str) -> ChartSpec:
        fig = px.imshow(matrix, text_auto=".2f", aspect="auto", title=title)
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "heatmap"), chart_type="heatmap")

    def _build_correlation_matrix(self, matrix: pd.DataFrame, title: str) -> ChartSpec:
        fig = px.imshow(matrix, text_auto=".2f", aspect="auto", title=title)
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "correlation_matrix"), chart_type="correlation_matrix")

    def _build_treemap(self, df: pd.DataFrame, names: str, values: str, title: str) -> ChartSpec:
        fig = px.treemap(df, path=[names], values=values, title=title, color=values, color_continuous_scale="Blues")
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "treemap"), chart_type="treemap")

    def _build_waterfall(self, df: pd.DataFrame, categories: str, values: str, title: str) -> ChartSpec:
        limited = df.head(8)
        fig = go.Figure(
            go.Waterfall(
                name=title,
                orientation="v",
                measure=["relative"] * len(limited),
                x=limited[categories].astype(str),
                y=limited[values],
            )
        )
        fig.update_layout(title=title)
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "waterfall"), chart_type="waterfall")

    def _build_funnel(self, df: pd.DataFrame, categories: str, values: str, title: str) -> ChartSpec:
        limited = df.head(8)
        fig = go.Figure(go.Funnel(y=limited[categories].astype(str), x=limited[values]))
        fig.update_layout(title=title)
        return ChartSpec(title=title, figure=self._color_traces(self._format(fig, title), "funnel"), chart_type="funnel")

    def _build_gauge(self, df: pd.DataFrame, column: str, title: str) -> ChartSpec:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        value = float(series.mean()) if not series.empty else 0.0
        upper = float(series.max()) if not series.empty else max(value, 1.0)
        if upper <= 0:
            upper = 1.0
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=value,
                number={"font": {"size": 34}},
                gauge={
                    "axis": {"range": [0, upper]},
                    "bar": {"color": self.theme["accent"]},
                    "steps": [
                        {"range": [0, upper * 0.5], "color": "#e2e8f0"},
                        {"range": [upper * 0.5, upper], "color": "#cbd5e1"},
                    ],
                },
                title={"text": title},
            )
        )
        return ChartSpec(title=title, figure=self._format(fig, title), chart_type="gauge")

    def _build_kpi_cards(self, df: pd.DataFrame, columns: list[str], title: str) -> ChartSpec:
        values = []
        labels = []
        for col in columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            values.append(float(series.sum()) if not series.empty else 0.0)
            labels.append(col)

        fig = go.Figure()
        for idx, (label, value) in enumerate(zip(labels, values)):
            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=value,
                    title={"text": label},
                    number={"valueformat": ",.2f"},
                    domain={
                        "x": [idx / max(len(labels), 1), (idx + 1) / max(len(labels), 1)],
                        "y": [0, 1],
                    },
                )
            )
        fig.update_layout(title=title)
        return ChartSpec(title=title, figure=self._format(fig, title), chart_type="kpi_cards")

    def _build_table_view(self, df: pd.DataFrame, title: str) -> ChartSpec:
        fig = go.Figure(
            data=[
                go.Table(
                    header={"values": list(df.columns), "fill_color": self.theme["accent"], "font": {"color": "white"}},
                    cells={"values": [df[col] for col in df.columns], "fill_color": "#ffffff"},
                )
            ]
        )
        fig.update_layout(title=title, height=460)
        return ChartSpec(title=title, figure=self._format(fig, title), chart_type="table_view")
