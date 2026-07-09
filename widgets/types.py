"""Concrete widget type definitions."""

from __future__ import annotations

from widgets.base import BaseWidget


class KPIWidget(BaseWidget):
    widget_type = "kpi"


class ChartWidget(BaseWidget):
    widget_type = "chart"


class TableWidget(BaseWidget):
    widget_type = "table"


class PivotWidget(BaseWidget):
    widget_type = "pivot"


class TextWidget(BaseWidget):
    widget_type = "text"


class ImageWidget(BaseWidget):
    widget_type = "image"


class LogoWidget(BaseWidget):
    widget_type = "logo"


class DividerWidget(BaseWidget):
    widget_type = "divider"


class ShapeWidget(BaseWidget):
    widget_type = "shape"
