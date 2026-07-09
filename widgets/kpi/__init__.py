"""Register built-in widget types."""

from __future__ import annotations

from widgets.registry import register_widget
from widgets.types import (
    ChartWidget,
    DividerWidget,
    ImageWidget,
    KPIWidget,
    LogoWidget,
    PivotWidget,
    ShapeWidget,
    TableWidget,
    TextWidget,
)


def register_builtin_widgets() -> None:
    for widget_cls in (
        KPIWidget,
        ChartWidget,
        TableWidget,
        PivotWidget,
        TextWidget,
        ImageWidget,
        LogoWidget,
        DividerWidget,
        ShapeWidget,
    ):
        register_widget(widget_cls.widget_type, widget_cls)


register_builtin_widgets()
