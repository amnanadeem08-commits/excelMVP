from __future__ import annotations

import unittest

from canvas.grid import WidgetPlacement as CanvasPlacement
from widgets import (
    EventBus,
    WidgetController,
    WidgetFactory,
    WidgetRenderer,
    list_widget_types,
    register_widget,
)
from decision_intelligence import DecisionObject
from widgets.ai_adapter import WidgetAIAdapter
from widgets.base import BaseWidget
from widgets.databinding import DatasetRegistry, default_binding, resolve_dataset
from widgets.events import REQUIRED_EVENTS
from widgets.export_adapter import WidgetExportAdapter
from widgets.models import WidgetPlacement
from widgets.renderer import RenderContext
from widgets.types import ChartWidget, KPIWidget


class WidgetFrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        import pandas as pd

        self.df = pd.DataFrame({"revenue": [100, 200], "product": ["A", "B"]})
        self.registry = DatasetRegistry()
        self.registry.register("dataset-1", self.df)

    def test_builtin_registry_lists_core_widgets(self) -> None:
        types = list_widget_types()
        for expected in ("kpi", "chart", "table", "pivot", "text", "image", "logo", "divider", "shape"):
            self.assertIn(expected, types)

    def test_widget_factory_creates_typed_widget(self) -> None:
        widget = WidgetFactory.create("kpi", title="Revenue", dataset_id="dataset-1")
        self.assertIsInstance(widget, KPIWidget)
        self.assertEqual(widget.widget_type, "kpi")
        self.assertEqual(widget.data_binding.dataset_id, "dataset-1")

    def test_legacy_placement_maps_to_widget_type(self) -> None:
        placement = CanvasPlacement(
            widget_id="exec-kpis",
            widget_type="kpi_grid",
            col=0,
            row=1,
            col_span=12,
            row_span=2,
            metadata={"count": 2},
        )
        widget = WidgetFactory.from_legacy_placement(
            placement,
            legacy_type="kpi_grid",
            widget_id="exec-kpis",
            dataset_id="dataset-1",
            theme="Corporate Blue",
            mode_key="executive",
        )
        self.assertEqual(widget.widget_type, "kpi")
        self.assertEqual(widget.widget_metadata.legacy_type, "kpi_grid")

    def test_serialization_round_trip(self) -> None:
        widget = WidgetFactory.create(
            "chart",
            title="Revenue Trend",
            dataset_id="dataset-1",
            placement=WidgetPlacement(col=0, row=2, col_span=12, row_span=3),
        )
        restored = BaseWidget.from_dict(widget.to_dict())
        self.assertEqual(restored.widget_id, widget.widget_id)
        self.assertEqual(restored.widget_type, "chart")
        self.assertEqual(restored.placement.row_span, 3)

    def test_data_binding_resolves_without_storing_dataframe(self) -> None:
        binding = default_binding("dataset-1", columns=["revenue"])
        resolved = resolve_dataset(binding, self.registry)
        self.assertEqual(list(resolved.columns), ["revenue"])
        widget = WidgetFactory.create("table", dataset_id="dataset-1")
        self.assertNotIsInstance(widget.data_binding, type(self.df))

    def test_controller_lifecycle_and_visibility(self) -> None:
        bus = EventBus()
        events: list[str] = []
        bus.subscribe("*", lambda event: events.append(event.event_type))
        controller = WidgetController(bus)
        widget = controller.create_widget("text", title="Header", dataset_id="dataset-1")
        controller.set_visibility(widget.widget_id, False)
        controller.lock(widget.widget_id)
        self.assertFalse(controller.get(widget.widget_id).widget_state.visible)
        self.assertTrue(controller.get(widget.widget_id).widget_state.locked)
        self.assertIn("widget_created", events)
        self.assertIn("widget_visibility_changed", events)

    def test_required_events_exist(self) -> None:
        for event_name in REQUIRED_EVENTS:
            self.assertTrue(event_name.startswith("widget_"))

    def test_renderer_registers_all_widget_types(self) -> None:
        renderer = WidgetRenderer()
        builtin_types = ("kpi", "chart", "table", "pivot", "text", "image", "logo", "divider", "shape")
        for widget_type in builtin_types:
            widget = WidgetFactory.create(widget_type, dataset_id="dataset-1", title=widget_type)
            self.assertTrue(renderer.can_render(widget))

    def test_export_adapter_builds_payload(self) -> None:
        widget = WidgetFactory.create("kpi", title="Revenue", dataset_id="dataset-1")
        result = WidgetExportAdapter().export(widget, "pdf")
        self.assertEqual(result.widget_type, "kpi")
        self.assertIn("binding", result.payload)
        self.assertEqual(result.payload["target"], "pdf")

    def test_ai_adapter_exposes_capabilities(self) -> None:
        widget = WidgetFactory.create("chart", title="Trend", dataset_id="dataset-1")
        adapter = WidgetAIAdapter()
        adapter.set_context(artifacts={"_df_cache": self.df, "summary": {"rows": 2, "columns": 2}})
        insight = adapter.explain_widget(widget)
        decision = adapter.get_decision(widget)
        self.assertIsInstance(decision, DecisionObject)
        self.assertGreaterEqual(adapter.confidence_score(widget), 0.35)
        self.assertGreater(insight.confidence, 0.0)
        self.assertIn("decision_id", insight.metadata)

    def test_widget_validation_detects_missing_dataset(self) -> None:
        widget = WidgetFactory.create("table", title="Data")
        issues = widget.validate()
        self.assertTrue(any("dataset_id" in issue for issue in issues))

    def test_plugin_registration(self) -> None:
        class PluginWidget(BaseWidget):
            widget_type = "plugin_metric"

        register_widget("plugin_metric", PluginWidget)
        widget = WidgetFactory.create("plugin_metric", dataset_id="dataset-1")
        self.assertEqual(widget.widget_type, "plugin_metric")

    def test_lifecycle_hooks_are_callable(self) -> None:
        widget = WidgetFactory.create("divider", dataset_id="dataset-1")
        widget.before_render()
        widget.after_render()
        widget.before_export()
        widget.after_export()
        widget.before_delete()
        widget.dispose()


if __name__ == "__main__":
    unittest.main()
