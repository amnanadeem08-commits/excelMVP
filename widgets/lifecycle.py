"""Widget lifecycle hooks."""

from __future__ import annotations

from typing import Any, Protocol


class LifecycleContext(Protocol):
    widget_id: str
    render_target: str


class LifecycleHooks:
    """Extensible lifecycle contract for widgets and future plugins."""

    def initialize(self, context: dict[str, Any] | None = None) -> None:
        return None

    def before_render(self, context: dict[str, Any] | None = None) -> None:
        return None

    def after_render(self, context: dict[str, Any] | None = None) -> None:
        return None

    def before_export(self, context: dict[str, Any] | None = None) -> None:
        return None

    def after_export(self, context: dict[str, Any] | None = None) -> None:
        return None

    def before_delete(self, context: dict[str, Any] | None = None) -> None:
        return None

    def dispose(self, context: dict[str, Any] | None = None) -> None:
        return None
