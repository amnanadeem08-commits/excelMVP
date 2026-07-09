"""Widget controller: lifecycle and state only."""

from __future__ import annotations

from typing import Any

from widgets.base import BaseWidget
from widgets.events import EventBus
from widgets.models import utc_now
from widgets.widget_factory import WidgetFactory


class WidgetController:
    """Manage widget lifecycle without rendering logic."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self._widgets: dict[str, BaseWidget] = {}

    @property
    def widgets(self) -> list[BaseWidget]:
        return list(self._widgets.values())

    def get(self, widget_id: str) -> BaseWidget | None:
        return self._widgets.get(widget_id)

    def create_widget(self, widget_type: str, **kwargs: Any) -> BaseWidget:
        widget = WidgetFactory.create(widget_type, **kwargs)
        widget.initialize({"controller": True})
        self._widgets[widget.widget_id] = widget
        self.event_bus.emit("widget_created", widget.widget_id, widget_type=widget.widget_type)
        return widget

    def add_widget(self, widget: BaseWidget) -> BaseWidget:
        widget.initialize({"controller": True})
        self._widgets[widget.widget_id] = widget
        self.event_bus.emit("widget_created", widget.widget_id, widget_type=widget.widget_type)
        return widget

    def sync_from_widgets(self, widgets: list[BaseWidget]) -> None:
        self._widgets = {widget.widget_id: widget for widget in widgets}

    def update_widget(self, widget: BaseWidget) -> None:
        widget.touch()
        self._widgets[widget.widget_id] = widget
        self.event_bus.emit("widget_updated", widget.widget_id, widget_type=widget.widget_type)

    def delete_widget(self, widget_id: str) -> bool:
        widget = self._widgets.get(widget_id)
        if widget is None:
            return False
        widget.before_delete()
        del self._widgets[widget_id]
        widget.dispose()
        self.event_bus.emit("widget_deleted", widget_id, widget_type=widget.widget_type)
        return True

    def set_visibility(self, widget_id: str, visible: bool) -> bool:
        widget = self._widgets.get(widget_id)
        if widget is None:
            return False
        widget.widget_state.visible = visible
        widget.touch()
        self.event_bus.emit("widget_visibility_changed", widget_id, visible=visible)
        self.event_bus.emit("widget_updated", widget_id, visible=visible)
        return True

    def select_widget(self, widget_id: str | None) -> None:
        for widget in self._widgets.values():
            widget.widget_state.selected = widget.widget_id == widget_id
        if widget_id:
            self.event_bus.emit("widget_selected", widget_id)

    def lock(self, widget_id: str) -> bool:
        widget = self._widgets.get(widget_id)
        if widget is None:
            return False
        widget.widget_state.locked = True
        widget.touch()
        self.event_bus.emit("widget_updated", widget_id, locked=True)
        return True

    def unlock(self, widget_id: str) -> bool:
        widget = self._widgets.get(widget_id)
        if widget is None:
            return False
        widget.widget_state.locked = False
        widget.touch()
        self.event_bus.emit("widget_updated", widget_id, locked=False)
        return True

    def refresh(self, widget_id: str) -> bool:
        widget = self._widgets.get(widget_id)
        if widget is None:
            return False
        widget.widget_state.last_refresh = utc_now()
        widget.widget_state.dirty = False
        self.event_bus.emit("widget_refreshed", widget_id)
        self.event_bus.emit("widget_data_changed", widget_id)
        return True

    def refresh_all(self) -> int:
        count = 0
        for widget_id in list(self._widgets.keys()):
            if self.refresh(widget_id):
                count += 1
        return count
