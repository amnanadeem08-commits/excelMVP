"""Enterprise Intelligent Widget Framework."""

from widgets.ai_adapter import AIInsight, WidgetAIAdapter
from widgets.base import BaseWidget
from widgets.canvas_bridge import DashboardWidgetBridge
from widgets.controller import WidgetController
from widgets.databinding import DataBinding, DatasetRegistry, default_binding, resolve_dataset
from widgets.events import EventBus, REQUIRED_EVENTS, WidgetEvent
from widgets.export_adapter import ExportResult, WidgetExportAdapter
from widgets.models import (
    COMPATIBILITY_VERSION,
    WIDGET_SCHEMA_VERSION,
    WidgetMetadata,
    WidgetPermissions,
    WidgetPlacement,
    WidgetState,
    WidgetStyle,
)
from widgets.registry import get_widget_class, list_widget_types, register_widget
from widgets.renderer import RenderContext, WidgetRenderer
from widgets.validators import validate_widget
from widgets.widget_factory import LEGACY_TYPE_MAP, WidgetFactory

# Ensure built-in widgets are registered on import.
import widgets.kpi  # noqa: F401

__all__ = [
    "AIInsight",
    "COMPATIBILITY_VERSION",
    "DashboardWidgetBridge",
    "DataBinding",
    "DatasetRegistry",
    "EventBus",
    "ExportResult",
    "LEGACY_TYPE_MAP",
    "REQUIRED_EVENTS",
    "RenderContext",
    "WIDGET_SCHEMA_VERSION",
    "WidgetAIAdapter",
    "WidgetController",
    "WidgetEvent",
    "WidgetExportAdapter",
    "WidgetFactory",
    "WidgetMetadata",
    "WidgetPermissions",
    "WidgetPlacement",
    "WidgetRenderer",
    "WidgetState",
    "WidgetStyle",
    "BaseWidget",
    "default_binding",
    "get_widget_class",
    "list_widget_types",
    "register_widget",
    "resolve_dataset",
    "validate_widget",
]
