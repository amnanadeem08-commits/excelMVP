"""Widget registry and plugin registration."""

from __future__ import annotations

from typing import Type

from widgets.base import BaseWidget


_REGISTRY: dict[str, Type[BaseWidget]] = {}


def register_widget(widget_type: str, widget_cls: Type[BaseWidget]) -> None:
    _REGISTRY[widget_type] = widget_cls


def get_widget_class(widget_type: str) -> Type[BaseWidget]:
    if widget_type not in _REGISTRY:
        from widgets.base import BaseWidget as FallbackWidget

        return FallbackWidget
    return _REGISTRY[widget_type]


def list_widget_types() -> list[str]:
    return sorted(_REGISTRY.keys())


def is_registered(widget_type: str) -> bool:
    return widget_type in _REGISTRY
