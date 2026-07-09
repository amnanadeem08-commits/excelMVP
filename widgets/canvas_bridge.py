"""Bridge between canvas layout and widget framework."""

from __future__ import annotations

from typing import Any

import pandas as pd

from canvas.layout import DashboardLayout
from decision_intelligence.engine import DecisionIntelligenceEngine, get_default_engine
from decision_intelligence.integration import evaluate_dashboard_widgets
from widgets.ai_adapter import WidgetAIAdapter
from widgets.controller import WidgetController
from widgets.databinding import DatasetRegistry
from widgets.events import EventBus
from widgets.export_adapter import WidgetExportAdapter
from widgets.renderer import RenderContext, WidgetRenderer
from widgets.widget_factory import WidgetFactory


class DashboardWidgetBridge:
    """Orchestrate Workbook -> Canvas -> Widget Controller -> Renderer."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self.controller = WidgetController(self.event_bus)
        self.renderer = WidgetRenderer(self.event_bus)
        self.export_adapter = WidgetExportAdapter()
        self.decision_engine = get_default_engine()
        self.ai_adapter = WidgetAIAdapter(self.decision_engine)
        self.dataset_registry = DatasetRegistry()

    def build_from_layout(
        self,
        layout: DashboardLayout,
        *,
        dataset_id: str,
        dataframe: pd.DataFrame,
        theme: str,
        mode_key: str,
    ) -> list:
        self.dataset_registry.register(dataset_id, dataframe)
        widgets = WidgetFactory.from_canvas_layout(
            layout.widgets,
            dataset_id=dataset_id,
            theme=theme,
            mode_key=mode_key,
        )
        self.controller.sync_from_widgets(widgets)
        return widgets

    def render_dashboard(
        self,
        widgets: list,
        *,
        artifacts: dict[str, Any],
        theme: dict[str, Any] | None,
        dashboard_config: dict[str, Any] | None,
        grid_visible: bool = True,
    ) -> dict[str, Any]:
        context = RenderContext(
            dataset_registry=self.dataset_registry,
            artifacts=artifacts,
            theme=theme,
            dashboard_config=dashboard_config,
            grid_visible=grid_visible,
            render_target="dashboard",
        )
        self.renderer.render_many(widgets, context)
        return {
            "widget_count": len(widgets),
            "export_bundle": self.export_adapter.export_dashboard_bundle(widgets),
        }

    def explain_widget(self, widget_id: str):
        widget = self.controller.get(widget_id)
        if widget is None:
            return None
        return self.ai_adapter.explain_widget(widget)

    def evaluate_decisions(
        self,
        widgets: list,
        *,
        artifacts: dict[str, Any],
        dataframe: pd.DataFrame,
    ) -> list:
        self.ai_adapter.set_context(artifacts=artifacts)
        return evaluate_dashboard_widgets(
            widgets,
            artifacts=artifacts,
            dataframe=dataframe,
            engine=self.decision_engine,
        )

    def executive_decision_summary(self, decisions: list) -> str:
        return self.decision_engine.executive_summary(decisions)
